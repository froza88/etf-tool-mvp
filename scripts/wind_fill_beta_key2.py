#!/usr/bin/env python3
"""Wind 批量补充 beta/alpha + PE分位 (Key2)

同一只 ETF 同时查询格式B(beta/alpha)和PE分位
"""

import json, os, subprocess, time, sys

ROOT = '/Users/apangduo/WorkBuddy/Claw/etf-tool-mvp'
WIND_DIR = os.path.join(ROOT, 'data/wind_full')
SRC = os.path.join(ROOT, 'prototypes/etf_core_data.json')
NODE = '/Users/apangduo/.workbuddy/binaries/node/versions/22.12.0/bin/node'
CLI = os.path.expanduser('~/.agents/skills/wind-mcp-skill/scripts/cli.mjs')

TODAY = '20260628'

os.environ['WIND_API_KEY'] = 'ak_c16fDxkjM88xw5uxVTdyYIis6jxP8W15'

with open(SRC) as f:
    data = json.load(f)

# 缺失 beta/alpha (β优先, 顺便获取PE分位)
needs_beta = [e for e in data
              if e.get('beta') in (None, '', [])
              and e.get('invest_type') == '被动指数型基金']

print(f'需要补充 beta/alpha: {len(needs_beta)} 只')

# 先测试1只
code = needs_beta[0]['code']
name = needs_beta[0].get('name', code)

# 格式B: beta+alpha
q = f'{code}.OF {name} 管理费率 托管费率 风险指标 贝塔 阿尔法 信息比率'
print(f'\n测试: {code} {name}')
print(f'问法: {q}')

os.makedirs(WIND_DIR, exist_ok=True)

result = subprocess.run(
    [NODE, CLI, 'call', 'fund_data', 'get_fund_info', json.dumps({'question': q})],
    capture_output=True, text=True, timeout=45,
    env={**os.environ}
)

print(f'退出码: {result.returncode}')
if result.returncode == 0 and result.stdout.strip():
    raw = json.loads(result.stdout)
    inner = json.loads(raw['content'][0]['text'])
    
    # 保存缓存
    cache_path = os.path.join(WIND_DIR, f'{code}_{TODAY}_formatB.json')
    with open(cache_path, 'w') as f:
        json.dump(raw, f, ensure_ascii=False)
    print(f'缓存: {cache_path}')
    
    blocks = inner['data']['data']
    for i, blk in enumerate(blocks):
        cols = [c['name'] for c in blk['columns']]
        row = blk['rows'][0]
        print(f'Block {i}: cols={cols[:6]}...')
        for fld in ['BETA', 'ALPHA', '信息比率', '管理费率_支持历史', '托管费率_支持历史']:
            if fld in cols:
                print(f'  => {fld} = {row[cols.index(fld)]}')
else:
    print(f'Failed or empty')
    print(f'stdout: {result.stdout[:200]}')
    print(f'stderr: {result.stderr[:200]}')
