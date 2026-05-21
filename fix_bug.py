#!/usr/bin/env python3
# 修复 data_absorber.py 的 bug（quality 比较逻辑错误）
import sys

filepath = "data_absorber.py"
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

old = '                "quality": new_quality if new_priority < _source_index(\n                    meta_entry.get("quality", "low"))\n                ) else meta_entry.get("quality", new_quality),'

new = '                "quality": new_quality if quality_order.get(new_quality, 0) > quality_order.get(\n                    meta_entry.get("quality", "low"), 0) else meta_entry.get("quality", new_quality),'

if old in content:
    content = content.replace(old, new)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print("✅ 修复成功")
else:
    print("❌ 未找到匹配字符串")
    sys.exit(1)
