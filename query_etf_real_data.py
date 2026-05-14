#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
使用 WeStock Data 批量更新ETF真实数据
自动获取：规模、管理费、托管费、收益率、回撤、夏普比率、成立日期
"""

import subprocess
import json
import re
import time
from datetime import datetime

def query_etf_data(etf_code):
    """
    使用 westockdata 查询ETF真实数据
    返回字典：{字段名: 值}
    """
    try:
        # 调用 westockdata 查询ETF详情
        result = subprocess.run(
            ['npx', '-y', 'westock-data-clawhub@1.0.4', 'etf', f'sh{etf_code}'],
            capture_output=True,
            text=True,
            timeout=30,
            cwd='/Users/apangduo/WorkBuddy/Claw'
        )
        
        if result.returncode != 0:
            return None
        
        output = result.stdout
        
        # 解析Markdown表格数据
        # 格式：| sh510300 | 沪深300ETF华泰柏瑞 | ... |
        pattern = r'\| sh' + etf_code + r' \| ([^\n]+) \|'
        match = re.search(pattern, output)
        
        if not match:
            return None
        
        # 表格有太多字段，直接保存到文件，稍后解析
        with open(f'/tmp/etf_raw_{etf_code}.txt', 'w', encoding='utf-8') as f:
            f.write(output)
        
        # 尝试从输出中提取关键数字
        data = {}
        
        # 使用更简单的方法：让AI分析输出
        # 这里先返回原始输出路径
        return {'raw_file': f'/tmp/etf_raw_{etf_code}.txt'}
        
    except Exception as e:
        print(f"  错误: {e}")
        return None

# 读取当前ETF列表
exec(open('/Users/apangduo/WorkBuddy/Claw/etf-tool-mvp/etf_data.py', 'r', encoding='utf-8').read())

print(f"开始批量查询 {len(ETFs)} 只ETF的真实数据...\n")
print("=" * 100)

success_count = 0
fail_count = 0

for i, etf in enumerate(ETFs):
    code = etf['code']
    print(f"\n[{i+1}/{len(ETFs)}] 查询 {code} {etf['name']}...")
    
    data = query_etf_data(code)
    
    if data and 'raw_file' in data:
        print(f"  ✓ 数据已保存: {data['raw_file']}")
        success_count += 1
    else:
        print(f"  ✗ 查询失败")
        fail_count += 1
    
    # 礼貌延迟
    time.sleep(2)
    
    # 每10只暂停一下，避免被限流
    if (i + 1) % 10 == 0:
        print(f"\n已处理 {i+1} 只，暂停5秒...\n")
        time.sleep(5)

print("\n" + "=" * 100)
print(f"完成！")
print(f"成功: {success_count} 只")
print(f"失败: {fail_count} 只")
print(f"\n原始数据已保存到 /tmp/etf_raw_*.txt")
print("下一步：运行解析脚本，提取字段并更新 etf_data.py")
