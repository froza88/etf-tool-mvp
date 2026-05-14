#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简单的 NeoData 测试脚本
"""
import json
import sys
import subprocess

script_path = "/Users/apangduo/.workbuddy/skills/NeoData金融搜索服务/scripts/query.py"

def query_etf(etf_code):
    """查询单个 ETF"""
    print(f"\n{'='*60}")
    print(f"查询: {etf_code}")
    print(f"{'='*60}\n")
    
    # 直接调用 query.py
    cmd = ["python3", script_path, "--query", f"{etf_code} ETF 规模 费率 成立时间 回报"]
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30
       )
        
        # 输出结果
        if result.stdout:
            # 尝试解析 JSON
            try:
                # 查找 JSON 开始位置
                json_start = result.stdout.find('{')
                if json_start >= 0:
                    json_str = result.stdout[json_start:]
                    data = json.loads(json_str)
                    print("✅ 查询成功!")
                    
                    # 提取关键信息
                    if 'data' in data and 'apiData' in data['data']:
                        api_data = data['data']['apiData']
                        if 'apiRecall' in api_data:
                            print(f"\n返回了 {len(api_data['apiRecall'])} 个数据块:")
                            for i, item in enumerate(api_data['apiRecall']):
                                print(f"  {i+1}. {item.get('type', 'N/A')} - {item.get('desc', 'N/A')}")
               except json.JSONDecodeError:
                    print("返回（非 JSON）:")
                    print(result.stdout[:500])
            else:
                print("返回:")
                print(result.stdout[:500])
        
        if result.stderr:
            print("\n错误:")
            print(result.stderr[:200])
    
    except subprocess.TimeoutExpired:
        print("❌ 查询超时")
    except Exception as e:
        print(f"❌ 错误: {e}")

if __name__ == "__main__":
    # 测试 3 个 ETF
    etfs = ["510300", "510880", "510500"]
    
    for etf in etfs:
        query_etf(etf)
    
    print("\n\n✅ 测试完成!")
