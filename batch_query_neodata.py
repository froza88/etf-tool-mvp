#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
使用 NeoData 金融搜索服务批量获取 ETF 数据
"""
import json
import sys
import os
from pathlib import Path

# 添加脚本目录到 Python 路径
script_dir = Path("/Users/apangduo/.workbuddy/skills/NeoData金融搜索服务/scripts")
sys.path.insert(0, str(script_dir))

from query import main as query_main

def query_etf_data(etf_code):
    """
    查询单个 ETF 的详细数据
    """
    print(f"\n{'='*60}")
    print(f"查询 ETF: {etf_code}")
    print(f"{'='*60}")
    
    # 构造查询语句 - 涵盖我们需要的所有字段
    queries = [
        f"{etf_code} ETF 规模 成立时间",
        f"{etf_code} ETF 管理费率 托管费率",
        f"{etf_code} ETF 成立以来回报 最大回撤 夏普比率"
   ]
    
    results = {}
    for i, query in enumerate(queries, 1):
        print(f"\n查询 {i}/3: {query}")
        sys.argv = ["query.py", "--query", query]
        
        # 捕获输出
        from io import StringIO
        old_stdout = sys.stdout
        sys.stdout = mystdout = StringIO()
        
        try:
            query_main()
        except SystemExit:
            pass
        except Exception as e:
            print(f"查询出错: {e}")
        
        sys.stdout = old_stdout
        output = mystdout.getvalue()
        
        # 尝试解析 JSON
        try:
            # 查找 JSON 部分
            json_start = output.find('{')
            if json_start != -1:
                json_str = output[json_start:]
                data = json.loads(json_str)
                results[f"query_{i}"] = data
                
                # 提取关键信息
                if 'data' in data and 'apiData' in data['data']:
                    api_data = data['data']['apiData']
                    if 'apiRecall' in api_data:
                        for item in api_data['apiRecall']:
                            if 'content' in item:
                                print(f"  类型: {item.get('type', 'N/A')}")
                               print(f"  内容预览: {item['content'][:200]}...")
       except json.JSONDecodeError:
            print(f"  无法解析 JSON，原始输出:")
            print(output[:500])
    
    return results

def main():
    # 测试前 3 个 ETF
    test_etfs = ["510300", "510880", "510500"]
    
    all_results = {}
    for etf in test_etfs:
        all_results[etf] = query_etf_data(etf)
    
    # 保存结果
    output_file = "/Users/apangduo/WorkBuddy/Claw/etf-tool-mvp/neodata_etf_test.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)
    
    print(f"\n\n结果已保存到: {output_file}")

if __name__ == "__main__":
    main()
