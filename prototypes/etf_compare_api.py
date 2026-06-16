#!/usr/bin/env python3
"""
ETF 对比 API — 给腾讯元器调用
部署: PythonAnywhere WSGI
端点: POST /api/compare
请求: {"etf_code1":"512660", "etf_code2":"512710"}
响应: 两只ETF的17项对比数据 + 结论
"""
from flask import Flask, jsonify, request
import json, os, re

app = Flask(__name__)
BASE = os.path.dirname(os.path.abspath(__file__))

# 加载快照数据（部署时一并上传）
def load_snapshot():
    # 找最新的快照文件
    snap_dir = os.path.join(BASE, 'snapshots')
    if not os.path.exists(snap_dir):
        snap_dir = BASE
    files = sorted([f for f in os.listdir(snap_dir) if f.endswith('.json')], reverse=True)
    for f in files:
        path = os.path.join(snap_dir, f)
        try:
            with open(path) as fp:
                data = json.load(fp)
                if 'standard_data' in data:
                    return {e['code']: e for e in data['standard_data']}
        except:
            continue
    return {}

SNAPSHOT = load_snapshot()

def safe_num(v, default=None):
    try: return float(v) if v is not None else default
    except: return default

@app.after_request
def cors(r):
    r.headers['Access-Control-Allow-Origin'] = '*'
    r.headers['Access-Control-Allow-Headers'] = 'Content-Type,Authorization'
    r.headers['Access-Control-Allow-Methods'] = 'GET,POST,OPTIONS'
    return r

@app.route('/api/compare', methods=['POST', 'GET', 'OPTIONS'])
def compare():
    if request.method == 'OPTIONS':
        return jsonify({})
    
    # 支持 POST JSON 和 GET 参数
    if request.method == 'POST':
        data = request.get_json(silent=True) or {}
    else:
        data = request.args
    
    code1 = data.get('etf_code1', '').strip()
    code2 = data.get('etf_code2', '').strip()
    
    if not code1 or not code2:
        return jsonify({"error": "请提供 etf_code1 和 etf_code2", "hint": "如 {\"etf_code1\":\"512660\", \"etf_code2\":\"512710\"}"}), 400
    
    e1 = SNAPSHOT.get(code1)
    e2 = SNAPSHOT.get(code2)
    
    if not e1 or not e2:
        missing = []
        if not e1: missing.append(code1)
        if not e2: missing.append(code2)
        return jsonify({"error": f"未找到: {','.join(missing)}", "hint": "检查代码是否正确"}), 404
    
    def extract(e):
        return {
            "code": e.get("code"),
            "name": e.get("name"),
            "scale_yi": safe_num(e.get("scale")),
            "fee_rate": safe_num(e.get("fee_rate")),
            "close": safe_num(e.get("close")),
            "change_pct": safe_num(e.get("change_pct")),
            "year_1_return": safe_num(e.get("year_1_return")),
            "year_3_return": safe_num(e.get("year_3_return")),
            "annual_vol": safe_num(e.get("annual_vol")),
            "max_drawdown": safe_num(e.get("max_drawdown")),
            "sharpe_ratio": safe_num(e.get("sharpe_ratio")),
            "calmar_ratio": safe_num(e.get("calmar_ratio")),
            "benchmark": e.get("benchmark", ""),
            "issuer_short": e.get("issuer_short", ""),
            "volume": safe_num(e.get("volume")),
        }
    
    d1, d2 = extract(e1), extract(e2)
    
    # 简单结论：数据对比
    better = []
    if d1.get("year_1_return") and d2.get("year_1_return"):
        better.append(f"近1年: {code1 if d1['year_1_return'] > d2['year_1_return'] else code2}领先")
    if d1.get("sharpe_ratio") and d2.get("sharpe_ratio"):
        better.append(f"夏普: {code1 if d1['sharpe_ratio'] > d2['sharpe_ratio'] else code2}更高")
    
    return jsonify({
        "success": True,
        "etf1": d1,
        "etf2": d2,
        "summary": "；".join(better) if better else "数据加载完成",
        "data_date": os.path.basename(sorted([f for f in os.listdir(os.path.join(BASE, 'snapshots') if os.path.exists(os.path.join(BASE, 'snapshots')) else BASE) if f.endswith('.json')], reverse=True)[0]) if SNAPSHOT else "未知",
    })

@app.route('/api/health')
def health():
    return jsonify({"status": "ok", "etfs": len(SNAPSHOT)})

# 本地测试
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"ETF Compare API → http://localhost:{port}/api/compare")
    app.run(host='0.0.0.0', port=port, debug=True)
