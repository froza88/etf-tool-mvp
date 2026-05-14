#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
解析已抓取的ETF数据文件，更新 etf_data.py
只处理成功抓取的ETF（37行的文件）
"""

import re
import os

def parse_etf_file(file_path):
    """解析单个ETF数据文件"""
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    
    # 找到数据行（包含 shXXXXX)
    pattern = r'\| (sh\d+) \| ([^\n]+)'
    match = re.search(pattern, content)
    
    if not match:
        return None
    
    etf_code = match.group(1)  # sh510300
    data_line = match.group(0)
    
    # 分割字段
    fields = [f.strip() for f in data_line.split('|')]
    
    # 提取数据
    data = {}
    try:
        # [5]: establishDate (2012-05-04 00:00:00)
        if len(fields) > 5:
            date_str = fields[5]
            date_match = re.search(r'(\d{4}-\d{2}-\d{2})', date_str)
            if date_match:
                data['launch_date'] = date_match.group(1)
        
        # [15-24]: 各种数值字段
        # [20]: totalMV (规模，单位：元)
        if len(fields) > 20:
            try:
                total_mv = float(fields[20])
                data['scale'] = round(total_mv / 100000000, 2)
            except:
                pass
        
        # 查找管理费和托管费（百分比格式）
        pct_values = re.findall(r'(\d+\.\d+)%', data_line)
        if len(pct_values) >= 2:
            data['management_fee'] = float(pct_values[0])
            data['custody_fee'] = float(pct_values[1])
            data['fee'] = round(data['management_fee'] + data['custody_fee'], 2)
        
        # 收益率和回撤（在后面字段）
        # 尝试提取数字字段
        numeric_fields = []
        for f in fields:
            try:
                val = float(f)
                numeric_fields.append(val)
            except:
                pass
        
        # 通常最后几个是收益率和回撤
        if len(numeric_fields) >= 5:
            data['year_1_return'] = numeric_fields[-5]
            data['year_3_return'] = numeric_fields[-4]
            data['max_drawdown'] = numeric_fields[-3]
            if len(numeric_fields) >= 6:
                data['sharpe_ratio'] = numeric_fields[-6]
        
        data['code'] = etf_code[2:]  # 去掉sh前缀
        return data
        
    except Exception as e:
        print(f"  解析错误: {e}")
        return None

# 读取当前ETF列表
exec(open('/Users/apangduo/WorkBuddy/Claw/etf-tool-mvp/etf_data.py', 'r', encoding='utf-8').read())

# 找到所有成功抓取的文件
import glob
success_files = glob.glob('/tmp/etf_*.txt')

print(f"找到 {len(success_files)} 个数据文件")
print(f"开始解析并更新数据...\n")

updated_count = 0
failed_count = 0

for file_path in success_files:
    # 跳过错误文件（只有几行）
    if os.path.getsize(file_path) < 1000:  # 小于1KB，可能是错误文件
        continue
    
    data = parse_etf_file(file_path)
    
    if not data or 'code' not in data:
        failed_count += 1
        continue
    
    # 在ETF列表中找到对应的ETF并更新
    etf_code = data['code']
    found = False
    
    for etf in ETFs:
        if etf['code'] == etf_code:
            # 更新字段
            if 'scale' in data:
                etf['scale'] = data['scale']
            if 'launch_date' in data:
                etf['launch_date'] = data['launch_date']
            if 'management_fee' in data:
                etf['management_fee'] = data['management_fee']
                etf['custody_fee'] = data['custody_fee']
                etf['fee'] = data['fee']
            if 'year_1_return' in data:
                etf['year_1_return'] = data['year_1_return']
                etf['year_3_return'] = data['year_3_return']
                etf['max_drawdown'] = data['max_drawdown']
                if 'sharpe_ratio' in data:
                    etf['sharpe_ratio'] = data['sharpe_ratio']
            
            print(f"✓ 已更新 {etf_code}: scale={data.get('scale', '?')}  fee={data.get('fee', '?')}")
            updated_count += 1
            found = True
            break
    
    if not found:
        print(f"✗ 未找到 {etf_code} 在 etf_data.py 中")
        failed_count += 1

print(f"\n\n{'='*80}")
print(f"完成！成功更新: {updated_count} 只，失败: {failed_count} 只")

# 保存更新后的文件
output = "ETFs = [\n"
for i, etf in enumerate(ETFs):
    output += "    {\n"
    for key, value in etf.items():
        if key == 'top_holdings':
            holdings_str = "[" + ", ".join([f"'{h}'" for h in value]) + "]"
            output += f"        \"{key}\": {holdings_str},\n"
        elif isinstance(value, str):
            output += f"        \"{key}\": \"{value}\",\n"
        else:
            output += f"        \"{key}\": {value},\n"
    
    if i < len(ETFs) - 1:
        output += "    },\n"
    else:
        output += "    }\n"

output += "]\n"

with open('/Users/apangduo/WorkBuddy/Claw/etf-tool-mvp/etf_data_updated.py', 'w', encoding='utf-8') as f:
    f.write(output)

print(f"\n已保存到: etf_data_updated.py")
print(f"请检查无误后重命名为 etf_data.py")
