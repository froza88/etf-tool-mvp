#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
使用 NeoData 批量获取 ETF 持仓数据
数据来源: NeoData 金融搜索服务

功能:
1. 从 etf_data.py 读取所有ETF代码
2. 使用 NeoData API 批量获取持仓数据
3. 更新 etf_data.py 中的 top_holdings 字段
"""

import os
import re
import json
import time
import subprocess
from pathlib import Path

# 配置
ETf_DATA_FILE = Path(__file__).parent / 'etf_data.py'
NEO_SCRIPT = Path(__file__).parent / '..' / '..' / '.workbuddy' / 'skills' / 'NeoData金融搜索服务' / 'scripts' / 'query.py'
NEO_SCRIPT = NEO_SCRIPT.resolve()


def read_etf_codes():
    """从 etf_data.py 读取所有ETF代码"""
    with open(ETF_DATA_FILE, 'r', encoding='utf-8') as f:
        content = f.read()
    
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


def query_neodata(query):
    """
    调用 NeoData 查询
    
    参数:
        query: 查询字符串，如 "510300 ETF 持仓"
    
    返回:
        dict: JSON 响应，或 None
    """
    try:
        cmd = ['python3', str(NEO_SCRIPT), '--query', query]
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode != 0:
            print(f"   ⚠️ NeoData 查询失败: {result.stderr[:100]}")
            return None
        
        # 解析 JSON 输出
        output = result.stdout
        # 查找 JSON 部分（可能在文本中间）
        json_start = output.find('{')
        if json_start == -1:
            return None
        
        json_str = output[json_start:]
        data = json.loads(json_str)
        return data
        
    except subprocess.TimeoutExpired:
        print(f"   ⚠️ NeoData 查询超时")
        return None
    except Exception as e:
        print(f"   ❌ NeoData 查询错误: {e}")
        return None


def parse_holdings_from_neodata(data):
    """
    从 NeoData 响应中解析持仓数据
    
    参数:
        data: NeoData 返回的 JSON
    
    返回:
        list: ['股票名称 占比%', ...] 或 None
    """
    if not data or data.get('code') != '200':
        return None
    
    try:
        api_data = data.get('data', {}).get('apiData', {})
        api_recall = api_data.get('apiRecall', [])
        
        for item in api_recall:
            if item.get('type') == '持仓信息' or '持仓' in item.get('desc', ''):
                content = item.get('content', '')
                
                # 解析持仓表格
                holdings = []
                lines = content.split('\n')
                
                for line in lines:
                    # 匹配 "1 股票代码 股票名称 占比%" 格式
                    parts = line.split()
                    if len(parts) >= 4 and '%' in parts[-1]:
                        stock_name = parts[2]
                        pct = parts[3]
                        holdings.append(f"{stock_name} {pct}")
                    
                    if len(holdings) >= 10:
                        break
                
                if holdings:
                    return holdings
        
        return None
        
    except Exception as e:
        print(f"   ⚠️ 解析持仓数据失败: {e}")
        return None


def update_etf_data_file(holdings_dict):
    """
    更新 etf_data.py 文件中的 top_holdings
    
    参数:
        holdings_dict: {etf_code: [holdings_list]}
    
    返回:
        int: 成功更新的ETF数量
    """
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
            indent = code_match.group(1)
            etf_code = code_match.group(2)
            
            # 添加当前行
            new_lines.append(line)
            i += 1
            
            # 查找对应的 top_holdings 行
            while i < len(lines):
                if '"top_holdings"' in lines[i]:
                    if etf_code in holdings_dict and holdings_dict[etf_code]:
                        # 更新 top_holdings
                        holdings_str = "[" + ", ".join([f"'{h}'" for h in holdings_dict[etf_code]]) + "]"
                        new_lines.append(indent + '"top_holdings": ' + holdings_str + ',\n')
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
            
        else:
            new_lines.append(line)
            i += 1
    
    # 写回文件
    backup_file = ETF_DATA_FILE.with_suffix('.py.backup2')
    with open(backup_file, 'w', encoding='utf-8') as f:
        f.writelines(new_lines)
    
    print(f"\n✅ 更新完成！")
    print(f"   备份文件: {backup_file}")
    print(f"   请检查备份文件无误后，重命名为 {ETF_DATA_FILE}")
    
    return updated_count


def main():
    print("=" * 70)
    print("使用 NeoData 批量获取 ETF 持仓数据")
    print("=" * 70)
    print()
    
    # 1. 读取所有ETF代码
    print("📖 正在读取ETF代码...")
    etf_codes = read_etf_codes()
    print(f"   找到 {len(etf_codes)} 只ETF")
    print()
    
    # 2. 批量获取持仓数据
    print("🌐 正在使用 NeoData 获取持仓数据...")
    print("   (如果脚本提示 TOKEN_EXPIRED，会自动处理)")
    print()
    
    holdings_dict = {}
    success_count = 0
    
    for i, code in enumerate(etf_codes, 1):
        print(f"   ({i}/{len(etf_codes)}) {code}...", end=' ')
        
        # 构造查询
        query = f"{code} ETF 持仓股票"
        
        # 调用 NeoData
        data = query_neodata(query)
        
        if data:
            holdings = parse_holdings_from_neodata(data)
            
            if holdings:
                holdings_dict[code] = holdings
                success_count += 1
                print(f"✅ 成功 ({len(holdings)}只股票)")
            else:
                holdings_dict[code] = None
                print("⚠️  未解析到持仓数据")
        else:
            holdings_dict[code] = None
            print("❌ 查询失败")
        
        # 礼貌性延迟
        time.sleep(1)
    
    print()
    print(f"   成功获取: {success_count}/{len(etf_codes)} 只ETF")
    print()
    
    # 3. 询问是否更新文件
    if success_count > 0:
        print("=" * 70)
        response = input("是否更新 etf_data.py 文件？(y/n): ")
        
        if response.lower() == 'y':
            print()
            print("💾 正在更新 etf_data.py...")
            updated = update_etf_data_file(holdings_dict)
            print(f"   ✅ 成功更新 {updated} 只ETF")
            print()
            print("=" * 70)
            print("✅ 完成！请检查备份文件，无误后重命名为 etf_data.py")
        else:
            print()
            print("⚠️  已取消更新")
            print("   持仓数据已保存在内存中，但未写入文件")
        
        print("=" * 70)
    else:
        print("⚠️  未成功获取任何ETF的持仓数据，未更新文件")


if __name__ == '__main__':
    main()
