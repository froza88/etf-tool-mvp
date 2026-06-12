#!/usr/bin/env python3
"""补齐风险指标：calmar_ratio + sortino_ratio"""
import json, os, glob, math

ROOT = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(ROOT, 'etf_standard_data.json')
HISTORY = os.path.join(ROOT, 'data', 'history')
BACKUP = os.path.join(ROOT, 'etf_standard_data.backup.json')

# 备份
import shutil
shutil.copy(DATA, BACKUP)
print(f"Backup saved to {BACKUP}")

with open(DATA) as f:
    etfs = json.load(f)

total = len(etfs)
print(f"Total ETFs: {total}")

risk_free = 0.025  # 2.5% risk-free rate

def is_valid(v):
    if v is None:
        return False
    if isinstance(v, str) and v.strip() == '':
        return False
    return True

def compute_sortino(prices, rf=risk_free):
    """Sortino ratio from daily prices"""
    if len(prices) < 60:
        return None
    returns = []
    for i in range(1, len(prices)):
        if prices[i] and prices[i-1] and prices[i-1] > 0:
            r = (prices[i] - prices[i-1]) / prices[i-1]
            returns.append(r)
    if len(returns) < 50:
        return None
    negative = [r for r in returns if r < 0]
    if len(negative) < 5:
        return None
    mean_neg = sum(negative) / len(negative)
    downside_var = sum((r - mean_neg) ** 2 for r in negative) / (len(negative) - 1)
    downside_dev = math.sqrt(downside_var)
    ann_downside = downside_dev * math.sqrt(252)
    if ann_downside < 0.001:
        return None
    total_ret = 1.0
    for r in returns:
        total_ret *= (1 + r)
    ann_ret = total_ret ** (252 / len(returns)) - 1
    return round((ann_ret - rf) / ann_downside, 4)

# ===== 1. calmar_ratio = year_1_return / abs(max_drawdown) =====
calmar_filled = 0
for e in etfs:
    if is_valid(e.get('calmar_ratio')):
        continue
    y1 = e.get('year_1_return')
    dd = e.get('max_drawdown')
    if is_valid(y1) and is_valid(dd):
        try:
            y1v = float(y1)
            ddv = abs(float(dd))
            if ddv > 0:
                e['calmar_ratio'] = round(y1v / ddv, 4)
                calmar_filled += 1
        except (ValueError, TypeError):
            pass

print(f"\ncalmar_ratio: filled {calmar_filled} via year_1_return/max_drawdown")

# ===== 2. sortino_ratio from K-line daily data =====
sortino_filled = 0
sortino_skipped = 0
sortino_no_data = 0

for e in etfs:
    if is_valid(e.get('sortino_ratio')):
        continue
    code = e['code']
    hist_file = os.path.join(HISTORY, f"{code}.json")
    if not os.path.exists(hist_file):
        sortino_no_data += 1
        continue
    try:
        with open(hist_file) as f:
            hist = json.load(f)
        prices = hist.get('prices', [])
        if not prices:
            sortino_skipped += 1
            continue
        sr = compute_sortino(prices)
        if sr is not None:
            e['sortino_ratio'] = sr
            sortino_filled += 1
        else:
            sortino_skipped += 1
    except Exception:
        sortino_skipped += 1

print(f"\nsortino_ratio:")
print(f"  filled: {sortino_filled}")
print(f"  skipped (insufficient data): {sortino_skipped}")
print(f"  no history file: {sortino_no_data}")

# 保存
with open(DATA, 'w') as f:
    json.dump(etfs, f, ensure_ascii=False, indent=2)
print(f"\nSaved to {DATA}")

# 最终覆盖度
print("\n=== Final Coverage ===")
for fld in ['calmar_ratio', 'sortino_ratio', 'max_drawdown', 'annual_vol', 'sharpe_ratio']:
    cnt = sum(1 for e in etfs if is_valid(e.get(fld)))
    print(f"  {fld}: {cnt}/{total} ({cnt*100//total}%)")
