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
    if not code1 or not code2:
        return jsonify({"error": "请提供 etf_code1 和 etf_code2"}), 400
    e1, e2 = DB.get(code1), DB.get(code2)
    if not e1 or not e2:
        return jsonify({"error": f"未找到: {[c for c in [code1,code2] if not DB.get(c)]}"}), 404
    return jsonify({"etf1": e1, "etf2": e2})

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
