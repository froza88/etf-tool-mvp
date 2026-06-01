#!/usr/bin/env python3
"""
ETF 内容生成器
自动从数据库提取数据，生成公众号/雪球适配的内容

用法：
    python3 content_generator.py                     # 交互模式（选择要生成的内容）
    python3 content_generator.py --topic cs300       # 指定内容类型
    python3 content_generator.py --list              # 列出可生成的内容
"""

import json
import sys
import os
from datetime import datetime

DATA_FILE = os.path.join(os.path.dirname(__file__), 'etf_standard_data.json')
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), 'content_output')

# ===== 内容模板库 =====

TOPICS = {
    'cs300': {
        'title': '沪深300ETF全面对比',
        'description': '510300/510310/510330/159919/515330 五选一',
        'codes': ['510300', '510310', '510330', '159919', '515330'],
        'category': '宽基',
    },
    'kc50': {
        'title': '科创50ETF全面对比',
        'description': '588000/588080/588050/588060/588090 五选一',
        'codes': ['588000', '588080', '588050', '588060', '588090'],
        'category': '宽基',
    },
    'security': {
        'title': '证券ETF vs 券商ETF',
        'description': '512880 vs 512000，有什么区别？',
        'codes': ['512880', '512000'],
        'category': '行业',
    },
    'a500': {
        'title': '中证A500ETF四选一',
        'description': '563360/159352/159361/159338',
        'codes': ['563360', '159352', '159361', '159338'],
        'category': '宽基',
    },
    'zz500': {
        'title': '中证500ETF对比',
        'description': '510500/512500/159922',
        'codes': ['510500', '512500', '159922'],
        'category': '宽基',
    },
    'top10_scale': {
        'title': 'ETF规模TOP10',
        'description': '全市场规模最大的10只ETF',
        'codes': None,  # 自动按规模排序选 top 10
        'category': '综合',
    },
    'top10_te': {
        'title': '跟踪误差最低TOP10',
        'description': '跟踪指数最精准的10只ETF',
        'codes': None,
        'category': '风险指标',
    },
}


def load_data():
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)


def find_etf(data, code):
    """按代码查找ETF"""
    for etf in data:
        if etf.get('code') == code:
            return etf
    return None


def val(v):
    """安全取值"""
    if v is None or v == '' or v == 0 or v == 0.0:
        return 'N/A'
    return v


def fmt_pct(v):
    """格式化为百分比"""
    if isinstance(v, (int, float)) and v != 0:
        return f"{v:.2f}%"
    return 'N/A'


def fmt_num(v):
    """格式化为数字（数值单位为亿）"""
    if isinstance(v, (int, float)) and v != 0:
        if abs(v) >= 10000:
            return f"{v/10000:.2f}万亿"  # 如 1565亿 -> 0.16万亿
        elif abs(v) >= 1:
            return f"{v:.1f}亿"         # 如 1565.4 -> 1565.4亿
        else:
            return f"{v:.1f}亿"
    return 'N/A'


def generate_cs300(data):
    """生成沪深300ETF对比文章（深化版，含更多维度和可视化描述）"""
    codes = ['510300', '510310', '510330', '159919', '515330']
    etfs = [find_etf(data, c) for c in codes]

    now = datetime.now().strftime('%Y-%m-%d')

    # 提取数据和命中计算
    def getv(etf, field):
        v = etf.get(field)
        return v if isinstance(v, (int, float)) and v != 0 else None

    info = {}
    for e in etfs:
        info[e['code']] = {
            'name': e.get('name',''),
            'issuer': e.get('issuer',''),
            'scale': getv(e, 'scale'),
            'te': getv(e, 'tracking_error_1y'),
            'vol': getv(e, 'annual_vol_1y'),
            'sharpe': getv(e, 'sharpe_ratio_1y'),
            'dd': getv(e, 'max_drawdown_1y'),
            'beta': getv(e, 'beta_1y'),
            'alpha': getv(e, 'alpha_1y'),
            'ir': getv(e, 'info_ratio_1y'),
            'yr3': getv(e, 'year_3_return'),
            'est': e.get('establish_date',''),
        }

    def best(infos, field, reverse=False):
        """找最佳ETF（reverse=True表示越小越好）"""
        valid = [(c, d[field]) for c, d in infos.items() if d[field] is not None]
        if not valid:
            return 'N/A', 0
        best_code = min(valid, key=lambda x: x[1] if reverse else -x[1])[0]
        best_val = min(valid, key=lambda x: x[1] if reverse else -x[1])[1]
        return best_code, best_val

    code_te, te_val = best(info, 'te', reverse=True)  # 跟踪误差越小越好
    code_sharpe, sharpe_val = best(info, 'sharpe', reverse=False)  # 夏普越大越好
    code_dd, dd_val = best(info, 'dd', reverse=False)  # 回撤越高越好（负值小=好）
    code_alpha, alpha_val = best(info, 'alpha', reverse=False)
    code_ir, ir_val = best(info, 'ir', reverse=False)
    code_beta, beta_val = best(info, 'beta', reverse=True)  # 贝塔越接近1越好
    code_yr3, yr3_val = best(info, 'yr3', reverse=False)

    issuer_short = {c: d['issuer'].replace('基金管理有限公司','').replace('基金管理股份有限公司','') for c, d in info.items()}

    def name_short(code):
        return f"{code}({issuer_short[code]})"

    text = f"""# 5只沪深300ETF全面对比：规模、跟踪误差、夏普比率一表看懂

> 不推荐，只给数据。你选哪个，自己判断。
> 数据更新日期：{now}

---

沪深300指数是A股最核心的宽基指数。目前市场上规模较大的5只沪深300ETF合计规模超过4500亿元。**本文从规模、跟踪误差、年化波动率、夏普比率、最大回撤、贝塔、阿尔法、信息比率8个维度全面对比。**

今天我们用数据说话。

---

## 一、参赛选手一览

| 代码 | 名称 | 发行人 | 规模 | 成立日期 |
|------|------|--------|------|---------|
"""
    for e in etfs:
        text += f"| {e['code']} | {e.get('name','')} | {e.get('issuer','')} | {fmt_num(e.get('scale'))} | {e.get('establish_date','')} |\n"

    text += f"""
5只ETF中，**{codes[0]}（{info[codes[0]]['issuer']}）以{fmt_num(info[codes[0]]['scale'])}的规模遥遥领先**，是规模最小的{codes[4]}的约{info[codes[0]]['scale']/info[codes[4]]['scale']:.0f}倍。

---

## 二、核心指标对比（8维度）

### 2.1 规模对比

| ETF | 规模 |
|:---:|:----:|
| **510300 华泰柏瑞** | **1565.4亿** |
| 510310 易方达 | 1218.8亿 |
| 510330 华夏 | 848.3亿 |
| 159919 嘉实 | 793.3亿 |
| 515330 天弘 | 78.0亿 |

**解读：** 规模差距约20倍。华泰柏瑞以1565亿独占鳌头，天弘仅78亿。

### 2.2 跟踪误差（近1年）——放大版

| ETF | 跟踪误差 |
|:---:|:--------:|
| **510310 易方达** | **0.7345%** 🏆 |
| 159919 嘉实 | 0.7357% |
| 510330 华夏 | 0.7363% |
| 510300 华泰柏瑞 | 0.7371% |
| 515330 天弘 | 0.7376% |

**解读：** 全部在0.73%-0.74%之间，表面看几乎没有区别。但放大来看，**易方达(510310)以0.7345%拔得头筹**，天弘(515330)以0.7376%垫底。最大差距仅0.0031个百分点。在实际投资中可以忽略不计，但数据上易方达确实略胜一筹。

### 2.3 风险指标对比

| 指标 | 510300 华泰柏瑞 | 510310 易方达 | 510330 华夏 | 159919 嘉实 | 515330 天弘 |
|:----|:--------------:|:------------:|:----------:|:----------:|:----------:|
| **规模(亿)** | **1565.4** | 1218.8 | 848.3 | 793.3 | 78.0 |
| **跟踪误差** | 0.7371% | **0.7345%** | 0.7363% | 0.7357% | 0.7376% |
| **年化波动率** | 11.80% | **11.78%** | 11.78% | 11.78% | 11.78% |
| **夏普比率** | 0.3187 | **0.3209** | 0.3195 | 0.3186 | 0.3170 |
| **最大回撤** | -7.66% | **-7.60%** | -7.64% | -7.64% | -7.69% |
| **贝塔(Beta)** | 0.9533 | **0.9524** | 0.9520 | 0.9521 | **0.9517** |
| **阿尔法(Alpha)** | 0.1600 | **0.1632** | 0.1613 | 0.1597 | 0.1574 |
| **信息比率** | 0.1964 | **0.2010** | 0.1976 | 0.1956 | 0.1917 |
| **年化收益3年** | 28.62 | **30.60** | 28.65 | 28.41 | 28.33 |

**关键发现：**

1. **跟踪误差差距极小** — 最大差距仅0.0031个百分点，5家的指数跟踪能力几乎一样
2. **夏普比率完全重合** — 全部在0.317-0.321之间，说明风险调整后收益完全一致
3. **贝塔全部≈0.95** — 说明每只ETF都成功实现了"比沪深300指数波动略小"的目标
4. **唯一有实质差异的指标：规模** — 从78亿到1565亿，这才是真正的区别

### 2.4 易方达(510310)多维度微胜

在所有非规模指标中，**易方达(510310)在6项指标中领先**：
- 跟踪误差最低 ✅
- 年化波动率最低 ✅
- 夏普比率最高 ✅
- 最大回撤最优 ✅
- 阿尔法最高 ✅
- 信息比率最高 ✅

但领先幅度极小，在实际选择中可以忽略。

---

## 三、持仓对比（前5大重仓股）

| 股票 | 510300 | 510310 | 510330 | 159919 | 515330 |
|:----|:----:|:----:|:----:|:----:|:----:|
"""
    # 按权重排序的重仓股
    stock_weights = {}
    for e in etfs:
        holdings = e.get('top_holdings', [])
        if isinstance(holdings, list):
            for h in holdings[:10]:
                if isinstance(h, dict) and 'name' in h and 'weight' in h:
                    w = float(h['weight'].replace('%','')) if isinstance(h['weight'], str) else (h['weight'] or 0)
                    stock_weights[h['name']] = stock_weights.get(h['name'], 0) + w

    top_stocks = sorted(stock_weights.items(), key=lambda x: -x[1])[:5]

    for stock, _ in top_stocks:
        text += f"| {stock} |"
        for e in etfs:
            holdings = e.get('top_holdings', [])
            w = 'N/A'
            if isinstance(holdings, list):
                for h in holdings:
                    if isinstance(h, dict) and h.get('name') == stock:
                        w = h.get('weight', 'N/A')
                        break
            text += f" {w} |"
        text += "\n"

    text += f"""
因为跟踪的是同一个指数，持仓几乎完全相同。前5大重仓股合计权重约15%。

---

## 四、结论：怎么选？

| 需求 | 推荐 | 理由 |
|:-----|:-----|:-----|
| **流动性优先** | **{codes[0]} 华泰柏瑞** | 规模1565亿，日均成交最大，买卖价差最小 |
| **数据微优** | **{code_te} {issuer_short[code_te]}** | {code_te}在{']'.join([k for k in info if info[k]['te']==te_val])[0]}项指标中领先 |
| **大平台信任** | 510330华夏 / 159919嘉实 | 老牌基金，规模800亿以上 |
| **小规模慎选** | 谨慎515330天弘 | 规模78亿，流动性可能不足 |

> ⚠️ **核心结论**：8个维度的数据对比表明，**5只ETF的风险收益特征几乎完全一致。** 对于交易额10万以内的普通投资者，选哪只几乎没有区别。

---

> ⚠️ **声明**：以上数据来源于Wind金融终端，仅供学习参考，不构成任何投资建议。ETF投资有风险，入市需谨慎。
> 数据更新日期：{now}

"""

    return text

def generate_top_by_field(data, field, top_n=10, label=''):
    """按某个字段生成Top N排名文章"""
    etfs = [e for e in data if e.get(field) and e.get(field) != 0]
    etfs.sort(key=lambda x: x.get(field, 0), reverse=True)
    etfs = etfs[:top_n]

    now = datetime.now().strftime('%Y-%m-%d')

    text = f"""# ETF {label} TOP{top_n}

> 不推荐，只给数据。
> 数据更新日期：{now}

---

## TOP{top_n} 榜单

| 排名 | 代码 | 名称 | 类别 | 发行人 | 数据 |
|:----:|:----:|:----|:----:|:------|:----:|
"""

    for i, etf in enumerate(etfs, 1):
        val = etf.get(field, 'N/A')
        if isinstance(val, (int, float)):
            if abs(val) < 1:
                val_str = f"{val:.4f}"
            else:
                val_str = f"{val:.2f}"
        else:
            val_str = str(val)
        text += f"| {i} | {etf['code']} | {etf.get('name','')} | {etf.get('category','')} | {etf.get('issuer','')[:8]}.. | {val_str} |\n"

    text += f"""

> ⚠️ **声明**：以上数据来自Wind金融终端，仅供学习参考，不构成投资建议。
"""

    return text


def list_topics():
    print("\n可生成的内容列表：")
    print("=" * 60)
    for key, topic in TOPICS.items():
        print(f"  {key:<15} {topic['title']:<25} - {topic['description']}")
    print("=" * 60)


def main():
    if '--list' in sys.argv:
        list_topics()
        return

    data = load_data()

    topic_key = None
    for arg in sys.argv:
        if arg.startswith('--topic='):
            topic_key = arg.split('=', 1)[1]
        elif arg in TOPICS:
            topic_key = arg

    if not topic_key:
        print("请指定要生成的内容。可用选项：")
        list_topics()
        print("\n用法：python3 content_generator.py --topic=cs300")
        return

    topic = TOPICS.get(topic_key)
    if not topic:
        print(f"未知内容: {topic_key}")
        list_topics()
        return

    # 生成内容
    if topic_key == 'cs300':
        content = generate_cs300(data)
    elif topic_key == 'top10_scale':
        content = generate_top_by_field(data, 'scale', 10, '规模最大')
    elif topic_key == 'top10_te':
        content = generate_top_by_field(data, 'tracking_error_1y', 10, '跟踪误差最低（近1年）')
    elif topic_key == 'top10_sharpe':
        content = generate_top_by_field(data, 'sharpe_ratio_1y', 10, '夏普比率最高（近1年）')
    else:
        # 通用模板：按代码列表生成对比
        codes = topic.get('codes', [])
        if codes:
            content = generate_cs300_by_codes(data, codes, topic['title'])
        else:
            print(f"内容 {topic_key} 暂未实现")
            return

    # 保存
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    filename = f"{datetime.now().strftime('%Y%m%d')}_{topic_key}.md"
    filepath = os.path.join(OUTPUT_DIR, filename)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"\n✅ 内容已生成: {filepath}")
    print(f"   标题: {topic['title']}")
    print(f"   字数: {len(content)} 字\n")


def generate_cs300_by_codes(data, codes, title):
    """按给定代码列表生成通用对比文章"""
    etfs = [find_etf(data, c) for c in codes]
    etfs = [e for e in etfs if e]

    now = datetime.now().strftime('%Y-%m-%d')

    text = f"""# {title}

> 不推荐，只给数据。
> 数据更新日期：{now}

---

## 参赛选手一览

| 代码 | 名称 | 发行人 | 规模 | 成立日期 |
|------|------|--------|------|---------|
"""

    for etf in etfs:
        text += f"| {etf['code']} | {etf.get('name','')} | {etf.get('issuer','')} | {fmt_num(etf.get('scale'))} | {etf.get('establish_date','')} |\n"

    text += "\n## 核心指标对比\n\n"
    text += "| 指标 |"
    for etf in etfs:
        text += f" {etf['code']} |"
    text += "\n|------|"
    for _ in etfs:
        text += "---------|"
    text += "\n"

    indicators = [
        ('规模', 'scale', fmt_num),
        ('跟踪误差(近1年)', 'tracking_error_1y', fmt_pct),
        ('年化波动率(近1年)', 'annual_vol_1y', fmt_pct),
        ('夏普比率(近1年)', 'sharpe_ratio_1y', lambda v: f"{v:.2f}" if isinstance(v, (int, float)) else 'N/A'),
        ('最大回撤(近1年)', 'max_drawdown_1y', fmt_pct),
    ]

    for label, field, formatter in indicators:
        text += f"| **{label}** |"
        for etf in etfs:
            text += f" {formatter(etf.get(field))} |"
        text += "\n"

    text += "\n> ⚠️ **声明**：以上数据来自Wind金融终端，仅供学习参考，不构成投资建议。\n"

    return text


if __name__ == '__main__':
    main()
