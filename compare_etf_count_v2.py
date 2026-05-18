#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
对比AKShare全量ETF列表与本地数据
找出差异：多出的 or 缺失的ETF
"""

import json
import akshare as ak
import sys

sys.stdout.reconfigure(encoding='utf-8')

print("=" * 60)
print("对比ETF数量差异")
print("=" * 60)

# 1. 获取AKShare全量ETF列表
print("\n[1/3] 获取AKShare全量ETF列表...")
try:
    df_ak = ak.fund_etf_spot_em()
    ak_count = len(df_ak)
    print(f"AKShare ETF总数: {ak_count} 只")
    ak_codes = set(df_ak['代码'].tolist())
except Exception as e:
    print(f"获取AKShare数据失败: {e}")
    sys.exit(1)

# 2. 加载本地ETF数据
print("\n[2/3] 加载本地ETF数据...")
try:
    with open('/Users/apangduo/WorkBuddy/Claw/etf-tool-mvp/etf_data_generated.json', 'r', encoding='utf-8') as f:
        local_data = json.load(f)
    
    if isinstance(local_data, dict) and 'data' in local_data:
        local_count = len(local_data['data'])
        local_codes = set([etf['code'] for etf in local_data['data']])
    elif isinstance(local_data, dict):
        local_count = len(local_data)
        local_codes = set(local_data.keys())
    else:
        raise ValueError("未知的数据格式")
    
    print(f"本地ETF总数: {local_count} 只")
except Exception as e:
    print(f"加载本地数据失败: {e}")
    sys.exit(1)

# 3. 对比差异
print("\n[3/3] 对比差异...")
diff_count = local_count - ak_count
print(f"数量差异: {diff_count} 只 (本地 {local_count} - AKShare {ak_count})")

# 找出AKShare有但本地没有的ETF
missing_in_local = ak_codes - local_codes
print(f"\nAKShare有但本地缺失的ETF: {len(missing_in_local)} 只")
if missing_in_local:
    print("\n前10只:")
    for i, code in enumerate(list(missing_in_local)[:10], 1):
        row = df_ak[df_ak['代码'] == code]
        if not row.empty:
            name = row.iloc[0]['名称']
            print(f"  {i}. {code} {name}")

# 找出本地有但AKShare没有的ETF
extra_in_local = local_codes - ak_codes
print(f"\n本地有但AKShare缺失的ETF: {len(extra_in_local)} 只")
if extra_in_local:
    print("\n前10只:")
    for i, code in enumerate(list(extra_in_local)[:10], 1):
        if isinstance(local_data, dict) and 'data' in local_data:
            etf = next((e for e in local_data['data'] if e['code'] == code), None)
        elif isinstance(local_data, dict):
            etf = local_data.get(code)
        else:
            etf = None
        
        if etf:
            name = etf['name'] if isinstance(etf, dict) and 'name' in etf else str(etf)[:50]
            print(f"  {i}. {code} {name}")

# 生成详细报告
print("\n" + "=" * 60)
print("详细报告")
print("=" * 60)

if len(missing_in_local) > 0:
    print(f"\n⚠️ 缺失 {len(missing_in_local)} 只ETF，建议补充:")
    for i, code in enumerate(missing_in_local, 1):
        row = df_ak[df_ak['代码'] == code]
        if not row.empty:
            name = row.iloc[0]['名称']
            print(f"  {i}. {code} {name}")

if len(extra_in_local) > 0:
    print(f"\n⚠️ 多出 {len(extra_in_local)} 只ETF，可能是:")
    print("  - 已退市的ETF")
    print("  - 数据重复")
    print("  - 代码错误")
    for i, code in enumerate(list(extra_in_local)[:5], 1):
        if isinstance(local_data, dict) and 'data' in local_data:
            etf = next((e for e in local_data['data'] if e['code'] == code), None)
        elif isinstance(local_data, dict):
            etf = local_data.get(code)
        else:
            etf = None
        
        if etf:
            name = etf['name'] if isinstance(etf, dict) and 'name' in etf else 'Unknown'
            print(f"  {i}. {code} {name}")

if len(missing_in_local) == 0 and len(extra_in_local) == 0:
    print("\n✅ 数据完全一致！")

print("\n" + "=" * 60)
print("完成")
print("=" * 60)
