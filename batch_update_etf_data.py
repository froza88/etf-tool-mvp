#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
使用 WeStock Data 批量获取ETF真实数据
更新 etf_data.py 中的字段
"""

import subprocess
import json
import re
from time import sleep

# 读取当前ETF列表
exec(open('/Users/apangduo/WorkBuddy/Claw/etf-tool-mvp/etf_data.py', 'r', encoding='utf-8').read())

print(f"开始更新 {len(ETFs)} 只ETF的真实数据...\n")

updated = []
failed = []

for i, etf in enumerate(ETFs):
    code = etf['code']
    print(f"[{i+1}/{len(ETFs)}] 正在查询 {code} {etf['name']}...", end=' ')
    
    try:
        # 调用 westockdata 查询ETF详情
        result = subprocess.run(
            ['npx', '-y', 'westock-data-clawhub@1.0.4', 'etf', f'sh{code}'],
            capture_output=True,
            text=True,
            timeout=30,
            cwd='/Users/apangduo/WorkBuddy/Claw'
        )
        
        if result.returncode != 0:
            print(f"✗ 查询失败")
            failed.append(etf)
            continue
        
        output = result.stdout
        
        # 解析返回的Markdown表格
        # 查找 | sh510300 | ... | 这样的行
        match = re.search(r'\| sh' + code + r' \| ([^\n]+)', output)
        
        if not match:
            print(f"✗ 未找到数据")
            failed.append(etf)
            continue
        
        # 解析表格数据（很复杂，先保存原始输出）
        with open(f'/tmp/etf_{code}.txt', 'w', encoding='utf-8') as f:
            f.write(output)
        
        print(f"✓ 数据已保存")
        updated.append(etf)
        
        # 礼貌延迟
        sleep(1)
        
    except Exception as e:
        print(f"✗ 错误: {e}")
        failed.append(etf)

print(f"\n\n完成！")
print(f"成功: {len(updated)} 只")
print(f"失败: {len(failed)} 只")

if failed:
    print(f"\n失败的ETF:")
    for etf in failed:
        print(f"  {etf['code']} {etf['name']}")
