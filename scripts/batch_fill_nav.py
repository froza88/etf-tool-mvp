#!/usr/bin/env python3
"""批量补全 ETF NAV（单位净值）数据
数据源: AKShare fund_etf_fund_info_em()
"""
import json
import time
import sys
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    import akshare as ak
except ImportError:
    print("请先安装 akshare: pip install akshare")
    sys.exit(1)

# Paths
DATA_FILE = '/Users/apangduo/WorkBuddy/Claw/etf-tool-mvp/prototypes/etf_core_data.json'
BACKUP_FILE = DATA_FILE.replace('.json', '.nav_backup.json')

def load_data():
    with open(DATA_FILE) as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, ensure_ascii=False)

def fetch_nav(code):
    """Fetch latest NAV for a single ETF. Returns (code, nav) or (code, None)."""
    try:
        # 最近5个交易日，确保拿到最新净值
        df = ak.fund_etf_fund_info_em(fund=str(code), start_date='20260620', end_date='20260628')
        if df is None or df.empty:
            return (code, None)
        # 取最新一行
        latest = df.iloc[-1]
        nav = float(latest['单位净值'])
        return (code, nav)
    except Exception as e:
        return (code, None)

def main():
    print("Loading data...")
    data = load_data()
    
    # Backup
    import shutil
    shutil.copy(DATA_FILE, BACKUP_FILE)
    print(f"Backup saved to {BACKUP_FILE}")
    
    # Find missing NAV ETFs
    missing = [(i, e) for i, e in enumerate(data) if e.get('nav') is None]
    total_missing = len(missing)
    print(f"Missing NAV: {total_missing}/{len(data)}")
    
    if total_missing == 0:
        print("All NAVs already filled!")
        return
    
    # Fetch in parallel with rate limiting
    success = 0
    fail = 0
    start_time = time.time()
    
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {}
        for i, etf in missing:
            code = etf['code']
            futures[executor.submit(fetch_nav, code)] = (i, code, etf['name'])
        
        for f in as_completed(futures):
            idx, code, name = futures[f]
            try:
                code_str, nav = f.result()
                if nav is not None:
                    data[idx]['nav'] = nav
                    success += 1
                else:
                    fail += 1
                
                done = success + fail
                if done % 50 == 0 or done == total_missing:
                    elapsed = time.time() - start_time
                    rate = done / elapsed
                    eta = (total_missing - done) / rate if rate > 0 else 0
                    print(f"Progress: {done}/{total_missing} ({100*done/total_missing:.1f}%) | "
                          f"OK={success} FAIL={fail} | "
                          f"Rate={rate:.1f}/s | ETA={eta:.0f}s")
            except Exception as e:
                fail += 1
                print(f"  Error: {code} {name}: {e}")
    
    elapsed = time.time() - start_time
    print(f"\nDone in {elapsed:.1f}s. Success: {success}, Failed: {fail}")
    
    # Save
    save_data(data)
    print(f"Saved to {DATA_FILE}")
    
    # Verify
    data2 = load_data()
    has_nav = sum(1 for e in data2 if e.get('nav') is not None)
    print(f"NAV coverage: {has_nav}/{len(data2)} = {100*has_nav/len(data2):.1f}%")

if __name__ == '__main__':
    main()
