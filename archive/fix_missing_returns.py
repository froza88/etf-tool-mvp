#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修复无收益率的ETF
尝试从多个数据源获取收益率数据
"""
import json
import sys
from pathlib import Path
from datetime import datetime, timedelta

ROOT = Path(__file__).parent
STANDARD_DATA = ROOT / "etf_standard_data.json"

print("=== 修复无收益率的ETF ===\n")

# 加载现有数据
with open(STANDARD_DATA, 'r', encoding='utf-8') as f:
    etf_data = json.load(f)

# 找出无收益率的ETF
no_return = [etf for etf in etf_data if not etf.get('year_1_return') or etf.get('year_1_return') == 0]
print(f"找到 {len(no_return)} 只无收益率的ETF\n")

fixed = 0
failed = []

for etf in no_return:
    code = etf.get('code', '')
    name = etf.get('name', '')
    
    print(f"处理 {code} - {name}...")
    
    # 方案1: 尝试从盈米获取（如果有权限）
    # TODO: 调用盈米API
    
    # 方案2: 尝试从AKShare下载历史数据并计算
    try:
        import akshare as ak
        end_date = datetime.now().strftime('%Y%m%d')
        start_date = (datetime.now() - timedelta(days=365)).strftime('%Y%m%d')
        
        df = ak.fund_etf_hist_em(
            symbol=code, 
            period='daily', 
            start_date=start_date, 
            end_date=end_date, 
            adjust='qfq'
        )
        
        if df is not None and len(df) >= 252:  # 至少252个交易日
            prices = df['收盘'].tolist()
            year_1_return = (prices[-1] - prices[-252]) / prices[-252] * 100
            etf['year_1_return'] = round(year_1_return, 1)
            print(f"  ✅ 从AKShare计算收益率: {etf['year_1_return']}%")
            fixed += 1
        else:
            print(f"  ⚠️  历史数据不足 ({len(df) if df is not None else 0} 条)")
            failed.append(code)
    except Exception as e:
        print(f"  ❌ 下载失败: {e}")
        failed.append(code)
    
    print()

print(f"\n=== 修复结果 ===")
print(f"成功修复: {fixed} 只")
print(f"修复失败: {len(failed)} 只")
if failed:
    print(f"失败列表: {failed}")

# 保存更新后的数据
if fixed > 0:
    with open(STANDARD_DATA, 'w', encoding='utf-8') as f:
        json.dump(etf_data, f, ensure_ascii=False, indent=2)
    print(f"\n✅ 已保存: {STANDARD_DATA.name}")
