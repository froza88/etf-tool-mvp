#!/usr/bin/env python3
"""Wind MCP 批量补充 beta/alpha + PE分位

策略：
1. 从 etf_core_data.json 找到缺失 beta/alpha 的被动指数型ETF
2. 用Wind格式B查询 beta/alpha
3. 缓存到 wind_full/{code}_{date}.json
4. 解析并更新 etf_core_data.json
5. 重建静态数据
"""

import json
import os
import subprocess
import time
import sys
from datetime import date

ROOT = '/Users/apangduo/WorkBuddy/Claw/etf-tool-mvp'
WIND_DIR = os.path.join(ROOT, 'data/wind_full')
SRC = os.path.join(ROOT, 'prototypes/etf_core_data.json')
NODE = '/Users/apangduo/.workbuddy/binaries/node/versions/22.12.0/bin/node'
CLI = os.path.expanduser('~/.agents/skills/wind-mcp-skill/scripts/cli.mjs')
TODAY = date.today().strftime('%Y%m%d')

# ── 加载数据 ──
with open(SRC) as f:
    data = json.load(f)

# ── 找到缺失 beta 的被动指数型 ETF ──
missing = [e for e in data
           if e.get('beta') in (None, '', [])
           and e.get('invest_type') == '被动指数型基金']

print(f'缺失 beta/alpha: {len(missing)} 只')

# ── 按名称长度排序（短的先测，快速验证） ──
missing.sort(key=lambda e: len(e.get('name', '')))

# 先测试第一只
test_e = missing[0]
code = test_e['code']
name = test_e.get('name', code)
question = f'{code}.OF {name} 管理费率 托管费率 风险指标 贝塔 阿尔法 信息比率'

print(f'\n--- 测试第1只: {code} {name} ---')
print(f'问法: {question}')

result = subprocess.run(
    [NODE, CLI, 'call', 'fund_data', 'get_fund_info', json.dumps({'question': question})],
    capture_output=True, text=True, timeout=30
)

print(f'退出码: {result.returncode}')
print(f'stdout前300: {result.stdout[:300]}')
if result.stderr:
    print(f'stderr: {result.stderr[:300]}')

if result.returncode == 0 and result.stdout.strip():
    try:
        raw = json.loads(result.stdout)
        inner = json.loads(raw['content'][0]['text'])
        blocks = inner['data']['data']
        
        # 保存缓存
        os.makedirs(WIND_DIR, exist_ok=True)
        cache_path = os.path.join(WIND_DIR, f'{code}_{TODAY}.json')
        with open(cache_path, 'w') as f:
            json.dump(raw, f, ensure_ascii=False)
        print(f'缓存: {cache_path}')
        
        # 解析
        for i, blk in enumerate(blocks):
            cols = [c['name'] for c in blk['columns']]
            row = blk['rows'][0]
            print(f'Block {i}: cols={cols}')
            print(f'  row={row}')
            for fld in ['BETA', 'ALPHA', '信息比率', '管理费率_支持历史', '托管费率_支持历史']:
                if fld in cols:
                    idx = cols.index(fld)
                    print(f'  => {fld} = {row[idx]}')
    except Exception as e:
        print(f'解析失败: {e}')
else:
    print('查询失败或返回空')
