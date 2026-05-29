from flask import Flask, render_template, request, jsonify
from datetime import datetime, timedelta
import etf_data
import etf_data_service
import json
import os
import sys
from pathlib import Path

app = Flask(__name__)

# 防浏览器缓存（开发阶段必须）
@app.after_request
def add_no_cache_header(response):
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

ROOT = Path(__file__).parent

# 方案C1：L2 数据内存缓存（避免 L1/L2 跳变）
# key = codes字符串（如 "510300,510500,159915"），value = {"etfs": [...], "updated": isoformat, "cached_at": timestamp}
_l2_memory_cache = {}
_L2_CACHE_TTL = 600  # 缓存有效期 10 分钟

# 性能优化：缓存默认数据服务（避免每个请求都创建）
_default_service = None
_default_service_mtime = 0

# AKShare 全市场 ETF 数据缓存（5分钟TTL，避免每次拉取全市场~20秒）
_akshare_cache = {"data": None, "timestamp": 0, "ttl": 300}

# AKShare ETF 现货字段显示顺序（按对比逻辑排列，字段名必须与 fund_etf_spot_em() 返回完全一致）
_AKSHARE_FIELD_ORDER = [
    # === 基本信息 ===
    "代码", "名称",
    # === 价格 ===
    "最新价", "IOPV实时估值", "基金折价率",
    "开盘价", "最高价", "最低价", "昨收",
    # === 涨跌 ===
    "涨跌幅", "涨跌额",
    # === 成交 ===
    "成交量", "成交额", "换手率", "量比",
    # === 资金流向 ===
    "主力净流入-净额", "主力净流入-净占比",
    "超大单净流入-净额", "超大单净流入-净占比",
    "大单净流入-净额", "大单净流入-净占比",
    "中单净流入-净额", "中单净流入-净占比",
    "小单净流入-净额", "小单净流入-净占比",
    # === 盘口 ===
    "委比", "外盘", "内盘", "现手", "买一", "卖一",
    # === 份额/市值 ===
    "最新份额", "流通市值", "总市值",
    # === 时间 ===
    "数据日期", "更新时间",
]

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

    # 数据更新时间：优先用 etf.updated，否则用数据文件修改时间
    data_updated = etf.get('updated', '')
    if not data_updated:
        try:
            import time
            mtime = os.path.getmtime(etf_data.STANDARD_DATA_FILE)
            data_updated = time.strftime("%Y-%m-%d %H:%M", time.localtime(mtime))
        except Exception:
            data_updated = ''
    etf['_data_updated'] = data_updated

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
    """ETF对比页 - Pro Terminal v3 炫酷版（L1基础+L2实时字段合并，无跳变）"""
    codes = request.args.get('codes', '')
    code_list = [c.strip() for c in codes.split(',') if c.strip()]
    
    # 第一步：加载 L1 本地数据（完整字段）
    etfs_l2 = []
    data_source = "local_db"
    try:
        from etf_data_service import LocalJSONSource
        local_source = LocalJSONSource()
        etfs_l2 = local_source.get_etfs_by_codes(code_list)
        print(f"[compare/v3] L1 数据加载成功: {len(etfs_l2)} 只 ETF", file=sys.stderr)
    except Exception as e:
        print(f"[compare/v3] L1 数据加载失败: {e}", file=sys.stderr)
        etfs_l2 = []
    
    # 第二步：加载 L2 实时字段（WeStock），合并到 L1 数据上
    if etfs_l2:
        try:
            from etf_data_service import WeStockSource
            westock_source = WeStockSource()  # 预加载用缓存保证稳定，客户端实时fetch才force_refresh
            etfs_l2_only = westock_source.get_etfs_by_codes(code_list)
            if etfs_l2_only:
                data_source = "local_db+westock"
                # L2 字段覆盖到 L1 数据上
                l2_map = {e['code']: e for e in etfs_l2_only if 'code' in e}
                for etf in etfs_l2:
                    l2_data = l2_map.get(etf.get('code'))
                    if l2_data:
                        for key, val in l2_data.items():
                            if key != 'code' and val is not None:
                                etf[key] = val
                print(f"[compare/v3] L2 字段合并完成: {len(etfs_l2_only)} 只", file=sys.stderr)
        except Exception as e:
            print(f"[compare/v3] L2 合并失败，使用纯 L1: {e}", file=sys.stderr)
    
    return render_template('compare_v3.html', codes=codes, etfs_l2=etfs_l2, data_source=data_source, updated=datetime.now().isoformat())


def update_l1_cache_from_l2(etfs_l2):
    """
    L2 数据更新后，同步更新 L1 缓存文件（etf_standard_data.json）
    这样下次打开页面时，L1 缓存就是最新的，避免数字跳变
    """
    try:
        from pathlib import Path
        import json
        
        STANDARD_FILE = Path(__file__).parent / "etf_standard_data.json"
        
        # 1. 加载 L1 缓存
        with open(STANDARD_FILE, encoding="utf-8") as f:
            l1_data = json.load(f)
        
        # 处理两种格式：list 或 {"etfs": []}
        l1_etfs = l1_data if isinstance(l1_data, list) else l1_data.get("etfs", [])
        l1_by_code = {etf.get("code", ""): etf for etf in l1_etfs}
        
        # 2. 更新 L1 缓存（只更新 L2 返回的 ETF）
        updated_count = 0
        for etf_l2 in etfs_l2:
            code = etf_l2.get("code", "")
            if code in l1_by_code:
                l1_etf = l1_by_code[code]
                # 更新关键字段（scale, close, change_pct 等），带范围验证
                fields_to_update = ["scale", "close", "change_pct", "prev_close", "volume"]
                for field in fields_to_update:
                    if field in etf_l2:
                        val = etf_l2[field]
                        # 范围验证：防止错误数据污染 L1 缓存
                        if field == "scale" and isinstance(val, (int, float)):
                            if 1e6 <= val <= 1e12:  # 100万 ~ 1万亿
                                l1_etf[field] = val
                            else:
                                print(f"[L1 Cache] {code} scale={val} 超出范围，跳过", file=sys.stderr)
                        elif field == "close" and isinstance(val, (int, float)):
                            if 0.1 <= val <= 100:  # ETF 价格合理范围
                                l1_etf[field] = val
                            else:
                                print(f"[L1 Cache] {code} close={val} 超出范围，跳过", file=sys.stderr)
                        elif field == "change_pct" and isinstance(val, (int, float)):
                            if -20 <= val <= 20:  # 涨跌幅 -20% ~ +20%
                                l1_etf[field] = val
                            else:
                                print(f"[L1 Cache] {code} change_pct={val} 超出范围，跳过", file=sys.stderr)
                        elif field == "volume" and isinstance(val, (int, float)):
                            if val >= 0:  # 成交量必须非负
                                l1_etf[field] = val
                            else:
                                print(f"[L1 Cache] {code} volume={val} 超出范围，跳过", file=sys.stderr)
                        else:
                            l1_etf[field] = val  # 其他字段直接更新
                updated_count += 1
        
        # 3. 保存 L1 缓存
        with open(STANDARD_FILE, "w", encoding="utf-8") as f:
            json.dump(l1_data, f, ensure_ascii=False, indent=2)
        
        print(f"[L1 Cache] 已同步更新 {updated_count} 只 ETF 的 L1 缓存", file=sys.stderr)
        
    except Exception as e:
        print(f"[L1 Cache] 更新 L1 缓存失败: {e}", file=sys.stderr)


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
    fresh = request.args.get('fresh', '0') == '1'  # fresh=1 强制刷新，跳过所有缓存
    
    if not codes:
        return jsonify({"error": "请提供ETF代码", "codes": []}), 400
    
    # 根据 source 参数选择数据源
    if source == 'westock':
        # L2: 先查内存缓存（避免重复调用 API 导致数据不一致）
        cache_key = ','.join(sorted(codes))
        cache_entry = _l2_memory_cache.get(cache_key)
        if not fresh and cache_entry and (datetime.now().timestamp() - cache_entry["cached_at"]) < _L2_CACHE_TTL:
            print(f"[API] L2 内存缓存命中: {cache_key}", file=sys.stderr)
            etfs = cache_entry["etfs"]
            data_source = "memory_cache_l2"
        else:
            # L2: 缓存未命中，调用 WeStockSource 获取数据
            try:
                from etf_data_service import WeStockSource
                westock_source = WeStockSource(force_refresh=fresh)
                etfs = westock_source.get_etfs_by_codes(codes)
                update_l1_cache_from_l2(etfs)
                data_source = "westock"
                # C1: 写入内存缓存（供后续 L1/L2 请求使用，避免跳变）
                _l2_memory_cache[cache_key] = {
                    "etfs": etfs,
                    "updated": datetime.now().isoformat(),
                    "cached_at": datetime.now().timestamp()
                }
            except Exception as e:
                print(f"[API] WeStockSource 调用失败: {e}", file=sys.stderr)
                # 降级：使用本地数据
                service = get_default_service()
                etfs = service.get_etfs_by_codes(codes)
                data_source = "local_db_fallback"
    else:
        # L1: 直接使用本地数据库（不走 L2 缓存，避免字段不全）
        service = get_default_service()
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
    colors = ['#00d4ff', '#f59e0b', '#f97316', '#7c3aed', '#ec4899', '#06b6d4']
    return render_template('compare_print.html', etfs=etfs, now=datetime.now().strftime('%Y-%m-%d %H:%M'), colors=colors)


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




# ========== AI 聊天分析接口 ==========
def _load_etf_by_codes(codes):
    """按代码列表加载 ETF 数据（从 etf_standard_data.json）"""
    data_file = ROOT / "etf_standard_data.json"
    if not data_file.exists():
        return []
    try:
        with open(data_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        etfs = data if isinstance(data, list) else data.get('etfs', [])
        code_set = set(codes)
        return [e for e in etfs if isinstance(e, dict) and e.get('code') in code_set]
    except Exception:
        return []

def _fmt_val(v, unit=''):
    if v is None or v == '': return '-'
    if isinstance(v, (int, float)):
        if unit == '亿': return f'{v/1e8:.1f}亿'
        if unit == '%': return f'{v*100:.2f}%'
        return f'{v:.2f}'
    return str(v)

def _generate_analysis(question, etfs):
    """基于规则和 ETF 数据生成分析文本（MVP 版本）"""
    if not etfs:
        return '未找到相关 ETF 数据。'
    
    lines = []
    lines.append(f'## ETF 对比分析（{len(etfs)} 只）')
    lines.append('')
    
    # 1. 基础信息表
    lines.append('| ETF | 规模 | 近1年 | 近3年 | 费率 | 夏普 |')
    lines.append('|-----|------|--------|--------|------|------|')
    for e in etfs:
        code = e.get('code', '-')
        name = e.get('name', '-')[:8]  # 截断
        scale = _fmt_val(e.get('scale'), '亿')
        y1 = _fmt_val(e.get('year_1_return'), '%')
        y3 = _fmt_val(e.get('year_3_return'), '%')
        fee = _fmt_val(e.get('fee_rate'), '%')
        sharpe = _fmt_val(e.get('sharpe_ratio'))
        lines.append(f'| {code} {name} | {scale} | {y1} | {y3} | {fee} | {sharpe} |')
    
    lines.append('')
    
    # 2. 优劣势分析
    lines.append('### 优劣势分析')
    for e in etfs:
        name = e.get('name', e.get('code', '-'))
        lines.append(f'**{name}**')
        # 优势
        pros = []
        if e.get('year_1_return') and e.get('year_1_return') > 0:
            pros.append(f'近1年收益 {e["year_1_return"]:.2f}%')
        if e.get('scale') and e.get('scale') > 1e9:
            pros.append(f'规模 {e["scale"]/1e8:.0f}亿，流动性好')
        if e.get('fee_rate') and e.get('fee_rate') < 0.003:
            pros.append(f'费率低（{e["fee_rate"]*100:.2f}%）')
        if pros:
            lines.append(f'- ✅ 优势：{", ".join(pros)}')
        # 劣势
        cons = []
        if e.get('max_drawdown') and e.get('max_drawdown') < -15:
            cons.append(f'最大回撤 {e["max_drawdown"]:.1f}%，风险较高')
        if e.get('annual_vol') and e.get('annual_vol') > 25:
            cons.append(f'波动率高（{e["annual_vol"]:.1f}%）')
        if e.get('fee_rate') and e.get('fee_rate') > 0.005:
            cons.append(f'费率偏高（{e["fee_rate"]*100:.2f}%）')
        if cons:
            lines.append(f'- ⚠️ 劣势：{", ".join(cons)}')
        lines.append('')
    
    # 3. 投资建议
    lines.append('### 投资建议')
    # 找出最优（夏普比率最高 or 收益最高）
    best = max(etfs, key=lambda e: e.get('sharpe_ratio') or e.get('year_1_return') or 0)
    lines.append(f'**推荐：{best.get("name", best.get("code"))}** —— 综合表现最优（夏普 {best.get("sharpe_ratio","N/A")}，近1年 {best.get("year_1_return","N/A")}%）')
    lines.append('')
    lines.append('⚠️ 本分析仅基于历史数据，不构成投资建议。投资有风险，决策需谨慎。')
    
    return '\n'.join(lines)


@app.route('/api/ai-chat', methods=['POST'])
def api_ai_chat():
    """AI 聊天分析接口 —— 接收用户问题 + ETF 代码，返回分析报告"""
    try:
        data = request.get_json(force=True)
        question = data.get('question', '').strip()
        codes = data.get('codes', [])
        
        if not question:
            return jsonify({'error': '问题不能为空'}), 400
        if not codes:
            return jsonify({'error': '未提供 ETF 代码'}), 400
        
        # 加载 ETF 数据
        etfs = _load_etf_by_codes(codes)
        if not etfs:
            return jsonify({'error': f'未找到代码 {codes} 的 ETF 数据'}), 404
        
        # 生成分析（规则引擎 MVP）
        answer = _generate_analysis(question, etfs)
        return jsonify({'answer': answer})
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500




# ========== 工具类 API（对比工具后端代理）==========
@app.route('/api/tools/akshare/etf-compare')
def api_tools_akshare_etf_compare():
    """
    AKShare ETF 对比 API - 代理 AKShare 实时数据
    带5分钟内存缓存，避免每次拉取全市场（~20秒）
    前端对比工具调用此接口，后端调 AKShare 并返回数据（解决 CORS 问题）
    """
    import time
    codes = request.args.get('codes', '').split(',')
    codes = [c.strip() for c in codes if c.strip()]

    if not codes:
        return jsonify({'error': '请提供 ETF 代码', 'etfs': []}), 400

    try:
        import akshare as ak
        import pandas as pd

        now = time.time()
        cache = _akshare_cache

        # ===== 缓存命中检查 =====
        if cache["data"] is not None and (now - cache["timestamp"]) < cache["ttl"]:
            df = cache["data"]
            cached = True
        else:
            # 拉取全市场 ETF 现货数据（慢，约10-20秒）
            df = ak.fund_etf_spot_em()
            if df is None or len(df) == 0:
                return jsonify({'error': 'AKShare 数据为空', 'etfs': []}), 500
            cache["data"] = df
            cache["timestamp"] = now
            cached = False

        # 筛选指定代码
        df['代码'] = df['代码'].astype(str).str.zfill(6)
        mask = df['代码'].isin([c.zfill(6) for c in codes])
        filtered = df[mask].copy()

        if len(filtered) == 0:
            return jsonify({
                'error': f'未找到代码 {codes} 的 ETF 数据',
                'etfs': [],
                'available_count': len(df)
            }), 404

        # 按用户输入的 codes 顺序排序
        code_order = {c.zfill(6): i for i, c in enumerate(codes)}
        filtered['__sort'] = filtered['代码'].map(code_order)
        filtered = filtered.sort_values('__sort').drop(columns=['__sort'])

        # 收集所有实际存在的字段
        actual_fields = list(filtered.columns)

        # 按 _AKSHARE_FIELD_ORDER 排序，未定义的放最后
        ordered_fields = []
        for f in _AKSHARE_FIELD_ORDER:
            if f in actual_fields:
                ordered_fields.append(f)
        for f in actual_fields:
            if f not in ordered_fields and not f.startswith('__'):
                ordered_fields.append(f)

        # 转换为前端需要的格式（按固定字段顺序）
        etfs = []
        for _, row in filtered.iterrows():
            etf = {}
            for col in ordered_fields:
                val = row[col]
                if pd.isna(val):
                    etf[col] = None
                elif isinstance(val, (pd.Timestamp,)):
                    etf[col] = str(val)
                else:
                    etf[col] = val
            etfs.append(etf)

        return jsonify({
            'etfs': etfs,
            'count': len(etfs),
            'source': 'akshare_api',
            'updated': datetime.now().isoformat(),
            'cached': cached,
            'cache_age_sec': int(now - cache["timestamp"]) if cached else 0
        })

    except ImportError:
        return jsonify({'error': 'AKShare 未安装，请运行 pip install akshare', 'etfs': []}), 500
    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        print(f"[API] AKShare 调用失败: {e}\n{error_detail}", file=__import__('sys').stderr)
        return jsonify({'error': str(e), 'etfs': []}), 500




@app.route('/tools/akshare-compare')
def tools_akshare_compare():
    """AKShare ETF 对比工具页面"""
    from flask import send_from_directory
    return send_from_directory('tools', 'akshare_etf_compare.html')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=True, use_reloader=False, host='0.0.0.0', port=port)

