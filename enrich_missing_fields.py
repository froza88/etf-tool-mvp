#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据吸收式更新脚本 - 填表格思路
原则：能获取的数据都保存，不断丰富本地数据库

核心逻辑：
1. 加载现有数据（etf_standard_data.json）
2. 遍历每个ETF，检查缺失字段
3. 尝试从本地缓存/其他数据源补充缺失字段
4. 保存更新后的数据
"""

import json
import sys
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).parent
STANDARD_DATA = ROOT / "etf_standard_data.json"
OUTPUT = ROOT / "etf_standard_data.json"

print("=== 数据吸收式更新（填表格思路）===\n")

# 加载现有数据
if not STANDARD_DATA.exists():
    print(f"❌ 文件不存在: {STANDARD_DATA.name}")
    sys.exit(1)

with open(STANDARD_DATA, 'r', encoding='utf-8') as f:
    etf_data = json.load(f)

print(f"✅ 加载现有数据: {len(etf_data)} 只 ETF\n")

# 定义需要填充的字段及其数据源
FIELDS_TO_FILL = {
    "issuer": "从 name 字段提取或已知映射",
    "scale": "从 etf_complete_all.json 或计算得到",
    "close": "从 etf_data_generated.json 获取",
    "change_pct": "从 etf_data_generated.json 获取",
    "top_holdings": "从 etf_data_generated.json 或 AKShare 获取",
    "year_1_return": "从 etf_calculated_metrics.json 获取",
    "year_3_return": "从 etf_calculated_metrics.json 获取",
    "max_drawdown": "从 etf_calculated_metrics.json 获取",
    "sharpe_ratio": "从 etf_calculated_metrics.json 获取",
}

# 统计信息
stats = {
    "total": len(etf_data),
    "updated": 0,
    "fields_added": defaultdict(int),
    "fields_missing": defaultdict(int),
}

# 加载辅助数据文件（本地缓存）
auxiliary_data = {}

# 1. 加载 etf_data_generated.json（非凸数据）
gen_map = {}
gen_file = ROOT / "etf_data_generated.json"
if gen_file.exists():
    with open(gen_file, 'r', encoding='utf-8') as f:
        gen_data = json.load(f)
    for item in gen_data:
        code = str(item.get("code", ""))
        if code:
            gen_map[code] = item
    print(f"✅ 加载非凸数据: {len(gen_map)} 只")

# 2. 加载 etf_calculated_metrics.json（自算指标）
calc_map = {}
calc_file = ROOT / "etf_calculated_metrics.json"
if calc_file.exists():
    with open(calc_file, 'r', encoding='utf-8') as f:
        calc_data = json.load(f)
    for code, metrics in calc_data.items():
        calc_map[code] = metrics
    print(f"✅ 加载自算指标: {len(calc_map)} 只")

print(f"\n开始吸收式更新...\n")

# 遍历每个 ETF，填充缺失字段
for i, etf in enumerate(etf_data):
    code = etf.get("code", "")
    updated = False
    
    # 1. 补充 issuer（如果缺失）
    if not etf.get("issuer"):
        # 从非凸数据获取
        gen = gen_map.get(code, {})
        if gen.get("issuer"):
            etf["issuer"] = gen["issuer"]
            stats["fields_added"]["issuer"] += 1
            updated = True
        else:
            stats["fields_missing"]["issuer"] += 1
    
    # 2. 补充 close/change_pct（如果缺失）
    if etf.get("close", 0) == 0:
        gen = gen_map.get(code, {})
        if gen.get("close"):
            etf["close"] = gen["close"]
            stats["fields_added"]["close"] += 1
            updated = True
        else:
            stats["fields_missing"]["close"] += 1
    
    if etf.get("change_pct", 0) == 0:
        gen = gen_map.get(code, {})
        if gen.get("change_pct"):
            etf["change_pct"] = gen["change_pct"]
            stats["fields_added"]["change_pct"] += 1
            updated = True
    
    # 3. 补充 top_holdings（如果缺失）
    if not etf.get("top_holdings"):
        gen = gen_map.get(code, {})
        if gen.get("top_holdings"):
            etf["top_holdings"] = gen["top_holdings"][:5]
            stats["fields_added"]["top_holdings"] += 1
            updated = True
        else:
            stats["fields_missing"]["top_holdings"] += 1
    
    # 4. 补充风险指标（如果缺失）
    if etf.get("year_1_return", 0) == 0:
        calc = calc_map.get(code, {})
        if calc.get("year_1_return"):
            etf["year_1_return"] = calc["year_1_return"]
            etf["year_3_return"] = calc.get("year_3_return", 0)
            etf["max_drawdown"] = calc.get("max_drawdown", 0)
            etf["sharpe_ratio"] = calc.get("sharpe_ratio", 0)
            etf["annual_vol"] = calc.get("annual_vol", 0)
            stats["fields_added"]["year_1_return"] += 1
            updated = True
        else:
            stats["fields_missing"]["year_1_return"] += 1
    
    if updated:
        stats["updated"] += 1
    
    # 进度显示
    if (i + 1) % 200 == 0:
        print(f"   进度: {i+1}/{len(etf_data)}  已更新: {stats['updated']}")

print(f"\n✅ 更新完成\n")

# 保存更新后的数据
with open(OUTPUT, 'w', encoding='utf-8') as f:
    json.dump(etf_data, f, ensure_ascii=False, indent=2)

print(f"✅ 已保存: {OUTPUT.name}")
print(f"   文件大小: {OUTPUT.stat().st_size / 1024:.0f} KB\n")

# 输出统计报告
print("=== 吸收式更新报告 ===\n")
print(f"总 ETF 数: {stats['total']}")
print(f"已更新: {stats['updated']} 只\n")

if stats["fields_added"]:
    print("✅ 补充字段统计:")
    for field, count in sorted(stats["fields_added"].items(), key=lambda x: -x[1]):
        pct = count / stats["total"] * 100
        print(f"   {field}: +{count} 只 ({pct:.1f}%)")

if stats["fields_missing"]:
    print("\n⚠️  仍缺失字段统计:")
    for field, count in sorted(stats["fields_missing"].items(), key=lambda x: -x[1]):
        pct = count / stats["total"] * 100
        print(f"   {field}: {count} 只 ({pct:.1f}%)")

print("\n=== 使用说明 ===")
print("\n1. 将此脚本加入每日更新流程:")
print("   python3 enrich_missing_fields.py")
print("\n2. 结合 sync_etf_list.py 使用:")
print("   python3 sync_etf_list.py   # 同步最新ETF列表")
print("   python3 enrich_missing_fields.py  # 补充缺失字段")
print("   python3 build_standard_data.py   # 重新生成标准化数据")
print("\n3. 定期运行，不断丰富本地数据库")
