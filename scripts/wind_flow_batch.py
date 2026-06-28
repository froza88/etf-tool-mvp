#!/usr/bin/env python3
"""Wind MCP 批量查询近一周净申购赎回份额 → 近5日净流入"""
import json, os, subprocess, time
from datetime import datetime

NODE = '/Users/apangduo/.workbuddy/binaries/node/versions/22.12.0/bin/node'
CLI = os.path.expanduser('~/.agents/skills/wind-mcp-skill/scripts/cli.mjs')
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCE_FILE = os.path.join(BASE_DIR, 'prototypes', 'etf_core_data.json')
OUTPUT_FILE = os.path.join(BASE_DIR, 'prototypes', 'etf_flow_fields.json')

def query_flow(code, name):
    q = f'{code}.OF {name} 最近一周 净申购赎回 份额变动'
    cmd = [NODE, CLI, 'call', 'fund_data', 'get_fund_info', json.dumps({'question': q})]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=25)
        raw = result.stdout.strip()
        resp = json.loads(raw)
        if resp.get('isError'): return None
        inner = json.loads(resp['content'][0]['text'])
        cols = [c['name'] for c in inner['data']['data'][0]['columns']]
        row = inner['data']['data'][0]['rows'][0]
        for i, c in enumerate(cols):
            if '净申购' in c:
                v = row[i]
                if v is not None:
                    return float(v)
        return None
    except:
        return None

def main():
    with open(SOURCE_FILE, encoding='utf-8') as f:
        etfs = json.load(f)
    
    # Skip already-filled
    todo = [e for e in etfs if not e.get('net_inflow_5d')]
    print(f'[{datetime.now():%H:%M:%S}] 近5日净流入: {len(todo)}/{len(etfs)} 只待补')
    print(f'预估: {len(todo)*5/60:.0f} 分钟\n')
    
    # Output as list of {code, net_inflow_5d} — writes to domain file only
    output_items = []
    done, fail = 0, 0
    for i, e in enumerate(todo):
        code, name = e['code'], e['name']
        print(f'[{datetime.now():%H:%M:%S}] [{i+1}/{len(todo)}] {code} {name}', end=' ', flush=True)
        
        flow = query_flow(code, name)
        if flow is not None:
            output_items.append({
                'code': code,
                'net_inflow_5d': round(flow, 2),
                'net_inflow_source': 'wind'
            })
            print(f'✅ {flow:+.0f}份')
            done += 1
        else:
            print('❌')
            fail += 1
        
        if (i+1) % 20 == 0:
            with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
                json.dump(output_items, f, ensure_ascii=False, indent=2)
            print(f'  [已保存 {i+1}]\n')
        
        if i < len(todo) - 1:
            time.sleep(5)
    
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(output_items, f, ensure_ascii=False, indent=2)
    
    has = sum(1 for e in etfs if e.get('net_inflow_5d')) + done
    print(f'\n完成: {done}/{fail} | 净流入覆盖: {has}/{len(etfs)} ({has/len(etfs)*100:.0f}%)')
    print(f'域文件: {OUTPUT_FILE}')

if __name__ == '__main__':
    main()
