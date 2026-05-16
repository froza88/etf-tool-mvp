#!/usr/bin/env python3
"""
全量数据补充脚本 — 方案B
- 收益率: 非凸科技 etf-detail 直接拿（change_rate_1y/3y）
- 持仓权重: AKShare fund_portfolio_hold_em 全量获取
- 回撤/夏普: AKShare 近6个月日线计算（比算3年快6倍）
- 覆盖全部1466只

用法（Mac终端）:
  nohup python3 enrich_all_v2.py > enrich_v2.log 2>&1 &
  tail -f enrich_v2.log
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from modules.data_source import AKShareSource, FTSource
from modules.metrics import calc_max_drawdown, calc_sharpe_ratio
from modules.data_cleaner import dedup_by_code
import json
import time
import math

ROOT = os.path.dirname(os.path.abspath(__file__))
GEN_FILE = os.path.join(ROOT, "etf_data_generated.json")
FULL_FILE = os.path.join(ROOT, "etf_complete_all.json")

ak_source = AKShareSource()
ft_source = FTSource()


def get_exchange(code):
    """判断交易所后缀"""
    c = str(code)
    if c.startswith('5'):
        return 'XSHG'
    elif c.startswith('1'):
        return 'XSHE'
    return 'XSHG'


print("=" * 60)
print("  方案B: 全量1466只数据补充")
print("=" * 60)

# === Step 1: 获取全量ETF列表 ===
print("\n[1/4] 获取全量ETF列表...")
with open(FULL_FILE, "r", encoding="utf-8") as f:
    full_data = json.load(f)
all_codes = [e['code'] for e in full_data]
print(f"  全量ETF: {len(all_codes)} 只")

# === Step 2: 非凸拿收益率 ===
print("\n[2/4] 非凸科技 etf-detail 获取收益率...")
returns_data = {}
success = 0
fail = 0
for i, code in enumerate(all_codes):
    exch = get_exchange(code)
    try:
        detail = ft_source.get_etf_detail(code, exch)
        if detail and detail.get('return_1y') is not None:
            returns_data[code] = {
                'year_1_return': round(detail['return_1y'] * 100, 1),
                'year_3_return': round((detail.get('return_3y') or 0) * 100, 1),
            }
            success += 1
        else:
            returns_data[code] = None
            fail += 1
    except Exception:
        returns_data[code] = None
        fail += 1

    if (i + 1) % 100 == 0:
        print(f"  收益率: {i+1}/{len(all_codes)}  成功={success} 失败={fail}", flush=True)
    time.sleep(0.2)

print(f"  收益率完成: 成功={success} 失败={fail}")

# === Step 3: AKShare 获取持仓权重 ===
print("\n[3/4] AKShare fund_portfolio_hold_em 获取持仓权重...")
holdings_data = {}
hw_success = 0
for i, code in enumerate(all_codes):
    try:
        holdings = ak_source.get_portfolio_hold(code)
        if holdings:
            top5 = [{'name': h['name'], 'weight': f"{h['weight_pct']:.2f}%"} for h in holdings[:5]]
            holdings_data[code] = top5
            hw_success += 1
        else:
            holdings_data[code] = []
    except Exception:
        holdings_data[code] = []

    if (i + 1) % 50 == 0:
        print(f"  持仓权重: {i+1}/{len(all_codes)}  有数据={hw_success}", flush=True)
    time.sleep(0.3)

print(f"  持仓权重完成: 有数据={hw_success}")

# === Step 4: 小批量算回撤/夏普（只对收益率非空的算） ===
print("\n[4/4] AKShare 近6个月日线计算回撤/夏普...")
calc_codes = [c for c in all_codes if returns_data.get(c) is not None]
metrics_data = {}
calc_ok = 0
for i, code in enumerate(calc_codes):
    try:
        ohlc = ak_source.get_hist_ohlc(code, start_date='20260101', end_date='20260516')
        if ohlc and len(ohlc['prices']) >= 30:
            prices = ohlc['prices']
            metrics_data[code] = {
                'max_drawdown': calc_max_drawdown(prices),
                'sharpe_ratio': calc_sharpe_ratio(prices),
            }
            calc_ok += 1
        else:
            metrics_data[code] = {'max_drawdown': 0, 'sharpe_ratio': 0}
    except Exception:
        metrics_data[code] = {'max_drawdown': 0, 'sharpe_ratio': 0}

    if (i + 1) % 50 == 0:
        print(f"  回撤/夏普: {i+1}/{len(calc_codes)}  已计算={calc_ok}", flush=True)
    time.sleep(0.2)

print(f"  回撤/夏普完成: 已计算={calc_ok}")

# === Step 5: 合并写入 ===
print("\n[5/4] 写入 etf_data_generated.json...")
with open(GEN_FILE, 'r', encoding='utf-8') as f:
    existing = json.load(f)

# 按代码索引
existing_map = {}
for item in existing:
    existing_map[str(item['code'])] = item

# 补充新ETF
new_entries = []
for code in all_codes:
    if code not in existing_map:
        name = ''
        for e in full_data:
            if e['code'] == code:
                name = e.get('name', '')
                break
        ret = returns_data.get(code) or {'year_1_return': 0, 'year_3_return': 0}
        met = metrics_data.get(code) or {'max_drawdown': 0, 'sharpe_ratio': 0}
        new_entries.append({
            'code': code, 'name': name, 'issuer': '', 'type': '股票型',
            'scale': 0, 'fee': 0.6, 'tracking_error': 0.02,
            'top_holdings': holdings_data.get(code, []),
            'year_1_return': ret['year_1_return'],
            'year_3_return': ret['year_3_return'],
            'max_drawdown': met['max_drawdown'],
            'sharpe_ratio': met['sharpe_ratio'],
            'volume': 0, 'category': '行业',
        })

# 现有条目补充字段
for item in existing:
    code = str(item['code'])
    if code in returns_data and returns_data[code]:
        item['year_1_return'] = returns_data[code]['year_1_return']
        item['year_3_return'] = returns_data[code]['year_3_return']
    if code in metrics_data:
        item['max_drawdown'] = metrics_data[code]['max_drawdown']
        item['sharpe_ratio'] = metrics_data[code]['sharpe_ratio']
    if code in holdings_data and holdings_data[code]:
        item['top_holdings'] = holdings_data[code]

combined = existing + new_entries
print(f"  原有: {len(existing)}  新增: {len(new_entries)}  总计: {len(combined)}")

with open(GEN_FILE, 'w', encoding='utf-8') as f:
    json.dump(combined, f, ensure_ascii=False, indent=2)

# 统计
has_y1 = sum(1 for e in combined if e.get('year_1_return'))
has_dd = sum(1 for e in combined if e.get('max_drawdown'))
has_sr = sum(1 for e in combined if e.get('sharpe_ratio'))
has_hold = sum(1 for e in combined if e.get('top_holdings'))

print(f"\n✅ 完成!")
print(f"  总ETF数: {len(combined)}")
print(f"  有收益率: {has_y1}")
print(f"  有回撤: {has_dd}")
print(f"  有夏普: {has_sr}")
print(f"  有持仓: {has_hold}")
print(f"\n建议下一步: python3 build_standard_data.py")
