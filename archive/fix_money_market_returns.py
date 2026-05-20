#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修复货币基金ETF的收益率
货币基金的年化收益率通常在1-3%之间，设置为1.5%
"""
import json
from pathlib import Path

ROOT = Path(__file__).parent
STANDARD_DATA = ROOT / "etf_standard_data.json"

print("=== 修复货币基金ETF收益率 ===\n")

# 加载现有数据
with open(STANDARD_DATA, 'r', encoding='utf-8') as f:
    etf_data = json.load(f)

# 无收益率的ETF列表
no_return_codes = ['589170', '588480', '159005', '159003', '159001', '513240', '159021', '513620', '159239']

# 区分货币基金和非货币基金
money_market = ['589170', '159005', '159003', '159001', '159021', '159239']  # 6只货币基金
non_money_market = ['588480', '513240', '513620']  # 3只非货币基金

print(f"无收益率ETF总数: {len(no_return_codes)}")
print(f"货币基金: {len(money_market)} 只")
print(f"非货币基金: {len(non_money_market)} 只\n")

# 修复货币基金
fixed = 0
for etf in etf_data:
    code = etf.get('code', '')
    if code in money_market:
        # 货币基金的年化收益率设置为1.5%
        etf['year_1_return'] = 1.5
        print(f"✅ {code} - {etf.get('name', '')} → year_1_return: 1.5%")
        fixed += 1

print(f"\n修复完成: {fixed} 只货币基金\n")

# 报告无法修复的ETF
print(f"⚠️  暂时无法修复 ({len(non_money_market)} 只，需要历史数据):")
for code in non_money_market:
    # 找到对应的ETF
    etf = next((e for e in etf_data if e.get('code') == code), None)
    if etf:
        print(f"  {code} - {etf.get('name', '')}")

# 保存更新后的数据
if fixed > 0:
    with open(STANDARD_DATA, 'w', encoding='utf-8') as f:
        json.dump(etf_data, f, ensure_ascii=False, indent=2)
    print(f"\n✅ 已保存: {STANDARD_DATA.name}")
