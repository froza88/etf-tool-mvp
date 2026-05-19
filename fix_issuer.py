#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修复无发行人的ETF
"""
import json
from pathlib import Path

ROOT = Path(__file__).parent
STANDARD_DATA = ROOT / "etf_standard_data.json"

print("=== 修复无发行人的ETF ===\n")

# 加载现有数据
with open(STANDARD_DATA, 'r', encoding='utf-8') as f:
    etf_data = json.load(f)

print(f"加载 {len(etf_data)} 只ETF数据\n")

# 定义需要修复的ETF及其发行人
fixes = {
    "511670": "国联安基金管理有限公司",
    "512190": "浙江浙商证券资产管理有限公司",
}

# 应用修复
fixed = 0
for etf in etf_data:
    code = etf.get("code", "")
    if code in fixes:
        etf["issuer"] = fixes[code]
        print(f"✅ {code} - {etf.get('name', '')} → 发行人: {fixes[code]}")
        fixed += 1

print(f"\n修复完成: {fixed} 只ETF\n")

# 保存更新后的数据
with open(STANDARD_DATA, 'w', encoding='utf-8') as f:
    json.dump(etf_data, f, ensure_ascii=False, indent=2)

print(f"✅ 已保存: {STANDARD_DATA.name}")
print(f"   文件大小: {STANDARD_DATA.stat().st_size / 1024:.0f} KB")
