#!/usr/bin/env python3
"""用 AKShare 计算 beta/alpha

方法: 取 ETF 和跟踪指数的过去1年日收益率
      用 CAPM 回归: ETF_ret = alpha + beta * index_ret + ε
"""

import json, os, time
import numpy as np
from datetime import date, timedelta

ROOT = '/Users/apangduo/WorkBuddy/Claw/etf-tool-mvp'
SRC = os.path.join(ROOT, 'prototypes/etf_core_data.json')

with open(SRC) as f:
    data = json.load(f)

# 缺失beta的被动指数型ETF
missing = [e for e in data
           if e.get('beta') in (None, '', [])
           and e.get('invest_type') == '被动指数型基金']

print(f'需要补 beta/alpha: {len(missing)} 只')

# 测试第一只：用 AKShare 获取历史数据并计算
code = missing[0]['code']
name = missing[0].get('name', '')
benchmark = missing[0].get('track_index', '').strip()
track_code = missing[0].get('track_index_code', '').strip()

print(f'\n测试: {code} {name}')
print(f'跟踪指数: {benchmark} -> {track_code}')

# 只输出方案确认
print(f'''
beta/alpha 自算方案:
1. 取 ETF 和指数的过去252个交易日收盘价
2. 计算日收益率: ret[i] = (close[i]-close[i-1])/close[i-1]
3. 用 np.polyfit(index_ret, etf_ret, 1) 回归
4. slope = beta, intercept = alpha
5. alpha 年化: 累加日均 alpha × 252

数据源: AKShare fund_etf_hist_em + stock_zh_index_daily
''')

print(f'共需处理 {len(missing)} 只 ETF。每只约 2 秒（获取2个历史价格序列），总计约 {len(missing)*2//60} 分钟。')
