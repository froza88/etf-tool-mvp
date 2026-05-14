#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
使用 NeoData 金融搜索服务获取 ETF 详细数据
"""
import json
import sys
import os

# 添加脚本目录到 Python 路径
script_dir = "/Users/apangduo/.workbuddy/skills/NeoData金融搜索服务/scripts"
sys.path.insert(0, script_dir)

# 导入 query 模块
from query import main as query_main
import argparse

def test_etf_query(etf_code):
    """测试查询单个 ETF 的数据"""
    print(f"\n=== 查询 ETF: {etf_code} ===")
    
    # 构造查询语句
    query = f"{etf_code} ETF 规模 管理费率 托管费率 成立以来回报 最大回撤"
    
    # 调用 query.py
    sys.argv = ["query.py", "--query", query]
    try:
        query_main()
   except SystemExit:
        pass  # query.py 会调用 sys.exit()
    
    print(f"\n=== 查询完成: {etf_code} ===")

if __name__ == "__main__":
    # 测试几个 ETF
    test_codes = ["510300", "510880", "510500"]
    
    for code in test_codes:
        test_etf_query(code)
        print("\n" + "="*60 + "\n")
