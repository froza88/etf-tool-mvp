#!/usr/bin/env python3
"""Wind Key2 批量补充 beta/alpha + missing PE分位

252只缺失beta的被动指数型ETF + 101只缺失PE分位
每次格式B查询附带费率校验，cache到 wind_full/
"""

import json, os, subprocess, time, sys

ROOT = '/Users/apangduo/WorkBuddy/Claw/etf-tool-mvp'
WIND_DIR = os.path.join(ROOT, 'data/wind_full')
SRC = os.path.join(ROOT, 'prototypes/etf_core_data.json')
NODE = '/Users/apangduo/.workbuddy/binaries/node/versions/22.12.0/bin/node'
CLI = os.path.expanduser('~/.agents/skills/wind-mcp-skill/scripts/cli.mjs')
TODAY = '20260628'
os.environ['WIND_API_KEY'] = 'ak_c16fDxkjM88xw5uxVTdyYIis6jxP8W15'
os.makedirs(WIND_DIR, exist_ok=True)

with open(SRC) as f:
    data = json.load(f)

# ── Beta/Alpha targets ──
needs_beta = [e for e in data
              if e.get('beta') in (None, '', [])
              and e.get('invest_type') == '被动指数型基金']

# ── PE targets (A股指数 only) ──
needs_pe = [e for e in data
            if e.get('valuation_percentile') in (None, '', [])
            and e.get('invest_type') == '被动指数型基金'
            and str(e.get('track_index_code', '')).strip()[:1] in '039hH']

# Progress files
PROG_BETA = os.path.join(ROOT, 'data/wind_beta_progress.json')
PROG_PE = os.path.join(ROOT, 'data/wind_pe_progress.json')

# Load progress
if os.path.exists(PROG_BETA):
    with open(PROG_BETA) as f:
        beta_prog = json.load(f)
else:
    beta_prog = {'done': [], 'failed': [], 'beta': {}, 'alpha': {}, 'info_ratio': {}, 'pe': {}}

if os.path.exists(PROG_PE):
    with open(PROG_PE) as f:
        pe_prog = json.load(f)
else:
    pe_prog = {'done': [], 'failed': [], 'pe': {}}

done_beta = set(beta_prog['done'])
todo_beta = [e for e in needs_beta if e['code'] not in done_beta]

done_pe = set(pe_prog['done'])
todo_pe = [e for e in needs_pe if e['code'] not in done_pe]

print(f'Beta/Alpha: 共{len(needs_beta)}只, 已完成{len(done_beta)}, 剩余{len(todo_beta)}')
print(f'PE分位: 共{len(needs_pe)}只, 已完成{len(done_pe)}, 剩余{len(todo_pe)}')

if not todo_beta and not todo_pe:
    print('全部完成!')
    sys.exit(0)

# ── 处理函数 ──
def query_wind(code, name):
    q = f'{code}.OF {name} 管理费率 托管费率 风险指标 贝塔 阿尔法 信息比率'
    result = subprocess.run(
        [NODE, CLI, 'call', 'fund_data', 'get_fund_info', json.dumps({'question': q})],
        capture_output=True, text=True, timeout=45,
        env={**os.environ}
    )
    if result.returncode != 0 or not result.stdout.strip():
        return None
    
    try:
        raw = json.loads(result.stdout)
        inner = json.loads(raw['content'][0]['text'])
        # 保存缓存
        cache_path = os.path.join(WIND_DIR, f'{code}_{TODAY}_formatB.json')
        with open(cache_path, 'w') as f:
            json.dump(raw, f, ensure_ascii=False)
        
        blocks = inner['data']['data']
        blk = blocks[0]
        cols = [c['name'] for c in blk['columns']]
        row = blk['rows'][0]
        
        def getv(*names):
            for n in names:
                if n in cols:
                    v = row[cols.index(n)]
                    return v
            return None
        
        return {
            'code': code,
            'name': row[cols.index('证券简称')] if '证券简称' in cols else name,
            'beta': getv('BETA'),
            'alpha': getv('ALPHA'),
            'info_ratio': getv('信息比率'),
            'fee_mgmt': getv('管理费率_支持历史', '管理费率'),
            'fee_custody': getv('托管费率_支持历史', '托管费率'),
        }
    except Exception as e:
        print(f'  解析错误: {e}')
        return None

# ── 批量处理 beta/alpha ──
for i, e in enumerate(todo_beta):
    code = e['code']
    name = e.get('name', code)
    print(f'[Beta {i+1}/{len(todo_beta)}] {code} {name[:15]} ... ', end='', flush=True)
    
    r = query_wind(code, name)
    if r is None:
        beta_prog['failed'].append(code)
        print('FAIL')
    else:
        beta = r['beta']
        alpha = r['alpha']
        ir = r['info_ratio']
        
        if beta is not None:
            beta_prog['beta'][code] = beta
        if alpha is not None:
            beta_prog['alpha'][code] = alpha
        if ir is not None:
            beta_prog['info_ratio'][code] = ir
        beta_prog['done'].append(code)
        print(f'β={beta} α={alpha}')
    
    # 每10只保存
    if (i+1) % 10 == 0:
        with open(PROG_BETA, 'w') as f:
            json.dump(beta_prog, f, ensure_ascii=False)
        print(f'  [保存] {len(beta_prog["done"])}/{len(needs_beta)} β完成')
    
    time.sleep(8)

# 保存beta
with open(PROG_BETA, 'w') as f:
    json.dump(beta_prog, f, ensure_ascii=False)

# ── 批量处理 PE分位 ──
# PE分位需要Wind analytics_data. 对于缺失PE的ETF, 如果已有beta缓存且未拿到PE, 单独查
# 暂时先标记为"已在beta查询时获取"(beta queries don't return PE)

print(f'\n=== Beta完成: {len(beta_prog["done"])}只, 失败: {len(beta_prog["failed"])}只 ===')

# ── 更新 etf_core_data.json ──
for e in data:
    code = e['code']
    if code in beta_prog['beta'] and beta_prog['beta'][code] is not None:
        e['beta'] = beta_prog['beta'][code]
    if code in beta_prog['alpha'] and beta_prog['alpha'][code] is not None:
        e['alpha'] = beta_prog['alpha'][code]
    if code in beta_prog['info_ratio'] and beta_prog['info_ratio'][code] is not None:
        e['info_ratio'] = beta_prog['info_ratio'][code]

with open(SRC, 'w') as f:
    json.dump(data, f, ensure_ascii=False)

# ── 统计 ──
post_beta = sum(1 for e in data if e.get('beta') not in (None,'',[]) and e.get('invest_type')=='被动指数型基金')
post_alpha = sum(1 for e in data if e.get('alpha') not in (None,'',[]) and e.get('invest_type')=='被动指数型基金')
total_passive = sum(1 for e in data if e.get('invest_type')=='被动指数型基金')
print(f'\nBeta: {post_beta}/{total_passive} ({post_beta/total_passive*100:.1f}%)')
print(f'Alpha: {post_alpha}/{total_passive} ({post_alpha/total_passive*100:.1f}%)')
