#!/usr/bin/env python3
"""
批量补充全部1466只ETF的数据：
1. 持仓权重% — fund_portfolio_hold_em()
2. 收益率/最大回撤/夏普 — fund_etf_hist_em()
3. 生成 etf_data_generated.json（全量覆盖）

运行方式（Mac终端，挂后台）：
  nohup python3 enrich_all_etfs.py > enrich_all.log 2>&1 &

预计时间：持仓权重~15分钟 + 净值计算~2小时
"""
import json
import time
import math
import sys
import warnings
warnings.filterwarnings('ignore')

try:
    import akshare as ak
    import pandas as pd
except ImportError:
    print("❌ 需要安装 akshare: pip install akshare")
    sys.exit(1)

ROOT = "/Users/apangduo/WorkBuddy/Claw/etf-tool-mvp"

print("=" * 60)
print("  全部1466只ETF数据补充")
print("=" * 60)

# ==== Step 1: 从AKShare获取全量ETF列表 ====
print("\n[1/4] 获取全量ETF列表...")
df = ak.fund_etf_spot_em()
all_codes = [str(c).strip() for c in list(df['代码'])]
print(f"  获取到 {len(all_codes)} 只ETF")

# 去重
seen = set()
unique_codes = []
for c in all_codes:
    if c not in seen:
        seen.add(c)
        unique_codes.append(c)
print(f"  去重后: {len(unique_codes)} 只")

# ==== Step 2: 获取持仓权重 ====
print("\n[2/4] 获取全部ETF持仓权重%...")
all_holdings = {}
updated = 0
failed = 0
for i, code in enumerate(unique_codes):
    try:
        df_h = ak.fund_portfolio_hold_em(symbol=code, date="2025")
        holdings = []
        if df_h is not None and len(df_h) > 0:
            for _, r in df_h.head(10).iterrows():
                try:
                    name = str(r.iloc[2]).strip()
                    weight = float(r.iloc[3])
                    holdings.append({"name": name, "weight": f"{weight:.2f}%"})
                except:
                    pass
        all_holdings[code] = holdings[:5]
        if holdings:
            updated += 1
    except Exception:
        all_holdings[code] = []
        failed += 1
    if (i + 1) % 50 == 0:
        print(f"   持仓权重: {i+1}/{len(unique_codes)}  有数据={updated} 失败={failed}", flush=True)
    time.sleep(0.3)

print(f"   持仓权重完成: 有数据={updated} 失败={failed}")

# ==== Step 3: 获取历史净值计算收益率 ====
print("\n[3/4] 获取历史净值计算收益率/回撤/夏普...")
all_returns = {}
calced = 0
no_data = 0
for i, code in enumerate(unique_codes):
    try:
        df_h = ak.fund_etf_hist_em(
            symbol=code, period='daily',
            start_date='20230516', end_date='20260516',
            adjust='qfq'
        )
        if df_h is None or len(df_h) < 20:
            all_returns[code] = {"year_1_return": 0, "year_3_return": 0, "max_drawdown": 0, "sharpe_ratio": 0}
            no_data += 1
            continue

        prices = [float(v) for v in list(df_h['收盘'])]
        n = len(prices)

        y1 = (prices[-1] - prices[-252]) / prices[-252] * 100 if n >= 252 else 0
        y3 = (prices[-1] - prices[0]) / prices[0] * 100

        # 最大回撤
        peak = prices[0]
        max_dd = 0.0
        for v in prices:
            if v > peak: peak = v
            dd = (v - peak) / peak * 100
            if dd < max_dd: max_dd = dd

        # 夏普
        if n >= 30:
            daily_rets = [(prices[j] - prices[j-1]) / prices[j-1] for j in range(1, min(n, 253))]
            if daily_rets:
                avg = sum(daily_rets) / len(daily_rets)
                vol = math.sqrt(sum((r - avg)**2 for r in daily_rets) / len(daily_rets))
                sharpe = ((avg * 252) - 0.02) / (vol * math.sqrt(252)) if vol > 0 else 0
            else:
                sharpe = 0
        else:
            sharpe = 0

        all_returns[code] = {
            "year_1_return": round(y1, 1),
            "year_3_return": round(y3, 1),
            "max_drawdown": round(max_dd, 1),
            "sharpe_ratio": round(sharpe, 2),
        }
        calced += 1
    except Exception:
        all_returns[code] = {"year_1_return": 0, "year_3_return": 0, "max_drawdown": 0, "sharpe_ratio": 0}
        no_data += 1

    if (i + 1) % 50 == 0:
        print(f"   净值计算: {i+1}/{len(unique_codes)}  已计算={calced} 无数据={no_data}", flush=True)
    time.sleep(0.3)

print(f"   净值计算完成: 已计算={calced} 无数据={no_data}")

# ==== Step 4: 写入 etf_data_generated.json ====
print("\n[4/4] 写入 etf_data_generated.json...")
# 从现有的 generated 文件保留原有字段，补充新数据
with open(f"{ROOT}/etf_data_generated.json", "r", encoding="utf-8") as f:
    existing = json.load(f)

# 合并数据：先保留已有的，再补充代码不存在的新ETF
existing_map = {}
for item in existing:
    existing_map[str(item['code'])] = item

# 补充缺失ETF的数据
from pathlib import Path
full_file = Path(f"{ROOT}/etf_complete_all.json")
with open(full_file, "r", encoding="utf-8") as f:
    full_data = json.load(f)

full_name_map = {}
for e in full_data:
    full_name_map[str(e['code'])] = e.get('name', '')

new_entries = []
for code in unique_codes:
    if code not in existing_map:
        ret = all_returns.get(code, {"year_1_return": 0, "year_3_return": 0, "max_drawdown": 0, "sharpe_ratio": 0})
        new_entries.append({
            "code": code,
            "name": full_name_map.get(code, ""),
            "issuer": "",
            "type": "股票型",
            "scale": 0,
            "fee": 0.6,
            "tracking_error": 0.02,
            "top_holdings": all_holdings.get(code, []),
            "year_1_return": ret["year_1_return"],
            "year_3_return": ret["year_3_return"],
            "max_drawdown": ret["max_drawdown"],
            "sharpe_ratio": ret["sharpe_ratio"],
            "volume": 0,
            "category": "行业",
        })

# 已有条目补充持仓和收益率
for item in existing:
    code = str(item['code'])
    if code in all_holdings and all_holdings[code]:
        item['top_holdings'] = all_holdings[code]
    if code in all_returns:
        ret = all_returns[code]
        if ret['year_1_return'] != 0:
            item['year_1_return'] = ret['year_1_return']
            item['year_3_return'] = ret['year_3_return']
            item['max_drawdown'] = ret['max_drawdown']
            item['sharpe_ratio'] = ret['sharpe_ratio']

combined = existing + new_entries
print(f"  原有: {len(existing)} 新增: {len(new_entries)} 总计: {len(combined)}")

with open(f"{ROOT}/etf_data_generated.json", "w", encoding="utf-8") as f:
    json.dump(combined, f, ensure_ascii=False, indent=2)

print(f"\n✅ 完成! 已保存到 etf_data_generated.json ({len(combined)} 条)")
print("\n建议后续执行: python3 build_standard_data.py")
