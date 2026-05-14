#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从东方财富网批量抓取所有ETF的真实持仓数据（最终简化版）
直接在脚本内部解析etf_data.py
"""

import re
import time
import random
import requests
from bs4 import BeautifulSoup

# 读取etf_data.py并提取ETF代码列表
def get_etf_codes():
    with open('/Users/apangduo/WorkBuddy/Claw/etf-tool-mvp/etf_data.py', 'r', encoding='utf-8') as f:
        content = f.read()

    # 执行文件内容获取ETFs变量
    exec_globals = {}
    exec(content, exec_globals)

    # 返回ETF代码和名称的列表
    etfs = []
    for etf in exec_globals.get('ETFs', []):
        etfs.append({
            'code': etf['code'],
            'name': etf['name']
        })
    return etfs

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

        soup = BeautifulSoup(response.text, 'html.parser')

        # 方法1：解析表格数据
        holdings = []

        # 查找所有行
        rows = soup.find_all('tr')
        for row in rows:
            # 查找股票名称列
            name_td = row.find('td', class_=re.compile('alignLeft'))
            pct_td = row.find('td', class_=re.compile('alignRight.*bold'))

            if name_td and pct_td:
                # 提取股票名称
                name = name_td.get_text(strip=True)
                # 提取占比
                pct = pct_td.get_text(strip=True)

                # 验证名称是中文，占比是数字+%
                if re.match(r'[\u4e00-\u9fa5]+', name) and re.match(r'\d+\.\d+%', pct):
                    holdings.append(f"{name} {pct}")
                    if len(holdings) >= 5:
                        break

        if len(holdings) >= 5:
            return holdings[:5]

        # 方法2：使用正则表达式直接匹配
        pattern = r'<a[^>]*>([\u4e00-\u9fa5]+)</a>\s*</td>\s*<td[^>]*>(\d+\.\d+%)'
        matches = re.findall(pattern, response.text)

        if matches and len(matches) >= 5:
            holdings = [f"{name} {pct}" for name, pct in matches[:5]]
            return holdings

        print(f"⚠️  {etf_code} 未找到持仓数据")
        return None

    except Exception as e:
        print(f"❌ {etf_code} 抓取失败: {str(e)}")
        return None

def update_etf_data():
    """更新所有ETF的持仓数据"""

    # 获取ETF列表
    etfs = get_etf_codes()
    print(f"📊 共 {len(etfs)} 只ETF需要更新\n")

    # 读取原文件
    with open('/Users/apangduo/WorkBuddy/Claw/etf-tool-mvp/etf_data.py', 'r', encoding='utf-8') as f:
        content = f.read()

    updated_count = 0
    failed_count = 0
    failed_etfs = []

    for i, etf in enumerate(etfs):
        etf_code = etf['code']
        etf_name = etf['name']

        print(f"[{i+1}/{len(etfs)}] 正在抓取 {etf_code} {etf_name}...")

        # 抓取持仓数据
        holdings = fetch_etf_holdings_from_eastmoney(etf_code)

        if holdings and len(holdings) == 5:
            # 生成新的top_holdings字符串
            holdings_str = "[" + ", ".join([f"'{h}'" for h in holdings]) + "]"

            # 使用正则表达式替换
            # 查找这个ETF的top_holdings字段
            pattern = rf'("code":\s*"{etf_code}".*?"top_holdings":\s*)\[.*?\]'
            replacement = rf'\1{holdings_str}'

            new_content = re.sub(pattern, replacement, content, flags=re.DOTALL)

            if new_content != content:
                content = new_content
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
        if i < len(etfs) - 1:  # 最后一个不需要延迟
            delay = random.uniform(2, 4)
            print(f"   等待 {delay:.1f} 秒...")
            time.sleep(delay)

    # 备份原文件
    backup_file = '/Users/apangduo/WorkBuddy/Claw/etf-tool-mvp/etf_data.py.backup'
    import shutil
    shutil.copy('/Users/apangduo/WorkBuddy/Claw/etf-tool-mvp/etf_data.py', backup_file)
    print(f"\n✅ 已备份原文件到: {backup_file}")

    # 保存更新后的文件
    with open('/Users/apangduo/WorkBuddy/Claw/etf-tool-mvp/etf_data.py', 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"\n📊 更新完成！")
    print(f"   成功: {updated_count} 只ETF")
    print(f"   失败: {failed_count} 只ETF")
    if failed_etfs:
        print(f"   失败列表（前10）: {failed_etfs[:10]}")

if __name__ == "__main__":
    print("🚀 开始批量抓取ETF持仓数据...")
    print("=" * 50)
    update_etf_data()
    print("=" * 50)
    print("✅ 全部完成！")
