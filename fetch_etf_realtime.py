#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量使用 WeStock Data 抓取ETF真实数据
直接解析Markdown表格，更新 etf_data.py
"""

import subprocess
import re
import time
import sys

def fetch_etf_markdown(etf_code):
    """获取ETF数据的Markdown原始文本"""
    try:
        result = subprocess.run(
            ['npx', '-y', 'westock-data-clawhub@1.0.4', 'etf', f'sh{etf_code}'],
            capture_output=True,
            text=True,
            timeout=30,
            cwd='/Users/apangduo/WorkBuddy/Claw'
        )
        if result.returncode == 0 and result.stdout:
            return result.stdout
        return None
    except Exception as e:
        return None

def parse_etf_data(md_text, etf_code):
    """
    解析WeStock返回的Markdown表格
    从单行表格中提取所有字段
    """
    if not md_text:
        return None
    
    # 找到包含ETF代码的数据行
    # 格式: | sh510300 | 沪深300ETF华泰柏瑞 | 2026-05-13 | 规模 | 2012-05-04 ...
    pattern = rf'\| sh{etf_code} \| ([^\n]+)'
    match = re.search(pattern, md_text)
    
    if not match:
        return None
    
    # 整个数据行
    data_line = match.group(0)
    
    # 用正则提取关键字段（根据表格列顺序）
    # 表头顺序: code|name|date|etfType|establishDate|...|totalMV|...|managementFee|custodyFee|...|return1Y|return3Y|...|maxDrawdown1Y|...
    
    # 简单粗暴的方法：按 | 分割，然后对照表头
    # 但Markdown表格字段太多，用正则直接提取数字
    
    data = {}
    
    # 提取规模 totalMV (单位：元)
    mv_match = re.search(r'\| (\d{5,}) \|', data_line)
    if mv_match:
        total_mv = float(mv_match.group(1))
        data['scale'] = round(total_mv / 100000000, 2)  # 转为亿元
    
    # 提取管理费
    # 在表格中，managementFee 通常在第18个字段左右
    # 改用更简单的方法：查找所有数字+%模式
    pct_matches = re.findall(r'(\d+\.?\d*)%', data_line)
    if len(pct_matches) >= 2:
        data['management_fee'] = float(pct_matches[0])  # 第一个%通常是管理费
        data['custody_fee'] = float(pct_matches[1])   # 第二个%是托管费
        data['fee'] = round(data['management_fee'] + data['custody_fee'], 2)
        
    # 提取收益率和回撤
    # return1Y, return3Y, maxDrawdown1Y 在表格后面部分
    # 提取所有带负号或正号的数字
    num_matches = re.findall(r'([-+]?\d+\.?\d*)', data_line)
    
    # 这会匹配太多数字，需要更智能的解析
    # 暂时先返回原始文本，让后续处理
    
    return data

def test_single_etf():
    """测试单只ETF抓取"""
    code = '510300'
    print(f"测试抓取 {code}...")
    
    md = fetch_etf_markdown(code)
    if not md:
        print("  ✗ 抓取失败")
        return
    
    print("  ✓ 抓取成功，正在解析...")
    
    # 保存到文件以便查看
    with open(f'/tmp/etf_{code}_raw.txt', 'w', encoding='utf-8') as f:
        f.write(md)
    print(f"  原始数据已保存: /tmp/etf_{code}_raw.txt")
    
    # 尝试解析
    data = parse_etf_data(md, code)
    if data:
        print(f"  解析结果: {data}")
    else:
        print("  ✗ 解析失败")

if __name__ == '__main__':
    test_single_etf()
