#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
完整版：批量抓取并更新ETF真实数据
直接解析Markdown表格，根据字段位置提取数据
"""

import subprocess
import re
import time
import os

def fetch_etf_to_file(etf_code):
    """调用CLI并保存输出到文件"""
    output_file = f'/tmp/etf_{etf_code}.txt'
    cmd = f"npx -y westock-data-clawhub@1.0.4 etf sh{etf_code} > {output_file} 2>/dev/null"
    ret = subprocess.run(cmd, shell=True, timeout=30, cwd='/Users/apangduo/WorkBuddy/Claw')
    return os.path.exists(output_file) and os.path.getsize(output_file) > 100

def parse_etf_file(file_path, etf_code):
    """解析文件，提取关键字段"""
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    
    # 找到数据行
    pattern = rf'\| sh{etf_code} \| ([^\n]+)'
    match = re.search(pattern, content)
    
    if not match:
        return None
    
    data_line = match.group(0)
    fields = [f.strip() for f in data_line.split('|')]
    
    # 根据刚才解析的字段位置
    # [5]: establishDate (2012-05-04 00:00:00)
    # [15]: closePrice (5.02)
    # [16]: changePct (1.09)
    # [17]: turnoverVolume (12726150)
    # [18]: turnoverValue (6331249194)
    # [19]: turnoverRate (3.81)
    # [20]: totalMV (167425000000) <- 规模！
    # 后面的字段：return1Y, return3Y, maxDrawdown等
    
    data = {}
    
    try:
        # 规模（单位：元，转为亿元）
        if len(fields) > 20:
            total_mv = float(fields[20])
            data['scale'] = round(total_mv / 100000000, 2)
        
        # 成立日期
        if len(fields) > 5:
            date_str = fields[5]
            date_match = re.search(r'(\d{4}-\d{2}-\d{2})', date_str)
            if date_match:
                data['launch_date'] = date_match.group(1)
        
        # 管理费和托管费（在表格后面部分）
        # 查找所有百分比数字
        pct_values = re.findall(r'(\d+\.\d+)%', data_line)
        if len(pct_values) >= 2:
            data['management_fee'] = float(pct_values[0])
            data['custody_fee'] = float(pct_values[1])
            data['fee'] = round(data['management_fee'] + data['custody_fee'], 2)
        
        # 收益率和回撤（需要找到正确的字段位置）
        # 从表格末尾往前找
        numeric_fields = []
        for f in fields:
            try:
                val = float(f)
                numeric_fields.append(val)
            except:
                pass
        
        # 通常最后几个数字字段是：return1Y, return3Y, maxDrawdown1Y, sharpe等
        if len(numeric_fields) >= 4:
            data['year_1_return'] = numeric_fields[-4]
            data['year_3_return'] = numeric_fields[-3]
            data['max_drawdown'] = numeric_fields[-2]
            if len(numeric_fields) >= 5:
                data['sharpe_ratio'] = numeric_fields[-5]
        
        return data if data else None
        
    except Exception as e:
        print(f"  解析错误: {e}")
        return None

# 读取当前ETF列表
exec(open('/Users/apangduo/WorkBuddy/Claw/etf-tool-mvp/etf_data.py', 'r', encoding='utf-8').read())

print(f"开始批量抓取 {len(ETFs)} 只ETF的真实数据...\n")

success_count = 0
fail_count = 0
results = []

for i, etf in enumerate(ETFs):
    code = etf['code']
    print(f"[{i+1}/{len(ETFs)}] 抓取 {code} {etf['name'][:20]}...", end=' ')
    
    # 抓取
    if not fetch_etf_to_file(code):
        print("✗ 抓取失败")
        fail_count += 1
        continue
    
    # 解析
    data = parse_etf_file(f'/tmp/etf_{code}.txt', code)
    
    if not data:
        print("✗ 解析失败")
        fail_count += 1
        continue
    
    # 保存结果
    results.append({'code': code, 'data': data})
    print(f"✓ scale={data.get('scale', '?')}  launch={data.get('launch_date', '?')}")
    success_count += 1
    
    # 每10只暂停
    if (i + 1) % 10 == 0:
        print(f"\n已处理 {i+1} 只，暂停3秒...\n")
        time.sleep(3)
    else:
        time.sleep(1)

print(f"\n\n{'='*80}")
print(f"完成！成功: {success_count} 只，失败: {fail_count} 只")

# 保存结果到JSON
import json
with open('/tmp/etf_real_data.json', 'w', encoding='utf-8') as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

print(f"\n数据已保存到: /tmp/etf_real_data.json")
print("下一步：运行 update_etf_data.py 将真实数据更新到 etf_data.py")
