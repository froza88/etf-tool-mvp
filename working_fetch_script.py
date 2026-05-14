#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
真正可用的ETF数据抓取脚本
1. 调用 westockdata CLI
2. 输出保存到文件（避免编码问题）
3. 用Python读取文件（UTF-8）
4. 正则提取关键字段
5. 更新 etf_data.py
"""

import subprocess
import re
import time
import os

def fetch_etf_to_file(etf_code, output_file):
    """调用CLI并保存输出到文件"""
    cmd = f"npx -y westock-data-clawhub@1.0.4 etf sh{etf_code} > {output_file} 2>/dev/null"
    ret = subprocess.run(cmd, shell=True, cwd='/Users/apangduo/WorkBuddy/Claw', timeout=30)
    return ret.returncode == 0 and os.path.exists(output_file)

def parse_etf_file(file_path, etf_code):
    """读取文件并解析ETF数据"""
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    
    # 找到数据行
    pattern = rf'\| sh{etf_code} \| ([^\n]+)'
    match = re.search(pattern, content)
    
    if not match:
        return None
    
    data_line = match.group(0)
    
    # 提取关键数据
    data = {}
    
    # 1. 规模 totalMV (单位：元，需要转亿元)
    # 在数据中找很长的数字（规模字段）
    large_nums = re.findall(r'\| (\d{10,}) \|', data_line)
    if large_nums:
        total_mv = float(large_nums[0])
        data['scale'] = round(total_mv / 100000000, 2)
    
    # 2. 管理费 managementFee (X.XX%)
    # 3. 托管费 custodyFee (X.XX%)
    pct_values = re.findall(r'(\d+\.\d+)%', content)
    if len(pct_values) >= 2:
        data['management_fee'] = float(pct_values[0])
        data['custody_fee'] = float(pct_values[1])
        data['fee'] = round(data['management_fee'] + data['custody_fee'], 2)
    
    # 4. 成立日期 establishDate
    date_match = re.search(r'(\d{4}-\d{2}-\d{2}) 00:00:00', content)
    if date_match:
        data['launch_date'] = date_match.group(1)
    
    # 5. 近1年收益 return1Y
    # 6. 近3年收益 return3Y  
    # 7. 最大回撤 maxDrawdown1Y
    # 这些在表格后面，需要更复杂的解析
    # 暂时先返回已提取的字段
    
    return data if data else None

# 测试：抓取510300
print("测试抓取 510300...")
if fetch_etf_to_file('510300', '/tmp/test_etf.txt'):
    print("  ✓ 数据已保存")
    data = parse_etf_file('/tmp/test_etf.txt', '510300')
    if data:
        print(f"  ✓ 解析成功：")
        for key, value in data.items():
            print(f"    {key}: {value}")
    else:
        print("  ✗ 解析失败")
else:
    print("  ✗ 抓取失败")
