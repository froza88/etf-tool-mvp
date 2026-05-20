#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
下载TOP50 ETF的历史数据
策略：分批下载，避免API限流
"""
import json
import time
from pathlib import Path
from datetime import datetime, timedelta

ROOT = Path(__file__).parent
STANDARD_DATA = ROOT / "etf_standard_data.json"
HISTORY_DIR = ROOT / "data" / "history"

print("=== 下载TOP50 ETF历史数据 ===\n")

# 加载ETF数据
with open(STANDARD_DATA, 'r', encoding='utf-8') as f:
    etf_data = json.load(f)

# 按规模排序，取TOP50
etf_sorted = sorted(etf_data, key=lambda x: x.get('scale', 0), reverse=True)
top50 = etf_sorted[:50]

print(f"TOP50 ETF列表（按规模排序）:")
for i, etf in enumerate(top50[:10], 1):  # 只显示前10只
    print(f"  {i}. {etf['code']} - {etf.get('name', '')} - 规模: {etf.get('scale', 0):.1f}亿")
print(f"  ... (共50只)\n")

# 下载历史数据
downloaded = 0
failed = 0

for i, etf in enumerate(top50, 1):
    code = etf['code']
    print(f"[{i}/50] 下载 {code} - {etf.get('name', '')}...")
    
    try:
        import akshare as ak
        
        # 计算日期范围（最近1年）
        end_date = datetime.now().strftime('%Y%m%d')
        start_date = (datetime.now() - timedelta(days=365)).strftime('%Y%m%d')
        
        # 下载历史数据
        df = ak.fund_etf_hist_em(
            symbol=code,
            period='daily',
            start_date=start_date,
            end_date=end_date,
            adjust='qfq'
        )
        
        if df is not None and len(df) > 0:
            # 保存到 data/history/
            history_file = HISTORY_DIR / f"{code}.json"
            history_data = {
                "code": code,
                "name": etf.get('name', ''),
                "start_date": df.iloc[0]['日期'],
                "end_date": df.iloc[-1]['日期'],
                "data": df.to_dict('records')
            }
            
            with open(history_file, 'w', encoding='utf-8') as f:
                json.dump(history_data, f, ensure_ascii=False, indent=2)
            
            print(f"  ✅ 成功: {len(df)} 条数据 -> {history_file.name}")
            downloaded += 1
        else:
            print(f"  ⚠️  无数据")
            failed += 1
            
    except Exception as e:
        print(f"  ❌ 失败: {e}")
        failed += 1
    
    # 限速：每次请求后暂停1秒
    time.sleep(1)
    
    # 每10只显示一次进度
    if i % 10 == 0:
        print(f"\n--- 进度: {i}/50, 成功: {downloaded}, 失败: {failed} ---\n")

print(f"\n=== 下载完成 ===")
print(f"成功: {downloaded} 只")
print(f"失败: {failed} 只")
print(f"成功率: {downloaded/50*100:.1f}%")
