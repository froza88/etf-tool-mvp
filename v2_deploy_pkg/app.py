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

@app.route('/api/compare', methods=['GET','POST'])
def api_compare():
    try:
        codes = []
        fmt = 'text'  # 默认 Markdown（元器兼容）
        if request.method == 'POST':
            data = request.get_json(force=True, silent=True) or {}
            codes = [c.strip() for c in data.get('codes','').split(',') if c.strip()]
            if not codes:
                # 支持 code1/code2 参数
                c1 = data.get('etf_code1','') or data.get('code1','') or data.get('etf1','')
                c2 = data.get('etf_code2','') or data.get('code2','') or data.get('etf2','')
                if c1: codes.append(c1.strip())
                if c2: codes.append(c2.strip())
            fmt = data.get('format','text')
        else:
            codes = [c.strip() for c in request.args.get('codes','').split(',') if c.strip()]
            fmt = request.args.get('format','text')
        
        if not codes:
            return jsonify({"error":"need codes"}), 400
        
        etfs = load_data()
        cs = set(codes)
        r = [e for e in etfs if e.get('code') in cs]
        
        if fmt == 'text':
            text = format_markdown(r)
            return text, 200, {'Content-Type': 'text/plain; charset=utf-8'}
        
        return jsonify({"codes":codes,"count":len(r),"etfs":r,"source":"pa_v2","updated":datetime.now().isoformat()})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error":str(e)}), 500

def format_markdown(etfs):
    """格式化为元器 readable markdown"""
    lines = []
    lines.append(f"## ETF 对比 ({len(etfs)}只)")
    lines.append("")
    
    for etf in etfs:
        lines.append(f"### {etf.get('name','')} ({etf.get('code','')})")
        lines.append(f"- 基金公司: {etf.get('issuer','')}")
        lines.append(f"- 分类: {etf.get('category','')}")
        lines.append(f"- 成立日期: {etf.get('listing_date','')}")
        lines.append(f"- 跟踪指数: {etf.get('benchmark','')}")
        lines.append(f"- 规模: {etf.get('scale','')} 亿元")
        lines.append(f"- 管理费: {etf.get('management_fee_rate','')}% | 托管费: {etf.get('custody_fee_rate','')}% | 总费率: {etf.get('fee_rate','')}%")
        lines.append(f"- 近1年收益: {etf.get('year_1_return','')}% | 近3年收益: {etf.get('year_3_return','')}%")
        lines.append(f"- 夏普比率: {etf.get('sharpe_ratio','')} | Calmar: {etf.get('calmar_ratio','')}")
        lines.append(f"- 最大回撤: {etf.get('max_drawdown','')}% | 年化波动: {etf.get('annual_vol','')}%")
        lines.append(f"- 跟踪误差: {etf.get('tracking_error','')}%")
        lines.append(f"- 日均成交额: {etf.get('volume','')} 手")
        hd = etf.get('top_holdings',[])
        if hd:
            top = ', '.join(f"{h.get('name','')} {h.get('weight','')}" for h in hd[:5])
            lines.append(f"- 前5大持仓: {top}")
        lines.append("")
    
    return '\n'.join(lines)

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

STOCKS = None
def load_stocks():
    global STOCKS
    if STOCKS is not None:
        return STOCKS
    try:
        sf = ROOT / 'stocks.json'
        with open(sf) as fp:
            raw = json.load(fp)
        STOCKS = raw.get('stocks', [])
        print(f"Loaded {len(STOCKS)} stocks", flush=True)
        return STOCKS
    except Exception as e:
        traceback.print_exc()
        return []

@app.route('/api/stock/search')
def api_stock_search():
    """A股搜索：代码或名称模糊匹配"""
    try:
        q = request.args.get('q','').strip()
        limit = int(request.args.get('limit','15'))
        if not q:
            return jsonify({"results":[],"total":0})
        sl = load_stocks()
        ql = q.lower()
        r = []
        for s in sl:
            if ql in s.get('code','').lower() or ql in s.get('name','').lower():
                r.append(s)
        return jsonify({"results":r[:limit],"total":len(r)})
    except Exception as e:
        return jsonify({"error":str(e)}), 500

@app.route('/api/valuation')
def api_valuation():
    """指数估值表 ─ 实时PE/PB分位（来源：legulegu.com）"""
    try:
        vf = ROOT / 'valuation.json'
        if vf.exists():
            with open(vf) as fp:
                data = json.load(fp)
            return jsonify(data)
        # Fallback: 没有估值文件时返回空
        return jsonify({'count': 0, 'rows': [], 'updated': '', 'source': 'no valuation.json'})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error":str(e)}), 500

@app.route('/api/quotes')
def api_quotes():
    """代理行情（服务端代理，支持腾讯/新浪）"""
    try:
        codes = request.args.get('codes','').strip()
        if not codes:
            return jsonify({"error":"need codes"}), 400
        import urllib.request
        cl = [c.strip() for c in codes.split(',')]
        # 构造新浪行情URL
        qlist = []
        for c in cl:
            p = 'sh' if (c.startswith('5') or c.startswith('6')) else 'sz'
            qlist.append(p + c)
        url = "https://hq.sinajs.cn/list=" + ','.join(qlist)
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0',
            'Referer': 'https://finance.sina.com.cn'
        })
        resp = urllib.request.urlopen(req, timeout=8)
        raw = resp.read().decode('gbk', errors='replace')
        # 解析新浪格式：var hq_str_sh510300="名字,今开,昨收,现价,..."
        results = {}
        for c in cl:
            results[c] = {}
        for line in raw.strip().split('\n'):
            line = line.strip()
            if not line or '=' not in line: continue
            val = line.split('"')[1] if '"' in line else line.split('=')[1]
            parts = val.split(',')
            if len(parts) >= 33:
                # 新浪格式：名字,今开,昨收,现价,最高,最低,...
                pass
            elif len(parts) >= 4:
                pass
            # 通过stock代码匹配：取line中的变量名
            var = line.split('=')[0].strip().replace('var hq_str_','')
            for c in cl:
                p = 'sh' if (c.startswith('5') or c.startswith('6')) else 'sz'
                if var == p + c and len(parts) >= 4:
                    price = parts[3]  # 现价（第3个字段，0-indexed）
                    prev = parts[2]   # 昨收
                    pct = ''
                    try:
                        cp = float(price); pc = float(prev)
                        if pc > 0: pct = str(round((cp - pc) / pc * 100, 2))
                    except: pass
                    results[c] = {
                        'latest_price': price,
                        'prev_close': prev,
                        'change_pct': pct,
                    }
                    break
        return jsonify(results)
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error":str(e)}), 500

@app.route('/')
def index():
    return jsonify({"service":"ETF Tool v2 API","endpoints":["/health","/api/compare","/api/etf/search","/api/etf/<code>","/api/quotes","/api/valuation","/api/stock/search"]})
