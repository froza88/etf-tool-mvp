#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
对比AKShare全量ETF列表与本地数据
找出差异：多出的1只 or 缺失的1只
"""

import json
import akshare as ak
import sys

# 修复中文输出
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
    
    # 保存AKShare列表
    ak_codes = set(df_ak['代码'].tolist())
except Exception as e:
    print(f"获取AKShare数据失败: {e}")
    sys.exit(1)

# 2. 加载本地ETF数据
print("\n[2/3] 加载本地ETF数据...")
try:
    # 尝试多个可能的数据文件
    possible_files = [
        '/Users/apangduo/WorkBuddy/Claw/etf-tool-mvp/etf_data_generated.json',
        '/Users/apangduo/WorkBuddy/Claw/etf-tool-mvp/etf_standard_data.json',
        '/Users/apangduo/WorkBuddy/Claw/etf-tool-mvp/etf_complete_all.json'
    ]
    
    local_data = None
    loaded_file = None
    for file_path in possible_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                local_data = json.load(f)
            loaded_file = file_path.split('/')[-1]
            print(f"已加载: {loaded_file}")
            break
        except FileNotFoundError:
            continue
    
    if local_data is None:
        raise FileNotFoundError("未找到任何数据文件")
    
    # 判断数据格式
    if isinstance(local_data, dict) and 'data' in local_data:
        local_count = len(local_data['data'])
        local_codes = set([etf['code'] for etf in local_data['data']])
    elif isinstance(local_data, dict):
        # 字典格式 {code: data}
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
diff_count = ak_count - local_count
print(f"数量差异: {diff_count} 只")

print("\n" + "=" * 60)
print("对比结果")
print("=" * 60)
print(f"\nAKShare: {ak_count} 只")
print(f"本地数据: {local_count} 只")
print(f"差异: {diff_count} 只")

# 找出AKShare有但本地没有的ETF
missing_in_local = ak_codes - local_codes
if missing_in_local:
    print(f"\nAKShare有但本地缺失的ETF ({len(missing_in_local)} 只):")
    for i, code in enumerate(list(missing_in_local)[:10], 1):
        row = df_ak[df_ak['代码'] == code]
        if not row.empty:
            name = row.iloc[0]['名称']
            print(f"  {i}. {code} {name}")
    if len(missing_in_local) > 10:
        print(f"  ... 还有 {len(missing_in_local) - 10} 只")
else:
    print("\n本地数据包含了AKShare的所有ETF")

# 找出本地有但AKShare没有的ETF
extra_in_local = local_codes - ak_codes
if extra_in_local:
    print(f"\n本地有但AKShare缺失的ETF ({len(extra_in_local)} 只):")
    for i, code in enumerate(list(extra_in_local)[:10], 1):
        if isinstance(local_data, dict) and 'data' in local_data:
            etf = next((e for e in local_data['data'] if e['code'] == code), None)
        else:
            etf = local_data.get(code)
        if etf:
            name = etf['name'] if isinstance(etf, dict) and 'name' in etf else str(etf)
            print(f"  {i}. {code} {name}")
    if len(extra_in_local) > 10:
        print(f"  ... 还有 {len(extra_in_local) - 10} 只")
else:
    print("\n本地数据没有AKShare不存在的ETF")

print("\n" + "=" * 60)
print("完成")
print("=" * 60)
