#!/usr/bin/env python3
"""批量 Wind MCP 查询缺失ETF，间隔 8s，后台执行"""

import json
import os
import sys
import subprocess
import time
from datetime import datetime

NODE = '/Users/apangduo/.workbuddy/binaries/node/versions/22.12.0/bin/node'
CLI = os.path.expanduser('~/.agents/skills/wind-mcp-skill/scripts/cli.mjs')
WIND_DIR = 'data/wind_full'
DATA_FILE = 'etf_standard_data.json'

os.makedirs(WIND_DIR, exist_ok=True)

def get_missing_codes():
    """获取需要 Wind 查询的 ETF 代码列表"""
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        etfs = json.load(f)
    
    wind_codes = set(f.replace('.json','').split('_')[0] 
                     for f in os.listdir(WIND_DIR) if f.endswith('.json'))
    
    # 无缓存 或 缺跟踪误差
    needed = set()
    for e in etfs:
        if e['code'] not in wind_codes:
            needed.add((e['code'], e['name'], 'no_cache'))
        elif not e.get('tracking_error'):
            needed.add((e['code'], e['name'], 'no_tracking_error'))
    
    return sorted(needed)

def query_wind(code, name):
    """查询单只 ETF 的 Wind 数据"""
    question = f'{code}.OF {name} 基本档案 规模 费率 净值 风险指标 夏普比率 波动率 最大回撤 跟踪误差 收益率'
    cmd = [NODE, CLI, 'call', 'fund_data', 'get_fund_info', json.dumps({'question': question})]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=25)
        return result.stdout.strip()
    except subprocess.TimeoutExpired:
        return None
    except Exception as e:
        return None

def parse_and_merge(code, raw_response):
    """解析新单块格式 Wind 响应并合并到数据文件"""
    if not raw_response:
        return {'status': 'timeout'}
    
    try:
        resp = json.loads(raw_response)
        if resp.get('isError'):
            return {'status': 'error', 'msg': str(resp.get('content', ''))[:200]}
        
        inner = json.loads(resp['content'][0]['text'])
        if inner.get('error'):
            return {'status': 'error', 'msg': str(inner['error'])[:200]}
        
        blocks = inner['data']['data']
        if not blocks:
            return {'status': 'empty'}
        
        blk = blocks[0]
        cols = [c['name'] for c in blk['columns']]
        
        # 找到目标 ETF 的行
        target_row = None
        for row in blk['rows']:
            if row[0] and code in row[0]:
                target_row = row
                break
        if not target_row and blk['rows']:
            target_row = blk['rows'][0]  # fallback
        
        if not target_row:
            return {'status': 'no_match'}
        
        def get_val(*names):
            for n in names:
                if n in cols:
                    v = target_row[cols.index(n)]
                    return v
            return None
        
        result = {}
        
        # 规模
        scale = get_val('上市基金规模_WIND计算')
        if scale and scale not in (None, '', 'null'):
            try:
                result['scale'] = float(scale)
            except: pass
        
        # 管理费率
        mgmt = get_val('管理费率_支持历史')
        if mgmt not in (None, '', 'null'):
            try:
                result['management_fee_rate'] = float(mgmt)
            except: pass
        
        # 净值
        nav = get_val('单位净值')
        if nav not in (None, '', 'null'):
            try: result['nav'] = float(nav)
            except: pass
        
        # 夏普
        sharpe = get_val('SHARPE')
        if sharpe not in (None, '', 'null'):
            try: result['sharpe_ratio'] = float(sharpe)
            except: pass
        
        # 波动率
        vol = get_val('年化波动率')
        if vol not in (None, '', 'null'):
            try: result['annual_vol'] = float(vol)
            except: pass
        
        # 最大回撤
        mdd = get_val('最大回撤')
        if mdd not in (None, '', 'null'):
            try: result['max_drawdown'] = float(mdd)
            except: pass
        
        # 跟踪误差
        te = get_val('跟踪误差')
        if te not in (None, '', 'null'):
            try: result['tracking_error'] = float(te)
            except: pass
        
        # 区间回报
        ret = get_val('区间回报')
        if ret not in (None, '', 'null'):
            try: result['year_1_return'] = float(ret)
            except: pass
        
        # 计算 calmar
        if 'year_1_return' in result and 'max_drawdown' in result:
            mdd_abs = abs(result['max_drawdown'])
            if mdd_abs > 0:
                result['calmar_ratio'] = round(result['year_1_return'] / mdd_abs, 2)
        
        result['status'] = 'ok'
        return result
        
    except Exception as e:
        return {'status': 'parse_error', 'msg': str(e)[:200]}

def main():
    tasks = get_missing_codes()
    print(f'[{datetime.now().strftime("%H:%M:%S")}] 待查询: {len(tasks)} 只 ETF')
    print(f'预估耗时: {len(tasks)*8/60:.0f} 分钟\n')
    
    success = 0
    fail = 0
    fields_filled = {}
    
    # 加载数据文件一次
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        etfs = json.load(f)
    etf_idx = {e['code']: i for i, e in enumerate(etfs)}
    
    for i, (code, name, reason) in enumerate(tasks):
        print(f'[{datetime.now().strftime("%H:%M:%S")}] [{i+1}/{len(tasks)}] {code} {name} ({reason})', end=' ... ')
        sys.stdout.flush()
        
        raw = query_wind(code, name)
        if not raw:
            print('❌ timeout')
            fail += 1
        else:
            # 保存原始响应
            cache_path = os.path.join(WIND_DIR, f'{code}_20260619.json')
            with open(cache_path, 'w', encoding='utf-8') as f:
                f.write(raw)
            
            parsed = parse_and_merge(code, raw)
            
            if parsed.get('status') == 'ok':
                # 合并到数据
                if code in etf_idx:
                    idx = etf_idx[code]
                    for field, value in parsed.items():
                        if field in ('status',):
                            continue
                        if value not in (None, '', 'null') and value != 0:
                            current = etfs[idx].get(field)
                            if current is None or current == '' or current == 0:
                                etfs[idx][field] = value
                                fields_filled[field] = fields_filled.get(field, 0) + 1
                
                print(f'✅ {parsed.get("tracking_error","?")}')
                success += 1
            else:
                print(f'⚠️ {parsed.get("status")}: {parsed.get("msg","")[:50]}')
                fail += 1
        
        # 每 10 只保存一次
        if (i + 1) % 10 == 0:
            with open(DATA_FILE, 'w', encoding='utf-8') as f:
                json.dump(etfs, f, ensure_ascii=False, indent=2)
        
        # 间隔 8 秒（最后一只不等待）
        if i < len(tasks) - 1:
            time.sleep(8)
    
    # 最终保存
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(etfs, f, ensure_ascii=False, indent=2)
    
    print(f'\n=== 完成 ===')
    print(f'成功: {success} | 失败: {fail}')
    print(f'字段填充: {fields_filled}')

if __name__ == '__main__':
    main()
