#!/usr/bin/env python3
"""修复ETF名称重复问题"""
import json

# 读取数据
with open('etf_complete_130.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

print(f"Total ETFs: {len(data)}")

# 检查和修复名称重复
fixed_count = 0
for etf in data:
    name = etf.get('name', '')
    manager = etf.get('manager', '')
    
    # 如果name以manager结尾，去掉重复的manager
    if manager and name.endswith(manager):
        new_name = name[:-len(manager)].rstrip('-')
        if new_name:
            print(f"Fix {etf.get('symbol_id')}: '{name}' -> '{new_name}'")
            etf['name'] = new_name
            fixed_count += 1

print(f"\nFixed {fixed_count} ETFs")

# 保存修复后的数据
with open('etf_complete_130.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print("Saved!")
