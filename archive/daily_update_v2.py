#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ETF 数据每日更新脚本 v2
修复 daily_update.py 的设计问题，专注每日增量更新

用法：
  python3 daily_update_v2.py              # 完整更新
  python3 daily_update_v2.py --push       # 更新后自动 git push
  python3 daily_update_v2.py --price-only # 只更新实时价格
"""

import json
import os
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).parent
STANDARD_FILE = ROOT / "etf_standard_data.json"
HISTORY_DIR = ROOT / "data" / "history"

def log(msg):
    """日志输出"""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

def load_standard():
    """加载标准化数据"""
    with open(STANDARD_FILE, encoding='utf-8') as f:
        return json.load(f)

def save_standard(data):
    """保存标准化数据"""
    with open(STANDARD_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    log(f"保存标准化数据: {len(data)} 只")

def get_latest_trading_day():
    """获取最近一个交易日（避免节假日问题）"""
    # 简单策略：尝试最近5天
    for i in range(1, 6):
        date = datetime.now() - timedelta(days=i)
        # 简单判断：周一到周五
        if date.weekday() < 5:  # 0=周一, 4=周五
            return date
    return datetime.now() - timedelta(days=1)

def update_prices(etfs):
    """Step 1: 用AKShare获取最新实时价格"""
    try:
        import akshare as ak
        log("Step 1: 获取实时行情...")
        df = ak.fund_etf_spot_em()
        log(f"  AKShare返回 {len(df)} 只ETF行情")
        
        # 构建 code→行情 映射
        price_map = {}
        for _, row in df.iterrows():
            try:
                code = str(row['代码']).strip()
                close = float(row['最新价'])
                change_pct = float(row['涨跌幅'])
                prev_close = float(row['昨收'])
                volume = float(row['成交额'])
                
                price_map[code] = {
                    'close': close,
                    'change_pct': change_pct,
                    'prev_close': prev_close,
                    'volume': round(volume / 1e8, 2) if volume else 0,
                }
            except:
                pass
        
        # 更新ETF数据
        updated = 0
        for etf in etfs:
            code = etf['code']
            if code in price_map:
                pm = price_map[code]
                etf['close'] = pm['close']
                etf['change_pct'] = pm['change_pct']
                etf['prev_close'] = pm['prev_close']
                etf['volume'] = pm['volume']
                updated += 1
        
        log(f"  价格更新: {updated}/{len(etfs)} 只")
        return True
    except Exception as e:
        log(f"  ⚠️ AKShare价格获取失败: {e}")
        return False

def update_history_incremental(etfs):
    """Step 2: 增量更新历史K线（修复节假日问题）"""
    log("Step 2: 增量更新历史K线...")
    
    # 获取最近交易日
    latest_day = get_latest_trading_day()
    log(f"  最近交易日: {latest_day.strftime('%Y-%m-%d')}")
    
    updated = 0
    failed = 0
    
    for i, etf in enumerate(etfs):
        code = etf['code']
        history_file = HISTORY_DIR / f"{code}.json"
        
        try:
            # 读取已有历史
            if history_file.exists():
                with open(history_file, encoding='utf-8') as f:
                    history = json.load(f)
                dates = history.get('dates', [])
                prices = history.get('prices', [])
                
                # 增量更新：只获取最近7天（确保覆盖节假日）
                from_date = latest_day - timedelta(days=7)
                to_date = latest_day
            else:
                # 无缓存：全量获取3年
                from_date = datetime.now() - timedelta(days=1100)
                to_date = datetime.now()
                dates = []
                prices = []
            
            # 调用AKShare获取历史数据
            import akshare as ak
            df = ak.fund_etf_hist_em(
                symbol=str(code),
                period='daily',
                start_date=from_date.strftime('%Y%m%d'),
                end_date=to_date.strftime('%Y%m%d'),
                adjust='qfq'
            )
            
            if df is not None and len(df) > 0:
                new_dates = [str(d) for d in df['日期']]
                new_prices = [float(v) for v in df['收盘']]
                
                # 合并去重
                for d, p in zip(new_dates, new_prices):
                    if d not in dates:
                        dates.append(d)
                        prices.append(p)
                
                # 按日期排序
                sorted_data = sorted(zip(dates, prices), key=lambda x: x[0])
                dates = [d for d, p in sorted_data]
                prices = [p for d, p in sorted_data]
                
                # 保存
                history = {
                    'code': code,
                    'dates': dates,
                    'prices': prices,
                    'count': len(prices),
                    'updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
                history_file.parent.mkdir(parents=True, exist_ok=True)
                with open(history_file, 'w', encoding='utf-8') as f:
                    json.dump(history, f, ensure_ascii=False)
                
                updated += 1
            else:
                failed += 1
            
        except Exception as e:
            failed += 1
            
        if (i + 1) % 100 == 0:
            log(f"  进度: {i+1}/{len(etfs)} 成功={updated} 失败={failed}")
        
        time.sleep(0.2)
    
    log(f"  完成: 成功={updated} 失败={failed}")
    return updated, failed

def git_commit_push():
    """Step 3: Git提交推送"""
    log("Step 3: Git提交...")
    try:
        subprocess.run(["git", "add", "-A"], cwd=ROOT, check=True, capture_output=True)
        result = subprocess.run(
            ["git", "commit", "-m", f"daily: {datetime.now().strftime('%Y-%m-%d')}数据更新"],
            cwd=ROOT, capture_output=True, text=True
        )
        if result.returncode == 0 or "nothing to commit" in result.stdout.lower():
            push = subprocess.run(["git", "push", "origin", "main"], 
                                  cwd=ROOT, capture_output=True, text=True)
            if push.returncode == 0:
                log("  ✅ Git push 成功")
                return True
        log(f"  Git状态: {result.stdout[:200]}")
    except Exception as e:
        log(f"  ⚠️ Git操作失败: {e}")
    return False

def main():
    import argparse
    parser = argparse.ArgumentParser(description="ETF数据每日更新 v2")
    parser.add_argument("--push", action="store_true", help="更新后自动git push")
    parser.add_argument("--price-only", action="store_true", help="只更新实时价格")
    args = parser.parse_args()
    
    log("=" * 50)
    log("ETF数据每日更新 v2")
    log("=" * 50)
    
    # 加载现有数据
    etfs = load_standard()
    log(f"加载标准化数据: {len(etfs)} 只")
    
    # Step 1: 更新价格
    update_prices(etfs)
    
    if not args.price_only:
        # Step 2: 增量更新历史K线
        update_history_incremental(etfs)
    
    # 保存标准化数据
    save_standard(etfs)
    
    # Step 3: Git push（可选）
    if args.push:
        git_commit_push()
    
    log("=" * 50)
    log("更新完成")
    log("=" * 50)
    
    # 统计
    has_price = sum(1 for e in etfs if e.get('close', 0) > 0)
    log(f"价格覆盖: {has_price}/{len(etfs)}")

if __name__ == "__main__":
    main()
