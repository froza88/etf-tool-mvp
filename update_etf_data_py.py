#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
更新 etf_data.py 中的 top_holdings 数据
从 etf_data_generated.json 读取真实持仓数据，更新到 etf_data.py
"""

import json
import re

# 读取 JSON 文件（包含真实的 top_holdings）
with open('etf_data_generated.json', 'r', encoding='utf-8') as f:
    json_data = json.load(f)

# 创建 code -> top_holdings 的映射
holdings_map = {}
for etf in json_data:
    code = etf['code']
    holdings_map[code] = etf['top_holdings']

# 读取 etf_data.py
with open('etf_data.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 使用正则表达式替换每个 ETF 的 top_holdings
# 模式：匹配 "top_holdings": ['持仓1 10%', '持仓2 8%', ...]
pattern = r'("top_holdings":\s*\[)(.*?)(\])'

def replace_holdings(match, code):
    """替换持仓数据"""
    prefix = match.group(1)
    suffix = match.group(3)
    
    if code in holdings_map:
        # 使用 JSON 文件中的真实数据
        holdings = holdings_map[code]
        # 格式化为 Python 列表字符串
        holdings_str = ', '.join([f"'{h}'" for h in holdings])
        return f"{prefix}{holdings_str}{suffix}"
    else:
        # 如果没有找到对应的数据，保持原样
        return match.group(0)

# 按 code 分段处理
lines = content.split('\n')
output_lines = []
current_code = None
in_top_holdings = False
holdings_buffer = []
new_content_parts = []

i = 0
while i < len(lines):
    line = lines[i]
    
    # 检测 ETF code
    code_match = re.search(r'"code":\s*"(\d+)"', line)
    if code_match:
        current_code = code_match.group(1)
    
    # 检测 top_holdings 开始
    if '"top_holdings"' in line:
        # 找到这一行的末尾
        if '[' in line and ']' in line:
            # 在同一行内完成
            if current_code and current_code in holdings_map:
                holdings = holdings_map[current_code]
                holdings_str = ', '.join([f"'{h}'" for h in holdings])
                line = f'        "top_holdings": [{holdings_str}],'
        else:
            # 多行格式
            in_top_holdings = True
            holdings_buffer = [line]
    
    # 处理多行的 top_holdings
    elif in_top_holdings:
        holdings_buffer.append(line)
        if ']' in line:
            # 结束，替换
            if current_code and current_code in holdings_map:
                holdings = holdings_map[current_code]
                # 生成新的多行格式
                new_lines = [f'        "top_holdings": [']
                for j, h in enumerate(holdings):
                    if j < len(holdings) - 1:
                        new_lines.append(f"            '{h}',")
                    else:
                        new_lines.append(f"            '{h}'")
                new_lines.append('        ],')
                # 替换 buffer 中的行
                holdings_buffer = new_lines
            
            output_lines.extend(holdings_buffer)
            holdings_buffer = []
            in_top_holdings = False
            i += 1
            continue
    
    if not in_top_holdings:
        output_lines.append(line)
    
    i += 1

# 写入新文件
new_content = '\n'.join(output_lines)
with open('etf_data_updated.py', 'w', encoding='utf-8') as f:
    f.write(new_content)

print(f"✅ 更新完成！")
print(f"📊 共更新 {len(holdings_map)} 个 ETF 的持仓数据")
print(f"📁 新文件：etf_data_updated.py")
print(f"\n⚠️  请检查无误后，将 etf_data_updated.py 重命名为 etf_data.py")
