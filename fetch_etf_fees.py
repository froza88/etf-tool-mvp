#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量抓取ETF完整真实数据 - 从东方财富网
抓取字段：管理费、托管费、规模、发行方、业绩数据等
"""

import requests
import json
import time
import re
from bs4 import BeautifulSoup

# 读取ETF代码列表
with open('/Users/apangduo/WorkBuddy/Claw/etf-tool-mvp/etf_codes.json', 'r', encoding='utf-8') as f:
    etf_list = json.load(f)

print(f"开始抓取 {len(etf_list)} 只ETF的完整数据...\n")

def fetch_etf_complete_data(etf_code, etf_name):
    """
    从东方财富网抓取ETF完整数据
    """
    url = f"https://fund.eastmoney.com/{etf_code}.html"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
        'Referer': 'https://fund.eastmoney.com/'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.encoding = 'utf-8'
        soup = BeautifulSoup(response.text, 'html.parser')
        
        data = {
            'code': etf_code,
            'name': etf_name,
            'management_fee': None,
            'custody_fee': None,
            'total_fee': None,
            'scale': None,
            'issuer': None
        }
        
        # 方法1：从页面文本中直接提取费率信息
        page_text = soup.get_text()
        
        # 查找管理费率
        mgmt_match = re.search(r'管理费率[：:]\s*([\d.]+)%', page_text)
        if mgmt_match:
            data['management_fee'] = float(mgmt_match.group(1))
        
        # 查找托管费率
        custody_match = re.search(r'托管费率[：:]\s*([\d.]+)%', page_text)
        if custody_match:
            data['custody_fee'] = float(custody_match.group(1))
        
        # 方法2：从表格中查找
        if data['management_fee'] is None:
            tables = soup.find_all('table')
            for table in tables:
                table_text = table.get_text()
                if '管理费率' in table_text or '基金托管费' in table_text:
                    # 解析表格中的费率
                    mgmt = re.search(r'管理费率[：:]*\s*([\d.]+)', table_text)
                    if mgmt:
                        data['management_fee'] = float(mgmt.group(1))
                    custody = re.search(r'托管费率[：:]*\s*([\d.]+)', table_text)
                    if custody:
                        data['custody_fee'] = float(custody.group(1))
                    break
        
        # 计算总费率
        if data['management_fee'] is not None and data['custody_fee'] is not None:
            data['total_fee'] = round(data['management_fee'] + data['custody_fee'], 3)
        elif data['management_fee'] is not None:
            data['total_fee'] = data['management_fee']
        elif data['custody_fee'] is not None:
            data['total_fee'] = data['custody_fee']
        
        # 查找发行方
        issuer_patterns = [
            r'基金管理人[：:]\s*([\u4e00-\u9fa5]+基金)',
            r'基金管理[：:]\s*([\u4e00-\u9fa5]+基金)',
            r'([\u4e00-\u9fa5]+(?:基金|资管|证券))'
        ]
        
        for pattern in issuer_patterns:
            issuer_match = re.search(pattern, page_text)
            if issuer_match:
                data['issuer'] = issuer_match.group(1)
                break
        
        # 查找基金规模
        scale_patterns = [
            r'基金规模[：:]\s*([\d.]+)\s*亿元',
            r'资产净值[：:]\s*([\d.]+)\s*亿元',
            r'最新规模[：:]\s*([\d.]+)\s*亿'
        ]
        
        for pattern in scale_patterns:
            scale_match = re.search(pattern, page_text)
            if scale_match:
                data['scale'] = float(scale_match.group(1))
                break
        
        return data
        
    except Exception as e:
        print(f"  ✗ {etf_code} 抓取失败: {str(e)}")
        return None

# 抓取所有ETF数据
results = []
failed = []

for i, etf in enumerate(etf_list, 1):
    etf_code = etf['code']
    etf_name = etf['name']
    
    print(f"[{i}/{len(etf_list)}] 正在抓取 {etf_code} {etf_name}...", end=' ')
    
    data = fetch_etf_complete_data(etf_code, etf_name)
    
    if data:
        results.append(data)
        fee_info = f"管理费:{data['management_fee']}% 托管费:{data['custody_fee']}%" if data['total_fee'] else "未找到费率"
        print(f"✓ {fee_info}")
    else:
        failed.append(etf)
        print("✗ 失败")
    
    # 礼貌性延迟
    time.sleep(0.5)

# 保存结果
print(f"\n抓取完成！")
print(f"成功: {len(results)} 只")
print(f"失败: {len(failed)} 只")

if results:
    # 保存为JSON
    with open('/Users/apangduo/WorkBuddy/Claw/etf-tool-mvp/etf_fees_data.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\n数据已保存到: etf_fees_data.json")
    
    # 显示部分结果
    print("\n前5只ETF的费率信息:")
    for item in results[:5]:
        print(f"  {item['code']} {item['name']}")
        print(f"    管理费: {item['management_fee']}%  托管费: {item['custody_fee']}%  总费率: {item['total_fee']}%")

if failed:
    print("\n失败的ETF:")
    for item in failed:
        print(f"  {item['code']} {item['name']}")
