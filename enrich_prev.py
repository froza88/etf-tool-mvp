#!/usr/bin/env python3
"""
补充前收盘价和实时涨跌幅
从非凸 etf-detail API 获取 prev_close + change_rate
"""
import sys, os, json, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from modules.data_source import FTSource

ROOT = os.path.dirname(os.path.abspath(__file__))
FULL_FILE = os.path.join(ROOT, "etf_complete_all.json")
OUTPUT = os.path.join(ROOT, "etf_prev_close.json")

def get_exchange(code):
    return 'XSHG' if str(code).startswith('5') else 'XSHE'

print("=== 补充前收盘价 ===")

with open(FULL_FILE, "r", encoding="utf-8") as f:
    data = json.load(f)
codes = [e['code'] for e in data]
print(f"ETF总数: {len(codes)}")

ft = FTSource()
prices = {}
ok = fail = 0

for i, code in enumerate(codes):
    try:
        detail = ft.get_etf_detail(code, get_exchange(code))
        if detail:
            prices[code] = {
                'prev_close': detail.get('prev_close'),
                'change_rate': detail.get('change_rate'),
            }
            ok += 1
        else:
            fail += 1
    except:
        fail += 1

    if (i + 1) % 100 == 0:
        print(f"  进度: {i+1}/{len(codes)}  成功={ok} 失败={fail}")
        with open(OUTPUT, "w", encoding="utf-8") as f:
            json.dump(prices, f, ensure_ascii=False)
    time.sleep(0.15)

with open(OUTPUT, "w", encoding="utf-8") as f:
    json.dump(prices, f, ensure_ascii=False)
print(f"完成! 成功={ok} 失败={fail}")
