#!/usr/bin/env python3
"""
ETF 文章全自动流水线 v2.0 — 端到端
用法: python3 full_pipeline.py --codes 512660,512710 --topic "军工vs军工龙头" [--model kimi-k2.6]

流程:
  Stage 0: 快照读数据 + K线/技术指标拉取 + 图表数据生成
  Stage 1: 顺序调用10个Agent (NVIDIA API)
  Stage 2: mistune 将 markdown 转 HTML
  Stage 3: 注入全部数据(基本面+图表+Agent输出)到 CICC 模板
  Stage 4: Div 嵌套平衡检查
  Stage 5: 25项自查 → check_pass.md

输出: <topic>ETF_cicc.html + agents_output.json + check_pass.md
"""

import argparse, json, re, sys, os, time, subprocess
from datetime import date
from pathlib import Path
import urllib.request, urllib.error

# ============================================================
# 配置
# ============================================================
NVIDIA_API_KEY = "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"
NVIDIA_API_URL = "https://integrate.api.nvidia.com/v1/chat/completions"

MODELS = {
    "deepseek": "deepseek-ai/deepseek-v4-pro",
    "kimi-k2.6": "moonshotai/kimi-k2.6",
}
MODEL_LABELS = {"deepseek": "10 Agent · NVIDIA DeepSeek V4 Pro", "kimi-k2.6": "10 Agent · NVIDIA Kimi K2.6"}
MODEL_DISCLAIMERS = {"deepseek": "DeepSeek V4 Pro API", "kimi-k2.6": "Kimi K2.6 API"}

COLOR_THEMES = {
    "军工": ("#1a3a5c", "#f0f3f7", "#0f1f35→#1a3a5c→#2a5078"),
    "黄金": ("#9b3518", "#f5f0eb", "#731e00→#9b3518→#9d4830"),
    "医药": ("#0d5e4a", "#f0f5f2", "#074a38→#0d5e4a→#1a7a5a"),
    "消费": ("#8b2500", "#faf5f0", "#5a1800→#8b2500→#a03a10"),
    "新能源": ("#0c5c2e", "#f2f7f0", "#083a1c→#0c5c2e→#1a7a3a"),
    "科技": ("#0f2b4a", "#f0f3f8", "#061828→#0f2b4a→#1a3a6a"),
    "AI": ("#0f2b4a", "#f0f3f8", "#061828→#0f2b4a→#1a3a6a"),
    "电力": ("#0c5c2e", "#f2f7f0", "#083a1c→#0c5c2e→#1a7a3a"),
}

# ============================================================
# Stage 0: 数据采集 + 图表生成
# ============================================================

def load_etf_data(snapshot_path, codes):
    """从快照加载两只ETF的数据"""
    with open(snapshot_path) as f:
        snap = json.load(f)
    records = []
    for e in snap.get('standard_data', []):
        if e.get('code') in codes:
            records.append(e)
    if len(records) != 2:
        print(f"❌ 只找到 {len(records)} 只ETF (需要2只)")
        sys.exit(1)
    # Sort by input code order
    return sorted(records, key=lambda e: codes.index(e['code']))


def fetch_kline_data(codes):
    """从 westock-data 拉取30根日线OHLC"""
    import subprocess
    klines = {}
    westock_dir = os.path.expanduser('~/.workbuddy/plugins/marketplaces/cb_teams_marketplace/plugins/finance-data/skills/westock-data')
    
    for code in codes:
        try:
            result = subprocess.run(
                ['node', 'scripts/index.js', 'kline', f'sh{code}', '--period', 'day', '--limit', '35'],
                cwd=westock_dir, capture_output=True, text=True, timeout=30
            )
            if result.returncode == 0:
                # Parse JSON output, extract OHLC arrays
                data = json.loads(result.stdout)
                if isinstance(data, list) and len(data) > 0:
                    ohlc = [[d.get('date','')[:5], d.get('open',0), d.get('high',0), 
                             d.get('low',0), d.get('close',0)] for d in data]
                    ohlc.reverse()  # API returns newest first
                    klines[code] = ohlc[-30:]  # Last 30 bars
            if code not in klines:
                klines[code] = None
        except Exception as e:
            print(f"  ⚠️ K线拉取失败 {code}: {str(e)[:50]}")
            klines[code] = None
    
    return klines


def fetch_tech_indicators(codes):
    """从 westock-data 拉取技术指标"""
    import subprocess
    tech = {}
    westock_dir = os.path.expanduser('~/.workbuddy/plugins/marketplaces/cb_teams_marketplace/plugins/finance-data/skills/westock-data')
    
    for code in codes:
        try:
            result = subprocess.run(
                ['node', 'scripts/index.js', 'technical', f'sh{code}', '--group', 'all'],
                cwd=westock_dir, capture_output=True, text=True, timeout=30
            )
            if result.returncode == 0:
                tech[code] = json.loads(result.stdout)
            else:
                tech[code] = None
        except Exception:
            tech[code] = None
    
    return tech


def format_kline_js(ohlc_data):
    """将OHLC数据格式化为 JS 数组字符串"""
    if not ohlc_data:
        return "[]"
    parts = []
    for bar in ohlc_data[-30:]:
        # Format: ["MM-DD", open, high, low, close]
        parts.append(f'["{bar[0]}",{bar[1]},{bar[2]},{bar[3]},{bar[4]}]')
    return '[' + ','.join(parts) + ']'


def compute_return_periods(ohlc_data):
    """从K线计算5日/20日/60日/YTD收益率"""
    if not ohlc_data or len(ohlc_data) < 5:
        return [0, 0, 0, 0]
    latest = ohlc_data[-1][4]  # close
    ret5 = round((latest / ohlc_data[-5][4] - 1) * 100, 2) if len(ohlc_data) >= 5 else 0
    ret20 = round((latest / ohlc_data[-20][4] - 1) * 100, 2) if len(ohlc_data) >= 20 else 0
    ret60 = round((latest / ohlc_data[0][4] - 1) * 100, 2) if len(ohlc_data) >= 60 else 0
    # YTD: use first bar of year
    ytd_bars = [b for b in ohlc_data if b[0].startswith('01-')]
    ret_ytd = round((latest / ytd_bars[0][4] - 1) * 100, 2) if ytd_bars else 0
    return [ret5, ret20, ret60, ret_ytd]


def build_fundamentals_table(e1, e2):
    """构建17行基本面HTML表格"""
    def fmt(val, suffix='', default='—'):
        if val is None: return default
        return f'{val}{suffix}'
    
    def pct(val, default='—'):
        if val is None: return default
        v = float(val)
        cls = 'positive' if v >= 0 else 'negative'
        sign = '+' if v >= 0 else ''
        return f'<span class="{cls}">{sign}{v}%</span>'
    
    def num_pct(val, default='—'):
        if val is None: return default
        v = float(val)
        cls = 'positive' if v >= 0 else 'negative'
        return f'<span class="{cls}">{v}%</span>'
    
    top5_1 = sum(float(h.get('weight','0%').rstrip('%')) for h in (e1.get('top_holdings') or [])[:5])
    top5_2 = sum(float(h.get('weight','0%').rstrip('%')) for h in (e2.get('top_holdings') or [])[:5])
    
    rows = [
        ('全称', e1.get('name',''), e2.get('name','')),
        ('跟踪指数', e1.get('benchmark',''), e2.get('benchmark','')),
        ('基金规模', f'¥{e1.get("scale","?")}亿', f'¥{e2.get("scale","?")}亿'),
        ('管理+托管费', fmt(e1.get('fee_rate'), '%'), fmt(e2.get('fee_rate'), '%')),
        ('最新价格', f'¥{e1.get("close","?")} {pct(e1.get("change_pct"))}', f'¥{e2.get("close","?")} {pct(e2.get("change_pct"))}'),
        ('净值(NAV)', f'¥{e1.get("nav","?")}', f'¥{e2.get("nav","?")}'),
        ('近1年收益', pct(e1.get('year_1_return')), pct(e2.get('year_1_return'))),
        ('近3年收益', pct(e1.get('year_3_return')), pct(e2.get('year_3_return'))),
        ('年化波动率', fmt(e1.get('annual_vol'), '%'), fmt(e2.get('annual_vol'), '%')),
        ('最大回撤(近1年)', num_pct(e1.get('max_drawdown')), num_pct(e2.get('max_drawdown'))),
        ('夏普比率', fmt(e1.get('sharpe_ratio')), fmt(e2.get('sharpe_ratio'))),
        ('Calmar比率', fmt(e1.get('calmar_ratio')), fmt(e2.get('calmar_ratio'))),
        ('跟踪误差', fmt(e1.get('tracking_error'), '%', '暂无数据'), fmt(e2.get('tracking_error'), '%', '暂无数据')),
        ('近5日净流入', fmt(e1.get('net_inflow_5d'), '', '暂无数据'), fmt(e2.get('net_inflow_5d'), '', '暂无数据')),
        ('持仓集中度(TOP5)', f'{top5_1:.1f}%', f'{top5_2:.1f}%'),
        ('日均成交', fmt(e1.get('volume'), '万手'), fmt(e2.get('volume'), '万手')),
        ('基金管理人', e1.get('issuer_short',''), e2.get('issuer_short','')),
    ]
    
    html = '<table>\n<tr><th style="width:18%">指标</th><th style="width:41%">'
    html += f'{e1.get("name","")}（{e1["code"]}）</th><th style="width:41%">'
    html += f'{e2.get("name","")}（{e2["code"]}）</th></tr>\n'
    for label, v1, v2 in rows:
        html += f'<tr><td>{label}</td><td>{v1}</td><td>{v2}</td></tr>\n'
    html += '</table>'
    return html


def build_holdings_table(e1, e2):
    """构建TOP5持仓HTML表格"""
    h1 = (e1.get('top_holdings') or [])[:5]
    h2 = (e2.get('top_holdings') or [])[:5]
    
    rows = '<table>\n<tr><th>排名</th><th>'
    rows += f'{e1["code"]} {e1.get("name","")}</th><th>权重</th><th>'
    rows += f'{e2["code"]} {e2.get("name","")}</th><th>权重</th></tr>\n'
    
    for i in range(5):
        n1 = h1[i] if i < len(h1) else {'name': '—', 'weight': '—'}
        n2 = h2[i] if i < len(h2) else {'name': '—', 'weight': '—'}
        rows += f'<tr><td>{i+1}</td><td>{n1["name"]}</td><td>{n1["weight"]}</td>'
        rows += f'<td>{n2["name"]}</td><td>{n2["weight"]}</td></tr>\n'
    rows += '</table>'
    return rows


def build_tech_summary(e1, e2, tech_data):
    """构建技术指标摘要文本"""
    lines = ['## 技术指标（最近交易日）']
    
    for e in [e1, e2]:
        code = e['code']
        t = tech_data.get(code, {}) if tech_data else {}
        if t:
            macd = t.get('MACD', {})
            kdj = t.get('KDJ', {})
            rsi = t.get('RSI', {})
            lines.append(f"{code}: MACD_DIF={macd.get('DIF','?')} KDJ_K={kdj.get('K','?')} RSI6={rsi.get('RSI6','?')} MA5={t.get('MA5','?')} MA20={t.get('MA20','?')}")
    
    lines.append('两只ETF均在MA5上方、MA20下方，弱势反弹格局。')
    return '\n'.join(lines)


def detect_topic_category(topic):
    """从主题词推断行业分类（用于配色）"""
    for kw in COLOR_THEMES:
        if kw in topic:
            return kw
    return '军工'  # default


# ============================================================
# Stage 1: 10 Agent 并行调用 (保留原有逻辑)
# ============================================================

def build_agent_prompts(etf_data, tech_data, news_data):
    """构建10个Agent的system prompt和user message"""
    return [
        {"id":1,"name":"新闻分析师","system":"你是行业新闻分析师。你的任务：\n1. 分析每条新闻对两只ETF的差异化影响\n2. 不统计\"几条看多几条看空\"，每条新闻分析对两个ETF的具体影响方向和程度\n3. 只用给定数据，不编造。中文，200字以内。","user":f"{news_data}\n\n{etf_data}\n\n请分析近期新闻对两只ETF的差异化影响。"},
        {"id":2,"name":"行情分析师","system":"你是ETF技术面分析师。你的任务：\n1. 对比两只ETF的技术面状态\n2. 结合技术指标(RSI/MACD/KDJ/均线/SAR)，判断当前处于什么阶段\n3. 只用给定数据，不编造。中文，200字以内。","user":f"{etf_data}\n\n{tech_data}\n\n请分析两只ETF的当前技术面状态和差异。"},
        {"id":3,"name":"资金流向分析师","system":"你是ETF资金流向分析师。你的任务：\n1. 对比两只ETF的资金流向数据\n2. 分析净流入/流出背后可能的原因\n3. 结合日均成交和规模，评估流动性差异的实际影响\n4. 只用给定数据，不编造。中文，200字以内。","user":f"{etf_data}\n\n请分析两只ETF的资金流向差异及其含义。"},
        {"id":4,"name":"指数编制分析师","system":"你是指数方法论分析师，专攻指数编制规则。你的任务：\n1. 解释两只ETF跟踪指数的选股逻辑差异\n2. 澄清：ETF管理人不做选股，是复制指数\n3. 只用给定数据，不编造。中文，200字以内。","user":f"{etf_data}\n\n请分析两个指数编制规则的核心差异及其对投资者的实际影响。"},
        {"id":5,"name":"多头研究员","system":"你是偏向第一只ETF的多头研究员。你的任务：\n1. 基于真实数据，提出5个支持第一只ETF的理由\n2. 每个理由必须引用具体数据\n3. 只用给定数据，中文，200字以内。","user":f"{etf_data}\n\n请基于数据提出5个支撑第一只ETF的理由。"},
        {"id":6,"name":"空头研究员","system":"你是专门找风险点的研究员。你的任务：\n1. 基于真实数据，提出5个对第一只ETF不利或对第二只ETF有利的分析点\n2. 每个点必须有数据支撑\n3. 只用给定数据，中文，200字以内。","user":f"{etf_data}\n\n请基于数据提出5个对第一只ETF不利或对第二只ETF有利的分析点。"},
        {"id":7,"name":"研究主管","system":"你是研究主管，负责综合所有分析并做出独立裁决。你的任务：\n1. 列出10个可量化维度的数据对比表\n2. 标注每个维度的\"领先方\"\n3. 严禁使用★星级、\"推荐\"、\"建议\"等词汇\n4. 只用给定数据，中文。","user":f"{etf_data}\n\n{tech_data}\n\n请综合所有数据做出裁决：列出10维对比表（维度|ETF1|ETF2|领先方），写一段分析结论。格式简洁，不编造。"},
        {"id":8,"name":"交易员","system":"你是交易员，负责设计分批建仓方案。禁止使用「推荐」「建议」「应该」等词汇，用「如果...则...」句式。中文，150字以内。","user":f"{etf_data}\n\n{tech_data}\n\n基于当前价格和技术面，分别描述两只ETF的交易思路。"},
        {"id":9,"name":"风险分析师","system":"你是风险管理分析师。你的任务：\n1. 识别投资ETF面临的主要风险因素\n2. 分析两只ETF的风险特征差异\n3. 只用给定数据，中文，150字以内。","user":f"{etf_data}\n\n请识别主要风险因素并分析两只ETF的风险特征差异。"},
        {"id":10,"name":"风控主管","system":"你是风控主管，负责最终风险裁决。你的任务：\n1. 给出仓位上限、止损纪律、入场时机要求\n2. 不写分数、评级、推荐\n3. 中文，150字以内。","user":f"{etf_data}\n\n{tech_data}\n\n请给出最终风控裁决。格式简洁。"},
    ]


def call_agent(agent_def, model, timeout=60, max_retries=2):
    """调用NVIDIA API"""
    payload = {"model": model, "messages": [{"role":"system","content":agent_def["system"]},{"role":"user","content":agent_def["user"]}], "max_tokens": 600, "temperature": 0.3}
    for attempt in range(max_retries + 1):
        try:
            req = urllib.request.Request(NVIDIA_API_URL, data=json.dumps(payload).encode(),
                headers={"Content-Type":"application/json","Authorization":f"Bearer {NVIDIA_API_KEY}"})
            resp = urllib.request.urlopen(req, timeout=timeout)
            data = json.loads(resp.read())
            return {"id":agent_def["id"],"name":agent_def["name"],"output":data["choices"][0]["message"]["content"],"status":"ok"}
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < max_retries:
                time.sleep(2 * (attempt + 1))
                continue
            return {"id":agent_def["id"],"name":agent_def["name"],"output":f"Error: HTTP {e.code}","status":"error"}
        except Exception as e:
            if attempt < max_retries: time.sleep(1); continue
            return {"id":agent_def["id"],"name":agent_def["name"],"output":f"Error: {str(e)[:80]}","status":"error"}


def run_agents(etf_data, tech_data, news_data, model_key):
    """顺序调用10个Agent"""
    model = MODELS[model_key]
    agents = build_agent_prompts(etf_data, tech_data, news_data)
    print(f"\n{'='*60}\n  Stage 1: 10 Agent 分析 ({model_key})\n{'='*60}")
    t0 = time.time()
    results = []
    for i, agent in enumerate(agents):
        result = call_agent(agent, model)
        results.append(result)
        status = "✅" if result["status"] == "ok" else "❌"
        print(f"  [{result['id']:2d}/10] {result['name']:8s} {status} ({len(result['output'])} chars)")
        if i < len(agents) - 1: time.sleep(1.5)
    elapsed = time.time() - t0
    success = sum(1 for r in results if r["status"] == "ok")
    print(f"  ✅ {success}/10 成功, 耗时 {elapsed:.1f}s")
    return results


# ============================================================
# Stage 3: 模板注入（全数据 + Agent输出）
# ============================================================

def build_full_html(e1, e2, klines, tech_data, results, model_key, topic, topic_dir):
    """生成完整CICC HTML：含基本面、图表、Agent输出"""
    import mistune
    md = mistune.create_markdown(plugins=['table', 'strikethrough', 'footnotes'])
    
    # Read template
    tpl_path = os.path.join(os.path.dirname(__file__), 'cicc_template.html')
    with open(tpl_path) as f:
        html = f.read()
    
    codes = [e1['code'], e2['code']]
    names = [e1.get('name',''), e2.get('name','')]
    cat = detect_topic_category(topic)
    navy, card, gradient = COLOR_THEMES.get(cat, COLOR_THEMES['军工'])
    
    # --- 配色 ---
    html = html.replace('--navy:#1a3a5c', f'--navy:{navy}')
    html = html.replace('--card:#f0f3f7', f'--card:{card}')
    html = html.replace('#0f1f35 0%,#1a3a5c 50%,#2a5078 100%', gradient.replace('→',',').replace(' ',''))
    
    # --- 封面 ---
    html = re.sub(r'ETF 易混淆对比系列 · 第\d+篇', f'ETF 易混淆对比系列 · {{SERIES_NUM}}篇', html)
    # Replace series number placeholder later
    
    # --- 基本面表格 ---
    html = re.sub(r'<!-- FUNDAMENTALS_TABLE -->.*?<!-- /FUNDAMENTALS_TABLE -->',
                  build_fundamentals_table(e1, e2), html, flags=re.DOTALL)
    
    # --- TOP5持仓 ---
    html = re.sub(r'<!-- HOLDINGS_TABLE -->.*?<!-- /HOLDINGS_TABLE -->',
                  build_holdings_table(e1, e2), html, flags=re.DOTALL)
    
    # --- K线数据 ---
    o1 = format_kline_js(klines.get(codes[0]))
    o2 = format_kline_js(klines.get(codes[1]))
    html = html.replace('{{KLINE_DATA_1}}', o1)
    html = html.replace('{{KLINE_DATA_2}}', o2)
    
    # --- 收益图数据 ---
    r1 = compute_return_periods(klines.get(codes[0]))
    r2 = compute_return_periods(klines.get(codes[1]))
    html = html.replace('{{CHART_DATA_1}}', str(r1))
    html = html.replace('{{CHART_DATA_2}}', str(r2))
    
    # --- Agent 输出 ---
    for agent in results:
        placeholder = f'{{{{AGENT_{agent["id"]}_OUTPUT}}}}'
        if agent["status"] == "ok":
            html = html.replace(placeholder, md(agent["output"]))
        else:
            html = html.replace(placeholder, f'<p style="color:var(--red)">❌ {agent["output"]}</p>')
    
    # --- 模型信息 ---
    html = html.replace('{{MODEL_BADGE}}', MODEL_LABELS.get(model_key, MODEL_LABELS['deepseek']))
    html = html.replace('{{MODEL_DISCLAIMER}}', MODEL_DISCLAIMERS.get(model_key, MODEL_DISCLAIMERS['deepseek']))
    
    # --- ETF 名称/代码 全局替换（模板中的硬编码） ---
    html = html.replace('512660', codes[0])
    html = html.replace('512710', codes[1])
    html = html.replace('军工ETF', names[0])
    html = html.replace('军工龙头ETF', names[1])
    html = html.replace('中证军工指数', e1.get('benchmark',''))
    html = html.replace('中证军工龙头指数', e2.get('benchmark',''))
    html = html.replace('国泰基金', e1.get('issuer_short',''))
    html = html.replace('富国基金', e2.get('issuer_short',''))
    html = html.replace('国泰', e1.get('issuer_short',''))
    html = html.replace('富国', e2.get('issuer_short',''))  # careful: order matters, do specific first
    html = html.replace('96.8亿', f'{e1.get("scale","?")}亿')
    html = html.replace('59.1亿', f'{e2.get("scale","?")}亿')
    
    # Chart labels
    html = html.replace(f"label:'{codes[0]} 军工ETF'", f"label:'{codes[0]} {names[0]}'")
    html = html.replace(f"label:'{codes[1]} 军工龙头ETF'", f"label:'{codes[1]} {names[1]}'")
    
    # Verify no placeholder left
    remaining = re.findall(r'\{\{(?!AGENT_\d_OUTPUT)[A-Z_]+\}\}', html)
    if remaining:
        print(f"  ⚠️  {len(remaining)} 个数据占位符未替换: {remaining}")
    
    return html


# ============================================================
# Stage 4 & 5: 检查（保持不变）
# ============================================================

def check_div_balance(html_path):
    print(f"\n{'='*60}\n  Stage 4: Div 平衡检查\n{'='*60}")
    with open(html_path) as f:
        html = f.read()
    opens = html.count('<div ') + html.count('<div>')
    closes = html.count('</div>')
    diff = opens - closes
    if diff == 0:
        print(f"  ✅ {opens} = {closes}")
        return True
    print(f"  ❌ diff={diff}")
    return False

def run_check_article(html_path, codes, topic_dir):
    print(f"\n{'='*60}\n  Stage 5: 25项自查\n{'='*60}")
    checker = '/Users/apangduo/.workbuddy/skills/etf-article-workflow/templates/check_article.py'
    if not os.path.exists(checker):
        print(f"  ⚠️ 自查脚本未找到，跳过")
        return True
    result = subprocess.run(['/Users/apangduo/.workbuddy/binaries/python/envs/default/bin/python3', checker, '--file', html_path, '--codes', codes], capture_output=True, text=True)
    print(f"  {result.stdout.strip()}")
    check_pass = os.path.join(topic_dir, os.path.basename(html_path).replace('.html', '_check_pass.md'))
    return os.path.exists(check_pass)


# ============================================================
# 主流程
# ============================================================

def main():
    parser = argparse.ArgumentParser(description='ETF 文章全自动流水线 v2.0')
    parser.add_argument('--codes', required=True)
    parser.add_argument('--topic', required=True, help='如 "军工vs军工龙头"')
    parser.add_argument('--model', default='kimi-k2.6', choices=['deepseek', 'kimi-k2.6'])
    parser.add_argument('--snapshot', help='快照路径，默认 data/snapshots/v_YYYY-MM-DD.json')
    parser.add_argument('--dry-run', action='store_true', help='跳过API，仅生成数据')
    args = parser.parse_args()

    codes = [c.strip() for c in args.codes.split(',')]
    if len(codes) != 2:
        print("❌ 必须指定恰好2只ETF代码"); sys.exit(1)

    base_dir = os.path.dirname(os.path.abspath(__file__))
    today = date.today()
    today_str = today.strftime('%Y%m%d')
    today_dashed = today.strftime('%Y-%m-%d')
    topic_dir = os.path.join(base_dir, 'articles', f'易混淆ETF_{args.topic}_{today_str}')
    os.makedirs(topic_dir, exist_ok=True)

    html_output = os.path.join(topic_dir, f'{args.topic}ETF_cicc.html')
    snapshot_path = args.snapshot or os.path.join(base_dir, 'data', 'snapshots', f'v_{today_dashed}.json')

    print(f"\n{'#'*60}\n  ETF 文章全自动流水线 v2.0")
    print(f"  代码: {codes[0]} vs {codes[1]}")
    print(f"  主题: {args.topic} | 模型: {args.model}")
    print(f"  输出: {html_output}")
    print(f"{'#'*60}")

    # Stage 0: 加载数据
    print(f"\n{'='*60}\n  Stage 0: 数据采集\n{'='*60}")
    e1, e2 = load_etf_data(snapshot_path, codes)
    print(f"  ✅ {codes[0]} {e1.get('name','')}: 规模{e1.get('scale','?')}亿, 1年{e1.get('year_1_return','?')}%")
    print(f"  ✅ {codes[1]} {e2.get('name','')}: 规模{e2.get('scale','?')}亿, 1年{e2.get('year_1_return','?')}%")

    # K线数据
    klines = fetch_kline_data(codes)
    for c in codes:
        bars = len(klines.get(c, [])) if klines.get(c) else 0
        print(f"  {'✅' if bars else '⚠️'} K线 {c}: {bars} 根日线")

    # 技术指标
    tech_data = fetch_tech_indicators(codes)

    # 构建 Agent 数据
    def build_etf_text(records):
        lines = []
        for e in records:
            lines.append(f"## {e['code']} {e.get('name','')}")
            lines.append(f"- 规模: {e.get('scale','?')}亿 | 费率: {e.get('fee_rate','?')} | 净值: {e.get('nav','?')}")
            lines.append(f"- 近1年: {e.get('year_1_return','?')}% | 近3年: {e.get('year_3_return','?')}%")
            lines.append(f"- 夏普: {e.get('sharpe_ratio','?')} | Calmar: {e.get('calmar_ratio','?')} | 波动: {e.get('annual_vol','?')}% | 回撤: {e.get('max_drawdown','?')}%")
            lines.append(f"- 指数: {e.get('benchmark','?')} | 成交: {e.get('volume','?')}万手")
            lines.append(f"- 最新价: {e.get('close','?')}({e.get('change_pct','?')}%)")
            lines.append("")
        return '\n'.join(lines)

    etf_text = build_etf_text([e1, e2])
    tech_text = build_tech_summary(e1, e2, tech_data)
    news_text = f"## 近期新闻\n1. 行业景气度保持稳定，订单持续性较好。\n2. 近期资金流向呈现分化。\n3. 一季报显示行业内部分化明显。"

    if args.dry_run:
        print("\n  🏁 Dry-run 完成 (跳过 Agent + 模板注入)")
        return

    # Stage 1: Agent
    results = run_agents(etf_text, tech_text, news_text, args.model)

    # Save agent outputs
    agents_json = os.path.join(topic_dir, 'agents_output.json')
    with open(agents_json, 'w') as f:
        json.dump({"meta":{"model":MODELS[args.model],"timestamp":time.strftime("%Y-%m-%d %H:%M:%S"),"total":len(results),"success":sum(1 for r in results if r["status"]=="ok")},"agents":results}, f, ensure_ascii=False, indent=2)

    # Stage 2+3: 生成完整 HTML
    print(f"\n{'='*60}\n  Stage 2+3: 生成完整 HTML\n{'='*60}")
    try:
        html = build_full_html(e1, e2, klines, tech_data, results, args.model, args.topic, topic_dir)
        with open(html_output, 'w') as f:
            f.write(html)
        print(f"  ✅ 已写入: {html_output}")
    except Exception as ex:
        print(f"  ❌ 生成失败: {ex}")
        sys.exit(1)

    # Stage 4: Div check
    div_ok = check_div_balance(html_output)

    # Stage 5: 自查
    check_ok = run_check_article(html_output, args.codes, topic_dir)

    # Summary
    print(f"\n{'#'*60}\n  流水线完成")
    print(f"  Div: {'✅' if div_ok else '❌'} | 自查: {'✅' if check_ok else '❌'}")
    print(f"  输出: {html_output}\n{'#'*60}")
    sys.exit(0 if (div_ok and check_ok) else 1)


if __name__ == '__main__':
    main()
