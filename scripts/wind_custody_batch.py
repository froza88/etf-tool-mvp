#!/usr/bin/env python3
"""Wind MCP 批量补充托管费率 — 87只，~12分钟"""

import json
import os
import subprocess
import time
from datetime import datetime

NODE = '/Users/apangduo/.workbuddy/binaries/node/versions/22.12.0/bin/node'
CLI = os.path.expanduser('~/.agents/skills/wind-mcp-skill/scripts/cli.mjs')
DATA_FILE = 'etf_standard_data.json'

def get_missing():
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        etfs = json.load(f)
    needs = [(e['code'], e['name']) for e in etfs 
             if not e.get('custody_fee_rate') or e['custody_fee_rate'] == 0]
    return needs, etfs

def query_fees(code, name):
    question = f'{code}.OF {name} 管理费率 托管费率'
    cmd = [NODE, CLI, 'call', 'fund_data', 'get_fund_info', json.dumps({'question': question})]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=25)
        return result.stdout.strip()
    except:
        return None

def parse_fees(raw, code):
    try:
        resp = json.loads(raw)
        if resp.get('isError'):
            return None
        inner = json.loads(resp['content'][0]['text'])
        blocks = inner['data']['data']
        if not blocks:
            return None
        blk = blocks[0]
        cols = [c['name'] for c in blk['columns']]
        
        for row in blk['rows']:
            if row[0] and code in row[0]:
                break
        else:
            row = blk['rows'][0] if blk['rows'] else None
        if not row:
            return None
        
        def get_val(*names):
            for n in names:
                if n in cols:
                    v = row[cols.index(n)]
                    return v
            return None
        
        result = {}
        mgmt = get_val('管理费率', '管理费率_支持历史')
        cust = get_val('托管费率', '托管费率_支持历史')
        
        if mgmt not in (None, '', 'null'):
            try: 
                mv = float(mgmt)
                if mv > 0: result['management_fee_rate'] = mv
            except: pass
        
        if cust not in (None, '', 'null'):
            try: 
                cv = float(cust)
                if cv > 0: result['custody_fee_rate'] = cv
            except: pass
        
        # Calculate total
        if 'management_fee_rate' in result and 'custody_fee_rate' in result:
            result['fee_rate'] = round(result['management_fee_rate'] + result['custody_fee_rate'], 4)
        
        return result if result else None
    except:
        return None

def main():
    needs, etfs = get_missing()
    print(f'[{datetime.now():%H:%M:%S}] 待补充托管费率: {len(needs)} 只')
    if not needs:
        print('无需补充')
        return
    print(f'预估耗时: {len(needs)*8/60:.0f} 分钟\n')
    
    etf_idx = {e['code']: i for i, e in enumerate(etfs)}
    success = fail = 0
    fields = {}
    
    for i, (code, name) in enumerate(needs):
        print(f'[{datetime.now():%H:%M:%S}] [{i+1}/{len(needs)}] {code} {name}', end=' ', flush=True)
        
        raw = query_fees(code, name)
        if not raw:
            print('❌ timeout')
            fail += 1
        else:
            parsed = parse_fees(raw, code)
            if parsed and code in etf_idx:
                idx = etf_idx[code]
                for field, value in parsed.items():
                    current = etfs[idx].get(field)
                    if current is None or current == '' or current == 0:
                        etfs[idx][field] = value
                        fields[field] = fields.get(field, 0) + 1
                print(f"✅ 托管={parsed.get('custody_fee_rate','?')}%")
                success += 1
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
    
    cust_ok = sum(1 for e in etfs if e.get('custody_fee_rate'))
    fee_ok = sum(1 for e in etfs if e.get('fee_rate'))
    print(f'\n=== 完成: {success}/{fail} ===')
    print(f'托管费率: {cust_ok}/{len(etfs)} ({cust_ok/len(etfs)*100:.1f}%)')
    print(f'总费率: {fee_ok}/{len(etfs)} ({fee_ok/len(etfs)*100:.1f}%)')

if __name__ == '__main__':
    main()
