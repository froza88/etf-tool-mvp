#!/usr/bin/env python3
"""
Flask WSGI wrapper —— 复用 enrich_proxy.py 的数据源和计算函数
在 PythonAnywhere 上运行，替代原来 http.server
"""
from flask import Flask, jsonify, request, send_file
import json
import os
import time
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

# 把当前目录加入 sys.path，方便导入 enrich_proxy
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from enrich_proxy import (
    fetch_ttjj_estimate,
    fetch_tencent_quote,
    enrich_batch,
)

app = Flask(__name__)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))


@app.after_request
def add_cors(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    return response


@app.route('/api/ttjj')
def api_ttjj():
    codes_str = request.args.get('codes', '')
    codes = [c.strip() for c in codes_str.split(',') if c.strip()]
    if not codes:
        return jsonify({"error": "需要ETF代码"})

    results = {}
    with ThreadPoolExecutor(max_workers=10) as ex:
        ttjj_futures = {ex.submit(fetch_ttjj_estimate, c): c for c in codes}
        tencent_futures = {ex.submit(fetch_tencent_quote, c): c for c in codes}

        for f in as_completed(ttjj_futures):
            code = ttjj_futures[f]
            results[code] = f.result() or {}

        for f in as_completed(tencent_futures):
            code = tencent_futures[f]
            tc = f.result()
            if tc:
                results[code]['prev_close'] = tc.get('nav', '')
                results[code]['latest_price'] = tc.get('estimate', '')
                results[code]['change_pct'] = tc.get('change_pct', '')
                results[code]['update_time'] = tc.get('update_time', '')

    return jsonify({"etfs": results})


@app.route('/api/enrich')
def api_enrich():
    codes_str = request.args.get('codes', '')
    codes = [c.strip() for c in codes_str.split(',') if c.strip() and len(c.strip()) == 6]
    if not codes:
        return jsonify({"error": "需要ETF代码"})

    start = time.time()
    results = enrich_batch(codes)
    elapsed = round(time.time() - start, 2)

    return jsonify({
        "etfs": results,
        "elapsed": elapsed,
        "source": "ttjj+eastmoney",
        "mode": "realtime",
    })


@app.route('/api/compare', methods=['POST', 'GET', 'OPTIONS'])
def api_compare():
    if request.method == 'OPTIONS':
        return jsonify({})
    data = request.get_json(silent=True) if request.method == 'POST' else request.args
    if not data:
        data = {}
    code1 = str(data.get('etf_code1', '')).strip()
    code2 = str(data.get('etf_code2', '')).strip()
    if not code1 or not code2:
        return jsonify({"error": "请提供 etf_code1 和 etf_code2"}), 400

    # 加载 ETF 数据
    db_file = os.path.join(BASE_DIR, 'etf_data.json')
    if not os.path.exists(db_file):
        return jsonify({"error": "数据文件不存在"}), 500
    with open(db_file) as f:
        db = json.load(f)

    e1, e2 = db.get(code1), db.get(code2)
    if not e1 or not e2:
        missing = [c for c in [code1, code2] if not db.get(c)]
        return jsonify({"error": f"未找到: {missing}"}), 404
    # 生成格式化文本
    def safe(val, fmt="{}"):
        if val is None: return "暂无"
        return fmt.format(val)

    markdown = f"""📊 **{e1['name']}** vs **{e2['name']}**

| 指标 | {e1['name']} | {e2['name']} |
|------|------|------|
| 代码 | {e1['code']} | {e2['code']} |
| 基金公司 | {e1['issuer']} | {e2['issuer']} |
| 规模（亿） | {e1['scale_yi']} | {e2['scale_yi']} |
| 费率（%） | {e1['fee_total']} | {e2['fee_total']} |
| 近1年收益（%） | {safe(e1['year_1_return'])} | {safe(e2['year_1_return'])} |
| 近3年收益（%） | {safe(e1['year_3_return'])} | {safe(e2['year_3_return'])} |
| 夏普比率 | {safe(e1['sharpe_ratio'])} | {safe(e2['sharpe_ratio'])} |
| 最大回撤（%） | {safe(e1['max_drawdown'])} | {safe(e2['max_drawdown'])} |
| 跟踪指数 | {e1['track_index']} | {e2['track_index']} |"""

    return jsonify({"etf1": e1, "etf2": e2, "markdown": markdown})


@app.route('/api/health')
def api_health():
    return jsonify({"status": "ok", "time": time.strftime("%Y-%m-%d %H:%M:%S")})


@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve_static(path):
    if not path or path == 'comparison_ca_hybrid.html':
        path = 'comparison_ca_hybrid.html'
    filepath = os.path.join(BASE_DIR, path)
    if os.path.isfile(filepath):
        # 设置正确的 Content-Type
        ext = os.path.splitext(filepath)[1].lower()
        mime = {
            '.html': 'text/html; charset=utf-8',
            '.js': 'application/javascript; charset=utf-8',
            '.css': 'text/css; charset=utf-8',
            '.json': 'application/json; charset=utf-8',
            '.png': 'image/png',
            '.svg': 'image/svg+xml',
        }.get(ext, 'application/octet-stream')
        return send_file(filepath, mimetype=mime)
    return jsonify({"error": "Not found"}), 404
