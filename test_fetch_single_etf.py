#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
使用 WeStock Data 批量抓取ETF真实数据并解析
"""
import subprocess
import re
import time
import json

def parse_etf_markdown(md_text, etf_code):
    """
    解析 WeStock Data 返回的 Markdown 表格
    返回字典，包含我们需要的字段
    """
    lines = md_text.split('\n')
    
    # 找到数据行（包含 sh510300 这样的代码）
    data_line = None
    for line in lines:
        if f'sh{etf_code}' in line or f'sz{etf_code}' in line:
            data_line = line
            break
    
    if not data_line:
        return None
    
    # 找到表头行
    header_line = None
    for i, line in enumerate(lines):
        if 'code | name | date |' in line or '--- | --- |' in line:
            # 表头在上面一行
            header_line = lines[i-1] if i > 0 else None
            break
    
    if not header_line:
        # 尝试直接找包含字段名的行
        for line in lines:
            if 'code | name | date |' in line:
                header_line = line
                break
    
    if not header_line:
        print(f"  ✗ 未找到表头")
        return None
    
    # 解析表头和数据
    headers = [h.strip() for h in header_line.split('|')]
    values = [v.strip() for v in data_line.split('|')]
    
    # 构建字典
    data = {}
    for i, header in enumerate(headers):
        if i < len(values):
            data[header] = values[i]
    
    return data

def map_to_etf_fields(westock_data):
    """
    将 WeStock 数据映射为 etf_data.py 的字段格式
    """
    try:
        # 规模：totalMV 单位是元，需要转成亿元
        total_mv = float(westick_data.get('totalMV', 0))
        size_in_yi = total_mv / 100000000  # 转换为亿元
        
        result = {
            'scale': round(size_in_yi, 2),
            'management_fee': float(westick_data.get('managementFee', 0)),
            'custody_fee': float(westick_data.get('custodyFee', 0)),
            'fee': round(float(westick_data.get('managementFee', 0)) + float(westick_data.get('custodyFee', 0)), 2),
            'year_1_return': float(westick_data.get('return1Y', 0)),
            'year_3_return': float(westick_data.get('return3Y', 0)),
            'max_drawdown': float(westick_data.get('maxDrawdown1Y', 0)),
            'launch_date': westick_data.get('establishDate', '')[:10] if westick_data.get('establishDate') else '',
        }
        
        return result
    except Exception as e:
        print(f"  映射错误: {e}")
        return None

def fetch_etf_real_data(etf_code):
    """
    抓取单只ETF的真实数据
    """
    try:
        result = subprocess.run(
            ['npx', '-y', 'westock-data-clawhub@1.0.4', 'etf', f'sh{etf_code}'],
            capture_output=True,
            text=True,
            timeout=30,
            cwd='/Users/apangduo/WorkBuddy/Claw'
        )
        
        if result.returncode != 0:
            return None
        
        # 解析Markdown
        data = parse_etf_markdown(result.stdout, etf_code)
        
        if not data:
            return None
        
        # 映射字段
        mapped = map_to_etf_fields(data)
        
        return mapped
        
    except Exception as e:
        print(f"  错误: {e}")
        return None

# 测试：抓取510300
print("测试抓取 510300 数据...")
data = fetch_etf_real_data('510300')

if data:
    print("\n✓ 抓取成功！")
    print(f"规模: {data['scale']} 亿元")
    print(f"管理费: {data['management_fee']}%")
    print(f"托管费: {data['custody_fee']}%")
    print(f"总费率: {data['fee']}%")
    print(f"近1年收益: {data['year_1_return']}%")
    print(f"近3年收益: {data['year_3_return']}%")
    print(f"最大回撤: {data['max_drawdown']}%")
    print(f"成立日期: {data['launch_date']}")
else:
    print("\n✗ 抓取失败")
