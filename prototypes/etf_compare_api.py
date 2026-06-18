#!/usr/bin/env python3
"""
ETF 对比 API — 腾讯元器 HTTP 节点
端: POST /api/compare  GET /api/health  GET /api/search
数据: etf_data.json (1510只ETF, 按code索引)
输出: 纯数据矩阵，不做价值判断
"""
from flask import Flask, jsonify, request
import json, os

app = Flask(__name__)
BASE = os.path.dirname(os.path.abspath(__file__))

# 加载数据
with open(os.path.join(BASE, 'etf_data.json')) as f:
    DB = json.load(f)

@app.after_request
def cors(r):
    r.headers['Access-Control-Allow-Origin'] = '*'
    r.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    r.headers['Access-Control-Allow-Methods'] = 'GET,POST,OPTIONS'
    return r

@app.route('/api/compare', methods=['POST', 'GET', 'OPTIONS'])
def compare():
    if request.method == 'OPTIONS':
        return jsonify({})
    data = request.get_json(silent=True) if request.method == 'POST' else request.args
    if not data:
        data = {}
    code1 = str(data.get('etf_code1', '')).strip()
    code2 = str(data.get('etf_code2', '')).strip()
    fmt = data.get('format', 'json')
    if not code1 or not code2:
        return jsonify({"error": "请提供 etf_code1 和 etf_code2"}), 400
    e1, e2 = DB.get(code1), DB.get(code2)
    if not e1 or not e2:
        return jsonify({"error": f"未找到: {[c for c in [code1,code2] if not DB.get(c)]}"}), 404

    def s(val, unit="", default="—"):
        """安全格式化：None/空 → 默认值，否则 `值+单位`"""
        if val is None or val == "" or val == "None":
            return default
        if isinstance(val, float):
            return f"{val}{unit}"
        return f"{val}{unit}"

    def pct(val):
        """百分比格式化，正数带+号"""
        if val is None:
            return "—"
        sign = "+" if val > 0 else ""
        return f"{sign}{val}%"

    # 等号：数据矩阵，不做⭐标记
    def cell_a(val, unit="", default="—"):
        return s(val, unit, default)

    def cell_b(val, unit="", default="—"):
        return s(val, unit, default)

    # ── 构建四维数据矩阵 ──

    # 一、基本画像
    profile_rows = []
    profile_rows.append(f"| 全称 | {s(e1.get('name'))} | {s(e2.get('name'))} |")
    profile_rows.append(f"| 代码 | {code1} | {code2} |")
    profile_rows.append(f"| 管理公司 | {s(e1.get('issuer'))} | {s(e2.get('issuer'))} |")
    profile_rows.append(f"| 基金规模 | {cell_a(e1.get('scale_yi'), '亿')} | {cell_b(e2.get('scale_yi'), '亿')} |")
    profile_rows.append(f"| 管理+托管费 | {cell_a(e1.get('fee_total'), '%')} | {cell_b(e2.get('fee_total'), '%')} |")
    profile_rows.append(f"| 跟踪指数 | {s(e1.get('track_index'))} | {s(e2.get('track_index'))} |")
    profile_rows.append(f"| 上市日期 | {s(e1.get('listing_date'))} | {s(e2.get('listing_date'))} |")
    profile_rows.append(f"| 基金经理 | {s(e1.get('fund_manager'))} | {s(e2.get('fund_manager'))} |")

    # 二、行情与收益
    perf_rows = []
    perf_rows.append(f"| 最新价格 | {cell_a(e1.get('close'))} {pct(e1.get('change_pct'))} | {cell_b(e2.get('close'))} {pct(e2.get('change_pct'))} |")
    perf_rows.append(f"| 近1年收益 | {pct(e1.get('year_1_return'))} | {pct(e2.get('year_1_return'))} |")
    perf_rows.append(f"| 近3年累计 | {pct(e1.get('year_3_return'))} | {pct(e2.get('year_3_return'))} |")
    perf_rows.append(f"| 近3年年化 | {pct(e1.get('annual_3y'))} | {pct(e2.get('annual_3y'))} |")
    perf_rows.append(f"| 日成交量 | {cell_a(e1.get('volume'), '万手')} | {cell_b(e2.get('volume'), '万手')} |")

    # 三、风险指标
    risk_rows = []
    risk_rows.append(f"| 年化波动率 | {cell_a(e1.get('annual_vol'), '%')} | {cell_b(e2.get('annual_vol'), '%')} |")
    risk_rows.append(f"| 最大回撤 | {cell_a(e1.get('max_drawdown'), '%')} | {cell_b(e2.get('max_drawdown'), '%')} |")
    risk_rows.append(f"| 夏普比率 | {cell_a(e1.get('sharpe_ratio'))} | {cell_b(e2.get('sharpe_ratio'))} |")
    risk_rows.append(f"| Calmar比率 | {cell_a(e1.get('calmar_ratio'))} | {cell_b(e2.get('calmar_ratio'))} |")
    risk_rows.append(f"| 跟踪误差 | {cell_a(e1.get('tracking_error'), '%')} | {cell_b(e2.get('tracking_error'), '%')} |")
    risk_rows.append(f"| 折溢价 | {cell_a(e1.get('premium_discount'))} | {cell_b(e2.get('premium_discount'))} |")

    # 四、前5大持仓
    h1 = e1.get('holdings', [])
    h2 = e2.get('holdings', [])
    h1_str = "  ".join([f"{h.get('name','')} {h.get('weight','')}%" for h in h1[:5]])
    h2_str = "  ".join([f"{h.get('name','')} {h.get('weight','')}%" for h in h2[:5]])

    # 计算共同持仓
    common = set()
    for h in h1[:10]:
        for hh in h2[:10]:
            if h.get('name') == hh.get('name'):
                common.add(h['name'])

    hold_rows = []
    hold_rows.append(f"| TOP5持仓 | {h1_str} | {h2_str} |")
    hold_rows.append(f"| TOP10共同持仓 | {'、'.join(common) if common else '无'} | — |")

    # ── 拼装输出 ──
    markdown = f"""📊 **{s(e1.get('name'))} vs {s(e2.get('name'))}**
> {code1} · {s(e1.get('issuer'))}   |   {code2} · {s(e2.get('issuer'))}   |   数据截止 06-18 收盘

## 一、基本画像
| 指标 | {code1} | {code2} |
|------|------|------|
{chr(10).join(profile_rows)}

## 二、行情与收益
| 指标 | {code1} | {code2} |
|------|------|------|
{chr(10).join(perf_rows)}

## 三、风险指标
| 指标 | {code1} | {code2} |
|------|------|------|
{chr(10).join(risk_rows)}

## 四、前五大持仓
| {code1} | {code2} |
|------|------|
| {h1_str} | {h2_str} |

> 共同持仓（TOP10内）：{'、'.join(common) if common else '无共同持仓'}
"""

    if fmt == 'text':
        return markdown, 200, {'Content-Type': 'text/plain; charset=utf-8'}
    return jsonify({"etf1": e1, "etf2": e2, "text": markdown})

@app.route('/api/search')
def search():
    kw = request.args.get('keyword', '').strip()
    if not kw:
        return jsonify({"results": []})
    results = [{"code": e["code"], "name": e["name"], "issuer": e["issuer"]}
               for e in DB.values() if kw in e.get("name","") or kw in e.get("code","")][:10]
    return jsonify({"results": results})
