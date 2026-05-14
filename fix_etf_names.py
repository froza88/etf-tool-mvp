#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修复ETF名称格式：去除重复的代码和基金公司
最终格式：代码-名称-基金公司
"""

import re

with open('/Users/apangduo/WorkBuddy/Claw/etf-tool-mvp/etf_data.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
for line in lines:
    # 匹配"name"字段
    name_match = re.match(r'^(\s+)"name":\s*"([^"]+)",?\s*$', line)
    if name_match:
        indent = name_match.group(1)
        full_name = name_match.group(2)

        # 如果名称中已经包含代码和基金公司（格式：代码-XXX-基金公司）
        if '-' in full_name:
            parts = full_name.split('-')
            # 取最后三个部分：代码、名称、基金公司
            if len(parts) >= 3:
                code = parts[0]
                issuer = parts[-1]
                name = '-'.join(parts[1:-1])
                # 去除名称中可能重复的代码
                if name.startswith(code + '-'):
                    name = name[len(code)+1:]
                new_name = f"{code}-{name}-{issuer}"
                line = f'{indent}"name": "{new_name}",\n'
                print(f"✅ {full_name} → {new_name}")

    new_lines.append(line)

# 写回文件
with open('/Users/apangduo/WorkBuddy/Claw/etf-tool-mvp/etf_data.py', 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print("\n✅ 所有ETF名称格式已修复！")
