#!/usr/bin/env python3
"""重新生成 ETF 数据完整度 HTML 报告（含适用性筛选）"""
import json, os
from datetime import date

DATA_FILE = '/Users/apangduo/WorkBuddy/Claw/etf-tool-mvp/prototypes/etf_core_data.json'
OUTPUT = '/Users/apangduo/WorkBuddy/Claw/outputs/etf_data_completeness_report.html'

# ============ 判定函数 ============
NON_RISK_TYPES = {"指数型-固收", "货币市场型基金", "商品型基金"}
NON_PE_TYPES = NON_RISK_TYPES | {"国际(QDII)股票型基金"}

def _is_delisted(e):
    return '退市' in str(e.get('name', ''))

def _yes(e): return True
def _is_active(e): return not _is_delisted(e)                           # 排除退市
def _is_risk(e): return _is_active(e) and e.get('invest_type') not in NON_RISK_TYPES
def _is_pe(e): return _is_active(e) and e.get('invest_type') not in NON_PE_TYPES
def _is_flow(e): return _is_active(e)

def _build_reason(all_ets, types, msg):
    parts = []
    for t in sorted(types):
        c = sum(1 for e in all_ets if e.get('invest_type') == t)
        if c > 0:
            parts.append(f"{t}类ETF{msg}({c}只)")
    return "; ".join(parts) if parts else "—"

def _reason_risk(ets):
    parts = []
    dl = sum(1 for e in ets if _is_delisted(e))
    if dl: parts.append(f"退市ETF({dl}只)")
    parts.append(_build_reason(ets, NON_RISK_TYPES, "无风险收益概念"))
    return "; ".join(p for p in parts if p) or "—"

def _reason_pe(ets):
    parts = []
    dl = sum(1 for e in ets if _is_delisted(e))
    if dl: parts.append(f"退市ETF({dl}只)")
    parts.append(_build_reason(ets, NON_PE_TYPES, "无PE概念（非股票型）"))
    return "; ".join(p for p in parts if p) or "—"

def _reason_holdings(ets):
    parts = []
    dl = sum(1 for e in ets if _is_delisted(e))
    if dl: parts.append(f"退市ETF({dl}只)")
    parts.append(_build_reason(ets, NON_PE_TYPES, "无股票持仓"))
    return "; ".join(p for p in parts if p) or "—"

def _reason_flow(ets):
    c = sum(1 for e in ets if _is_delisted(e))
    return f"退市ETF不适用({c}只)" if c else "—"

def _reason_delisted(ets):
    c = sum(1 for e in ets if _is_delisted(e))
    return f"退市ETF不适用({c}只)" if c else "—"

# ============== 指标定义 ==============
# (cat_zh, cat_en, field_key, label_zh, label_en, tier, applicable_fn, reason_fn)
# tier: "core"=核心21字段, "aux"=辅助19字段
FIELDS_CORE = [
    # ---- 21 核心字段 (ETF对比必需) ----
    ("核心行情", "Real-time",     "code",       "代码",         "Code",              _yes, None),
    ("核心行情", "Real-time",     "name",       "名称",         "Name",              _yes, None),
    ("核心行情", "Real-time",     "close",      "最新价",        "Latest Price",      _is_active, _reason_delisted),
    ("核心行情", "Real-time",     "change_pct", "涨跌幅(%)",     "Change %",          _is_active, _reason_delisted),
    ("收益与风险", "Return & Risk", "year_1_return", "近1年收益(%)", "1Y Return %",    _is_active, _reason_delisted),
    ("收益与风险", "Return & Risk", "year_3_return", "近3年收益(%)", "3Y Return %",    _is_active, _reason_delisted),
    ("收益与风险", "Return & Risk", "sharpe_ratio",  "夏普比率",     "Sharpe Ratio",    _is_risk, _reason_risk),
    ("收益与风险", "Return & Risk", "max_drawdown",  "最大回撤(%)",  "Max Drawdown %",  _is_risk, _reason_risk),
    ("收益与风险", "Return & Risk", "calmar_ratio",  "Calmar比率",  "Calmar Ratio",    _is_risk, _reason_risk),
    ("收益与风险", "Return & Risk", "annual_vol",    "年化波动率(%)", "Annual Vol %",   _is_risk, _reason_risk),
    ("风控", "Risk Control",     "alpha",         "Alpha",        "Alpha",             _is_risk, _reason_risk),
    ("风控", "Risk Control",     "beta",          "Beta",         "Beta",              _is_risk, _reason_risk),
    ("风控", "Risk Control",     "tracking_error","跟踪误差",       "Tracking Error",    _is_risk, _reason_risk),
    ("风控", "Risk Control",     "info_ratio",    "信息比率",       "Info Ratio",        _is_risk, _reason_risk),
    ("费率", "Fees",             "fee_mgmt",      "管理费率(%)",   "Mgmt Fee %",        _yes, None),
    ("费率", "Fees",             "fee_custody",   "托管费率(%)",   "Custody Fee %",     _yes, None),
    ("费率", "Fees",             "fee_total",     "总费率(%)",     "Total Fee %",       _yes, None),
    ("估值资金", "Val. & Flow",   "valuation_percentile", "PE估值分位(%)", "PE Percentile %", _is_pe, _reason_pe),
    ("估值资金", "Val. & Flow",   "top_holdings",  "前10持仓",      "Top 10 Holdings",   _is_pe, _reason_holdings),
    ("估值资金", "Val. & Flow",   "nav",           "单位净值",      "NAV",               _is_active, _reason_delisted),
    ("估值资金", "Val. & Flow",   "flow_shares",   "最新份额(份)",   "Shares",            _is_flow, _reason_flow),
]

FIELDS_AUX = [
    # ---- 19 辅助字段 (展示/标识/衍生) ----
    ("辅助行情", "Aux Price",        "prev_close",   "前收盘价",      "Prev Close",       _is_active, _reason_delisted),
    ("辅助行情", "Aux Price",        "volume",       "成交量(手)",    "Volume (lots)",    _is_active, _reason_delisted),
    ("辅助行情", "Aux Price",        "change_rate",  "涨跌率",        "Change Rate",      _is_active, _reason_delisted),
    ("辅助收益", "Aux Return",       "annual_3y",    "3年年化收益(%)", "Annualized 3Y %",  _is_active, _reason_delisted),
    ("辅助资金", "Aux Flow",         "main_net_inflow", "主力净流入(元)", "Net Inflow (CNY)", _is_flow, _reason_flow),
    ("辅助资金", "Aux Flow",         "main_net_ratio",  "主力净占比(%)", "Net Ratio %",      _is_flow, _reason_flow),
    ("辅助标识", "Aux Identity",     "issue_date",    "成立日期",      "Inception Date",   _is_active, _reason_delisted),
    ("辅助标识", "Aux Identity",     "listing_date",  "上市日期",      "Listing Date",     _yes, None),
    ("辅助标识", "Aux Identity",     "custodian",     "托管人",        "Custodian",        _is_active, _reason_delisted),
    ("辅助标识", "Aux Identity",     "fund_manager",  "基金经理",      "Fund Manager",     _is_active, _reason_delisted),
    ("辅助标识", "Aux Identity",     "issuer",        "发行商",        "Issuer",           _yes, None),
    ("辅助标识", "Aux Identity",     "issuer_full",   "发行商全称",    "Issuer Full Name", _yes, None),
    ("辅助标识", "Aux Identity",     "issuer_short",  "发行商简称",    "Issuer Short Name",_yes, None),
    ("辅助标识", "Aux Identity",     "invest_type",   "投资类型",      "Investment Type",  _is_active, _reason_delisted),
    ("辅助标识", "Aux Identity",     "category",      "资产大类",      "Asset Category",   _yes, None),
    ("辅助标识", "Aux Identity",     "short_name",    "简称",         "Short Name",       _yes, None),
    ("辅助标识", "Aux Identity",     "wind_code",     "Wind代码",      "Wind Code",        _yes, None),
    ("辅助标识", "Aux Identity",     "track_index",   "跟踪指数",      "Benchmark Index",  _yes, None),
    ("辅助标识", "Aux Identity",     "track_index_code","跟踪指数代码","Index Code",        _yes, None),
]

# ============ 生成 HTML ============
def _gen_rows(data, field_list, total):
    rows = []
    prev_cat = None
    for cat, cat_en, fkey, label_zh, label_en, is_applicable, reason_fn in field_list:
        applicable = sum(1 for e in data if is_applicable(e))
        not_applicable = total - applicable
        has_val = sum(1 for e in data if is_applicable(e) and e.get(fkey) is not None and e.get(fkey) != '')
        missing = applicable - has_val
        pct = has_val / applicable * 100 if applicable > 0 else 0
        
        cls = "status-ok" if pct >= 95 else ("status-warn" if pct >= 80 else "status-bad")
        icon = "✅" if pct >= 95 else ("⚠️" if pct >= 80 else "🔴")
        bar_w = min(100, int(pct))
        bar_c = "green-bar" if pct >= 95 else ("amber-bar" if pct >= 80 else "red-bar")
        reason = reason_fn(data) if reason_fn else "—"
        cat_sep = ' class="cat-sep"' if cat != prev_cat else ''
        prev_cat = cat
        cat_display = f"{cat}<br><span style='font-size:10px;color:#888'>{cat_en}</span>"
        
        rows.append(f"""<tr{cat_sep}>
<td class="cat">{cat_display}</td>
<td><code>{fkey}</code><br><span style='font-size:11px;color:#888'>{label_zh} / {label_en}</span></td>
<td class="num">{total}</td>
<td class="num">{applicable}</td>
<td class="num">{not_applicable}</td>
<td class="num">{has_val}</td>
<td class="num"><span class="pct-bar {bar_c}" style="width:{bar_w}px"></span>{pct:.1f}%</td>
<td class="num">{missing if missing > 0 else '—'}</td>
<td class="{cls}">{icon}</td>
<td class="reason">{reason}</td>
</tr>""")
    return rows

def _calc_weighted(data, field_list):
    pcts = []
    for cat, cat_en, fkey, label_zh, label_en, is_applicable, reason_fn in field_list:
        applicable = sum(1 for e in data if is_applicable(e))
        has_val = sum(1 for e in data if is_applicable(e) and e.get(fkey) is not None and e.get(fkey) != '')
        pcts.append(has_val / applicable * 100 if applicable > 0 else 0)
    return sum(pcts) / len(pcts) if pcts else 0

def gen_html(data):
    total = len(data)
    today_str = date.today().strftime('%Y年%-m月%-d日')
    
    rows_core = _gen_rows(data, FIELDS_CORE, total)
    rows_aux = _gen_rows(data, FIELDS_AUX, total)
    all_rows = rows_core + rows_aux
    weighted_core = _calc_weighted(data, FIELDS_CORE)
    weighted_aux = _calc_weighted(data, FIELDS_AUX)
    weighted_all = _calc_weighted(data, FIELDS_CORE + FIELDS_AUX)
    
    # Count stats
    cnt = {"green": 0, "amber": 0, "red": 0}
    for cat, cat_en, fkey, label_zh, label_en, is_applicable, reason_fn in FIELDS_CORE + FIELDS_AUX:
        applicable = sum(1 for e in data if is_applicable(e))
        has_val = sum(1 for e in data if is_applicable(e) and e.get(fkey) is not None and e.get(fkey) != '')
        pct = has_val / applicable * 100 if applicable > 0 else 0
        if pct >= 95: cnt["green"] += 1
        elif pct >= 80: cnt["amber"] += 1
        else: cnt["red"] += 1
    
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>ETF 数据完整度明细表</title>
<style>
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;background:#FEFCF8;color:#333;line-height:1.6;padding:24px}}
.container{{max-width:1200px;margin:0 auto}}
.header{{display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:24px;flex-wrap:wrap;gap:16px}}
.header h1{{font-size:22px;font-weight:600;color:#1a1a1a}}
.meta{{font-size:13px;color:#888;margin-top:4px}}
.summary-cards{{display:flex;gap:12px;flex-wrap:wrap;margin-bottom:20px}}
.card{{flex:1;min-width:140px;border-radius:8px;padding:14px 18px;text-align:center;border:0.5px solid #e8e4dc}}
.card .num{{font-size:28px;font-weight:600;margin-bottom:2px}}
.card .label{{font-size:12px;color:#888}}
.card.green{{background:#eaf3de;border-color:#97c459}}.card.green .num{{color:#3b6d11}}
.card.blue{{background:#e6f1fb;border-color:#85b7eb}}.card.blue .num{{color:#0c447c}}
.card.amber{{background:#faeeda;border-color:#ef9f27}}.card.amber .num{{color:#854f0b}}
.card.red{{background:#fcebeb;border-color:#f09595}}.card.red .num{{color:#a32d2d}}
table{{width:100%;border-collapse:collapse;font-size:13px;background:#fff;border-radius:8px;overflow:hidden;border:0.5px solid #e8e4dc}}
thead{{position:sticky;top:0}}
th{{background:#f5f3ed;font-weight:600;font-size:12px;text-align:left;padding:10px 12px;border-bottom:1.5px solid #ddd7c8;white-space:nowrap}}
th.cat{{border-right:1.5px solid #ddd7c8}}
td{{padding:8px 12px;border-bottom:0.5px solid #f0ece3}}
td.cat{{font-weight:500;background:#fafaf7;border-right:1.5px solid #ddd7c8}}
tr:hover td{{background:#fdf9f3}}
tr.cat-sep td{{border-top:2px solid #ddd7c8}}
.status-ok{{color:#3b6d11;font-weight:500}}
.status-warn{{color:#854f0b;font-weight:500}}
.status-bad{{color:#a32d2d;font-weight:500}}
.reason{{font-size:11px;color:#999;max-width:300px}}
.pct-bar{{display:inline-block;height:8px;border-radius:3px;margin-right:6px;vertical-align:middle}}
.green-bar{{background:#97c459}}
.amber-bar{{background:#ef9f27}}
.red-bar{{background:#e24b4a}}
.legend{{display:flex;gap:16px;margin-bottom:16px;font-size:12px;color:#888;flex-wrap:wrap}}
.legend span{{display:flex;align-items:center;gap:4px}}
.legend .dot{{width:10px;height:10px;border-radius:2px}}
.footer{{font-size:12px;color:#aaa;margin-top:20px;text-align:center}}
@media(max-width:768px){{body{{padding:12px}}table{{font-size:11px}}th,td{{padding:6px 8px}}}}
</style>
</head>
<body>
<div class="container">
<div class="header">
<div>
<h1>ETF 数据完整度明细表</h1>
<p class="meta">{today_str} · 共 {total}只ETF · {len(FIELDS_CORE)}核心字段 + {len(FIELDS_AUX)}辅助字段 · 逐字段标注适用性及缺失原因</p>
</div>
</div>
<div class="legend">
<span><span class="dot" style="background:#97c459"></span> 健康 ≥95%</span>
<span><span class="dot" style="background:#ef9f27"></span> 待补 80–95%</span>
<span><span class="dot" style="background:#e24b4a"></span> 缺失 &lt;80%</span>
<span style="margin-left:12px;color:#bbb">不适用的全部标注原因，不计入覆盖率</span>
</div>
<table>
<thead>
<tr>
<th class="cat">分类 / Category</th><th>字段 / Field</th><th class="num">总数</th><th class="num">适用</th><th class="num">不适用</th><th class="num">有值</th><th class="num">覆盖率</th><th class="num">缺数</th><th>状态</th><th>不适用原因说明</th>
</tr>
</thead>
<tbody>
{''.join(rows_core)}
<tr class="cat-sep"><td colspan="10" style="background:#fff7e6;text-align:center;font-weight:600;padding:10px;color:#854f0b">📋 辅助字段 / Auxiliary Fields ({len(FIELDS_AUX)} fields)</td></tr>
{''.join(rows_aux)}
</tbody>
</table>
<div class="summary-cards" style="margin-top:20px">
<div class="card green"><div class="num">{cnt['green']}</div><div class="label">健康字段 ≥95%</div></div>
<div class="card blue"><div class="num">{weighted_all:.1f}%</div><div class="label">综合覆盖率</div></div>
<div class="card blue"><div class="num">{weighted_core:.1f}%</div><div class="label">核心字段覆盖</div></div>
<div class="card blue"><div class="num">{weighted_aux:.1f}%</div><div class="label">辅助字段覆盖</div></div>
<div class="card amber"><div class="num">{cnt['amber']}</div><div class="label">待补字段 80–95%</div></div>
<div class="card red"><div class="num">{cnt['red']}</div><div class="label">缺失字段 &lt;80%</div></div>
</div>
<div class="footer">
核心21字段 = ETF对比必需指标 · 辅助19字段 = 展示/标识/衍生数据<br>
不计入的不适用场景：退市ETF(125只)、债券/货币/商品型无PE/风控概念、QDII无PE等<br>
NAV 33.9%→92.6%（2026-06-28更新）· 数据文件: prototypes/etf_core_data.json
</div>
</div>
</body>
</html>"""

def main():
    with open(DATA_FILE) as f:
        data = json.load(f)
    html = gen_html(data)
    os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)
    with open(OUTPUT, 'w') as f:
        f.write(html)
    print(f"✅ {OUTPUT}")

if __name__ == '__main__':
    main()
