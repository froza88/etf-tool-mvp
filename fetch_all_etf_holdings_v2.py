#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从东方财富网批量抓取所有ETF的真实持仓数据
使用正则表达式解析HTML页面
"""

import re
import time
import random
import requests
from bs4 import BeautifulSoup

# 读取现有的ETF数据
exec(open('/Users/apangduo/WorkBuddy/Claw/etf-tool-mvp/etf_data.py', 'r', encoding='utf-8').read())

def fetch_etf_holdings_from_eastmoney(etf_code):
    """
    从东方财富网抓取ETF前五大持仓
    返回格式：['股票名 占比%', ...]
    """
    url = f"https://fund.eastmoney.com/{etf_code}.html"

    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'Referer': 'https://fund.eastmoney.com/',
    }

    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.encoding = 'utf-8'

        if response.status_code != 200:
            print(f"❌ {etf_code} 请求失败: {response.status_code}")
            return None

        # 方法1：使用正则表达式提取持仓数据
        # 匹配格式：数字. 股票名 百分比%
        pattern = r'\d+\.\s*([\u4e00-\u9fa5]+)\s*(\d+\.\d+)%'
        matches = re.findall(pattern, response.text)

        if matches and len(matches) >= 5:
            holdings = [f"{name} {pct}%" for name, pct in matches[:5]]
            return holdings

        # 方法2：使用BeautifulSoup解析
        soup = BeautifulSoup(response.text, 'html.parser')

        # 查找所有包含数字的列表项
        holdings = []
        for li in soup.find_all('li'):
            text = li.get_text(strip=True)
            match = re.match(r'\d+\.\s*([\u4e00-\u9fa5]+)\s*(\d+\.\d+)%?', text)
            if match:
                name = match.group(1)
                pct = match.group(2)
                holdings.append(f"{name} {pct}%")
                if len(holdings) >= 5:
                    break

        if holdings:
            return holdings[:5]

        # 方法3：查找表格中的数据
        tables = soup.find_all('table')
        for table in tables:
            rows = table.find_all('tr')
            for row in rows:
                cells = row.find_all(['td', 'th'])
                if len(cells) >= 2:
                    text = ' '.join([cell.get_text(strip=True) for cell in cells])
                    match = re.search(r'([\u4e00-\u9fa5]+)\s*(\d+\.\d+)%?', text)
                    if match:
                        name = match.group(1)
                        pct = match.group(2)
                        if name not in [h.split()[0] for h in holdings]:
                            holdings.append(f"{name} {pct}%")
                            if len(holdings) >= 5:
                                break
            if len(holdings) >= 5:
                break

        if holdings:
            return holdings[:5]

        print(f"⚠️  {etf_code} 未找到持仓数据")
        return None

    except Exception as e:
        print(f"❌ {etf_code} 抓取失败: {str(e)}")
        return None

def update_etf_data():
    """更新所有ETF的持仓数据"""

    updated_count = 0
    failed_count = 0
    failed_etfs = []

    # 读取原文件
    with open('/Users/apangduo/WorkBuddy/Claw/etf-tool-mvp/etf_data.py', 'r', encoding='utf-8') as f:
        lines = f.readlines()

    new_lines = []
    i = 0
    while i < len(lines):
        line = lines[i]

        # 检测是否到了top_holdings行
        if '"top_holdings"' in line:
            # 向前查找code
            etf_code = None
            for j in range(max(0, i-20), i):
                code_match = re.match(r'^\s+"code":\s*"(\d+)",?\s*$', lines[j])
                if code_match:
                    etf_code = code_match.group(1)
                    break

            if etf_code:
                print(f"\n处理 {etf_code}...")
                holdings = fetch_etf_holdings_from_eastmoney(etf_code)

                if holdings and len(holdings) == 5:
                    # 生成新的top_holdings行
                    holdings_str = '[' + ', '.join([f"'{h}'" for h in holdings]) + ']'
                    # 找到top_holdings的结束位置
                    new_lines.append(f'        "top_holdings": {holdings_str},\n')

                    # 跳过原来的top_holdings行（可能跨多行）
                    while i < len(lines) and ']' not in lines[i]:
                        i += 1
                    if i < len(lines):
                        i += 1  # 跳过包含]的行

                    print(f"✅ {etf_code} 更新成功: {holdings[0]}")
                    updated_count += 1

                    # 随机延迟
                    delay = random.uniform(1, 3)
                    print(f"   等待 {delay:.1f} 秒...")
                    time.sleep(delay)
                    continue
                else:
                    failed_count += 1
                    failed_etfs.append(etf_code)
                    print(f"⚠️  {etf_code} 抓取失败，保持原数据")

        new_lines.append(line)
        i += 1

    # 保存更新后的文件
    backup_file = '/Users/apangduo/WorkBuddy/Claw/etf-tool-mvp/etf_data.py.backup'
    with open(backup_file, 'w', encoding='utf-8') as f:
        f.writelines(lines)
    print(f"\n✅ 已备份原文件到: {backup_file}")

    with open('/Users/apangduo/WorkBuddy/Claw/etf-tool-mvp/etf_data.py', 'w', encoding='utf-8') as f:
        f.writelines(new_lines)

    print(f"\n📊 更新完成！")
    print(f"   成功: {updated_count} 只ETF")
    print(f"   失败: {failed_count} 只ETF")
    if failed_etfs:
        print(f"   失败列表: {failed_etfs}")

if __name__ == "__main__":
    print("🚀 开始批量抓取ETF持仓数据...")
    print("=" * 50)
    update_etf_data()
    print("=" * 50)
    print("✅ 全部完成！")
