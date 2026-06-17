#!/usr/bin/env python3
"""
ETF 对比 API — 腾讯元器 HTTP 节点
端: POST /api/compare  GET /api/health  GET /api/search
数据: etf_data.json (1510只ETF, 按code索引)
部署: PythonAnywhere WSGI
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
    fmt = data.get('format', 'json')  # json 或 text
    if not code1 or not code2:
        return jsonify({"error": "请提供 etf_code1 和 etf_code2"}), 400
    e1, e2 = DB.get(code1), DB.get(code2)
    if not e1 or not e2:
        return jsonify({"error": f"未找到: {[c for c in [code1,code2] if not DB.get(c)]}"}), 404

    # 生成 markdown 格式化文本
    def safe(val, fmt_str="{}"):
        if val is None: return "暂无"
        return fmt_str.format(val)

    def better(a, b, reverse=False):
        """比较两个值，返回谁更优的标记"""
        if a is None or b is None:
            return "", ""
        if reverse:  # 越小越好（费率、回撤、波动）
            if a < b: return "⭐", ""
            if b < a: return "", "⭐"
            return "", ""
        else:  # 越大越好
            if a > b: return "⭐", ""
            if b > a: return "", "⭐"
            return "", ""

    tag1, tag2 = better(e1['year_1_return'], e2['year_1_return'])
    y1 = f"| 近 1 年收益 | {safe(e1['year_1_return'], '{}%')} {tag1} | {safe(e2['year_1_return'], '{}%')} {tag2} |"

    tag1, tag2 = better(e1['year_3_return'], e2['year_3_return'])
    y3 = f"| 近 3 年收益 | {safe(e1['year_3_return'], '{}%')} {tag1} | {safe(e2['year_3_return'], '{}%')} {tag2} |"

    tag1, tag2 = better(e1['sharpe_ratio'], e2['sharpe_ratio'])
    sharpe = f"| 夏普比率 | {safe(e1['sharpe_ratio'])} {tag1} | {safe(e2['sharpe_ratio'])} {tag2} |"

    tag1, tag2 = better(e1['calmar_ratio'], e2['calmar_ratio'])
    calmar = f"| 卡玛比率 | {safe(e1['calmar_ratio'])} {tag1} | {safe(e2['calmar_ratio'])} {tag2} |"

    tag1, tag2 = better(e1['max_drawdown'], e2['max_drawdown'], reverse=True)
    dd = f"| 最大回撤 | {safe(e1['max_drawdown'], '{}%')} {tag1} | {safe(e2['max_drawdown'], '{}%')} {tag2} |"

    tag1, tag2 = better(e1['annual_vol'], e2['annual_vol'], reverse=True)
    vol = f"| 年化波动 | {safe(e1['annual_vol'], '{}%')} {tag1} | {safe(e2['annual_vol'], '{}%')} {tag2} |"

    tag1, tag2 = better(e1['fee_total'], e2['fee_total'], reverse=True)
    fee = f"| 管理费率 | {safe(e1['fee_total'], '{}%')} {tag1} | {safe(e2['fee_total'], '{}%')} {tag2} |"

    markdown = f"""📊 **{e1['name']}** vs **{e2['name']}**

> {e1['code']} · {e1['issuer']} &nbsp;&nbsp;|&nbsp;&nbsp; {e2['code']} · {e2['issuer']}

---

### 💰 收益表现
| 指标 | {e1['name']} | {e2['name']} |
|------|------|------|
{y1}
{y3}

### ⚠️ 风险指标
| 指标 | {e1['name']} | {e2['name']} |
|------|------|------|
{sharpe}
{calmar}
{dd}
{vol}

### 📋 基本信息
| 指标 | {e1['name']} | {e2['name']} |
|------|------|------|
| 基金规模 | {e1['scale_yi']} 亿 | {e2['scale_yi']} 亿 |
{fee}
| 跟踪指数 | {e1['track_index']} | {e2['track_index']} |

### 🏭 前 5 大持仓
| {e1['name']} | {e2['name']} |
|------|------|
{e1['holdings_str'].replace(chr(10), ' | ')}  {e2['holdings_str'].replace(chr(10), ' | ')} |

⭐ = 该项表现更优"""

    if fmt == 'text':
        return markdown, 200, {'Content-Type': 'text/plain; charset=utf-8'}
    return jsonify({"etf1": e1, "etf2": e2, "text": markdown})

@app.route('/api/search')
def search():
    kw = request.args.get('keyword', '').strip()
    if not kw:
        return jsonify({"results": []})
    results = [{"code": e["code"], "name": e["name"], "issuer": e["issuer"]}
               for e in DB.values() if kw in e["name"] or kw in e["code"]][:10]
    return jsonify({"results": results})

@app.route('/api/health')
def health():
    return jsonify({"status": "ok", "etfs": len(DB)})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=True)
