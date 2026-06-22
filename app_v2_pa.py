"""
ETF 工具 v2 PA API — 部署版
数据源: etf_core_data.json (1685只, v10_full_1470)
"""
from flask import Flask, request, jsonify
from datetime import datetime
import json
import os
from pathlib import Path
from functools import wraps

app = Flask(__name__)

# ===========================================================
#  CORS 支持（EdgeOne 前端调 PA API 需要）
# ===========================================================

@app.after_request
def add_cors_headers(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    return response

@app.before_request
def handle_options():
    if request.method == 'OPTIONS':
        return '', 200

# ===========================================================
#  内存缓存（降低 PA CPU 消耗）
# ===========================================================

_cache = {}
_cache_timeout = {}

def cached(timeout_seconds=3600):
    """内存缓存装饰器"""
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            key = f.__name__ + str(args) + str(kwargs)
            now = datetime.now().timestamp()
            if key in _cache and now - _cache_timeout.get(key, 0) < timeout_seconds:
                return _cache[key]
            result = f(*args, **kwargs)
            _cache[key] = result
            _cache_timeout[key] = now
            return result
        return wrapper
    return decorator

# ===========================================================
#  数据加载（直接从 JSON 文件读取）
# ===========================================================

ROOT = Path(__file__).parent
DATA_FILE = ROOT / 'etf_core_data.json'

_etf_data = None
_etf_loaded_at = 0

def load_etf_data():
    """加载 ETF 数据（带进程级缓存，避免重复读文件）"""
    global _etf_data, _etfloaded_at
    now = datetime.now().timestamp()
    # 进程启动后缓存1小时，之后重新读文件
    if _etf_data is not None and now - _etf_loaded_at < 3600:
        return _etf_data
    if not DATA_FILE.exists():
        print(f"数据文件不存在: {DATA_FILE}", flush=True)
        return []
    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        # 兼容两种格式：list 或 {"etfs": [...]}
        if isinstance(data, dict):
            data = data.get('etfs', data.get('results', []))
        _etf_data = data if isinstance(data, list) else []
        _etf_loaded_at = now
        print(f"数据加载完成: {len(_etf_data)} 只 ETF", flush=True)
        return _etf_data
    except Exception as e:
        print(f"数据加载失败: {e}", flush=True)
        return []

# ===========================================================
#  API 端点（v2 前端需要）
# ===========================================================

@cached(timeout_seconds=3600)
@app.route('/api/etf/search')
def api_etf_search():
    """搜索 ETF（按代码或名称模糊匹配）"""
    q = request.args.get('q', '').strip()
    limit = int(request.args.get('limit', '15'))

    if not q:
        return jsonify({"results": [], "total": 0})

    etfs = load_etf_data()
    q_lower = q.lower()
    results = []

    for e in etfs:
        code = e.get('code', '')
        name = e.get('name', '')
        if q_lower in code.lower() or q_lower in name.lower():
            results.append({
                "code": code,
                "name": name,
                "category": e.get("category", ""),
                "issuer": e.get("issuer", ""),
                "scale": e.get("scale_yi"),
                "close": None,  # v10 无 close，前端走腾讯行情
                "year_1_return": e.get("year_1_return"),
                "fee_total": e.get("fee_total"),
            })

    total = len(results)
    return jsonify({"results": results[:limit], "total": total})

@cached(timeout_seconds=900)
@app.route('/api/etf/<code>')
def get_etf_api(code):
    """获取单只 ETF 详情"""
    etfs = load_etf_data()
    for e in etfs:
        if e.get('code') == code:
            return jsonify(e)
    return jsonify({"error": "ETF 不存在"}), 404

@cached(timeout_seconds=1800)
@app.route('/api/compare')
def api_compare():
    """对比数据 API — 核心端点"""
    codes = [c.strip() for c in request.args.get('codes', '').split(',') if c.strip()]
    if not codes:
        return jsonify({"error": "请提供 ETF 代码"}), 400

    etfs = load_etf_data()
    code_set = set(codes)
    result = [e for e in etfs if e.get('code') in code_set]

    return jsonify({
        "codes": codes,
        "count": len(result),
        "etfs": result,
        "source": "pa_api_v2",
        "updated": datetime.now().isoformat()
    })

@cached(timeout_seconds=3600)
@app.route('/api/etfs')
def get_etfs():
    """ETF 列表 API（分页）"""
    page = int(request.args.get('page', '1'))
    page_size = int(request.args.get('page_size', '50'))
    offset = (page - 1) * page_size

    etfs = load_etf_data()
    total = len(etfs)

    # 返回精简字段（匹配 v10 实际字段名）
    slim_fields = ['code', 'name', 'issuer', 'category', 'scale_yi',
                   'fee_total', 'year_1_return', 'year_3_return',
                   'sharpe_ratio', 'max_drawdown']
    slim = []
    for e in etfs[offset:offset + page_size]:
        slim.append({k: e.get(k) for k in slim_fields})

    return jsonify({
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size,
        "etfs": slim
    })

@app.route('/')
def index():
    """首页 — API 服务信息"""
    return jsonify({
        "service": "ETF Tool MVP API v2",
        "endpoints": {
            "/api/compare?codes=A,B": "ETF 对比（核心）",
            "/api/etf/<code>": "单只 ETF 详情",
            "/api/etf/search?q=xx": "模糊搜索",
            "/health": "健康检查"
        }
    })

# ===========================================================
#  健康检查
# ===========================================================

@app.route('/health')
def health():
    etfs = load_etf_data()
    return jsonify({
        "status": "ok",
        "version": "v2-pa",
        "etf_count": len(etfs),
        "data_file": str(DATA_FILE.name),
        "timestamp": datetime.now().isoformat()
    })

# ===========================================================
#  启动
# ===========================================================

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, use_reloader=False, host='0.0.0.0', port=port)
