#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量更新ETF名称格式：代码-名称-基金公司
"""

import re

# 读取文件
with open('etf_data.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 使用正则表达式替换name字段
# 匹配："name": "任意名称",
# 替换为："name": "代码-原名称-基金公司",

def replace_name(match):
    # 这里需要获取code和issuer，但简单做法是直接替换
    pass

# 更简单的方法：逐行读取并替换
lines = content.split('\n')
new_lines = []
i = 0
while i < len(lines):
    line = lines[i]
    # 如果这一行是"name": "xxx",
    if '"name":' in line and 'code' not in line:
        # 向前查找code，向后查找issuer
        code = None
        issuer = None

        # 向前查找code
        for j in range(i-1, max(0, i-10), -1):
            if '"code":' in lines[j]:
                code_match = re.search(r'"code":\s*"(\d+)"', lines[j])
                if code_match:
                    code = code_match.group(1)
                break

        # 向后查找issuer
        for j in range(i+1, min(len(lines), i+10)):
            if '"issuer":' in lines[j]:
                issuer_match = re.search(r'"issuer":\s*"([^"]+)"', lines[j])
                if issuer_match:
                    issuer = issuer_match.group(1)
                break

        # 提取原名称
        name_match = re.search(r'"name":\s*"([^"]+)"', line)
        if name_match and code and issuer:
            old_name = name_match.group(1)
            new_name = f"{code}-{old_name}-{issuer}"
            line = line.replace(f'"name": "{old_name}"', f'"name": "{new_name}"')
            print(f"✅ {old_name} → {new_name}")

    new_lines.append(line)
    i += 1

# 写回文件
with open('etf_data.py', 'w', encoding='utf-8') as f:
    f.write('\n'.join(new_lines))

print("\n✅ 所有ETF名称已更新！")
