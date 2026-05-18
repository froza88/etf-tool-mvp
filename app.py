from flask import Flask, render_template, request, jsonify
from datetime import datetime, timedelta
import etf_data
import os
import sys

app = Flask(__name__)

@app.route('/')
def index():
    """首页 - ETF列表和筛选器"""
    import time
    # 计算数据新鲜度
    data_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "etf_standard_data.json")
    data_mtime = "未知"
    if os.path.exists(data_file):
        mtime = os.path.getmtime(data_file)
        data_mtime = time.strftime("%Y-%m-%d %H:%M", time.localtime(mtime))
    return render_template('index.html', data_mtime=data_mtime)

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
    """ETF详情页 - 优先用 AKShare 实时价格覆盖静态数据"""
    etf = etf_data.get_etf_by_code(code)
    if not etf:
        return "ETF不存在", 404

    # 尝试用 AKShare 获取实时行情（单次单只，避免全量扫描性能问题）
    try:
        import akshare as ak
        # 使用 fund_etf_hist_em 获取最新一条日线数据（比 spot 更轻量）
        df = ak.fund_etf_hist_em(
            symbol=str(code),
            period='daily',
            start_date=(datetime.now() - timedelta(days=7)).strftime('%Y%m%d'),
            end_date=datetime.now().strftime('%Y%m%d'),
            adjust='qfq'
        )
        if df is not None and len(df) > 0:
            latest = df.iloc[-1]
            etf['close'] = float(latest['收盘'])
            etf['prev_close'] = float(latest['开盘'])  # 用开盘作为前收近似
            # 计算涨跌幅
            prev = etf.get('prev_close', etf['close'])
            if prev and prev > 0:
                etf['change_pct'] = round((etf['close'] - prev) / prev * 100, 2)
            # 成交额（亿元）
            amt = float(latest['成交额']) if '成交额' in latest else 0
            if amt > 1e8:
                etf['volume'] = round(amt / 1e8, 2)
            etf['_price_source'] = 'akshare_realtime'
    except Exception as e:
        print(f"实时价格获取失败 [{code}]: {e}", file=sys.stderr)
        etf['_price_source'] = 'static_cache'

    return render_template('detail.html', etf=etf)

@app.route('/compare')
def compare():
    """ETF对比页"""
    codes = request.args.get('codes', '').split(',')
    codes = [c for c in codes if c]  # 过滤空值

    etfs = []
    for code in codes:
        etf = etf_data.get_etf_by_code(code)
        if etf:
            etfs.append(etf)

    return render_template('compare.html', etfs=etfs)

@app.route('/compare/wind')
def compare_wind():
    """ETF对比页 - Wind风格专业版"""
    codes = request.args.get('codes', '').split(',')
    codes = [c for c in codes if c]
    etfs = []
    for code in codes:
        etf = etf_data.get_etf_by_code(code)
        if etf:
            etfs.append(etf)
    return render_template('compare_v2_wind.html', etfs=etfs)

@app.route('/screening-demo')
def screening_demo():
    """筛选演示页 - 新能源ETF筛选过程"""
    all_etfs = etf_data.get_all_etfs()

    # 筛选新能源相关ETF（名称包含关键词）
    keywords = ['新能源', '光伏', '新能源车', '电池', '风电', '电网', '碳中和']
    new_energy_etfs = []
    for etf in all_etfs:
        for keyword in keywords:
            if keyword in etf['name']:
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
        'passed': finalists[:3] if len(finalists) > 3 else finalists,  # 取前3名
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
    策略：首选本地缓存 → 回退AKShare实时 → 最终兜底模拟数据
    """
    import sys, os, math
    from datetime import datetime, timedelta

    ROOT = os.path.dirname(os.path.abspath(__file__))
    period = request.args.get('period', '1Y')
    periods_map = {'1M': 22, '3M': 66, '1Y': 252, '3Y': 756}
    limit = periods_map.get(period, 252)

    # ========== 策略1：首选本地历史缓存（最稳定，PA推荐） ==========
    try:
        cache_file = os.path.join(ROOT, "etf_history_cache.json")
        if os.path.exists(cache_file):
            with open(cache_file, encoding="utf-8") as f:
                cache = json.load(f)
            if code in cache:
                entry = cache[code]
                prices = entry.get('prices', [])
                dates = entry.get('dates', [])
                if len(prices) >= limit:
                    # 按周期截取
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

    # ========== 策略2：回退AKShare实时（本地开发用） ==========
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

    # ========== 策略3：模拟数据（最终兜底） ==========
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
    import subprocess, json, shutil, os

    ROOT = os.path.dirname(os.path.abspath(__file__))
    YINGMI_FILE = os.path.join(ROOT, "etf_yingmi_metrics.json")

    # 第1步：读本地 JSON 文件
    if os.path.exists(YINGMI_FILE):
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
        except:
            pass

    # 第2步：JSON 文件中没有，尝试调 CLI
    cli = shutil.which("yingmi-skill-cli")
    if not cli:
        mac_path = "/Users/apangduo/.workbuddy/binaries/node/versions/22.12.0/bin/yingmi-skill-cli"
        if os.path.exists(mac_path):
            cli = mac_path
    if not cli:
        return jsonify({"error": "盈米CLI未安装", "fallback": True}), 200

    cmd = f'{cli} mcp call GetBatchFundPerformance --input \'{"fundCodes":["{code}"]}\' 2>/dev/null'
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
                    except:
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

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=True, host='0.0.0.0', port=port)
