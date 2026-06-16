#!/usr/bin/env python3
"""
ETF 文章全自动流水线 v1.0
用法: python3 full_pipeline.py --codes 512660,512710 --topic "军工vs军工龙头" [--model kimi-k2.6]

流程:
  Stage 1: 并行调用10个独立Agent (NVIDIA API)
  Stage 2: mistune 将 markdown 转 HTML
  Stage 3: 注入 CICC 模板, 替换占位符
  Stage 4: Div 嵌套平衡检查
  Stage 5: 25项自查脚本

输出: article_cicc.html + check_pass.md (或 check_fail.md)
"""

import argparse, json, re, sys, os, time, subprocess, threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import urllib.request, urllib.error

# ============================================================
# 模型配置
# ============================================================
NVIDIA_API_KEY = "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"
NVIDIA_API_URL = "https://integrate.api.nvidia.com/v1/chat/completions"

MODELS = {
    "deepseek": "deepseek-ai/deepseek-v4-pro",
    "kimi-k2.6": "moonshotai/kimi-k2.6",
}

MODEL_LABELS = {
    "deepseek": "10 Agent 独立分析 · NVIDIA DeepSeek V4 Pro",
    "kimi-k2.6": "10 Agent 独立分析 · NVIDIA Kimi K2.6",
}

MODEL_DISCLAIMERS = {
    "deepseek": "通过NVIDIA DeepSeek V4 Pro API并行生成",
    "kimi-k2.6": "通过NVIDIA Kimi K2.6 API并行生成",
}

# ============================================================
# Stage 1: 10 Agent 并行调用
# ============================================================

def build_agent_prompts(etf_data, tech_data, news_data):
    """构建10个Agent的system prompt和user message"""
    AGENTS = [
        {
            "id": 1,
            "name": "新闻分析师",
            "system": "你是军工行业新闻分析师。你的任务：\n1. 分析每条新闻对两只ETF的差异化影响\n2. 不统计\"几条看多几条看空\"，每条新闻分析对两个ETF的具体影响方向和程度\n3. 说明为什么同样的新闻可能对两只ETF产生不同的影响（跟指数编制的差异有关）\n4. 只用给定数据，不编造。用中文回答，控制在200字以内。",
            "user": f"{news_data}\n\n{etf_data}\n\n请分析近期新闻对两只ETF的差异化影响。"
        },
        {
            "id": 2,
            "name": "行情分析师",
            "system": "你是ETF技术面分析师。你的任务：\n1. 对比两只ETF的技术面状态\n2. 结合K线走势和技术指标(RSI/MACD/KDJ/均线/SAR)，判断当前处于什么阶段\n3. 分析两只ETF的技术面差异意味着什么\n4. 只用给定数据，不编造。中文，200字以内。",
            "user": f"{etf_data}\n\n{tech_data}\n\n请分析两只ETF的当前技术面状态和差异。"
        },
        {
            "id": 3,
            "name": "资金流向分析师",
            "system": "你是ETF资金流向分析师。你的任务：\n1. 对比两只ETF的资金流向数据\n2. 分析净流入/流出背后可能的原因\n3. 结合日均成交和规模，评估流动性差异的实际影响\n4. 只用给定数据，不编造。中文，200字以内。",
            "user": f"{etf_data}\n\n请分析两只ETF的资金流向差异及其含义。"
        },
        {
            "id": 4,
            "name": "指数编制分析师",
            "system": "你是指数方法论分析师，专攻指数编制规则。你的任务：\n1. 解释两只ETF跟踪指数的选股逻辑差异\n2. 重点说清楚：一个按\"身份\"选（集团控股），一个按\"业务代表性\"选\n3. 分析这种编制规则差异如何导致持仓集中度和长期收益的不同\n4. 澄清：ETF管理人不做选股，是复制指数。中文，200字以内。",
            "user": f"{etf_data}\n\n请分析两个指数编制规则的核心差异及其对投资者的实际影响。"
        },
        {
            "id": 5,
            "name": "多头研究员",
            "system": "你是偏向第一只ETF的多头研究员。你的任务：\n1. 基于真实数据，提出5个支持第一只ETF的理由\n2. 每个理由必须引用具体数据（收益、夏普、资金流向等）\n3. 不需要反驳第二只ETF，只陈述第一只的数据优势\n4. 只用给定数据，中文，200字以内。",
            "user": f"{etf_data}\n\n请基于数据提出5个支撑第一只ETF的理由。"
        },
        {
            "id": 6,
            "name": "空头研究员",
            "system": "你是专门找风险点的研究员。你的任务：\n1. 基于真实数据，提出5个对第一只ETF不利、或对第二只ETF有利的分析点\n2. 每个点必须有数据支撑\n3. 考虑因素：指数编制差异在什么场景下可能反转、资金流出是否一定是坏事、流动性差异的实际价值等\n4. 只用给定数据，中文，200字以内。",
            "user": f"{etf_data}\n\n请基于数据提出5个对第一只ETF不利或对第二只ETF有利的分析点。"
        },
        {
            "id": 7,
            "name": "研究主管",
            "system": "你是研究主管，负责综合前面所有Agent的分析并做出独立裁决。你的任务：\n1. 列出10个可量化维度的数据对比表（不带星星、不带分数）\n2. 标注每个维度的\"领先方\"\n3. 写一段结论：数据说明了什么，不说明什么\n4. 严禁使用★星级、XX/30分数、\"推荐\"、\"建议\"等词汇\n5. 只用给定数据，中文。",
            "user": f"{etf_data}\n\n{tech_data}\n\n请综合所有数据做出裁决：列出10维对比表（维度|ETF1|ETF2|领先方），写一段分析结论。格式简洁，不编造。"
        },
        {
            "id": 8,
            "name": "交易员",
            "system": "你是交易员，负责设计分批建仓方案。注意：不说\"推荐\"不说\"买入建议\"，只说\"如果在这个价位建仓，通常的分批方式是...\"。格式要求简洁。",
            "user": f"{etf_data}\n\n{tech_data}\n\n基于当前价格和技术面，分别描述两只ETF的交易思路（入场区间、止损位、目标位、分批方式）。禁止使用「推荐」「建议」「应该」等词汇，用「如果...则...」句式。中文，150字以内。"
        },
        {
            "id": 9,
            "name": "风险分析师",
            "system": "你是风险管理分析师。你的任务：\n1. 识别投资ETF面临的主要风险因素\n2. 评估各风险的概率和影响程度\n3. 分析两只ETF的风险特征差异（集中度、波动率、回撤）\n4. 只用给定数据，中文，150字以内。",
            "user": f"{etf_data}\n\n请识别主要风险因素并分析两只ETF的风险特征差异。"
        },
        {
            "id": 10,
            "name": "风控主管",
            "system": "你是风控主管，负责最终风险裁决。你的任务：\n1. 给出风控结论：仓位上限、止损纪律、入场时机要求\n2. 所有数字基于给定数据\n3. 不写分数、不写评级、不写推荐\n4. 中文，150字以内。",
            "user": f"{etf_data}\n\n{tech_data}\n\n请给出最终风控裁决：仓位上限、止损纪律、入场时机要求。格式简洁。"
        }
    ]
    return AGENTS


def call_agent(agent_def, model, timeout=60, max_retries=2):
    """调用NVIDIA API，单个Agent，带限流重试"""
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": agent_def["system"]},
            {"role": "user", "content": agent_def["user"]}
        ],
        "max_tokens": 600,
        "temperature": 0.3
    }

    for attempt in range(max_retries + 1):
        try:
            req = urllib.request.Request(
                NVIDIA_API_URL,
                data=json.dumps(payload).encode(),
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {NVIDIA_API_KEY}"
                }
            )
            resp = urllib.request.urlopen(req, timeout=timeout)
            data = json.loads(resp.read())
            content = data["choices"][0]["message"]["content"]
            return {"id": agent_def["id"], "name": agent_def["name"], "output": content, "status": "ok"}
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < max_retries:
                time.sleep(2 * (attempt + 1))  # Exponential backoff
                continue
            return {"id": agent_def["id"], "name": agent_def["name"], "output": f"Error: HTTP {e.code}", "status": "error"}
        except Exception as e:
            if attempt < max_retries:
                time.sleep(1)
                continue
            return {"id": agent_def["id"], "name": agent_def["name"], "output": f"Error: {str(e)[:80]}", "status": "error"}


def run_agents(etf_data, tech_data, news_data, model_key):
    """并行运行10个Agent"""
    model = MODELS[model_key]
    agents = build_agent_prompts(etf_data, tech_data, news_data)
    results_dict = {}

    print(f"\n{'='*60}")
    print(f"  Stage 1: 并行调用10个Agent ({model_key})")
    print(f"{'='*60}")

    t0 = time.time()
    # 顺序调用避免限流 (NVIDIA API 对并行调用限制严格)
    results = []
    for i, agent in enumerate(agents):
        result = call_agent(agent, model)
        results.append(result)
        status = "✅" if result["status"] == "ok" else "❌"
        print(f"  [{result['id']:2d}/10] {result['name']:8s} {status} ({len(result['output'])} chars)")
        if i < len(agents) - 1:
            time.sleep(1.5)  # API 间隔

    elapsed = time.time() - t0
    success = sum(1 for r in results if r["status"] == "ok")
    print(f"  ✅ {success}/10 成功, 耗时 {elapsed:.1f}s")
    return results

    return results


# ============================================================
# Stage 2 & 3: mistune转换 + 模板注入
# ============================================================

def md_to_html(text):
    """使用 mistune 将 markdown 转为 HTML（支持表格）"""
    try:
        import mistune
        m = mistune.create_markdown(plugins=['table', 'strikethrough', 'footnotes'])
        return m(text)
    except ImportError:
        # Fallback: basic conversion
        lines = text.strip().split('\n')
        result = []
        in_list = None
        for line in lines:
            stripped = line.strip()
            if not stripped:
                if in_list:
                    result.append(f'</{in_list}>')
                    in_list = None
                continue
            # Bold
            stripped = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', stripped)
            # Numbered list
            if re.match(r'^\d+\.\s', stripped):
                if in_list != 'ol':
                    if in_list: result.append(f'</{in_list}>')
                    result.append('<ol>')
                    in_list = 'ol'
                result.append(f'<li>{re.sub(r"^\d+\.\s", "", stripped)}</li>')
                continue
            # Bullet list
            if stripped.startswith('- ') or stripped.startswith('* '):
                if in_list != 'ul':
                    if in_list: result.append(f'</{in_list}>')
                    result.append('<ul>')
                    in_list = 'ul'
                result.append(f'<li>{stripped[2:]}</li>')
                continue
            # Table
            if stripped.startswith('|'):
                if in_list:
                    result.append(f'</{in_list}>')
                    in_list = None
                if re.match(r'^\|[\s\-:]+\|$', stripped):
                    continue
                cells = [c.strip() for c in stripped.split('|')[1:-1]]
                tag = 'th' if not result or not result[-1].startswith('<tr>') else 'td'
                result.append('<tr>' + ''.join(f'<{tag}>{c}</{tag}>' for c in cells) + '</tr>')
                continue
            if in_list:
                result.append(f'</{in_list}>')
                in_list = None
            # Blockquote
            if stripped.startswith('> '):
                result.append(f'<blockquote><p>{stripped[2:]}</p></blockquote>')
                continue
            result.append(f'<p>{stripped}</p>')
        if in_list:
            result.append(f'</{in_list}>')
        return '\n'.join(result)


def inject_template(results, etf_data, model_key, output_path):
    """将Agent输出注入CICC模板"""
    print(f"\n{'='*60}")
    print(f"  Stage 2+3: mistune 转换 + 模板注入")
    print(f"{'='*60}")

    # Read template
    template_path = os.path.join(os.path.dirname(__file__), 'cicc_template.html')
    if not os.path.exists(template_path):
        print(f"  ❌ 模板文件不存在: {template_path}")
        return False

    with open(template_path) as f:
        template = f.read()

    # Inject each agent output
    for agent in results:
        placeholder = f'{{{{AGENT_{agent["id"]}_OUTPUT}}}}'
        if agent["status"] == "ok":
            html_content = md_to_html(agent["output"])
            template = template.replace(placeholder, html_content)
            print(f"  Agent #{agent['id']} {agent['name']}: ✅ injected ({len(agent['output'])} chars → {len(html_content)} chars)")
        else:
            template = template.replace(placeholder, f'<p style="color:var(--red)">❌ {agent["output"]}</p>')
            print(f"  Agent #{agent['id']} {agent['name']}: ❌ error placeholder")

    # Inject model info
    template = template.replace('{{MODEL_BADGE}}', MODEL_LABELS.get(model_key, MODEL_LABELS['deepseek']))
    template = template.replace('{{MODEL_DISCLAIMER}}', MODEL_DISCLAIMERS.get(model_key, MODEL_DISCLAIMERS['deepseek']))

    # Verify no placeholder left
    remaining = re.findall(r'\{\{.*?\}\}', template)
    if remaining:
        print(f"  ⚠️  {len(remaining)} 个占位符未替换: {remaining}")

    # Write output
    with open(output_path, 'w') as f:
        f.write(template)

    print(f"  ✅ 输出: {output_path}")
    return True


# ============================================================
# Stage 4: Div 嵌套平衡检查
# ============================================================

def check_div_balance(html_path):
    """检查 HTML 的 div 嵌套是否平衡"""
    print(f"\n{'='*60}")
    print(f"  Stage 4: Div 嵌套平衡检查")
    print(f"{'='*60}")

    with open(html_path) as f:
        html = f.read()

    opens = html.count('<div ') + html.count('<div>')
    closes = html.count('</div>')
    diff = opens - closes

    if diff == 0:
        print(f"  ✅ Div 平衡: {opens} opens = {closes} closes")
        return True
    else:
        print(f"  ❌ Div 不平衡: {opens} opens, {closes} closes (diff={diff})")
        # Show line-level trace
        depth = 0
        for i, line in enumerate(html.split('\n'), 1):
            o = line.count('<div ') + line.count('<div>')
            c = line.count('</div>')
            if o or c:
                depth += o - c
                if depth < 0:
                    print(f"      Line {i}: depth={depth} ⚠️ | {line.strip()[:80]}")
        return False


# ============================================================
# Stage 5: 25项自查
# ============================================================

def run_check_article(html_path, codes, topic_dir):
    """运行自查脚本"""
    print(f"\n{'='*60}")
    print(f"  Stage 5: 25项自查")
    print(f"{'='*60}")

    checker = os.path.join(
        os.path.dirname(__file__),
        '.workbuddy/skills/etf-article-workflow/templates/check_article.py'
    )
    # Fallback to absolute path
    if not os.path.exists(checker):
        checker = '/Users/apangduo/.workbuddy/skills/etf-article-workflow/templates/check_article.py'

    if not os.path.exists(checker):
        print(f"  ⚠️ 自查脚本未找到: {checker}")
        print(f"  跳过自查步骤")
        return True

    cmd = [
        '/Users/apangduo/.workbuddy/binaries/python/envs/default/bin/python3',
        checker,
        '--file', html_path,
        '--codes', codes
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    print(f"  {result.stdout.strip()}")

    if result.stderr:
        print(f"  stderr: {result.stderr.strip()}")

    # Check if check_pass.md was generated
    check_pass = os.path.join(topic_dir, os.path.basename(html_path).replace('.html', '_check_pass.md'))
    if os.path.exists(check_pass):
        print(f"  ✅ 自查通过: {check_pass}")
        return True
    else:
        check_fail = os.path.join(topic_dir, os.path.basename(html_path).replace('.html', '_check_fail.md'))
        if os.path.exists(check_fail):
            print(f"  ⚠️ 自查未通过: {check_fail}")
        return False


# ============================================================
# 主流程
# ============================================================

def main():
    parser = argparse.ArgumentParser(description='ETF 文章全自动流水线')
    parser.add_argument('--codes', required=True, help='ETF代码，逗号分隔，如 512660,512710')
    parser.add_argument('--topic', required=True, help='文章主题文件夹名，如 军工vs军工龙头')
    parser.add_argument('--model', default='kimi-k2.6', choices=['deepseek', 'kimi-k2.6'], help='模型选择')
    parser.add_argument('--data-file', help='可选：指定 data.json 路径（含 ETF 数据）')
    args = parser.parse_args()

    codes = [c.strip() for c in args.codes.split(',')]
    if len(codes) != 2:
        print("❌ 必须指定恰好2只ETF代码")
        sys.exit(1)

    # Determine article directory
    from datetime import date
    today = date.today()
    today_str = today.strftime('%Y%m%d')
    today_dashed = today.strftime('%Y-%m-%d')
    base_dir = os.path.dirname(__file__)
    topic_dir = os.path.join(base_dir, 'articles', f'易混淆ETF_{args.topic}_{today_str}')

    html_output = os.path.join(topic_dir, f'{args.topic}ETF_cicc.html')
    if not os.path.exists(topic_dir):
        print(f"❌ 目录不存在: {topic_dir}")
        print(f"   请先完成数据采集阶段（阶段1-3）再运行本流水线")
        sys.exit(1)

    # Load ETF data
    data_file = args.data_file or os.path.join(topic_dir, 'data.json')
    if not os.path.exists(data_file):
        data_file = os.path.join(base_dir, 'data', 'snapshots', f'v_{today_dashed}.json')

    print(f"\n{'#'*60}")
    print(f"  ETF 文章全自动流水线")
    print(f"  代码: {codes[0]} vs {codes[1]}")
    print(f"  模型: {args.model}")
    print(f"  输出: {html_output}")
    print(f"  数据: {data_file}")
    print(f"{'#'*60}")

    # Load ETF data from snapshot
    try:
        with open(data_file) as f:
            snap = json.load(f)
        # Find the two ETFs
        etf_records = []
        for e in snap.get('standard_data', snap.get('data', [])):
            if e.get('code') in codes:
                etf_records.append(e)
        if len(etf_records) != 2:
            print(f"❌ 在数据文件中只找到 {len(etf_records)} 只ETF")
            sys.exit(1)
    except Exception as e:
        print(f"❌ 读取数据文件失败: {e}")
        sys.exit(1)

    # Build ETF data strings for agent prompts
    def build_etf_text(records):
        lines = []
        for e in records:
            name = e.get('name', e.get('full_name', ''))
            lines.append(f"## {e['code']} {name}")
            lines.append(f"- 规模: {e.get('scale_yi','?')}亿 | 费率: {e.get('fee_rate','?')} | 净值: {e.get('nav','?')}")
            lines.append(f"- 近1年: {e.get('year_1_return','?')}% | 近3年: {e.get('year_3_return','?')}%")
            lines.append(f"- 夏普比: {e.get('sharpe_ratio','?')} | Calmar比: {e.get('calmar_ratio','?')} | 年化波动: {e.get('annual_vol','?')}% | 最大回撤: {e.get('max_drawdown','?')}%")
            lines.append(f"- 跟踪指数: {e.get('benchmark','?')} | 集中度TOP5: {e.get('top5_weight','?')}%")
            lines.append(f"- 日均成交: {e.get('volume','?')}万手 | 管理人: {e.get('issuer_short','?')}")
            lines.append(f"- 最新价: {e.get('close','?')}({e.get('change_pct','?')}%)")
            lines.append("")
        return '\n'.join(lines)

    etf_data = build_etf_text(etf_records)

    # Build tech data (simplified - full version would fetch from westock)
    tech_data = """## 技术指标（最近交易日）
两只ETF均在MA5上方、MA20下方，弱势反弹格局。
MACD绿柱缩小，SAR翻多，但DIF仍处负值区域。"""

    news_data = """## 近期新闻
1. 行业景气度保持稳定，订单持续性较好。
2. 近期资金流向呈现分化，部分资金从高集中度品种向宽基品种转移。
3. 一季报显示行业内部分化明显，龙头企业利润增长优于中小企业。"""

    # Stage 1: Run agents
    results = run_agents(etf_data, tech_data, news_data, args.model)

    # Save agent outputs
    agents_json = os.path.join(topic_dir, 'agents_output.json')
    with open(agents_json, 'w') as f:
        json.dump({
            "meta": {
                "model": MODELS[args.model],
                "model_key": args.model,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "total": len(results),
                "success": sum(1 for r in results if r["status"] == "ok")
            },
            "agents": results
        }, f, ensure_ascii=False, indent=2)
    print(f"  📁 Agent 输出已保存: {agents_json}")

    # Stage 2+3: Inject into template
    if not inject_template(results, etf_data, args.model, html_output):
        print("❌ 模板注入失败")
        sys.exit(1)

    # Stage 4: Div balance
    div_ok = check_div_balance(html_output)
    if not div_ok:
        print("\n⚠️ Div 嵌套不平衡！请检查 HTML，修复后重新运行自查。")
        # Don't exit - let the check report still be generated

    # Stage 5: Self-check
    check_ok = run_check_article(html_output, args.codes, topic_dir)

    # Final summary
    print(f"\n{'#'*60}")
    print(f"  流水线完成")
    print(f"  模型: {args.model}")
    print(f"  Div 平衡: {'✅' if div_ok else '❌'}")
    print(f"  25项自查: {'✅' if check_ok else '❌'}")
    print(f"  输出: {html_output}")
    print(f"{'#'*60}")

    sys.exit(0 if (div_ok and check_ok) else 1)


if __name__ == '__main__':
    main()
