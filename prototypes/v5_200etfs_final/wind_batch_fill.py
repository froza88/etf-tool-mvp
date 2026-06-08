#!/usr/bin/env python3
"""Wind批量补充ETF费率和跟踪误差"""
import json, subprocess, time, os, sys

NODE = '/Users/apangduo/.workbuddy/binaries/node/versions/22.12.0/bin/node'
CLI = os.path.expanduser('~/.agents/skills/wind-mcp-skill/scripts/cli.mjs')
JSON_FILE = '/Users/apangduo/WorkBuddy/Claw/etf-tool-mvp/prototypes/etf_core_data.json'

with open(JSON_FILE) as f:
    data = json.load(f)

need_fee = [e for e in data if e.get('fee_mgmt') is None or e.get('fee_custody') is None]
need_te = [e for e in data if e.get('tracking_error') is None]
need = sorted({e['code'] for e in need_fee + need_te})

print(f'开始查询 {len(need)} 只ETF...', flush=True)

for i, code in enumerate(need):
    e = next(x for x in data if x['code'] == code)
    name = e['name']
    sys.stdout.write(f'[{i+1}/{len(need)}] {code} {name} ')
    sys.stdout.flush()
    
    try:
        result = subprocess.run(
            [NODE, CLI, 'call', 'fund_data', 'get_fund_info',
             json.dumps({"question": f"{code} {name} 管理费率 托管费率 跟踪误差"})],
            capture_output=True, text=True, timeout=20
        )
        d = json.loads(result.stdout)
        mgmt_found = cust_found = te_found = False
        for c in d.get('content', []):
            inner = json.loads(c['text'])
            for tbl in inner.get('data', {}).get('data', []):
                cols = [col['name'] for col in tbl.get('columns', [])]
                for row in tbl.get('rows', []):
                    rd = dict(zip(cols, row))
                    if not mgmt_found and rd.get('管理费率_支持历史') is not None and rd.get('托管费率_支持历史') is not None:
                        if e.get('fee_mgmt') is None:
                            e['fee_mgmt'] = rd['管理费率_支持历史']
                            e['fee_custody'] = rd['托管费率_支持历史']
                            e['fee_total'] = round(e['fee_mgmt'] + e['fee_custody'], 2)
                        mgmt_found = cust_found = True
                    if not te_found and rd.get('跟踪误差') is not None:
                        if e.get('tracking_error') is None:
                            e['tracking_error'] = rd['跟踪误差']
                        te_found = True
        
        parts = []
        if mgmt_found: parts.append(f'费:{e.get("fee_mgmt")}/{e.get("fee_custody")}')
        if te_found: parts.append(f'TE:{e.get("tracking_error")}')
        print('✅ ' + ', '.join(parts), flush=True)
        
    except Exception as ex:
        print(f'❌ {ex}', flush=True)
    
    time.sleep(0.3)

fee_ok = sum(1 for e in data if e.get('fee_mgmt') is not None)
te_ok = sum(1 for e in data if e.get('tracking_error') is not None)
print(f'\n费率: {fee_ok}/100, 跟踪误差: {te_ok}/100', flush=True)

with open(JSON_FILE, 'w') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
print('✅ 已保存', flush=True)
