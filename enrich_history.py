#!/usr/bin/env python3
"""
批量获取ETF历史K线（AKShare），保存为静态缓存文件
供PythonAnywhere部署时使用（PA上AKShare被封，需预先生成）
"""
import json
import os
import time
import sys
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

ROOT = os.path.dirname(os.path.abspath(__file__))
OUTPUT = os.path.join(ROOT, "etf_history_cache.json")

# 加载ETF列表
with open(os.path.join(ROOT, "etf_standard_data.json"), encoding="utf-8") as f:
    etfs = json.load(f)

# 只缓存规模前200的ETF（覆盖95%以上访问量）
etfs_sorted = sorted(etfs, key=lambda x: x.get('scale', 0) or 0, reverse=True)
target_etfs = etfs_sorted[:200]

print(f"=== 批量获取历史K线 ===")
print(f"目标ETF: {len(target_etfs)} 只（规模Top200）")

try:
    import akshare as ak
except ImportError:
    print("❌ akshare 未安装")
    sys.exit(1)

cache = {}
ok = fail = 0

for i, etf in enumerate(target_etfs):
    code = etf['code']
    name = etf['name']

    try:
        # 获取3年数据（涵盖1M/3M/1Y/3Y所有周期）
        end_date = datetime.now()
        start_date = end_date - timedelta(days=1100)

        df = ak.fund_etf_hist_em(
            symbol=str(code),
            period='daily',
            start_date=start_date.strftime('%Y%m%d'),
            end_date=end_date.strftime('%Y%m%d'),
            adjust='qfq'
        )

        if df is not None and len(df) > 0:
            prices = [float(v) for v in list(df['收盘'])]
            dates = [str(d) for d in list(df['日期'])]

            cache[code] = {
                'name': name,
                'prices': prices,
                'dates': dates,
                'count': len(prices),
                'updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            ok += 1
        else:
            fail += 1
    except Exception as e:
        fail += 1
        print(f"  ⚠️ {code} {name}: {e}")

    if (i + 1) % 20 == 0 or i == len(target_etfs) - 1:
        print(f"  进度: {i+1}/{len(target_etfs)} 成功={ok} 失败={fail}")
        # 增量保存
        with open(OUTPUT, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False)

    time.sleep(0.3)  # 避免请求过快

print(f"\n✅ 完成! 成功={ok} 失败={fail}")
print(f"保存到: {OUTPUT}")
print(f"文件大小: {os.path.getsize(OUTPUT) / 1024:.0f} KB")
