#!/usr/bin/env python3
"""从已有 Wind 缓存中重解析缺失字段：跟踪误差、索提诺、阿尔法、贝塔、信息比率"""

import json
import os
import sys
from datetime import datetime
from collections import defaultdict

WIND_DIR = 'data/wind_full'
DATA_FILE = 'etf_standard_data.json'

def safe_float(v):
    """安全转float"""
    if v is None or v == '' or v == 'None':
        return None
    try:
        f = float(v)
        return f if f != 0 else None  # 0 视为无数据
    except (ValueError, TypeError):
        return None

def parse_wind_cache(filepath):
    """解析单个 Wind 缓存文件，提取 block 4 的风险指标"""
    result = {}
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            raw = json.load(f)
        
        if raw.get('isError'):
            return result
        
        inner = json.loads(raw['content'][0]['text'])
        blocks = inner['data']['data']
        
        if len(blocks) < 5:
            return result
        
        # Block 0: 基本信息
        blk0 = blocks[0]
        cols0 = [c['name'] for c in blk0['columns']]
        row0 = blk0['rows'][0] if blk0['rows'] else None
        if row0:
            def get0(*names):
                for n in names:
                    if n in cols0:
                        return row0[cols0.index(n)]
                return None
            
            result['benchmark'] = get0('业绩比较基准')  # 跟踪指数
            result['invest_type'] = get0('投资类型_二级分类', '基金类型')
        
        # Block 2: 费率
        blk2 = blocks[2]
        cols2 = [c['name'] for c in blk2['columns']]
        row2 = blk2['rows'][0] if blk2['rows'] else None
        if row2:
            def get2(*names):
                for n in names:
                    if n in cols2:
                        return row2[cols2.index(n)]
                return None
            
            mgmt = safe_float(get2('管理费率_支持历史'))
            cust = safe_float(get2('托管费率_支持历史'))
            if mgmt is not None:
                result['management_fee_rate'] = mgmt
            if cust is not None:
                result['custody_fee_rate'] = cust
            if mgmt is not None and cust is not None:
                result['fee_rate'] = mgmt + cust
        
        # Block 4: 风险指标（跟踪误差、索提诺、阿尔法、贝塔、信息比率等）
        blk4 = blocks[4] if len(blocks) > 4 else None
        if blk4:
            cols4 = [c['name'] for c in blk4['columns']]
            row4 = blk4['rows'][0] if blk4['rows'] else None
            if row4:
                def get4(*names):
                    for n in names:
                        if n in cols4:
                            return row4[cols4.index(n)]
                    return None
                
                # 近1年跟踪误差
                te = safe_float(get4('近1年跟踪误差'))
                if te is not None:
                    result['tracking_error'] = te
                
                # 近1年信息比率 → sortino 近似（实际需要下行波动率，这里用信息比率近似）
                ir = safe_float(get4('近1年信息比率'))
                if ir is not None:
                    result['info_ratio'] = ir
                
                # 近1年贝塔
                beta = safe_float(get4('近1年贝塔'))
                if beta is not None:
                    result['beta'] = beta
                
                # 近1年阿尔法
                alpha = safe_float(get4('近1年阿尔法'))
                if alpha is not None:
                    result['alpha'] = alpha
                
                # 近1年夏普（如果主文件没有）
                sharpe = safe_float(get4('近1年夏普比率'))
                if sharpe is not None:
                    result['sharpe_ratio'] = sharpe
                
                # 年化波动率
                vol = safe_float(get4('近1年年化波动率'))
                if vol is not None:
                    result['annual_vol'] = vol
                
                # 最大回撤
                mdd = safe_float(get4('近1年最大回撤'))
                if mdd is not None:
                    result['max_drawdown'] = mdd
        
        # Block 5: 收益率
        blk5 = blocks[5] if len(blocks) > 5 else None
        if blk5:
            cols5 = [c['name'] for c in blk5['columns']]
            row5 = blk5['rows'][0] if blk5['rows'] else None
            if row5:
                def get5(*names):
                    for n in names:
                        if n in cols5:
                            return row5[cols5.index(n)]
                    return None
                
                y1 = safe_float(get5('近1年回报'))
                if y1 is not None:
                    result['year_1_return'] = y1
                
                y3 = safe_float(get5('近3年回报'))
                if y3 is not None:
                    result['year_3_return'] = y3
                
                y2 = safe_float(get5('近2年回报'))
                if y2 is not None:
                    result['year_2_return'] = y2
                
                y6m = safe_float(get5('近6月回报'))
                if y6m is not None:
                    result['year_half_return'] = y6m
        
    except Exception as e:
        pass  # 跳过损坏的缓存
    
    return result

def main():
    print(f'[1/4] 加载 ETF 数据...')
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        etfs = json.load(f)
    
    # 按 code 建索引
    etf_map = {}
    for i, e in enumerate(etfs):
        etf_map[e['code']] = i
    
    print(f'  ETF 总数: {len(etfs)}')
    
    # 扫描 Wind 缓存文件
    print(f'\n[2/4] 扫描 Wind 缓存...')
    wind_files = {}
    for fname in os.listdir(WIND_DIR):
        if fname.endswith('.json') and not fname.startswith('.'):
            code = fname.split('_')[0]
            filepath = os.path.join(WIND_DIR, fname)
            # 取最新的日期
            if code not in wind_files:
                wind_files[code] = filepath
            else:
                # 比较日期
                old_date = wind_files[code].split('_')[-1].replace('.json', '')
                new_date = fname.split('_')[-1].replace('.json', '')
                if new_date > old_date:
                    wind_files[code] = filepath
    
    print(f'  Wind 缓存文件: {len(wind_files)}')
    
    # 统计缺失字段（解析前）
    missing_tracking = sum(1 for e in etfs if not e.get('tracking_error'))
    print(f'  解析前: tracking_error 缺失 {missing_tracking}/{len(etfs)}')
    
    print(f'\n[3/4] 解析 Wind 缓存...')
    stats = defaultdict(int)
    updated = 0
    not_found = 0
    
    for code, filepath in wind_files.items():
        if code not in etf_map:
            not_found += 1
            continue
        
        idx = etf_map[code]
        parsed = parse_wind_cache(filepath)
        
        if not parsed:
            stats['empty_parse'] += 1
            continue
        
        # 合并到 etf 数据（只填充当前缺失或为 None 的字段）
        for field, value in parsed.items():
            if value is not None:
                current = etfs[idx].get(field)
                if current is None or current == '' or current == 0:
                    etfs[idx][field] = value
                    stats[field] += 1
        
        updated += 1
    
    print(f'  已更新: {updated} 只 ETF')
    print(f'  ETF中找不到: {not_found}')
    print(f'\n  字段填充统计:')
    for field, count in sorted(stats.items()):
        print(f'    {field}: +{count}')
    
    # 后处理：计算 sortino_ratio（用 info_ratio 近似）
    # 真正的 sortino = (年化收益 - 无风险利率) / 下行波动率
    # info_ratio = (年化超额收益) / 跟踪误差，两者不完全等价
    # 我们保留 info_ratio 作为独立字段，sortino 需要下行数据才能算
    
    print(f'\n[4/4] 保存数据...')
    # 备份旧文件
    backup = f'{DATA_FILE}.backup_{datetime.now().strftime("%Y%m%d_%H%M")}'
    os.rename(DATA_FILE, backup)
    print(f'  备份: {backup}')
    
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(etfs, f, ensure_ascii=False, indent=2)
    
    # 最终统计
    print(f'\n=== 解析后覆盖率 ===')
    check_fields = {
        'tracking_error': '跟踪误差',
        'benchmark': '跟踪指数',
        'management_fee_rate': '管理费率',
        'custody_fee_rate': '托管费率',
        'fee_rate': '总费率',
        'invest_type': '投资类型',
        'info_ratio': '信息比率',
        'beta': '贝塔',
        'alpha': '阿尔法',
        'year_2_return': '2年收益',
        'year_half_return': '6月收益',
    }
    
    total = len(etfs)
    for key, cn in check_fields.items():
        valid = sum(1 for e in etfs if e.get(key) is not None and e.get(key) != '')
        cov = valid / total * 100
        print(f'  {cn:<12} {valid:>5}/{total}  {cov:>5.1f}%')
    
    print(f'\n完成!')

if __name__ == '__main__':
    main()
