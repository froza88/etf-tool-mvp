#!/usr/bin/env python3
"""批量补充ETF持仓 — 非凸 ftshare etf-component (快速，0.6s/只)"""
import json, time, sys, os, subprocess

DATA_FILE = 'prototypes/v10_full_1470/deploy/etf_core_data.json'
PROGRESS_FILE = 'holdings_progress.json'
SAVE_EVERY = 50

def code_to_symbol(code):
    """ETF代码 → XSHG/XSHE"""
    code = str(code)
    if code.startswith(('5', '6')):
        return f'{code}.XSHG'
    return f'{code}.XSHE'

def fetch_components(code):
    """调用 ftshare etf-component"""
    symbol = code_to_symbol(code)
    cmd = [
        '/usr/bin/python3',
        os.path.expanduser('~/.workbuddy/skills/ftshare-market-data/run.py'),
        'etf-component',
        '--symbol', symbol
    ]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        if r.returncode != 0:
            return None
        data = json.loads(r.stdout)
        return data.get('components', [])
    except:
        return None

def main():
    print('=' * 50, flush=True)
    print('批量补充ETF持仓 — ftshare etf-component', flush=True)
    print('=' * 50, flush=True)
    
    with open(DATA_FILE) as f:
        all_data = json.load(f)
    
    done = {}
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE) as f:
            done = json.load(f)
        print(f'恢复进度: {len(done)}只已完成', flush=True)
    
    # 筛选缺失持仓的ETF
    missing = [(i, x) for i, x in enumerate(all_data) 
               if (not x.get('holdings') or len(x.get('holdings','')) == 0)
               and x['code'] not in done]
    
    total = len(missing)
    print(f'待补充: {total} 只', flush=True)
    
    filled = 0
    for j, (idx, etf) in enumerate(missing):
        code = etf['code']
        name = etf.get('name', code)
        
        components = fetch_components(code)
        
        if components and len(components) > 0:
            top5 = components[:5]
            etf['holdings'] = [{'code': c, 'name': ''} for c in top5]
            etf['holdings_str'] = ', '.join(top5)
            filled += 1
            src = f'ftshare({len(components)}只)'
        else:
            src = '无数据'
        
        done[code] = {
            'source': src,
            'count': len(components) if components else 0,
            'ts': time.strftime('%H:%M:%S')
        }
        
        pct = (j+1)/total*100
        icon = '✅' if components else '❌'
        print(f'[{j+1}/{total} {pct:.0f}%] {code} {name[:12]:12s} | {icon} {src}', flush=True)
        
        # 定期保存
        if (j + 1) % SAVE_EVERY == 0:
            with open(DATA_FILE, 'w') as f:
                json.dump(all_data, f, ensure_ascii=False, indent=2)
            with open(PROGRESS_FILE, 'w') as f:
                json.dump(done, f, ensure_ascii=False)
            now = time.strftime('%H:%M:%S')
            print(f'  💾 [{now}] 已保存 — 填充{filled}/{total}只 ({filled/max(j+1,1)*100:.0f}%)', flush=True)
    
    # 最终保存
    with open(DATA_FILE, 'w') as f:
        json.dump(all_data, f, ensure_ascii=False, indent=2)
    with open(PROGRESS_FILE, 'w') as f:
        json.dump(done, f, ensure_ascii=False)
    
    fill_rate = filled/total*100 if total > 0 else 0
    print(f'\n{"="*50}', flush=True)
    print(f'✅ 完成！填充 {filled}/{total} 只ETF持仓 ({fill_rate:.1f}%)', flush=True)

if __name__ == '__main__':
    main()
