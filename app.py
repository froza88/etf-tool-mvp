from flask import Flask, render_template, request, jsonify
from datetime import datetime, timedelta
import etf_data
import etf_data_service
import json
import os
import sys
from pathlib import Path

app = Flask(__name__)

ROOT = Path(__file__).parent

# 性能优化：缓存默认数据服务（避免每个请求都创建）
_default_service = None
_default_service_mtime = 0

def get_default_service():
    """获取缓存的默认数据服务（仅在数据文件变化时重建）"""
    global _default_service, _default_service_mtime
    
    data_file = ROOT / "etf_standard_data.json"
    if not data_file.exists():
        return etf_data_service.create_default_service()
    
    mtime = os.path.getmtime(data_file)
    if _default_service is None or mtime != _default_service_mtime:
        print(f"[app] 重建数据服务（数据文件已更新：{datetime.fromtimestamp(mtime)}）", file=sys.stderr)
        _default_service = etf_data_service.create_default_service()
        _default_service_mtime = mtime
    
    return _default_service


@app.route('/')
def index():
    """首页 - ETF列表和筛选器"""
    import time
    # 计算数据新鲜度
    data_file = ROOT / "etf_standard_data.json"
    data_mtime = "未知"
    if data_file.exists():
        mtime = os.path.getmtime(data_file)
        data_mtime = time.strftime("%Y-%m-%d %H:%M", time.localtime(mtime))

    # 读取版本信息
    meta_file = ROOT / "data" / "meta.json"
    version_info = ""
    if meta_file.exists():
        try:
            with open(meta_file, "r", encoding="utf-8") as f:
                meta = json.load(f)
            version_info = meta.get("last_update", "")
        except Exception:
            pass

    return render_template('index.html', data_mtime=data_mtime, version_info=version_info)


@app.route('/api/etfs')
def get_etfs():
    """API：获取ETF列表（支持筛选、排序、分页）"""
    filters = {
        "type": request.args.get('type', ''),
        "scale_min": request.args.get('scale_min', ''),
        "scale_max": request.args.get('scale_max', ''),
        "return_min": request.args.get('return_min', ''),
        "category": request.args.get('category', ''),
        "keyword": request.args.get('keyword', '')
    }
    filters = {k: v for k, v in filters.items() if v}

    # 排序（默认按代码升序）
    sort_by = request.args.get('sort_by', 'code')
    sort_order = request.args.get('sort_order', 'asc')
    reverse = sort_order == 'desc'

    # 分页
    page = int(request.args.get('page', 1))
    page_size = int(request.args.get('page_size', 50))
    offset = (page - 1) * page_size

    etfs = etf_data.filter_etfs(filters)

    # 排序（安全处理None值）
    def sort_key(e):
        val = e.get(sort_by, 0)
        return val if val is not None else 0

    etfs.sort(key=sort_key, reverse=reverse)

    total = len(etfs)
    paged = etfs[offset:offset + page_size]

    # 精简字段（列表页只需要这些）
    list_fields = ['code', 'name', 'issuer_short', 'scale', 'shares', 'change_pct',
                   'change_rate', 'close', 'prev_close', 'annual_vol',
                   'year_1_return', 'year_3_return', 'volume', 'category']
    slim = [{k: e.get(k, 0) for k in list_fields} for e in paged]

    return jsonify({
        'total': total,
        'page': page,
        'page_size': page_size,
        'total_pages': (total + page_size - 1) // page_size,
        'etfs': slim
    })


@app.route('/etf/<code>')
def etf_detail(code):
    """ETF详情页 - 纯本地数据渲染，不再实时调API
    v2: 移除了 AKShare 实时调用（PythonAnywhere 会超时）
    数据由 pipeline 定期更新，实时性依赖 pipeline 更新频率
    """
    etf = etf_data.get_etf_by_code(code)

    # 查询即存储：后台触发缓存更新
    from services.cache_updater import update_etf_cache_background
    update_etf_cache_background([code], source="detail_page")

    if not etf:
        return "ETF不存在", 404

    # 标记数据来源
    etf['_price_source'] = 'local_cache'

    return render_template('detail.html', etf=etf)


@app.route('/compare')
def compare():
    """ETF对比页 - Pro Terminal v3"""
    codes = request.args.get('codes', '')
    return render_template('compare_v3.html', codes=codes)


@app.route('/compare/wind')
def compare_wind():
    """ETF对比页 - Wind风格专业版"""
    codes = request.args.get('codes', '').split(',')
    codes = [c for c in codes if c]

    # 查询即存储：后台触发缓存更新
    from services.cache_updater import update_etf_cache_background
    update_etf_cache_background(codes, source="compare_page")

    etfs = []
    for code in codes:
        etf = etf_data.get_etf_by_code(code)
        if etf:
            etfs.append(etf)
    return render_template('compare_v2_wind.html', etfs=etfs)

@app.route('/compare/v3')
def compare_v3():
    """ETF对比页 - Pro Terminal v3 炫酷版（数据通过API加载）"""
    codes = request.args.get('codes', '')
    return render_template('compare_v3.html', codes=codes)


@app.route('/api/compare')
def api_compare():
    """API：获取对比ETF数据（查询即存储）
    
    参数：
    - codes: ETF代码列表（逗号分隔）
    - source: 数据源（可选，默认='local'）
      - 'local': 本地数据库（L1）
      - 'westock': WeStock API（L2）
    """
    codes = request.args.get('codes', '').split(',')
    codes = [c.strip() for c in codes if c.strip()]
    source = request.args.get('source', 'local')  # 默认使用本地数据
    
    if not codes:
        return jsonify({"error": "请提供ETF代码", "codes": []}), 400
    
    # 根据 source 参数选择数据源
    if source == 'westock':
        # L2: 使用 WeStockSource 直接获取数据
        try:
            from etf_data_service import WeStockSource
            westock_source = WeStockSource()
            etfs = westock_source.get_etfs_by_codes(codes)
            data_source = "westock"
        except Exception as e:
            print(f"[API] WeStockSource 调用失败: {e}", file=sys.stderr)
            # 降级：使用本地数据
            service = get_default_service()
            etfs = service.get_etfs_by_codes(codes)
            data_source = "local_db_fallback"
    else:
        # L1: 使用本地数据库（默认）
        service = get_default_service()
        
        # 直接使用 local_source，避免过期检查导致调用 WeStock
        local_source = service.local_source
        etfs = local_source.get_etfs_by_codes(codes)
        data_source = "local_db"
    
    if not etfs:
        return jsonify({"error": "未找到ETF数据", "codes": codes}), 404
    
    return jsonify({
        "codes": codes,
        "count": len(etfs),
        "etfs": etfs,
        "source": data_source,
        "updated": datetime.now().isoformat()
    })

@app.route('/compare/v3/print')
def compare_v3_print():
    """ETF对比页 - 打印友好版"""
    codes = request.args.get('codes', '').split(',')
    codes = [c for c in codes if c]
    etfs = []
    for code in codes:
        etf = etf_data.get_etf_by_code(code)
        if etf:
            etfs.append(etf)
    from datetime import datetime
    return render_template('compare_print.html', etfs=etfs, now=datetime.now().strftime('%Y-%m-%d %H:%M'))


@app.route('/screening-demo')
def screening_demo():
    """筛选演示页 - 新能源ETF筛选过程"""
    all_etfs = etf_data.get_all_etfs()

    # 筛选新能源相关ETF（名称包含关键词）
    keywords = ['新能源', '光伏', '新能源车', '电池', '风电', '电网', '碳中和']
    new_energy_etfs = []
    for etf in all_etfs:
        for keyword in keywords:
            if keyword in etf.get('name', ''):
                new_energy_etfs.append(etf)
                break

    # 去重（根据code）
    seen_codes = set()
    unique_etfs = []
    for etf in new_energy_etfs:
        if etf['code'] not in seen_codes:
            unique_etfs.append(etf)
            seen_codes.add(etf['code'])

    # 筛选过程
    screening_steps = []

    # 第一层：规模过滤
    step1_passed = [etf for etf in unique_etfs if 10 <= etf['scale'] <= 150]
    screening_steps.append({
        'step': 1,
        'name': '第一层筛选：规模过滤',
        'criteria': '规模 ≥ 10亿 且 ≤ 150亿',
        'passed': step1_passed,
        'eliminated_count': len(unique_etfs) - len(step1_passed)
    })

    # 第二层：规模
    step2_passed = [etf for etf in step1_passed if (etf.get('scale') or 0) >= 5]
    screening_steps.append({
        'step': 2,
        'name': '第二层筛选：规模',
        'criteria': '规模>= 5亿',
        'passed': step2_passed,
        'eliminated_count': len(step1_passed) - len(step2_passed)
    })

    # 第三层：流动性
    step3_passed = [etf for etf in step2_passed if (etf.get('volume') or 0) >= 1]
    screening_steps.append({
        'step': 3,
        'name': '第三层筛选：流动性',
        'criteria': '日均成交额>= 1亿',
        'passed': step3_passed,
        'eliminated_count': len(step2_passed) - len(step3_passed)
    })

    # 终选：综合评分
    if step3_passed:
        for etf in step3_passed:
            score = 0
            score += min((etf.get('scale') or 0) / 100, 1) * 40
            score += max(min((etf.get('year_1_return') or 0) / 50, 1), 0) * 35
            score += min((etf.get('volume') or 0) / 10, 1) * 25
            etf['score'] = round(score, 2)

        finalists = sorted(step3_passed, key=lambda x: x['score'], reverse=True)
        winner = finalists[0] if finalists else None
    else:
        finalists = []
        winner = None

    screening_steps.append({
        'step': 5,
        'name': '最终对比：综合评分',
        'criteria': '规模、费率、跟踪误差、流动性综合评分',
        'passed': finalists[:3] if len(finalists) > 3 else finalists,
        'winner': winner
    })

    return render_template(
        'screening-demo-v2.html',
        total_count=len(unique_etfs),
        screening_steps=screening_steps,
        winner=winner
    )


@app.route('/api/etf/<code>')
def get_etf_api(code):
    """API：获取单个ETF详情"""
    etf = etf_data.get_etf_by_code(code)
    if not etf:
        return jsonify({"error": "ETF不存在"}), 404
    return jsonify(etf)


@app.route('/api/etf/<code>/history')
def get_etf_history(code):
    """API：获取ETF历史净值（用于走势图）
    v2策略：本地历史文件 → 本地缓存 → AKShare实时 → 模拟数据
    """
    import math

    period = request.args.get('period', '1Y')
    periods_map = {'1M': 22, '3M': 66, '1Y': 252, '3Y': 756}
    limit = periods_map.get(period, 252)

    # ========== 策略1：从 data/history/ 独立文件读取（最稳定） ==========
    try:
        sys.path.insert(0, str(ROOT))
        from modules.local_store import load_etf_history as _load_history
        hist = _load_history(code)
        if hist and len(hist.get('prices', [])) >= limit:
            prices = hist['prices'][-limit:]
            dates = hist.get('dates', [])[-limit:] if hist.get('dates') else []
            base = prices[0]
            normalized = [round(p / base, 4) for p in prices]
            return jsonify({
                "code": code,
                "period": period,
                "prices": normalized,
                "dates": dates,
                "base_value": base,
                "source": "local_history",
                "count": len(prices),
                "updated": hist.get('updated', '')
            })
    except Exception as e:
        print(f"本地历史文件读取失败 [{code}]: {e}", file=sys.stderr)

    # ========== 策略2：从旧的全局缓存文件读取 ==========
    try:
        cache_file = ROOT / "etf_history_cache.json"
        if cache_file.exists():
            with open(cache_file, encoding="utf-8") as f:
                cache = json.load(f)
            if code in cache:
                entry = cache[code]
                prices = entry.get('prices', [])
                dates = entry.get('dates', [])
                if len(prices) >= limit:
                    prices = prices[-limit:]
                    dates = dates[-limit:] if dates else []
                    base = prices[0]
                    normalized = [round(p / base, 4) for p in prices]
                    return jsonify({
                        "code": code,
                        "period": period,
                        "prices": normalized,
                        "dates": dates,
                        "base_value": base,
                        "source": "local_cache",
                        "count": len(prices),
                        "updated": entry.get('updated', '')
                    })
    except Exception as e:
        print(f"本地缓存读取失败 [{code}]: {e}", file=sys.stderr)

    # ========== 策略3：AKShare实时（仅本地开发用，PythonAnywhere会超时） ==========
    if os.environ.get('FLASK_ENV') != 'production':
        try:
            import akshare as ak
            end_date = datetime.now()
            if period == '1M':
                start_date = end_date - timedelta(days=35)
            elif period == '3M':
                start_date = end_date - timedelta(days=100)
            elif period == '1Y':
                start_date = end_date - timedelta(days=400)
            else:
                start_date = end_date - timedelta(days=1100)

            df = ak.fund_etf_hist_em(
                symbol=str(code),
                period='daily',
                start_date=start_date.strftime('%Y%m%d'),
                end_date=end_date.strftime('%Y%m%d'),
                adjust='qfq'
            )
            if df is not None and len(df) > 0:
                prices = [float(v) for v in list(df['收盘'])]
                dates = [str(d) for d in list(df['日期'])]
                if len(prices) >= 5:
                    base = prices[0]
                    normalized = [round(p / base, 4) for p in prices]
                    # 同时保存到本地
                    try:
                        from modules.local_store import save_etf_history
                        save_etf_history(code, prices, dates, source="akshare")
                    except Exception:
                        pass
                    return jsonify({
                        "code": code,
                        "period": period,
                        "prices": normalized,
                        "dates": dates,
                        "base_value": base,
                        "source": "akshare_realtime",
                        "count": len(prices)
                    })
        except Exception as e:
            print(f"AKShare 历史数据失败 [{code}]: {e}", file=sys.stderr)

    # ========== 策略4：模拟数据（最终兜底） ==========
    etf = etf_data.get_etf_by_code(code)
    annual_return = etf.get('year_1_return', 0) if etf else 0

    data = []
    value = 1.0
    daily_return = (annual_return / 100) / 252

    for i in range(limit):
        volatility = 0.02
        randomReturn = (math.sin(i * 0.1) * 0.01) + daily_return + (math.cos(i * 0.3) * 0.005)
        value = value * (1 + randomReturn)
        data.append(round(value, 4))

    return jsonify({
        "code": code,
        "period": period,
        "prices": data,
        "dates": [],
        "base_value": 1.0,
        "source": "simulated",
        "count": len(data),
        "note": "数据暂不可用，显示模拟数据"
    })


@app.route('/api/risk/<code>')
def get_risk_api(code):
    """优先从本地盈米 JSON 读取，找不到再调 CLI"""
    import subprocess, shutil

    YINGMI_FILE = ROOT / "etf_yingmi_metrics.json"

    # 第1步：读本地 JSON 文件
    if YINGMI_FILE.exists():
        try:
            with open(YINGMI_FILE, "r", encoding="utf-8") as f:
                yingmi_data = json.load(f)
            if code in yingmi_data:
                d = yingmi_data[code]
                result = {}
                for p, r_field, vol_field, dd_field, sharpe_field in [
                    ("oneYear", "year_1_return", "annual_vol_1y", "max_drawdown", "sharpe_ratio"),
                    ("threeYear", "year_3_return", "annual_vol_3y", "dd_3y", "sharpe_3y"),
                ]:
                    ret = d.get(r_field, 0) or 0
                    vol = d.get(vol_field, 0) or 0
                    dd = d.get(dd_field, 0) or 0
                    sharpe = d.get(sharpe_field, 0) or 0
                    calmar = round(abs(ret / dd), 2) if dd and dd != 0 else 0
                    result[p] = {
                        "收益能力": ret,
                        "抗波动能力": vol,
                        "抗回撤能力": dd,
                        "投资性价比": sharpe,
                        "卡玛值": calmar,
                    }
                return jsonify(result)
        except Exception:
            pass

    # 第2步：JSON 文件中没有，尝试调 CLI
    cli = shutil.which("yingmi-skill-cli")
    if not cli:
        mac_path = "/Users/apangduo/.workbuddy/binaries/node/versions/22.12.0/bin/yingmi-skill-cli"
        if os.path.exists(mac_path):
            cli = mac_path
    if not cli:
        return jsonify({"error": "盈米CLI未安装", "fallback": True}), 200

    cmd = f'{cli} mcp call GetBatchFundPerformance --input \'{{"fundCodes":["{code}"]}}\' 2>/dev/null'
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=15)
        raw = json.loads(r.stdout)
        if not raw or 'error' in raw[0] if isinstance(raw, list) else True:
            return jsonify({"error": "盈米数据不可用", "fallback": True}), 200
        fund = raw[0]
        da = fund.get('data', {})
        metrics = da.get('metricsAnalyzes', [])
        result = {}
        for p in ['oneYear', 'twoYear', 'threeYear', 'fiveYear']:
            pm = next((m for m in metrics if m['stageType'] == p), None)
            if pm and pm.get('isValid'):
                ms = {}
                for mm in pm.get('metrics', []):
                    t = mm.get('title', '')
                    v = mm.get('metricsValueText', '')
                    try:
                        ms[t] = float(v.replace('%', ''))
                    except Exception:
                        ms[t] = v
                ret = ms.get('收益能力', 0)
                dd = ms.get('抗回撤能力', 0)
                ms['卡玛值'] = round(ret / abs(dd), 2) if dd and dd != 0 else 0
                result[p] = ms
            else:
                result[p] = {"收益能力": 0, "抗波动能力": 0, "抗回撤能力": 0, "投资性价比": 0, "卡玛值": 0}
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e), "fallback": True}), 200


@app.route('/risk/<code>')
def risk_page(code):
    """风险指标详情页"""
    return render_template('risk.html', code=code)


@app.route('/api/data-status')
def data_status():
    """API：数据状态概览"""
    meta_file = ROOT / "data" / "meta.json"
    status = {
        "version": "v2",
        "features": ["local_store", "versioned_snapshots", "redundant_backup", "per_etf_history"],
    }

    if meta_file.exists():
        try:
            with open(meta_file, "r", encoding="utf-8") as f:
                meta = json.load(f)
            status["last_update"] = meta.get("last_update", "")
            status["last_step"] = meta.get("last_step", "")
            status["stats"] = meta.get("current_stats", {})
        except Exception:
            pass

    # 快照数量
    snapshots_dir = ROOT / "data" / "snapshots"
    if snapshots_dir.exists():
        status["snapshot_count"] = len(list(snapshots_dir.glob("v_*.json")))

    # 历史数据覆盖
    history_dir = ROOT / "data" / "history"
    if history_dir.exists():
        status["history_etf_count"] = len(list(history_dir.glob("*.json")))

    return jsonify(status)


@ app.route('/api/version', methods=['GET'])
def get_version():
    """获取数据版本信息（供 verify_sync.py 检查）"""
    version_file = ROOT / "data_version.json"
    if not version_file.exists():
        return jsonify({"error": "data_version.json not found"}), 404
    
    try:
        with open(version_file, "r", encoding="utf-8") as f:
            version_data = json.load(f)
        return jsonify(version_data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@ app.route('/api/sync', methods=['POST'])
def sync_data():
    """同步数据：从 GitHub 拉取最新数据并更新版本（供 GitHub webhook 触发）"""
    # 认证检查
    token = request.args.get('token') or request.headers.get('X-Deploy-Token', '')
    expected = os.environ.get('DEPLOY_TOKEN', '')
    if not expected or token != expected:
        return jsonify({"error": "unauthorized"}), 401

    import subprocess
    repo_dir = str(ROOT)
    try:
        # 0. 强制同步到远程版本（丢弃本地修改，如 data_version.json）
        reset_result = subprocess.run(
            ['git', 'fetch', 'origin', 'main'],
            cwd=repo_dir, capture_output=True, text=True, timeout=30
        )
        reset_result = subprocess.run(
            ['git', 'reset', '--hard', 'origin/main'],
            cwd=repo_dir, capture_output=True, text=True, timeout=30
        )

        # 1. git pull 拉取最新代码
        result = subprocess.run(
            ['git', 'pull', 'origin', 'main'],
            cwd=repo_dir, capture_output=True, text=True, timeout=30
        )
        if result.returncode != 0:
            return jsonify({"error": result.stderr, "stdout": result.stdout}), 500

        # 2. 更新 data_version.json（标记为 pythonanywhere 来源）
        version_result = subprocess.run(
            ['python3', 'update_data_version.py', '--source', 'pythonanywhere'],
            cwd=repo_dir, capture_output=True, text=True, timeout=30
        )

        # 3. touch WSGI 文件触发 reload
        wsgi_file = '/var/www/froza_pythonanywhere_com_wsgi.py'
        if os.path.exists(wsgi_file):
            os.utime(wsgi_file, None)

        return jsonify({
            "status": "success",
            "git_reset": reset_result.stdout,
            "git_output": result.stdout,
            "version_output": version_result.stdout,
            "version_error": version_result.stderr
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=True, host='0.0.0.0', port=port)
