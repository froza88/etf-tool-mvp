#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ETF持仓数据批量更新脚本 v2.0
数据来源: 东方财富网 https://fund.eastmoney.com/

功能:
1. 从 etf_data.py 读取所有ETF代码
2. 从东方财富网批量获取持仓数据
3. 更新 etf_data.py 中的 top_holdings 字段
4. 支持缓存和断点续传
"""

import re
import time
import json
import requests
from bs4 import BeautifulSoup
from pathlib import Path

# 配置
ETF_DATA_FILE = Path(__file__).parent / 'etf_data.py'
CACHE_DIR = Path(__file__).parent / 'cache'
CACHE_FILE = CACHE_DIR / 'etf_holdings_cache.json'

# 确保缓存目录存在
CACHE_DIR.mkdir(exist_ok=True)


def read_etf_codes():
    """从 etf_data.py 读取所有ETF代码"""
    with open(ETF_DATA_FILE, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 使用正则提取所有ETF代码
    pattern = r'"code":\s*"(\d+)"'
    codes = re.findall(pattern, content)
    
    # 去重但保持顺序
    seen = set()
    unique_codes = []
    for code in codes:
        if code not in seen:
            unique_codes.append(code)
            seen.add(code)
    
    return unique_codes


def load_cache():
    """加载缓存的持仓数据"""
    if CACHE_FILE.exists():
        with open(CACHE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


def save_cache(cache):
    """保存缓存"""
    with open(CACHE_FILE, 'w', encoding='utf-8') as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)


def fetch_etf_holdings(etf_code, max_retries=3):
    """
    从东方财富网获取ETF持仓数据
    
    参数:
        etf_code: ETF代码，如 "510300"
        max_retries: 最大重试次数
    
    返回:
        list: ['股票名称 占比%', ...] 或 None
    """
    url = f"https://fund.eastmoney.com/{etf_code}.html"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    }
    
    for attempt in range(max_retries):
        try:
            response = requests.get(url, headers=headers, timeout=15)
            response.encoding = 'utf-8'
            
            if response.status_code != 200:
                print(f"   ⚠️  HTTP {response.status_code}，重试 {attempt+1}/{max_retries}")
                time.sleep(2)
                continue
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 查找持仓数据表格
            # 东方财富网的持仓表格通常有特定的class或结构
            holdings = []
            
            # 方法1: 查找所有表格，寻找包含"股票代码"或"持仓比例"的表格
            tables = soup.find_all('table')
            
            for table in tables:
                # 检查表头是否包含关键词
                headers = table.find_all('th')
                header_text = ' '.join([h.get_text(strip=True) for h in headers])
                
                if '股票代码' in header_text or '持仓比例' in header_text or '占净值' in header_text:
                    # 找到正确的表格
                    rows = table.find_all('tr')[1:11]  # 前10大持仓，跳过表头
                    
                    for row in rows:
                        cols = row.find_all('td')
                        if len(cols) >= 3:
                            # 尝试多种可能的列位置
                            stock_name = None
                            holding_pct = None
                            
                            # 尝试查找股票名称和持仓比例
                            for i, col in enumerate(cols):
                                text = col.get_text(strip=True)
                                
                                # 持仓比例通常包含 %
                                if '%' in text and len(text) <= 10:
                                    holding_pct = text
                                
                                # 股票名称通常是纯中文或中英文混合
                                if re.match(r'^[\u4e00-\u9fa5a-zA-Z]+$', text) and len(text) >= 2:
                                    stock_name = text
                            
                            # 如果上面没找到，尝试固定位置
                            if not stock_name and len(cols) >= 2:
                                stock_name = cols[1].get_text(strip=True)
                            if not holding_pct and len(cols) >= 3:
                                holding_pct = cols[2].get_text(strip=True)
                            
                            if stock_name and holding_pct and '%' in holding_pct:
                                holdings.append(f"{stock_name} {holding_pct}")
                            
                            if len(holdings) >= 10:
                                break
                    
                    if holdings:
                        return holdings
            
            # 方法2: 如果上面没找到，尝试查找 class 包含 "hold" 或 "position" 的表格
            if not holdings:
                tables = soup.find_all('table', class_=re.compile(r'hold|position|持仓', re.I))
                
                for table in tables:
                    rows = table.find_all('tr')[1:11]
                    
                    for row in rows:
                        cols = row.find_all('td')
                        if len(cols) >= 3:
                            stock_name = cols[1].get_text(strip=True)
                            holding_pct = cols[2].get_text(strip=True)
                            
                            if stock_name and '%' in holding_pct:
                                holdings.append(f"{stock_name} {holding_pct}")
                            
                            if len(holdings) >= 10:
                                break
                    
                    if holdings:
                        return holdings
            
            # 如果还是没找到，可能是数据未更新或页面结构变化
            if not holdings:
                return None
            
        except Exception as e:
            print(f"   ❌ 错误: {e}，重试 {attempt+1}/{max_retries}")
            time.sleep(2)
    
    return None


def update_etf_data_file(holdings_dict):
    """
    更新 etf_data.py 文件中的 top_holdings
    
    参数:
        holdings_dict: {etf_code: [holdings_list]}
    
    返回:
        int: 成功更新的ETF数量
    """
    # 读取原文件
    with open(ETF_DATA_FILE, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    updated_count = 0
    new_lines = []
    i = 0
    
    while i < len(lines):
        line = lines[i]
        
        # 检查是否是 "code" 行
        code_match = re.match(r'^(\s+)"code":\s*"(\d+)"\s*,?\s*$', line)
        
        if code_match:
            indent = code_match.group(1)  # 缩进
            etf_code = code_match.group(2)
            
            # 添加当前行
            new_lines.append(line)
            i += 1
            
            # 查找对应的 top_holdings 行
            found_holdings = False
            while i < len(lines):
                if '"top_holdings"' in lines[i]:
                    if etf_code in holdings_dict and holdings_dict[etf_code]:
                        # 更新 top_holdings
                        holdings_str = "[" + ", ".join([f"'{h}'" for h in holdings_dict[etf_code]]) + "]"
                        new_lines.append(indent + '"top_holdings": ' + holdings_str + ',\n')
                        found_holdings = True
                        updated_count += 1
                        print(f"   ✅ 更新 {etf_code} 的持仓数据")
                    else:
                        # 保持原样
                        new_lines.append(lines[i])
                    
                    i += 1
                    break
                else:
                    new_lines.append(lines[i])
                    i += 1
            
            if not found_holdings:
                print(f"   ⚠️  未找到 {etf_code} 的 top_holdings")
            
        else:
            new_lines.append(line)
            i += 1
    
    # 写回文件
    with open(ETF_DATA_FILE, 'w', encoding='utf-8') as f:
        f.writelines(new_lines)
    
    return updated_count


def main():
    print("=" * 70)
    print("ETF持仓数据批量更新工具 v2.0")
    print("=" * 70)
    print()
    
    # 1. 读取所有ETF代码
    print("📖 正在读取ETF代码...")
    etf_codes = read_etf_codes()
    print(f"   找到 {len(etf_codes)} 只ETF")
    print()
    
    # 2. 加载缓存
    print("💾 正在加载缓存...")
    cache = load_cache()
    print(f"   缓存中有 {len(cache)} 只ETF的持仓数据")
    print()
    
    # 3. 批量获取持仓数据
    print("🌐 正在从东方财富网获取持仓数据...")
    print("   (已获取的数据将从缓存读取，按 Ctrl+C 可中断)")
    print()
    
    new_data_count = 0
    
    try:
        for i, code in enumerate(etf_codes, 1):
            print(f"   ({i}/{len(etf_codes)}) {code}...", end=' ')
            
            # 检查缓存
            if code in cache and cache[code]:
                print(f"✅ 缓存 ({len(cache[code])}只股票)")
                continue
            
            # 获取新数据
            holdings = fetch_etf_holdings(code)
            
            if holdings:
                cache[code] = holdings
                new_data_count += 1
                print(f"✅ 成功 ({len(holdings)}只股票)")
                
                # 每获取10只ETF保存一次缓存（断点续传）
                if new_data_count % 10 == 0:
                    save_cache(cache)
                    print(f"   💾 已保存缓存 ({len(cache)}只)")
            else:
                cache[code] = None
                print("❌ 无数据")
            
            # 礼貌性延迟
            time.sleep(1)
    
    except KeyboardInterrupt:
        print("\n\n⚠️  用户中断，正在保存缓存...")
        save_cache(cache)
        print("✅ 缓存已保存，下次运行将从中断处继续")
        return
    
    # 4. 保存最终缓存
    print()
    print("💾 正在保存缓存...")
    save_cache(cache)
    print(f"   ✅ 缓存已保存 ({len(cache)}只ETF)")
    print()
    
    # 5. 统计结果
    success_count = sum(1 for v in cache.values() if v is not None)
    print(f"   成功获取: {success_count}/{len(etf_codes)} 只ETF")
    print()
    
    # 6. 询问是否更新文件
    print("=" * 70)
    response = input("是否更新 etf_data.py 文件？(y/n): ")
    
    if response.lower() == 'y':
        print()
        print("💾 正在更新 etf_data.py...")
        updated = update_etf_data_file(cache)
        print(f"   ✅ 成功更新 {updated} 只ETF")
        print()
        print("=" * 70)
        print("✅ 完成！请检查 etf_data.py 文件")
    else:
        print()
        print("⚠️  已取消更新")
        print("   持仓数据已保存到缓存文件，下次可直接使用:")
        print(f"   {CACHE_FILE}")
    
    print("=" * 70)


if __name__ == '__main__':
    main()
