#!/usr/bin/env python3
"""
合并脚本：将并行产出合并到 etf_data_generated.json
数据源：
1. etf_temp_returns.json   ← 收益率（Script A）
2. etf_temp_metrics.json   ← 回撤/夏普（Script Bv2）
3. etf_data_generated.json ← 已有持仓等字段
输出：clean etf_data_generated.json
"""
import sys, os, json
ROOT = os.path.dirname(os.path.abspath(__file__))

def load(path):
    p = os.path.join(ROOT, path)
    if not os.path.exists(p):
        print(f"⚠️  {path} 不存在")
        return {}
    with open(p, "r", encoding="utf-8") as f:
        data = json.load(f)
    print(f"  {path}: {len(data)} 条")
    return data

print("=== 合并并行数据 ===")

# 加载三方数据
returns_data = load("etf_temp_returns.json")      # code → {year_1_return, year_3_return}
metrics_data = load("etf_temp_metrics.json")        # code → {max_drawdown, sharpe_ratio}

# 加载已有 generated 数据（含持仓）
with open(os.path.join(ROOT, "etf_data_generated.json"), "r", encoding="utf-8") as f:
    existing = json.load(f)
print(f"  etf_data_generated.json: {len(existing)} 条")

# 合并：按 code 建立索引
merged_map = {}
for item in existing:
    code = str(item.get("code", ""))
    if code:
        merged_map[code] = item

# 补充收益率
if returns_data:
    for code, ret in returns_data.items():
        if ret and code in merged_map:
            merged_map[code]["year_1_return"] = ret.get("year_1_return", 0)
            merged_map[code]["year_3_return"] = ret.get("year_3_return", 0)

# 补充回撤/夏普
if metrics_data:
    for code, met in metrics_data.items():
        if met and code in merged_map:
            merged_map[code]["max_drawdown"] = met.get("max_drawdown", 0)
            merged_map[code]["sharpe_ratio"] = met.get("sharpe_ratio", 0)

# 统计
total = len(merged_map)
has_y1 = sum(1 for e in merged_map.values() if e.get("year_1_return") not in (None, 0))
has_dd = sum(1 for e in merged_map.values() if e.get("max_drawdown") not in (None, 0))
has_sr = sum(1 for e in merged_map.values() if e.get("sharpe_ratio") not in (None, 0.0))
has_hold = sum(1 for e in merged_map.values() if e.get("top_holdings") and len(e.get("top_holdings",[])) > 0)

print(f"\n合并完成:")
print(f"  总ETF数: {total}")
print(f"  有收益率: {has_y1}")
print(f"  有回撤:   {has_dd}")
print(f"  有夏普:   {has_sr}")
print(f"  有持仓:   {has_hold}")

# 写入
combined = list(merged_map.values())
out_path = os.path.join(ROOT, "etf_data_generated.json")
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(combined, f, ensure_ascii=False, indent=2)
print(f"\n写入 {out_path} 完成 ({len(combined)} 条)")
