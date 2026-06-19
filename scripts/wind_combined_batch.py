#!/usr/bin/env python3
"""Wind MCP 合并费率和风险查询 — 一次查全 管理费率/托管费率/贝塔/阿尔法/信息比率"""
import json, os, subprocess, time, sys
from datetime import datetime

NODE = '/Users/apangduo/.workbuddy/binaries/node/versions/22.12.0/bin/node'
CLI = os.path.expanduser('~/.agents/skills/wind-mcp-skill/scripts/cli.mjs')
DATA_FILE = 'etf_standard_data.json'

def get_missing():
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        etfs = json.load(f)
    # Missing custody OR beta — one query covers both
    needs = []
    for e in etfs:
        need_cust = not e.get('custody_fee_rate') or e['custody_fee_rate'] == 0
        need_beta = not e.get('beta') or e.get('beta') == 0
        if need_cust or need_beta:
            needs.append((e['code'], e['name']))
    return needs, etfs

def query_combined(code, name):
    q = f'{code}.OF {name} 管理费率 托管费率 风险指标 贝塔 阿尔法 信息比率'
    cmd = [NODE, CLI, 'call', 'fund_data', 'get_fund_info', json.dumps({'question': q})]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=25)
        return result.stdout.strip()
    except:
        return None

def parse_combined(raw, code):
    try:
        resp = json.loads(raw)
        if resp.get('isError'):
            return None
        inner = json.loads(resp['content'][0]['text'])
        blk = inner['data']['data'][0]
        cols = [c['name'] for c in blk['columns']]
        for row in blk['rows']:
            if row[0] and code in row[0]:
                break
        else:
            row = blk['rows'][0] if blk['rows'] else None
        if not row:
            return None
        
        def g(*ns):
            for n in ns:
                if n in cols:
                    v = row[cols.index(n)]
                    return v
            return None
        
        r = {}
        for key, names in {
            'management_fee_rate': ['管理费率_支持历史'],
            'custody_fee_rate': ['托管费率_支持历史'],
            'beta': ['BETA'],
            'alpha': ['ALPHA'],
            'info_ratio': ['信息比率'],
        }.items():
            v = g(*names)
            if v not in (None, '', 'null', 'None'):
                try:
                    r[key] = float(v)
                except:
                    pass
        return r if r else None
    except:
        return None

def main():
    needs, etfs = get_missing()
    print(f'[{datetime.now():%H:%M:%S}] 合并查询: {len(needs)} 只')
    print(f'预估: {len(needs)*8/60:.0f} 分钟\n')
    
    etf_idx = {e['code']: i for i, e in enumerate(etfs)}
    ok = fail = 0
    
    for i, (code, name) in enumerate(needs):
        print(f'[{datetime.now():%H:%M:%S}] [{i+1}/{len(needs)}] {code} {name}', end=' ', flush=True)
        raw = query_combined(code, name)
        if not raw:
            print('❌')
            fail += 1
        else:
            p = parse_combined(raw, code)
            if p and code in etf_idx:
                idx = etf_idx[code]
                filled = []
                for f, v in p.items():
                    if v != 0:
                        if not etfs[idx].get(f):
                            etfs[idx][f] = v; filled.append(f)
                print(f'✅ {",".join(filled)}' if filled else '✅ 已齐')
                ok += 1
            else:
                print('⚠️ 解析失败')
                fail += 1
        
        if (i+1) % 10 == 0:
            with open(DATA_FILE, 'w', encoding='utf-8') as f:
                json.dump(etfs, f, ensure_ascii=False, indent=2)
        
        if i < len(needs) - 1:
            time.sleep(8)
    
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(etfs, f, ensure_ascii=False, indent=2)
    
    total = len(etfs)
    c = sum(1 for e in etfs if e.get('custody_fee_rate'))
    b = sum(1 for e in etfs if e.get('beta'))
    print(f'\n托管费率: {c}/{total} ({c/total*100:.0f}%)')
    print(f'贝塔: {b}/{total} ({b/total*100:.0f}%)')

if __name__ == '__main__':
    main()
