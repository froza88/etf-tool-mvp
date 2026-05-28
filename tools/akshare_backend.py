#!/usr/bin/env python3
"""
AKShare ETF 对比工具 - 后端 API

提供 AKShare ETF 现货行情数据 API，供前端 HTML 调用。

运行：
    python3 akshare_backend.py
    
访问：
    http://localhost:8888/
"""

from flask import Flask, jsonify, render_template_string, request
import akshare as ak
import pandas as pd
from datetime import datetime
import json

app = Flask(__name__)

# ========== 配置 ==========
PORT = 8888
DEBUG = True
BASE_DIR = Path(__file__).parent

# ========== 路由 ==========

@app.route('/')
def index():
    """返回 AKShare ETF 对比工具 HTML 页面"""
    html_file = BASE_DIR / 'akshare_etf_compare.html'
    with open(html_file, 'r', encoding='utf-8') as f:
        html_content = f.read()
    return render_template_string(html_content)

@app.route('/api/akshare/etf/spot')
def get_etf_spot():
    """
    获取 ETF 现货行情数据（AKShare）
    
    参数：
        codes: 逗号分隔的 ETF 代码列表（如 "510300,510500,159915"）
    
    返回：
        JSON 格式的 ETF 行情数据
    """
    codes = request.args.get('codes', '')
    if not codes:
        return jsonify({'error': '请提供 ETF 代码（codes 参数）'}), 400
    
    code_list = [c.strip() for c in codes.split(',')]
    
    try:
        # 获取全市场 ETF 行情
        df = ak.fund_etf_spot_em()
        
        # 筛选指定代码
        df_filtered = df[df['代码'].isin(code_list)]
        
        if df_filtered.empty:
            return jsonify({'error': f'未找到代码: {codes}'}), 404
        
        # 转换为字典列表
        result = []
        for _, row in df_filtered.iterrows():
            etf_data = {}
            for col in df.columns:
                value = row[col]
                # 处理 NaN/NaT
                if pd.isna(value):
                    etf_data[col] = None
                else:
                    etf_data[col] = value
            result.append(etf_data)
        
        return jsonify({
            'success': True,
            'count': len(result),
            'data': result,
            'fields': df.columns.tolist(),
            'update_time': datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/akshare/etf/list')
def get_etf_list():
    """
    获取 ETF 列表（用于前端下拉选择）
    
    返回：
        所有 ETF 的代码和名称
    """
    try:
        df = ak.fund_etf_spot_em()
        etf_list = []
        for _, row in df.iterrows():
            etf_list.append({
                'code': row['代码'],
                'name': row['名称']
            })
        return jsonify({
            'success': True,
            'count': len(etf_list),
            'data': etf_list
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/akshare/etf/hist')
def get_etf_hist():
    """
    获取 ETF 历史 K 线数据（AKShare）
    
    参数：
        code: ETF 代码（如 "510300"）
        start_date: 开始日期（如 "20240101"）
        end_date: 结束日期（如 "20241231"）
    
    返回：
        JSON 格式的 K 线数据
    """
    code = request.args.get('code', '')
    start_date = request.args.get('start_date', '20240101')
    end_date = request.args.get('end_date', datetime.now().strftime('%Y%m%d'))
    
    if not code:
        return jsonify({'error': '请提供 ETF 代码（code 参数）'}), 400
    
    try:
        df = ak.fund_etf_hist_em(
            symbol=code,
            period="daily",
            start_date=start_date,
            end_date=end_date,
            adjust="qfq"
        )
        
        if df.empty:
            return jsonify({'error': f'未找到 {code} 的历史数据'}), 404
        
        # 转换为字典列表
        result = []
        for _, row in df.iterrows():
            row_dict = {}
            for col in df.columns:
                value = row[col]
                if pd.isna(value):
                    row_dict[col] = None
                else:
                    row_dict[col] = value
            result.append(row_dict)
        
        return jsonify({
            'success': True,
            'code': code,
            'count': len(result),
            'data': result,
            'fields': df.columns.tolist()
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ========== 主入口 ==========

if __name__ == '__main__':
    print(f"AKShare ETF 对比工具后端启动...")
    print(f"访问地址: http://localhost:{PORT}/")
    print(f"API 文档:")
    print(f"  GET /api/akshare/etf/spot?codes=510300,510500")
    print(f"  GET /api/akshare/etf/list")
    print(f"  GET /api/akshare/etf/hist?code=510300&start_date=20240101")
    app.run(host='0.0.0.0', port=PORT, debug=DEBUG)
