#!/usr/bin/env python3
# 精准修复 data_absorber.py 的 bug（186-188行）
import sys

filepath = "data_absorber.py"
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# 精确 old string（含真实换行符）
old = ('                "quality": new_quality if new_priority < _source_index(\n'
       '                    meta_entry.get("quality", "low"))\n'
       '                ) else meta_entry.get("quality", new_quality),\n')

# new string（含真实换行符）
new = ('                "quality": new_quality if quality_order.get(new_quality, 0) > quality_order.get(\n'
       '                    meta_entry.get("quality", "low"), 0) else meta_entry.get("quality", new_quality),\n')

if old in content:
    content = content.replace(old, new, 1)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print("✅ 修复成功")
else:
    print("❌ 未找到匹配")
    # 调试：打印文件该位置附近的内容
    idx = content.find('new_priority < _source_index')
    if idx >= 0:
        print(f"找到 new_priority 在位置 {idx}")
        print(repr(content[idx-20:idx+100]))
    sys.exit(1)
