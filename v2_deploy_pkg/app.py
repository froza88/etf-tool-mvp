"""
ETF v2 PA API — 精简版
数据源: etf_core_data.json (1685只)
"""
from flask import Flask, request, jsonify
from datetime import datetime
import json
import traceback
import sys
from pathlib import Path

app = Flask(__name__)

# CORS
@app.after_request
def add_cors(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET,POST,OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    return response

@app.before_request
def handle_options():
    if request.method == 'OPTIONS':
        return '', 200

# 数据
ROOT = Path(__file__).parent
DATA = None

def load_data():
    global DATA
    if DATA is not None:
        return DATA
    try:
        f = ROOT / 'etf_core_data.json'
        print(f"Loading {f}...", flush=True)
        with open(f) as fp:
            raw = json.load(fp)
        DATA = raw if isinstance(raw, list) else raw.get('etfs', [])
        print(f"Loaded {len(DATA)} ETFs", flush=True)
        return DATA
    except Exception as e:
        traceback.print_exc()
        return []

# API
@app.route('/health')
def health():
    d = load_data()
    return jsonify({"status":"ok","version":"v2-pa","etf_count":len(d)})

@app.route('/api/compare')
def api_compare():
    try:
        codes = [c.strip() for c in request.args.get('codes','').split(',') if c.strip()]
        if not codes:
            return jsonify({"error":"need codes"}), 400
        etfs = load_data()
        cs = set(codes)
        r = [e for e in etfs if e.get('code') in cs]
        return jsonify({"codes":codes,"count":len(r),"etfs":r,"source":"pa_v2","updated":datetime.now().isoformat()})
    except Exception as e:
        return jsonify({"error":str(e)}), 500

@app.route('/api/etf/search')
def api_search():
    try:
        q = request.args.get('q','').strip()
        limit = int(request.args.get('limit','15'))
        if not q:
            return jsonify({"results":[],"total":0})
        etfs = load_data()
        ql = q.lower()
        r = []
        for e in etfs:
            if ql in e.get('code','').lower() or ql in e.get('name','').lower():
                r.append({"code":e.get('code'),"name":e.get('name'),"category":e.get('category',''),"issuer":e.get('issuer',''),"scale":e.get('scale_yi'),"year_1_return":e.get('year_1_return'),"fee_total":e.get('fee_total')})
        return jsonify({"results":r[:limit],"total":len(r)})
    except Exception as e:
        return jsonify({"error":str(e)}), 500

@app.route('/api/etf/<code>')
def api_etf(code):
    try:
        for e in load_data():
            if e.get('code') == code:
                return jsonify(e)
        return jsonify({"error":"not found"}), 404
    except Exception as ex:
        return jsonify({"error":str(ex)}), 500

@app.route('/')
def index():
    return jsonify({"service":"ETF Tool v2 API","endpoints":["/health","/api/compare","/api/etf/search","/api/etf/<code>"]})
