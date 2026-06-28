#!/usr/bin/env python3
"""从 etf_core_data.json 生成小程序静态数据文件

输出结构:
  static/
    search_index.json   — ETF搜索索引（客户端本地搜）
    etf/{code}.json     — 每只ETF完整数据
    valuation.json      — 指数估值表
"""

import json
import os
from pathlib import Path

SRC = 'prototypes/etf_core_data.json'
OUT = 'miniprogram/static'

# ── 加载数据 ──
with open(SRC) as f:
    data = json.load(f)

total = len(data)
print(f'加载 {total} 只 ETF')

# ── 确保输出目录 ──
etf_dir = os.path.join(OUT, 'etf')
os.makedirs(etf_dir, exist_ok=True)

# ── 1. 生成 search_index.json ──
search_fields = [
    'code', 'name', 'short_name', 'category', 'issuer', 'issuer_short',
    'invest_type', 'benchmark', 'track_index'
]
search_index = []
for e in data:
    entry = {}
    for f in search_fields:
        v = e.get(f)
        if v is not None and v != '':
            entry[f] = v
    # 加两个核心指标给搜索结果排序
    entry['scale'] = e.get('scale_yi', 0) or 0
    entry['change_pct'] = e.get('change_pct')
    search_index.append(entry)

with open(os.path.join(OUT, 'search_index.json'), 'w') as f:
    json.dump(search_index, f, ensure_ascii=False, separators=(',', ':'))
print(f'search_index.json: {len(search_index)}条, {os.path.getsize(os.path.join(OUT, "search_index.json"))/1024:.0f}KB')

# ── 2. 生成 etf/{code}.json ──
compare_fields = [
    'code', 'name', 'short_name', 'category', 'issuer', 'issuer_full', 'issuer_short',
    'invest_type', 'benchmark', 'track_index', 'track_index_code',
    'issue_date', 'listing_date', 'custodian', 'fund_manager',
    'scale_yi', 'close', 'change_pct', 'change_rate', 'prev_close', 'volume',
    'year_1_return', 'year_3_return', 'year_half_return', 'year_2_return',
    'sharpe_ratio', 'annual_vol', 'max_drawdown', 'calmar_ratio',
    'management_fee_rate', 'custody_fee_rate', 'fee_rate', 'fee_mgmt', 'fee_custody', 'fee_total',
    'beta', 'alpha', 'tracking_error', 'info_ratio',
    'valuation_percentile',
    'main_net_inflow', 'main_net_ratio', 'flow_shares',
    'nav', 'premium_discount',
    'top_holdings', 'holdings_str',
    'flow_data_date', 'flow_source',
]
count = 0
for e in data:
    code = e.get('code', '')
    if not code:
        continue
    detail = {}
    for f in compare_fields:
        v = e.get(f)
        if v is not None and v != '' and v != []:
            detail[f] = v
    with open(os.path.join(etf_dir, f'{code}.json'), 'w') as f:
        json.dump(detail, f, ensure_ascii=False, separators=(',', ':'))
    count += 1

print(f'etf/*.json: {count} 个文件')

# ── 3. 生成 valuation.json ──
# 提取有 valuation_percentile 的 ETF 用于估值表
val_rows = []
for e in data:
    vp = e.get('valuation_percentile')
    if vp is not None and vp != '' and vp != []:
        val_rows.append({
            'code': e.get('code', ''),
            'name': e.get('name', ''),
            'benchmark': e.get('benchmark', ''),
            'valuation_percentile': vp,
            'close': e.get('close'),
            'change_pct': e.get('change_pct'),
            'year_1_return': e.get('year_1_return'),
        })

# 按分位排序
val_rows.sort(key=lambda x: float(x['valuation_percentile']) if isinstance(x['valuation_percentile'], (int, float)) else float(x['valuation_percentile']))

valuation = {
    'updated': '2026-06-27',
    'total': len(val_rows),
    'rows': val_rows
}
with open(os.path.join(OUT, 'valuation.json'), 'w') as f:
    json.dump(valuation, f, ensure_ascii=False, separators=(',', ':'))
print(f'valuation.json: {len(val_rows)}条, {os.path.getsize(os.path.join(OUT, "valuation.json"))/1024:.0f}KB')

# ── 4. 生成 version.json（用于缓存校验） ──
version = {'version': '2026-06-28', 'total': total, 'etf_count': count}
with open(os.path.join(OUT, 'version.json'), 'w') as f:
    json.dump(version, f, ensure_ascii=False)
print(f'version.json: {version}')

print(f'\n✅ 静态数据生成完成 → {OUT}/')
print(f'   文件大小: {sum(os.path.getsize(os.path.join(dp, fn)) for dp,_,fs in os.walk(OUT) for fn in fs)/1024:.0f}KB')
