"""
ETF 工具 Web 应用 — 方案C 简化版
架构：每日快照（首页列表）+ 实时聚合（对比页）
"""
from flask import Flask, render_template, request, jsonify, send_from_directory
from datetime import datetime, timedelta
import etf_data
import json
import os
import sys
from pathlib import Path

app = Flask(__name__)

@app.after_request
def add_no_cache_header(response):
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

ROOT = Path(__file__).parent


# ============================================================
#  页面路由
# ============================================================

@app.route('/')
def index():
    """首页 - ETF列表和筛选器（前端JS调 /api/etfs 取数据）"""
    import time
    data_file = ROOT / "etf_standard_data.json"
    data_mtime = time.strftime("%Y-%m-%d %H:%M", time.localtime(os.path.getmtime(data_file))) if data_file.exists() else "未知"

    meta_file = ROOT / "data" / "meta.json"
    version_info = ""
    if meta_file.exists():
        try:
            with open(meta_file, "r", encoding="utf-8") as f:
                version_info = json.load(f).get("last_update", "")
        except Exception:
            pass
    return render_template('index.html', data_mtime=data_mtime, version_info=version_info)


@app.route('/etf/<code>')
def etf_detail(code):
    """ETF详情页 - 纯本地数据渲染"""
    etf = etf_data.get_etf_by_code(code)
    if not etf:
        return "ETF不存在", 404

    from services.cache_updater import update_etf_cache_background
    update_etf_cache_background([code], source="detail_page")

    etf['_price_source'] = 'local_cache'
    data_updated = etf.get('updated', '')
    if not data_updated:
        try:
            import time
            data_updated = time.strftime("%Y-%m-%d %H:%M", time.localtime(os.path.getmtime(etf_data.STANDARD_DATA_FILE)))
        except Exception:
            data_updated = ''
    etf['_data_updated'] = data_updated
    return render_template('detail.html', etf=etf)


@app.route('/compare')
def compare():
    """ETF对比页 - 方案C：服务端 L1+ L2 聚合（合并 v3 + v3_v2）"""
    codes = request.args.get('codes', '')
    code_list = [c.strip() for c in codes.split(',') if c.strip()]
    etfs = []
    data_source = "local_db"

    if code_list:
        # L1: 本地快照
        try:
            from etf_data_service import LocalJSONSource
            etfs = LocalJSONSource().get_etfs_by_codes(code_list)
        except Exception as e:
            print(f"[compare] L1 加载失败: {e}", file=sys.stderr)
            etfs = []

        # L2: WeStock 实时字段叠加（排除 scale，保护 L1 权威规模数据）
        if etfs:
            try:
                from etf_data_service import WeStockSource
                l2_data = WeStockSource().get_etfs_by_codes(code_list)
                if l2_data:
                    data_source = "local_db+westock"
                    l2_map = {e['code']: e for e in l2_data if 'code' in e}
                    for etf in etfs:
                        l2 = l2_map.get(etf.get('code'))
                        if l2:
                            for k, v in l2.items():
                                if k not in ('code', 'scale') and v is not None:
                                    etf[k] = v
            except Exception as e:
                print(f"[compare] L2 合并失败，使用纯 L1: {e}", file=sys.stderr)

    return render_template('compare_v3_v2.html', codes=codes, etfs_l2=etfs,
                           data_source=data_source, updated=datetime.now().isoformat())


@app.route('/risk/<code>')
def risk_page(code):
    return render_template('risk.html', code=code)


# ============================================================
#  数据 API
# ============================================================

@app.route('/api/etfs')
def get_etfs():
    """ETF列表 API：筛选、排序、分页"""
    filters = {k: v for k, v in {
        "type": request.args.get('type', ''),
        "scale_min": request.args.get('scale_min', ''),
        "scale_max": request.args.get('scale_max', ''),
        "return_min": request.args.get('return_min', ''),
        "category": request.args.get('category', ''),
        "keyword": request.args.get('keyword', '')
    }.items() if v}

    sort_by = request.args.get('sort_by', 'code')
    sort_order = request.args.get('sort_order', 'asc')
    page, page_size = int(request.args.get('page', 1)), int(request.args.get('page_size', 50))
    offset = (page - 1) * page_size

    etfs = etf_data.filter_etfs(filters)
    etfs.sort(key=lambda e: e.get(sort_by, 0) or 0, reverse=(sort_order == 'desc'))

    total = len(etfs)
    slim_fields = ['code', 'name', 'issuer_short', 'scale', 'shares', 'change_pct',
                   'change_rate', 'close', 'prev_close', 'annual_vol',
                   'year_1_return', 'year_3_return', 'volume', 'category']
    slim = [{k: e.get(k, 0) for k in slim_fields} for e in etfs[offset:offset + page_size]]

    return jsonify({
        'total': total, 'page': page, 'page_size': page_size,
        'total_pages': (total + page_size - 1) // page_size, 'etfs': slim
    })


@app.route('/api/etf/search')
def api_etf_search():
    """搜索 ETF（按代码或名称模糊匹配）"""
    q = request.args.get('q', '').strip()
    limit = int(request.args.get('limit', '15'))
    if not q:
        return jsonify({"results": [], "total": 0})

    try:
        with open(ROOT / 'etf_standard_data.json', 'r', encoding='utf-8') as f:
            all_etfs = json.load(f)
    except Exception:
        return jsonify({"results": [], "total": 0})

    q_lower = q.lower()
    results = []
    for e in all_etfs:
        if q_lower in e.get('code', '').lower() or q_lower in e.get('name', '').lower():
            results.append({
                "code": e.get("code"), "name": e.get("name"),
                "category": e.get("category"), "issuer": e.get("issuer"),
                "scale": e.get("scale"), "close": e.get("close"),
                "year_1_return": e.get("year_1_return"), "change_rate": e.get("change_rate", 0),
            })
    total = len(results)
    return jsonify({"results": results[:limit], "total": total})


@app.route('/api/etf/<code>')
def get_etf_api(code):
    etf = etf_data.get_etf_by_code(code)
    return jsonify({"error": "ETF不存在"}), 404 if not etf else jsonify(etf)


@app.route('/api/etf/<code>/history')
def get_etf_history(code):
    """ETF历史净值 API — 三层回退：本地历史文件 → 旧缓存 → 模拟数据"""
    import math
    period = request.args.get('period', '1Y')
    periods_map = {'1M': 22, '3M': 66, '1Y': 252, '3Y': 756}
    limit = periods_map.get(period, 252)

    def _normalize_return(prices, dates=None):
        base = prices[0]
        normalized = [round(p / base, 4) for p in prices]
        return normalized, dates or [], base

    # 策略1：本地独立历史文件
    try:
        sys.path.insert(0, str(ROOT))
        from modules.local_store import load_etf_history
        hist = load_etf_history(code)
        if hist and len(hist.get('prices', [])) >= limit:
            prices = hist['prices'][-limit:]
            dates = hist.get('dates', [])[-limit:] if hist.get('dates') else []
            norm, d, base = _normalize_return(prices, dates)
            return jsonify({"code": code, "period": period, "prices": norm, "dates": d,
                            "base_value": base, "source": "local_history", "count": len(prices),
                            "updated": hist.get('updated', '')})
    except Exception as e:
        print(f"本地历史读取失败 [{code}]: {e}", file=sys.stderr)

    # 策略2：旧全局缓存
    try:
        cache_file = ROOT / "etf_history_cache.json"
        if cache_file.exists():
            with open(cache_file, encoding="utf-8") as f:
                cache = json.load(f)
            if code in cache:
                entry = cache[code]
                prices = entry.get('prices', [])[-limit:]
                norm, d, base = _normalize_return(prices, entry.get('dates', [])[-limit:] if entry.get('dates') else [])
                if len(prices) >= limit:
                    return jsonify({"code": code, "period": period, "prices": norm, "dates": d,
                                    "base_value": base, "source": "local_cache", "count": len(prices),
                                    "updated": entry.get('updated', '')})
    except Exception as e:
        print(f"缓存读取失败 [{code}]: {e}", file=sys.stderr)

    # 策略3：模拟数据（最终兜底）
    etf = etf_data.get_etf_by_code(code)
    annual_return = etf.get('year_1_return', 0) if etf else 0
    daily_return = (annual_return / 100) / 252
    data = []
    value = 1.0
    for i in range(limit):
        value *= (1 + math.sin(i * 0.1) * 0.01 + daily_return + math.cos(i * 0.3) * 0.005)
        data.append(round(value, 4))
    return jsonify({"code": code, "period": period, "prices": data, "dates": [],
                    "base_value": 1.0, "source": "simulated", "count": len(data),
                    "note": "数据暂不可用，显示模拟数据"})


@app.route('/api/compare')
def api_compare():
    """对比数据 API — 方案C简化版：L1本地 + L2 WeStock 叠加（无内存缓存）"""
    codes = [c.strip() for c in request.args.get('codes', '').split(',') if c.strip()]
    if not codes:
        return jsonify({"error": "请提供ETF代码"}), 400

    from etf_data_service import LocalJSONSource, WeStockSource

    try:
        etfs = LocalJSONSource().get_etfs_by_codes(codes)
        data_source = "local_db"
    except Exception as e:
        print(f"[api/compare] L1 失败: {e}", file=sys.stderr)
        return jsonify({"error": "数据加载失败", "codes": codes}), 500

    # L2 WeStock 叠加（排除 scale）
    if etfs:
        try:
            l2_data = WeStockSource().get_etfs_by_codes(codes)
            if l2_data:
                data_source = "local_db+westock"
                l2_map = {e['code']: e for e in l2_data if 'code' in e}
                for etf in etfs:
                    l2 = l2_map.get(etf.get('code'))
                    if l2:
                        for k, v in l2.items():
                            if k not in ('code', 'scale') and v is not None:
                                etf[k] = v
        except Exception as e:
            print(f"[api/compare] L2 合并失败: {e}", file=sys.stderr)

    return jsonify({"codes": codes, "count": len(etfs), "etfs": etfs,
                    "source": data_source, "updated": datetime.now().isoformat()})


# ============================================================
#  风险 API
# ============================================================

@app.route('/api/risk/<code>')
def get_risk_api(code):
    """风险指标 API — 优先本地 JSON，回退 CLI"""
    import subprocess, shutil
    YINGMI_FILE = ROOT / "etf_yingmi_metrics.json"

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
                    result[p] = {"收益能力": ret, "抗波动能力": vol, "抗回撤能力": dd, "投资性价比": sharpe, "卡玛值": calmar}
                return jsonify(result)
        except Exception:
            pass

    # CLI 回退
    cli = shutil.which("yingmi-skill-cli")
    if not cli:
        mac_path = "/Users/apangduo/.workbuddy/binaries/node/versions/22.12.0/bin/yingmi-skill-cli"
        if os.path.exists(mac_path):
            cli = mac_path
    if not cli:
        return jsonify({"error": "盈米CLI未安装", "fallback": True}), 200

    try:
        cmd = f'{cli} mcp call GetBatchFundPerformance --input \'{{"fundCodes":["{code}"]}}\' 2>/dev/null'
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=15)
        raw = json.loads(r.stdout)
        if not raw or (isinstance(raw, list) and 'error' in raw[0]):
            return jsonify({"error": "盈米数据不可用", "fallback": True}), 200
        fund = raw[0]
        metrics = fund.get('data', {}).get('metricsAnalyzes', [])
        result = {}
        for p in ['oneYear', 'twoYear', 'threeYear', 'fiveYear']:
            pm = next((m for m in metrics if m['stageType'] == p), None)
            if pm and pm.get('isValid'):
                ms = {}
                for mm in pm.get('metrics', []):
                    t = mm.get('title', '')
                    try:
                        ms[t] = float(mm.get('metricsValueText', '').replace('%', ''))
                    except Exception:
                        ms[t] = mm.get('metricsValueText', '')
                ret = ms.get('收益能力', 0)
                dd = ms.get('抗回撤能力', 0)
                ms['卡玛值'] = round(ret / abs(dd), 2) if dd and dd != 0 else 0
                result[p] = ms
            else:
                result[p] = {"收益能力": 0, "抗波动能力": 0, "抗回撤能力": 0, "投资性价比": 0, "卡玛值": 0}
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e), "fallback": True}), 200


# ============================================================
#  运维 API
# ============================================================

@app.route('/api/data-status')
def data_status():
    """数据状态概览"""
    meta_file = ROOT / "data" / "meta.json"
    status = {"version": "v2", "features": ["local_store", "versioned_snapshots", "per_etf_history"]}

    if meta_file.exists():
        try:
            with open(meta_file, "r", encoding="utf-8") as f:
                meta = json.load(f)
            status.update({
                "last_update": meta.get("last_update", ""),
                "last_step": meta.get("last_step", ""),
                "stats": meta.get("current_stats", {})
            })
        except Exception:
            pass

    snapshots_dir = ROOT / "data" / "snapshots"
    if snapshots_dir.exists():
        status["snapshot_count"] = len(list(snapshots_dir.glob("v_*.json")))

    history_dir = ROOT / "data" / "history"
    if history_dir.exists():
        status["history_etf_count"] = len(list(history_dir.glob("*.json")))

    return jsonify(status)


@app.route('/api/version')
def get_version():
    version_file = ROOT / "data_version.json"
    if not version_file.exists():
        return jsonify({"error": "data_version.json not found"}), 404
    try:
        with open(version_file, "r", encoding="utf-8") as f:
            return jsonify(json.load(f))
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/sync', methods=['POST'])
def sync_data():
    """GitHub webhook 数据同步"""
    import subprocess
    token = request.args.get('token') or request.headers.get('X-Deploy-Token', '')
    if not os.environ.get('DEPLOY_TOKEN') or token != os.environ['DEPLOY_TOKEN']:
        return jsonify({"error": "unauthorized"}), 401

    repo_dir = str(ROOT)
    try:
        subprocess.run(['git', 'fetch', 'origin', 'main'], cwd=repo_dir, capture_output=True, text=True, timeout=30)
        subprocess.run(['git', 'reset', '--hard', 'origin/main'], cwd=repo_dir, capture_output=True, text=True, timeout=30)
        result = subprocess.run(['git', 'pull', 'origin', 'main'], cwd=repo_dir, capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            return jsonify({"error": result.stderr}), 500

        version_result = subprocess.run(
            ['python3', 'update_data_version.py', '--source', 'pythonanywhere'],
            cwd=repo_dir, capture_output=True, text=True, timeout=30
        )

        wsgi_file = '/var/www/froza_pythonanywhere_com_wsgi.py'
        if os.path.exists(wsgi_file):
            os.utime(wsgi_file, None)

        return jsonify({"status": "success", "git_output": result.stdout,
                        "version_output": version_result.stdout})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============================================================
#  AI 聊天分析
# ============================================================

def _load_etf_by_codes(codes):
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


def _generate_analysis(etfs):
    """基于规则生成分析（MVP 版）"""
    if not etfs:
        return '未找到相关 ETF 数据。'

    lines = [f'## ETF 对比分析（{len(etfs)} 只）', '']
    lines.append('| ETF | 规模 | 近1年 | 近3年 | 费率 | 夏普 |')
    lines.append('|-----|------|--------|--------|------|------|')
    for e in etfs:
        code, name = e.get('code', '-'), (e.get('name', '-') or '')[:8]
        scale = f'{e.get("scale", 0)/1e8:.1f}亿' if e.get('scale') else '-'
        y1 = f'{e.get("year_1_return", 0):.2f}%' if e.get('year_1_return') else '-'
        y3 = f'{e.get("year_3_return", 0):.2f}%' if e.get('year_3_return') else '-'
        fee = f'{e.get("fee_rate", 0)*100:.2f}%' if e.get('fee_rate') else '-'
        sharpe = f'{e.get("sharpe_ratio", 0):.2f}' if e.get('sharpe_ratio') else '-'
        lines.append(f'| {code} {name} | {scale} | {y1} | {y3} | {fee} | {sharpe} |')

    lines += ['', '### 优劣势分析']
    for e in etfs:
        name = e.get('name', e.get('code', '-'))
        lines.append(f'**{name}**')
        pros, cons = [], []
        if e.get('year_1_return') and e['year_1_return'] > 0:
            pros.append(f'近1年收益 {e["year_1_return"]:.2f}%')
        if (e.get('scale') or 0) > 1e9:
            pros.append(f'规模 {e["scale"]/1e8:.0f}亿，流动性好')
        if e.get('fee_rate') and e['fee_rate'] < 0.003:
            pros.append(f'费率低（{e["fee_rate"]*100:.2f}%）')
        if e.get('max_drawdown') and e['max_drawdown'] < -15:
            cons.append(f'最大回撤 {e["max_drawdown"]:.1f}%，风险较高')
        if (e.get('annual_vol') or 0) > 25:
            cons.append(f'波动率高（{e["annual_vol"]:.1f}%）')
        if e.get('fee_rate') and e['fee_rate'] > 0.005:
            cons.append(f'费率偏高（{e["fee_rate"]*100:.2f}%）')
        if pros:
            lines.append(f'- ✅ 优势：{", ".join(pros)}')
        if cons:
            lines.append(f'- ⚠️ 劣势：{", ".join(cons)}')
        lines.append('')

    best = max(etfs, key=lambda e: e.get('sharpe_ratio') or e.get('year_1_return') or 0)
    lines += ['### 投资建议',
              f'**推荐：{best.get("name", best.get("code"))}** —— 综合表现最优（夏普 {best.get("sharpe_ratio","N/A")}，近1年 {best.get("year_1_return","N/A")}%）',
              '', '⚠️ 本分析仅基于历史数据，不构成投资建议。']
    return '\n'.join(lines)


@app.route('/api/ai-chat', methods=['POST'])
def api_ai_chat():
    try:
        data = request.get_json(force=True)
        question = data.get('question', '').strip()
        codes = data.get('codes', [])
        if not question or not codes:
            return jsonify({'error': '问题或代码不能为空'}), 400
        etfs = _load_etf_by_codes(codes)
        if not etfs:
            return jsonify({'error': f'未找到代码 {codes} 的 ETF 数据'}), 404
        return jsonify({'answer': _generate_analysis(etfs)})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


# ============================================================
#  筛选演示 / V2
# ============================================================

@app.route('/screening-demo')
def screening_demo():
    """筛选演示页 - 新能源ETF筛选过程"""
    all_etfs = etf_data.get_all_etfs()
    keywords = ['新能源', '光伏', '新能源车', '电池', '风电', '电网', '碳中和']
    new_energy_etfs = []
    seen = set()
    for etf in all_etfs:
        for kw in keywords:
            if kw in etf.get('name', '') and etf['code'] not in seen:
                new_energy_etfs.append(etf)
                seen.add(etf['code'])
                break

    steps = []
    # 第一层：规模 10-150亿
    s1 = [e for e in new_energy_etfs if 10 <= (e.get('scale') or 0) <= 150]
    steps.append({'step': 1, 'name': '规模过滤（10-150亿）', 'passed': s1, 'eliminated_count': len(new_energy_etfs) - len(s1)})

    # 第二层：规模>=5亿
    s2 = [e for e in s1 if (e.get('scale') or 0) >= 5]
    steps.append({'step': 2, 'name': '规模>=5亿', 'passed': s2, 'eliminated_count': len(s1) - len(s2)})

    # 第三层：日均成交额>=1亿
    s3 = [e for e in s2 if (e.get('volume') or 0) >= 1]
    steps.append({'step': 3, 'name': '日均成交额>=1亿', 'passed': s3, 'eliminated_count': len(s2) - len(s3)})

    # 终选：综合评分
    winner = None
    if s3:
        for e in s3:
            score = min((e.get('scale') or 0) / 100, 1) * 40
            score += max(min((e.get('year_1_return') or 0) / 50, 1), 0) * 35
            score += min((e.get('volume') or 0) / 10, 1) * 25
            e['score'] = round(score, 2)
        finalists = sorted(s3, key=lambda x: x['score'], reverse=True)
        winner = finalists[0]
        steps.append({'step': 5, 'name': '综合评分', 'passed': finalists[:3], 'winner': winner})
    else:
        steps.append({'step': 5, 'name': '综合评分', 'passed': [], 'winner': None})

    return render_template('screening-demo-v2.html', total_count=len(new_energy_etfs),
                          screening_steps=steps, winner=winner)


@app.route('/v2')
def v2_index():
    return send_from_directory(str(ROOT / 'v2' / 'frontend'), 'index.html')


# ============================================================
#  启动 & 扩展注册
# ============================================================

# 注册工具 API（AKShare / WeStock 代理）
from tools.tools_api import register_tools_api
register_tools_api(app)

# ============================================================
#  项目状态仪表盘
# ============================================================

@app.route('/state')
def state_dashboard():
    """项目状态仪表盘——读取 STATE.md 渲染为可视化面板"""
    from pathlib import Path
    state_file = Path(__file__).parent / '.workbuddy' / 'memory' / 'STATE.md'
    state_md = ""
    if state_file.exists():
        state_md = state_file.read_text(encoding='utf-8')
    return render_template('state.html', state_md=state_md, updated=datetime.now().isoformat())

@app.route('/api/state')
def api_state():
    """返回 STATE.md 原始内容"""
    from pathlib import Path
    state_file = Path(__file__).parent / '.workbuddy' / 'memory' / 'STATE.md'
    if state_file.exists():
        return state_file.read_text(encoding='utf-8'), 200, {'Content-Type': 'text/plain; charset=utf-8'}
    return "STATE.md 不存在", 404

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=True, use_reloader=False, host='0.0.0.0', port=port)
