#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量更新ETF名称格式：代码-名称-基金公司
更可靠的版本
"""

import re

# 读取文件
with open('/Users/apangduo/WorkBuddy/Claw/etf-tool-mvp/etf_data.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
i = 0
while i < len(lines):
    line = lines[i]

    # 检测是否到了name行
    name_match = re.match(r'^(\s+)"name":\s*"([^"]+)",?\s*$', line)
    if name_match:
        indent = name_match.group(1)
        old_name = name_match.group(2)

        # 向前查找code（最多往前找15行）
        code = None
        for j in range(max(0, i-15), i):
            code_match = re.match(r'^\s+"code":\s*"(\d+)",?\s*$', lines[j])
            if code_match:
                code = code_match.group(1)
                break

        # 向后查找issuer（最多往后找15行）
        issuer = None
        for j in range(i+1, min(len(lines), i+15)):
            issuer_match = re.match(r'^\s+"issuer":\s*"([^"]+)",?\s*$', lines[j])
            if issuer_match:
                issuer = issuer_match.group(1)
                break

        # 如果找到了code和issuer，替换name
        if code and issuer:
            new_name = f"{code}-{old_name}-{issuer}"
            new_line = f'{indent}"name": "{new_name}",\n'
            print(f"✅ {old_name} → {new_name}")
            line = new_line

    new_lines.append(line)
    i += 1

# 写回文件
with open('/Users/apangduo/WorkBuddy/Claw/etf-tool-mvp/etf_data.py', 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print("\n✅ 所有ETF名称已更新完成！")
