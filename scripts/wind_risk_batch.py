#!/usr/bin/env python3
"""批量 Wind MCP 风险指标补充（贝塔/阿尔法/信息比率），447只，~60分钟"""

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
    # 缺 beta 或 alpha
    needs = [(e['code'], e['name']) for e in etfs if not e.get('beta') or not e.get('alpha')]
    return needs, etfs

def query_risk(code, name):
    question = f'{code}.OF {name} 风险指标 贝塔 阿尔法 信息比率 跟踪误差'
    cmd = [NODE, CLI, 'call', 'fund_data', 'get_fund_info', json.dumps({'question': question})]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=25)
        return result.stdout.strip()
    except:
        return None

def parse_risk(raw, code):
    """解析风险指标响应"""
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
        
        # Find target row
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
        
        beta = get_val('近一年BETA', '近1年BETA', 'BETA')
        if beta not in (None, '', 'null'):
            try: result['beta'] = float(beta)
            except: pass
        
        alpha = get_val('近一年ALPHA', '近1年ALPHA', 'ALPHA')
        if alpha not in (None, '', 'null'):
            try: result['alpha'] = float(alpha)
            except: pass
        
        ir_ = get_val('近一年信息比率', '近1年信息比率', '信息比率')
        if ir_ not in (None, '', 'null'):
            try: result['info_ratio'] = float(ir_)
            except: pass
        
        te = get_val('近一年跟踪误差', '近1年跟踪误差', '跟踪误差')
        if te not in (None, '', 'null'):
            try: result['tracking_error'] = float(te)
            except: pass
        
        vol = get_val('近一年年化波动率', '近1年年化波动率', '年化波动率')
        if vol not in (None, '', 'null'):
            try: result['annual_vol'] = float(vol)
            except: pass
        
        return result if result else None
    except:
        return None

def main():
    needs, etfs = get_missing()
    print(f'[{datetime.now():%H:%M:%S}] 待补充风险指标: {len(needs)} 只')
    print(f'预估耗时: {len(needs)*8/60:.0f} 分钟\n')
    
    etf_idx = {e['code']: i for i, e in enumerate(etfs)}
    
    success = 0
    fail = 0
    fields = {}
    
    for i, (code, name) in enumerate(needs):
        print(f'[{datetime.now():%H:%M:%S}] [{i+1}/{len(needs)}] {code} {name}', end=' ... ')
        sys.stdout = __import__('sys').stdout  # ensure
        __import__('sys').stdout.flush()
        
        raw = query_risk(code, name)
        if not raw:
            print('❌ timeout')
            fail += 1
        else:
            parsed = parse_risk(raw, code)
            if parsed and code in etf_idx:
                idx = etf_idx[code]
                for field, value in parsed.items():
                    if value not in (None, '', 0):
                        current = etfs[idx].get(field)
                        if current is None or current == '' or current == 0:
                            etfs[idx][field] = value
                            fields[field] = fields.get(field, 0) + 1
                print(f"✅ β={parsed.get('beta','?')} α={parsed.get('alpha','?')}")
                success += 1
            else:
                print('⚠️ 解析失败')
                fail += 1
        
        if (i + 1) % 10 == 0:
            with open(DATA_FILE, 'w', encoding='utf-8') as f:
                json.dump(etfs, f, ensure_ascii=False, indent=2)
            print(f'  [已保存 {i+1}/{len(needs)}]')
        
        if i < len(needs) - 1:
            time.sleep(8)
    
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(etfs, f, ensure_ascii=False, indent=2)
    
    print(f'\n=== 完成 ===')
    print(f'成功: {success} | 失败: {fail}')
    print(f'字段填充: {fields}')
    
    # Quick stats
    beta_ok = sum(1 for e in etfs if e.get('beta'))
    alpha_ok = sum(1 for e in etfs if e.get('alpha'))
    total = len(etfs)
    print(f'\n贝塔: {beta_ok}/{total} ({beta_ok/total*100:.1f}%)')
    print(f'阿尔法: {alpha_ok}/{total} ({alpha_ok/total*100:.1f}%)')

if __name__ == '__main__':
    import sys
    main()
