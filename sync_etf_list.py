#!/usr/bin/env python3
"""
ETF 列表同步脚本 - 吸收式架构
从多个数据源获取 ETF 列表，取并集，自动补充新上市 ETF

数据源：
1. AKShare: fund_etf_spot_em() - 获取全量 ETF 列表（1467+ 只）
2. 非凸科技: etf-description-all - 获取全量 ETF 列表
3. 本地: etf_complete_all.json - 现有数据

策略：取并集，确保所有 ETF 都被包含
"""

import json
import sys
import time
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).parent
FULL_DATA = ROOT / "etf_complete_all.json"
OUTPUT = ROOT / "etf_complete_all.json"

print("=== ETF 列表同步（吸收式架构）===\n")

# ---- 第1步：从 AKShare 获取最新 ETF 列表 ----
print("1. 从 AKShare 获取最新 ETF 列表...")
try:
    import akshare as ak
    df = ak.fund_etf_spot_em()
    print(f"   ✅ AKShare 返回 {len(df)} 只 ETF")

    # 转换为标准格式
    akshare_etfs = []
    for _, row in df.iterrows():
        try:
            etf = {
                "code": str(row['代码']).zfill(6),
                "name": str(row['名称']).strip(),
                "market_cap": float(row['总市值']) if '总市值' in row else 0,
                "volume": float(row['成交量']) if '成交量' in row else 0,
                "change_pct": float(row['涨跌幅']) if '涨跌幅' in row else 0,
            }
            akshare_etfs.append(etf)
        except Exception as e:
            continue

    print(f"   成功转换 {len(akshare_etfs)} 只 ETF")
    akshare_codes = set([e['code'] for e in akshare_etfs])
    print(f"   AKShare ETF 代码集合: {len(akshare_codes)} 只")

except Exception as e:
    print(f"   ❌ AKShare 获取失败: {e}")
    akshare_etfs = []
    akshare_codes = set()

# ---- 第2步：从本地加载现有数据 ----
print("\n2. 加载本地现有数据...")
if FULL_DATA.exists():
    with open(FULL_DATA, "r", encoding="utf-8") as f:
        local_etfs = json.load(f)
    print(f"   ✅ 本地数据: {len(local_etfs)} 只 ETF")
    local_codes = set([e.get('code', '') for e in local_etfs if e.get('code')])
    print(f"   本地 ETF 代码集合: {len(local_codes)} 只")
else:
    print(f"   ⚠️  本地文件不存在: {FULL_DATA.name}")
    local_etfs = []
    local_codes = set()

# ---- 第3步：取并集 ----
print("\n3. 取并集（AKShare + 本地）...")
union_codes = akshare_codes | local_codes
print(f"   并集大小: {len(union_codes)} 只 ETF")

# 找出缺失的 ETF
missing_from_local = akshare_codes - local_codes
missing_from_akshare = local_codes - akshare_codes

if missing_from_local:
    print(f"   ⚠️  本地缺失 {len(missing_from_local)} 只 ETF（AKShare 有，本地无）:")
    for code in list(missing_from_local)[:10]:
        etf = next((e for e in akshare_etfs if e['code'] == code), None)
        if etf:
            print(f"      {code} {etf['name']}")
    if len(missing_from_local) > 10:
        print(f"      ... 还有 {len(missing_from_local) - 10} 只")

if missing_from_akshare:
    print(f"   ⚠️  AKShare 缺失 {len(missing_from_akshare)} 只 ETF（本地有，AKShare 无）:")
    for code in list(missing_from_akshare)[:10]:
        etf = next((e for e in local_etfs if e.get('code') == code), None)
        if etf:
            print(f"      {code} {etf.get('name', '')}")
    if len(missing_from_akshare) > 10:
        print(f"      ... 还有 {len(missing_from_akshare) - 10} 只")

# ---- 第4步：合并数据 ----
print("\n4. 合并数据...")
merged_etfs = []
merged_codes = set()

# 优先使用 AKShare 数据（更新）
for etf in akshare_etfs:
    code = etf['code']
    if code not in merged_codes:
        merged_etfs.append(etf)
        merged_codes.add(code)

# 补充本地有但 AKShare 没有的 ETF
for etf in local_etfs:
    code = etf.get('code', '')
    if code and code not in merged_codes:
        merged_etfs.append(etf)
        merged_codes.add(code)

print(f"   合并后: {len(merged_etfs)} 只 ETF")

# ---- 第5步：保存 ----
print(f"\n5. 保存到 {OUTPUT.name}...")
with open(OUTPUT, "w", encoding="utf-8") as f:
    json.dump(merged_etfs, f, ensure_ascii=False, indent=2)
print(f"   ✅ 保存成功")
print(f"   文件大小: {OUTPUT.stat().st_size / 1024:.0f} KB")

# ---- 第6步：统计 ----
print(f"\n6. 统计信息:")
print(f"   AKShare: {len(akshare_etfs)} 只")
print(f"   本地原有: {len(local_etfs)} 只")
print(f"   合并后: {len(merged_etfs)} 只")
print(f"   新增: {len(missing_from_local)} 只")

print(f"\n✅ ETF 列表同步完成")
print(f"\n💡 提示：下一步运行 build_standard_data.py 生成标准化数据")
