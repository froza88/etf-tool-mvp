#!/usr/bin/env python3
# 按行号精准修复 data_absorber.py bug（186-188行）
with open('data_absorber.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# 行号（1-indexed）：186-188 → 0-indexed: 185-187
# 替换这3行
new_lines = [
    '                "quality": new_quality if quality_order.get(new_quality, 0) > quality_order.get(\n',
    '                    meta_entry.get("quality", "low"), 0) else meta_entry.get("quality", new_quality),\n'
]

lines[185:188] = new_lines  # 替换186-188行（0-indexed 185:188是切片到188 exclusive，即185,186,187）

with open('data_absorber.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)
print("✅ 修复完成（按行号替换186-188行）")
