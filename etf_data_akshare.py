#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ETF真实数据获取模块 (基于 AkShare)
版本: 2.0
数据来源: AkShare (免费、开源金融数据接口)

功能:
1. 获取ETF基金基本信息（规模、费率、成立日期、发行人）
2. 获取ETF历史净值数据
3. 计算真实指标（收益率、最大回撤、夏普比率等）
4. 获取ETF持仓数据
"""

import os
import json
import time
import akshare as ak
import pandas as pd
from datetime import datetime, timedelta

# 缓存配置
CACHE_DIR = 'cache'
CACHE_VALIDITY_DAYS = 1
CACHE_META_FILE = os.path.join(CACHE_DIR, 'etf_cache_meta.json')

# 确保缓存目录存在
os.makedirs(CACHE_DIR, exist_ok=True)


def get_cache_meta():
    """读取缓存元数据"""
    if os.path.exists(CACHE_META_FILE):
        with open(CACHE_META_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


def save_cache_meta(meta):
    """保存缓存元数据"""
    with open(CACHE_META_FILE, 'w', encoding='utf-8') as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)


def is_cache_valid(cache_file):
    """检查缓存是否有效（1天内）"""
    if not os.path.exists(cache_file):
        return False
    
    mtime = os.path.getmtime(cache_file)
    age_hours = (time.time() - mtime) / 3600
    
    return age_hours < (CACHE_VALIDITY_DAYS * 24)


def fetch_etf_fund_info(etf_code):
    """
    获取ETF基金基本信息
    
    参数:
        etf_code: ETF代码，如 "510300"
    
    返回:
        dict: {
            'scale': float,      # 规模（亿元）
            'fee': float,         # 管理费率（%）
            'launch_date': str,   # 成立日期 YYYY-MM-DD
            'issuer': str,        # 基金管理人
            'name': str,          # ETF名称
        }
    """
    try:
        # AkShare接口：fund_etf_fund_info_em
        # 注意：参数名是 fund，不是 symbol
        df = ak.fund_etf_fund_info_em(
            fund=etf_code,
            start_date="20200101",
            end_date=datetime.now().strftime("%Y%m%d")
        )
        
        if df.empty:
            return None
        
        # 提取关键信息
        info = {
            'name': df.iloc[0].get('基金简称', etf_code),
            'scale': float(df.iloc[0].get('基金规模', 0)),
            'fee': float(df.iloc[0].get('管理费率', 0)),
            'launch_date': str(df.iloc[0].get('成立日期', '')),
            'issuer': df.iloc[0].get('基金管理人', ''),
        }
        
        return info
        
    except Exception as e:
        print(f"获取ETF {etf_code} 基本信息失败: {e}")
        return None


def fetch_etf_hist_data(etf_code, start_date="20200101"):
    """
    获取ETF历史净值数据
    
    参数:
        etf_code: ETF代码
        start_date: 起始日期 YYYYMMDD
    
    返回:
        DataFrame: 包含日期、净值、涨跌幅等
    """
    try:
        # AkShare接口：fund_etf_hist_em
        # 注意：日期格式必须是 YYYYMMDD
        end_date = datetime.now().strftime("%Y%m%d")
        
        df = ak.fund_etf_hist_em(
            symbol=etf_code,
            period="daily",
            start_date=start_date,
            end_date=end_date
        )
        
        return df
        
    except Exception as e:
        print(f"获取ETF {etf_code} 历史数据失败: {e}")
        return None


def calculate_metrics_from_hist(df_hist):
    """
    基于历史数据计算真实指标
    
    参数:
        df_hist: 历史净值DataFrame
    
    返回:
        dict: {
            'year_1_return': float,    # 近1年收益率
            'year_3_return': float,    # 近3年收益率
            'max_drawdown': float,     # 最大回撤
            'sharpe_ratio': float,     # 夏普比率
            'volatility': float,       # 波动率
        }
    """
    if df_hist is None or df_hist.empty:
        return {
            'year_1_return': 0,
            'year_3_return': 0,
            'max_drawdown': 0,
            'sharpe_ratio': 0,
            'volatility': 0,
        }
    
    try:
        # 确保日期列是datetime类型
        df_hist['日期'] = pd.to_datetime(df_hist['日期'])
        df_hist = df_hist.sort_values('日期')
        
        # 净值列
        net_value_col = '净值' if '净值' in df_hist.columns else '累计净值'
        df_hist['净值'] = df_hist[net_value_col].astype(float)
        
        # 计算收益率
        today = datetime.now()
        one_year_ago = today - timedelta(days=365)
        three_years_ago = today - timedelta(days=3*365)
        
        # 近1年收益率
        df_1y = df_hist[df_hist['日期'] >= one_year_ago]
        if len(df_1y) > 1:
            year_1_return = ((df_1y['净值'].iloc[-1] / df_1y['净值'].iloc[0]) - 1) * 100
        else:
            year_1_return = 0
        
        # 近3年收益率
        df_3y = df_hist[df_hist['日期'] >= three_years_ago]
        if len(df_3y) > 1:
            year_3_return = ((df_3y['净值'].iloc[-1] / df_3y['净值'].iloc[0]) - 1) * 100
        else:
            year_3_return = 0
        
        # 最大回撤
        df_hist['累计最大值'] = df_hist['净值'].cummax()
        df_hist['回撤'] = (df_hist['净值'] - df_hist['累计最大值']) / df_hist['累计最大值'] * 100
        max_drawdown = df_hist['回撤'].min()
        
        # 波动率（年化）
        df_hist['日收益率'] = df_hist['净值'].pct_change()
        volatility = df_hist['日收益率'].std() * (252 ** 0.5) * 100
        
        # 夏普比率（假设无风险利率为3%）
        risk_free_rate = 3.0
        annual_return = year_1_return
        sharpe_ratio = (annual_return - risk_free_rate) / volatility if volatility > 0 else 0
        
        return {
            'year_1_return': round(year_1_return, 2),
            'year_3_return': round(year_3_return, 2),
            'max_drawdown': round(max_drawdown, 2),
            'sharpe_ratio': round(sharpe_ratio, 2),
            'volatility': round(volatility, 2),
        }
        
    except Exception as e:
        print(f"计算指标失败: {e}")
        return {
            'year_1_return': 0,
            'year_3_return': 0,
            'max_drawdown': 0,
            'sharpe_ratio': 0,
            'volatility': 0,
        }


def fetch_etf_holdings(etf_code):
    """
    获取ETF持仓股票数据
    
    参数:
        etf_code: ETF代码
    
    返回:
        list: ['股票名称 占比%', ...]
    """
    try:
        # 尝试从东方财富网获取
        import requests
        from bs4 import BeautifulSoup
        
        url = f"https://fund.eastmoney.com/{etf_code}.html"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        response.encoding = 'utf-8'
        
        if response.status_code != 200:
            return None
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 查找持仓表格
        holdings = []
        tables = soup.find_all('table')
        
        for table in tables:
            rows = table.find_all('tr')
            for row in rows[1:11]:  # 前10大持仓
                cols = row.find_all('td')
                if len(cols) >= 3:
                    stock_name = cols[1].get_text(strip=True)
                    holding_pct = cols[2].get_text(strip=True)
                    
                    if stock_name and '%' in holding_pct:
                        holdings.append(f"{stock_name} {holding_pct}")
                
                if len(holdings) >= 10:
                    break
            
            if holdings:
                break
        
        return holdings if holdings else None
        
    except Exception as e:
        print(f"获取ETF {etf_code} 持仓数据失败: {e}")
        return None


def get_all_etfs_with_real_data(etf_code_list, use_cache=True, fetch_real_data=True):
    """
    获取所有ETF的真实数据
    
    参数:
        etf_code_list: ETF代码列表
        use_cache: 是否使用缓存
        fetch_real_data: 是否获取真实数据
    
    返回:
        list: ETF数据列表
    """
    cache_file = os.path.join(CACHE_DIR, 'etf_data_real.json')
    
    # 检查缓存
    if use_cache and is_cache_valid(cache_file):
        print(f"✅ 使用缓存数据: {cache_file}")
        with open(cache_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    # 获取真实数据
    if not fetch_real_data:
        print("⚠️  未获取真实数据（fetch_real_data=False）")
        return []
    
    print(f"🌐 正在获取 {len(etf_code_list)} 只ETF的真实数据...")
    
    etfs = []
    for i, code in enumerate(etf_code_list, 1):
        print(f"   ({i}/{len(etf_code_list)}) 获取 {code}...", end=' ')
        
        # 获取基本信息
        info = fetch_etf_fund_info(code)
        
        if info is None:
            print("❌ 失败")
            continue
        
        # 获取历史数据
        df_hist = fetch_etf_hist_data(code)
        metrics = calculate_metrics_from_hist(df_hist)
        
        # 获取持仓数据
        holdings = fetch_etf_holdings(code)
        
        # 构造ETF数据
        etf = {
            "code": code,
            "name": info['name'],
            "type": "股票型",  # 默认值，可根据实际需要调整
            "scale": info['scale'],
            "fee": info['fee'],
            "tracking_error": 0.02,  # 需要另外计算
            "year_1_return": metrics['year_1_return'],
            "year_3_return": metrics['year_3_return'],
            "max_drawdown": metrics['max_drawdown'],
            "sharpe_ratio": metrics['sharpe_ratio'],
            "launch_date": info['launch_date'],
            "issuer": info['issuer'],
            "underlying": info['name'],
            "top_holdings": holdings if holdings else [],
            "volume": 0,  # 需要另外获取
            "category": "宽基",  # 默认值，可根据实际需要调整
        }
        
        etfs.append(etf)
        print("✅ 成功")
        
        # 礼貌性延迟
        time.sleep(0.5)
    
    # 保存到缓存
    with open(cache_file, 'w', encoding='utf-8') as f:
        json.dump(etfs, f, ensure_ascii=False, indent=2)
    
    # 更新元数据
    meta = {
        'last_update': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'total_etfs': len(etfs),
        'fetch_real_data': True,
        'data_source': 'AkShare',
        'cache_version': '2.0'
    }
    save_cache_meta(meta)
    
    print(f"\n✅ 数据已保存到缓存: {cache_file}")
    print(f"   共获取 {len(etfs)} 只ETF")
    
    return etfs


if __name__ == '__main__':
    # 测试代码
    print("=" * 60)
    print("ETF真实数据获取模块测试")
    print("=" * 60)
    
    # 测试单只ETF
    print("\n1. 测试获取ETF基本信息...")
    info = fetch_etf_fund_info("510300")
    print(f"   结果: {info}")
    
    print("\n2. 测试获取ETF历史数据...")
    df = fetch_etf_hist_data("510300")
    if df is not None:
        print(f"   共 {len(df)} 条记录")
        print(f"   最新净值: {df.iloc[-1]['净值']}")
    
    print("\n3. 测试计算指标...")
    metrics = calculate_metrics_from_hist(df)
    print(f"   结果: {metrics}")
    
    print("\n4. 测试获取持仓数据...")
    holdings = fetch_etf_holdings("510300")
    print(f"   结果: {holdings[:3] if holdings else '无数据'}")
    
    print("\n" + "=" * 60)
    print("测试完成！")
