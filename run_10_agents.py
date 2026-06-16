#!/usr/bin/env python3
"""
真·10 Agent 并行分析脚本
每个Agent使用独立的system prompt，只接收自己领域的数据，独立产出分析。
用法: python3 run_10_agents.py
输出: agents_output.json (10个Agent的完整分析结果)
"""

import json, time, sys

API_KEY = "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"
API_URL = "https://integrate.api.nvidia.com/v1/chat/completions"
MODEL = "deepseek-ai/deepseek-v4-pro"

# ============================================================
# ETF 数据（从真实API采集）
# ============================================================
ETF_DATA = """
## 512660 国泰中证军工ETF
- 规模: 96.8亿 | 费率: 0.60% | 净值: 1.28
- 近1年: +37.37% | 近3年: +26.01% | YTD: 暂缺
- 夏普比: 1.14 | Calmar比: 1.49 | 年化波动: 30.27% | 最大回撤: -25.15%
- 跟踪误差: 0.05%(Wind) | 跟踪指数: 中证军工指数(399967)
- 持仓TOP5: 中国船舶8.48% 航发动力4.04% 航天电子3.70% 光启技术3.65% 中国卫星3.05% (集中度22.9%)
- 近5日净流入: +0.11% | 日均成交: 250万手 | 管理人: 国泰基金 | 上市: 2016-08-08
- 最新价: 1.267(+1.61%)
- 指数编制: 十大军工集团控股+主营业务涉军, 约80只成分股

## 512710 富国中证军工龙头ETF
- 规模: 59.1亿 | 费率: 0.60% | 净值: 0.69
- 近1年: +29.26% | 近3年: +7.44% | YTD: 暂缺
- 夏普比: 0.88 | Calmar比: 1.15 | 年化波动: 33.27% | 最大回撤: -25.54%
- 跟踪误差: 0.05%(Wind) | 跟踪指数: 中证军工龙头指数(931066)
- 持仓TOP5: 航发动力9.47% 航天电子8.68% 中国卫星7.18% 中航光电6.35% 中航沈飞6.18% (集中度37.9%)
- 近5日净流入: -1.35% | 日均成交: 490万手 | 管理人: 富国基金 | 上市: 2019-08-26
- 最新价: 0.676(-1.74%)
- 指数编制: 从军工业务+军转民业务中精选30家代表性公司
"""

TECH_DATA = """
## 技术指标（最近交易日）
512660: MACD_DIF=-0.036 MACD柱=+0.001(绿柱缩小) KDJ_K=51.17 KDJ_J=82.28 RSI6=53.22 CCI14=13.03 SAR=1.203 MA5=1.244 MA20=1.289 价格在SAR上方
512710: MACD_DIF=-0.025 MACD柱=+0.001(绿柱缩小) KDJ_K=45.47 KDJ_J=70.45 RSI6=46.47 CCI14=-16.87 SAR=0.645 MA5=0.667 MA20=0.696 价格在SAR上方
两只ETF均在MA5上方、MA20下方，弱势反弹格局。
"""

NEWS_DATA = """
## 近期新闻
1. 2026年国防支出预算增速维持7.2%，连续三年高于GDP增速。
2. 国际局势持续紧张，中国军工出口份额提升。
3. 军工企业一季报分化：龙头订单饱满，中小企业利润承压。
4. 北向资金近两周减持军工板块，但内资军工ETF份额逆势增长。
"""

# ============================================================
# 10个Agent的定义
# ============================================================
AGENTS = [
    {
        "id": 1,
        "name": "新闻分析师",
        "system": """你是军工行业新闻分析师。你的任务：
1. 分析每条新闻对512660（中证军工指数ETF）和512710（中证军工龙头ETF）的差异化影响
2. 不统计"几条看多几条看空"，每条新闻分析对两个ETF的具体影响方向和程度
3. 说明为什么同样的新闻可能对两只ETF产生不同的影响（跟指数编制的差异有关）
4. 只用给定数据，不编造。用中文回答，控制在200字以内。""",
        "user": f"{NEWS_DATA}\n\n{ETF_DATA.split('## 512710')[0]}\n\n请分析近期新闻对两只ETF的差异化影响。"
    },
    {
        "id": 2,
        "name": "行情分析师",
        "system": """你是ETF技术面分析师。你的任务：
1. 对比512660和512710的技术面状态
2. 结合K线走势和技术指标(RSI/MACD/KDJ/均线/SAR)，判断当前处于什么阶段
3. 分析两只ETF的技术面差异意味着什么
4. 只用给定数据，不编造。中文，200字以内。""",
        "user": f"{ETF_DATA}\n\n{TECH_DATA}\n\n请分析两只ETF的当前技术面状态和差异。"
    },
    {
        "id": 3,
        "name": "资金流向分析师",
        "system": """你是ETF资金流向分析师。你的任务：
1. 对比两只ETF的资金流向数据
2. 分析净流入/流出背后可能的原因
3. 结合日均成交和规模，评估流动性差异的实际影响
4. 只用给定数据，不编造。中文，200字以内。""",
        "user": f"{ETF_DATA}\n\n请分析两只ETF的资金流向差异及其含义。"
    },
    {
        "id": 4,
        "name": "指数编制分析师",
        "system": """你是指数方法论分析师，专攻指数编制规则。你的任务：
1. 解释中证军工指数(399967)和中证军工龙头指数(931066)的选股逻辑差异
2. 重点说清楚：一个按"身份"选（集团控股），一个按"业务代表性"选
3. 分析这种编制规则差异如何导致持仓集中度和长期收益的不同
4. 澄清：ETF管理人不做选股，是复制指数。中文，200字以内。""",
        "user": f"{ETF_DATA}\n\n请分析两个指数编制规则的核心差异及其对投资者的实际影响。"
    },
    {
        "id": 5,
        "name": "多头研究员",
        "system": """你是偏向512660（中证军工指数ETF）的多头研究员。你的任务：
1. 基于真实数据，提出5个支持512660的理由
2. 每个理由必须引用具体数据（收益、夏普、资金流向等）
3. 不需要反驳512710，只陈述512660的数据优势
4. 只用给定数据，中文，200字以内。""",
        "user": f"{ETF_DATA}\n\n请基于数据提出5个支撑512660的理由。"
    },
    {
        "id": 6,
        "name": "空头研究员",
        "system": """你是专门找风险点的研究员。你的任务：
1. 基于真实数据，提出5个对512660不利、或对512710有利的分析点
2. 每个点必须有数据支撑
3. 考虑因素：指数编制差异在什么场景下可能反转、资金流出是否一定是坏事、流动性差异的实际价值等
4. 只用给定数据，中文，200字以内。""",
        "user": f"{ETF_DATA}\n\n请基于数据提出5个对512660不利或对512710有利的分析点。"
    },
    {
        "id": 7,
        "name": "研究主管",
        "system": """你是研究主管，负责综合前面所有Agent的分析并做出独立裁决。你的任务：
1. 列出10个可量化维度的数据对比表（不带星星、不带分数）
2. 标注每个维度的"领先方"
3. 写一段结论：数据说明了什么，不说明什么
4. 严禁使用★星级、XX/30分数、"推荐"、"建议"等词汇
5. 只用给定数据，中文。""",
        "user": f"{ETF_DATA}\n\n{TECH_DATA}\n\n请综合所有数据做出裁决：列出10维对比表（维度|512660|512710|领先方），写一段分析结论。格式简洁，不编造。"
    },
    {
        "id": 8,
        "name": "交易员",
        "system": """你是交易员，负责设计分批建仓方案。注意：不说"推荐"不说"买入建议"，只说"如果在这个价位建仓，通常的分批方式是..."。格式要求简洁。""",
        "user": f"{ETF_DATA}\n\n{TECH_DATA}\n\n基于当前价格和技术面，分别描述512660和512710的交易思路（入场区间、止损位、目标位、分批方式）。禁止使用「推荐」「建议」「应该」等词汇，用「如果...则...」句式。中文，150字以内。"
    },
    {
        "id": 9,
        "name": "风险分析师",
        "system": """你是风险管理分析师。你的任务：
1. 识别投资军工ETF面临的主要风险因素
2. 评估各风险的概率和影响程度
3. 分析两只ETF的风险特征差异（集中度、波动率、回撤）
4. 只用给定数据，中文，150字以内。""",
        "user": f"{ETF_DATA}\n\n请识别主要风险因素并分析两只ETF的风险特征差异。"
    },
    {
        "id": 10,
        "name": "风控主管",
        "system": """你是风控主管，负责最终风险裁决。你的任务：
1. 给出风控结论：仓位上限、止损纪律、入场时机要求
2. 所有数字基于给定数据
3. 不写分数、不写评级、不写推荐
4. 中文，150字以内。""",
        "user": f"{ETF_DATA}\n\n{TECH_DATA}\n\n请给出最终风控裁决：仓位上限、止损纪律、入场时机要求。格式简洁。"
    }
]


def call_agent(agent_def, timeout=45):
    """调用NVIDIA API，单个Agent"""
    import urllib.request
    
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": agent_def["system"]},
            {"role": "user", "content": agent_def["user"]}
        ],
        "max_tokens": 600,
        "temperature": 0.3
    }
    
    req = urllib.request.Request(
        API_URL,
        data=json.dumps(payload).encode(),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {API_KEY}"
        }
    )
    
    try:
        resp = urllib.request.urlopen(req, timeout=timeout)
        data = json.loads(resp.read())
        content = data["choices"][0]["message"]["content"]
        return {"id": agent_def["id"], "name": agent_def["name"], "output": content, "status": "ok"}
    except Exception as e:
        return {"id": agent_def["id"], "name": agent_def["name"], "output": f"Error: {str(e)[:100]}", "status": "error"}


# ============================================================
# 主流程
# ============================================================
if __name__ == "__main__":
    from concurrent.futures import ThreadPoolExecutor, as_completed
    
    total = len(AGENTS)
    results_dict = {}
    
    # 并行调用，保持ID顺序输出
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(call_agent, agent): agent for agent in AGENTS}
        for f in as_completed(futures):
            result = f.result()
            results_dict[result["id"]] = result
            status = "✅" if result["status"] == "ok" else "❌"
            print(f"[{result['id']}/{total}] Agent #{result['id']} {result['name']} ... {status} ({len(result['output'])} chars)")
    
    # 按ID排序
    results = [results_dict[i] for i in sorted(results_dict.keys())]
    
    # 保存结果
    output = {
        "meta": {
            "model": MODEL,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "total": len(results),
            "success": sum(1 for r in results if r["status"] == "ok")
        },
        "agents": results
    }
    
    out_path = "/Users/apangduo/WorkBuddy/Claw/etf-tool-mvp/articles/易混淆ETF_军工vs军工龙头_20260616/agents_output.json"
    with open(out_path, "w") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ 完成: {output['meta']['success']}/{total} 成功")
    print(f"📁 输出: {out_path}")
    
    # 打印摘要
    print("\n=== Agent输出摘要 ===")
    for r in results:
        preview = r["output"][:120].replace("\n", " ")
        print(f"  #{r['id']} {r['name']}: {preview}...")
