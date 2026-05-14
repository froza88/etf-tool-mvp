#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从东方财富网批量抓取所有ETF的真实持仓数据（最终版）
读取etf_codes.json获取ETF列表
"""

import re
import time
import random
import json
import requests
from bs4 import BeautifulSoup

def fetch_etf_holdings_from_eastmoney(etf_code):
    """
    从东方财富网抓取ETF前五大持仓
    返回格式：['股票名 占比%', ...]
    """
    url = f"https://fund.eastmoney.com/{etf_code}.html"

    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
    }

    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.encoding = 'utf-8'

        if response.status_code != 200:
            return None

        soup = BeautifulSoup(response.text, 'html.parser')

        # 解析表格数据
        holdings = []

        rows = soup.find_all('tr')
        for row in rows:
            name_td = row.find('td', class_=re.compile('alignLeft'))
            pct_td = row.find('td', class_=re.compile('alignRight.*bold'))

            if name_td and pct_td:
                name = name_td.get_text(strip=True)
                pct = pct_td.get_text(strip=True)

                if re.match(r'[\u4e00-\u9fa5]+', name) and re.match(r'\d+\.\d+%', pct):
                    holdings.append(f"{name} {pct}")
                    if len(holdings) >= 5:
                        break

        if len(holdings) >= 5:
            return holdings[:5]

        return None

    except Exception as e:
        return None

def update_etf_data():
    """更新所有ETF的持仓数据（逐行处理）"""

    # 读取ETF代码列表
    with open('/Users/apangduo/WorkBuddy/Claw/etf-tool-mvp/etf_codes.json', 'r', encoding='utf-8') as f:
        etfs = json.load(f)

    print(f"📊 共 {len(etfs)} 只ETF需要更新\n")

    # 读取原文件
    with open('/Users/apangduo/WorkBuddy/Claw/etf-tool-mvp/etf_data.py', 'r', encoding='utf-8') as f:
        lines = f.readlines()

    new_lines = []
    i = 0
    updated_count = 0
    failed_count = 0
    current_etf_code = None

    while i < len(lines):
        line = lines[i]

        # 检测是否到了code行
        code_match = re.match(r'^(\s+)"code":\s*"(\d+)",?\s*$', line)
        if code_match:
            current_etf_code = code_match.group(2)

        # 检测是否到了top_holdings行
        if '"top_holdings"' in line and current_etf_code:
            print(f"[{updated_count+failed_count+1}/{len(etfs)}] 处理 {current_etf_code}...")

            # 抓取持仓数据
            holdings = fetch_etf_holdings_from_eastmoney(current_etf_code)

            if holdings and len(holdings) == 5:
                # 生成新的top_holdings行
                holdings_str = "[" + ", ".join([f"'{h}'" for h in holdings]) + "]"
                new_lines.append(f'        "top_holdings": {holdings_str},\n')

                # 跳过原来的top_holdings行（可能跨多行）
                while i < len(lines) and ']' not in lines[i]:
                    i += 1
                if i < len(lines):
                    i += 1  # 跳过包含]的行

                print(f"✅ 更新成功: {holdings[0]}")
                updated_count += 1

                # 随机延迟
                if updated_count + failed_count < len(etfs):
                    delay = random.uniform(2, 4)
                    print(f"   等待 {delay:.1f} 秒...")
                    time.sleep(delay)

                current_etf_code = None
                continue
            else:
                print(f"⚠️  抓取失败，保持原数据")
                failed_count += 1

        new_lines.append(line)
        i += 1

    # 备份原文件
    backup_file = '/Users/apangduo/WorkBuddy/Claw/etf-tool-mvp/etf_data.py.backup'
    with open(backup_file, 'w', encoding='utf-8') as f:
        f.writelines(lines)
    print(f"\n✅ 已备份原文件到: {backup_file}")

    # 保存更新后的文件
    with open('/Users/apangduo/WorkBuddy/Claw/etf-tool-mvp/etf_data.py', 'w', encoding='utf-8') as f:
        f.writelines(new_lines)

    print(f"\n📊 更新完成！")
    print(f"   成功: {updated_count} 只ETF")
    print(f"   失败: {failed_count} 只ETF")

if __name__ == "__main__":
    print("🚀 开始批量抓取ETF持仓数据...")
    print("=" * 50)
    update_etf_data()
    print("=" * 50)
    print("✅ 全部完成！")
