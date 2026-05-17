#!/usr/bin/env python3
"""
补充最新价：从非凸 etf-detail API 获取 close 价格
增量保存，可并行运行
"""
import sys, os, json, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from modules.data_source import FTSource

ROOT = os.path.dirname(os.path.abspath(__file__))
GEN_FILE = os.path.join(ROOT, "etf_data_generated.json")
FULL_FILE = os.path.join(ROOT, "etf_complete_all.json")
OUTPUT = os.path.join(ROOT, "etf_prices.json")

def get_exchange(code):
    return 'XSHG' if str(code).startswith('5') else 'XSHE'

print("=== 补充最新价 ===")

with open(FULL_FILE, "r", encoding="utf-8") as f:
    data = json.load(f)
codes = [(e['code'], e.get('name', '')) for e in data]
print(f"ETF总数: {len(codes)}")

ft = FTSource()
prices = {}
ok = fail = 0

for i, (code, name) in enumerate(codes):
    try:
        detail = ft.get_etf_detail(code, get_exchange(code))
        if detail and detail.get('close') is not None:
            prices[code] = {
                'close': detail['close'],
                'change_rate': detail.get('return_6m'),  # 非凸的涨跌幅字段
            }
            ok += 1
        else:
            prices[code] = {'close': 0, 'change_rate': 0}
            fail += 1
    except Exception:
        prices[code] = {'close': 0, 'change_rate': 0}
        fail += 1

    if (i + 1) % 100 == 0:
        print(f"  进度: {i+1}/{len(codes)}  成功={ok} 失败={fail}")
        with open(OUTPUT, "w", encoding="utf-8") as f:
            json.dump(prices, f, ensure_ascii=False)
    time.sleep(0.15)

with open(OUTPUT, "w", encoding="utf-8") as f:
    json.dump(prices, f, ensure_ascii=False)
print(f"完成! 成功={ok} 失败={fail}")
