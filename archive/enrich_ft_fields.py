#!/usr/bin/env python3
"""从非凸etf-detail API补充market_cap/issue_date/custodian/tracking_index"""
import sys, os, json, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from modules.data_source import FTSource

ROOT = os.path.dirname(os.path.abspath(__file__))

def get_exchange(code):
    return 'XSHG' if str(code).startswith('5') else 'XSHE'

with open(os.path.join(ROOT, "etf_data_generated.json"), encoding="utf-8") as f:
    gen = json.load(f)
print(f"生成数据: {len(gen)} 条")

ft = FTSource()
updated = 0
seen = {}
for i, item in enumerate(gen):
    code = str(item['code'])
    # 跳过已处理的重复代码
    if code in seen:
        continue
    seen[code] = True
    
    try:
        detail = ft.get_etf_detail(code, get_exchange(code))
        if detail:
            item['market_cap'] = detail.get('market_cap', 0)
            item['issue_date'] = detail.get('issue_date', '')
            item['custodian'] = detail.get('custodian', '')
            item['tracking_index'] = detail.get('tracking_index', '')
            updated += 1
    except:
        pass
    
    if (i + 1) % 100 == 0:
        print(f"  进度: {i+1}/{len(gen)} 已更新={updated}")

with open(os.path.join(ROOT, "etf_data_generated.json"), "w", encoding="utf-8") as f:
    json.dump(gen, f, ensure_ascii=False, indent=2)
print(f"完成! 更新了 {updated}/{len(gen)} 条")
