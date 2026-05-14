#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从东方财富网批量抓取所有ETF的真实持仓数据
自动更新 etf_data.py
"""

import re
import time
import random
import json
from bs4 import BeautifulSoup
import requests

# 读取现有的ETF数据
exec(open('etf_data.py', 'r', encoding='utf-8').read())

def fetch_etf_holdings_from_eastmoney(etf_code):
    """
    从东方财富网抓取ETF前五大持仓
    返回格式：['股票名 占比%', ...]
    """
    url = f"https://fund.eastmoney.com/{etf_code}.html"

    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'Referer': 'https://fund.eastmoney.com/',
    }

    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.encoding = 'utf-8'

        if response.status_code != 200:
            print(f"❌ {etf_code} 请求失败: {response.status_code}")
            return None

        soup = BeautifulSoup(response.text, 'html.parser')

        # 方法1：查找持仓表格
        holdings = []

        # 尝试查找持仓数据的script标签
        scripts = soup.find_all('script')
        for script in scripts:
            if script.string and 'position' in script.string:
                # 解析JavaScript中的持仓数据
                # 示例数据格式：	data: [{"gpmc":"1","gpdm":"300750","gpmc":"宁德时代","zjbl":"4.27"}]
                pattern = r'"gpdm":"(\d+)"|"zqdm":"(\d+)"'
                # 更复杂的解析逻辑...
                pass

        # 方法2：直接解析HTML表格（更可靠）
        # 查找包含持仓信息的表格
        tables = soup.find_all('table')
        for table in tables:
            rows = table.find_all('tr')
            for row in rows:
                cells = row.find_all(['td', 'th'])
                if len(cells) >= 3:
                    # 尝试提取股票名称和占比
                    text = ' '.join([cell.get_text(strip=True) for cell in cells])
                    # 匹配：股票名 + 数字%
                    match = re.search(r'([\u4e00-\u9fa5]+)\s+(\d+\.\d+)%?', text)
                    if match:
                        stock_name = match.group(1)
                        percentage = match.group(2)
                        holdings.append(f"{stock_name} {percentage}%")

        if holdings:
            return holdings[:5]  # 只返回前5个

        # 方法3：使用正则表达式直接从HTML中提取
        # 东方财富网的页面通常包含这样的数据：
        # <span class="name">宁德时代</span><span class="ratio">4.27%</span>
        name_pattern = r'<span[^>]*class="[^"]*name[^"]*"[^>]*>([\u4e00-\u9fa5]+)</span>'
        ratio_pattern = r'<span[^>]*class="[^"]*ratio[^"]*"[^>]*>(\d+\.\d+)%</span>'

        names = re.findall(name_pattern, response.text)
        ratios = re.findall(ratio_pattern, response.text)

        if names and ratios:
            holdings = [f"{names[i]} {ratios[i]}%" for i in range(min(5, len(names), len(ratios)))]
            return holdings

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
    with open('etf_data.py', 'r', encoding='utf-8') as f:
        content = f.read()

    # 遍历所有ETF
    for i, etf in enumerate(ETFs):
        etf_code = etf['code']
        etf_name = etf['name']

        print(f"\n[{i+1}/{len(ETFs)}] 正在抓取 {etf_code} {etf_name}...")

        # 抓取持仓数据
        holdings = fetch_etf_holdings_from_eastmoney(etf_code)

        if holdings and len(holdings) == 5:
            # 更新 top_holdings
            holdings_str = "[" + ", ".join([f"'{h}'" for h in holdings]) + "]"
            old_pattern = rf'("code":\s*"{etf_code}".*?"top_holdings":\s*)\[.*?\]'
            new_str = rf'\1{holdings_str}'

            content_new = re.sub(old_pattern, new_str, content, flags=re.DOTALL)

            if content_new != content:
                content = content_new
                print(f"✅ {etf_code} 更新成功: {holdings[0]}")
                updated_count += 1
            else:
                print(f"⚠️  {etf_code} 更新失败：未找到匹配项")
                failed_count += 1
                failed_etfs.append(etf_code)
        else:
            print(f"⚠️  {etf_code} 抓取失败，保持原数据")
            failed_count += 1
            failed_etfs.append(etf_code)

        # 随机延迟，避免被封
        delay = random.uniform(1, 3)
        print(f"   等待 {delay:.1f} 秒...")
        time.sleep(delay)

    # 保存更新后的文件
    backup_file = 'etf_data.py.backup'
    import shutil
    shutil.copy('etf_data.py', backup_file)
    print(f"\n✅ 已备份原文件到: {backup_file}")

    with open('etf_data.py', 'w', encoding='utf-8') as f:
        f.write(content)

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
