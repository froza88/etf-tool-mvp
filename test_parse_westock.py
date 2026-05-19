#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试解析 westock-data etf 命令的输出
"""
import re
from pathlib import Path

def parse_westock_etf_output(output_text):
    """
    解析 westock-data etf 命令的输出
    返回: list of dict, 每个dict包含一个ETF的数据
    """
    results = []
    
    # 按 #### 分割每个ETF的数据块
    blocks = re.split(r'^#### ', output_text, flags=re.MULTILINE)
    
    for block in blocks[1:]:  # 第一个是空字符串
        lines = block.strip().split('\n')
        etf_code = lines[0].strip()  # 第一行是ETF代码
        
        etf_data = {'code': etf_code}
        
        # 查找主表格（包含 | code | name | date | ...）
        in_main_table = False
        for i, line in enumerate(lines):
            if '| code | name | date |' in line:
                # 找到主表格的header行
                header_line = line
                # 下一行是分隔线（|---|---|...）
                # 再下一行是数据行
                data_line = lines[i+2] if i+2 < len(lines) else ''
                
                # 解析header和data
                headers = [h.strip() for h in header_line.split('|')[1:-1]]
                values = [v.strip() for v in data_line.split('|')[1:-1]]
                
                # 创建字段映射
                for j, header in enumerate(headers):
                    if j < len(values):
                        etf_data[header] = values[j]
                
                in_main_table = True
                break
        
        # 查找持仓明细表格
        in_holdings = False
        holdings = []
        for i, line in enumerate(lines):
            if '**持仓明细' in line or '**持仓' in line:
                # 找到持仓表格开始
                # 跳过表头和分隔线
                for j in range(i+3, min(i+25, len(lines))):
                    if lines[j].startswith('|') and '---' not in lines[j]:
                        # 解析持仓行
                        parts = [p.strip() for p in lines[j].split('|')[1:-1]]
                        if len(parts) >= 3:
                            holdings.append({
                                'code': parts[0],
                                'name': parts[1],
                                'ratio': parts[2]
                            })
                    elif not lines[j].startswith('|'):
                        break
                break
        
        etf_data['holdings'] = holdings
        results.append(etf_data)
    
    return results

# 测试：解析样例文件
sample_file = Path('/tmp/westock_etf_sample.txt')
if sample_file.exists():
    with open(sample_file, 'r', encoding='utf-8') as f:
        output_text = f.read()
    
    results = parse_westock_etf_output(output_text)
    
    print(f"解析到 {len(results)} 只ETF的数据\n")
    
    for etf in results:
        print(f"ETF: {etf['code']} - {etf.get('name', 'N/A')}")
        print(f"  管理人: {etf.get('manageInstitution', 'N/A')}")
        print(f"  规模: {etf.get('size', 'N/A')}")
        print(f"  收盘价: {etf.get('closePrice', 'N/A')}")
        print(f"  持仓数量: {len(etf.get('holdings', []))} 只")
        if etf.get('holdings'):
            print(f"  前3大持仓: {[h['name'] for h in etf['holdings'][:3]]}")
        print()
else:
    print(f"样例文件不存在: {sample_file}")
