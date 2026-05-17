from flask import Flask, render_template, request, jsonify
import etf_data
import os

app = Flask(__name__)

@app.route('/')
def index():
    """首页 - ETF列表和筛选器"""
    return render_template('index.html')

@app.route('/api/etfs')
def get_etfs():
    """API：获取ETF列表（支持筛选、排序、分页）"""
    filters = {
        "type": request.args.get('type', ''),
        "scale_min": request.args.get('scale_min', ''),
        "scale_max": request.args.get('scale_max', ''),
        "fee_max": request.args.get('fee_max', ''),
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
    list_fields = ['code', 'name', 'issuer', 'scale', 'change_pct',
                   'year_1_return', 'year_3_return', 'close', 'volume', 'category']
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
    """ETF详情页"""
    etf = etf_data.get_etf_by_code(code)
    if not etf:
        return "ETF不存在", 404
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

@app.route('/screening-demo')
def screening_demo():
    """筛选演示页 - 新能源ETF筛选过程"""
    # 获取所有新能源相关ETF
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
    
    # 第二层：费率对比（使用动态参数或默认值0.6%）
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

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=True, host='0.0.0.0', port=port)
