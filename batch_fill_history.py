#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量填充ETF历史K线到 data/history/{code}.json

数据源：非凸科技 market.ft.tech (etf-ohlcs API)
策略：按规模排序，从大到小填充，支持并行执行

用法：
  python3 batch_fill_history.py                    # 填充 Top 200（并行）
  python3 batch_fill_history.py --limit 50          # 只填 Top 50
  python3 batch_fill_history.py --all               # 全部填充
  python3 batch_fill_history.py --dry-run           # 只展示，不执行
  python3 batch_fill_history.py --workers 10        # 并行度 10（默认 20）
  python3 batch_fill_history.py --resume            # 从进度恢复
"""

import json
import os
import sys
import time
import subprocess
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Semaphore

ROOT = Path(__file__).parent
STANDARD_FILE = ROOT / "etf_standard_data.json"
HISTORY_DIR = ROOT / "data" / "history"
PROGRESS_FILE = ROOT / "data" / "history_progress.json"
FAILED_FILE = ROOT / "data" / "failed_etfs.json"
FT_RUN_PY = Path(os.path.expanduser("~")) / ".workbuddy" / "skills" / "ftshare-market-data" / "run.py"

# API限流保护：最多10个并发请求（防止被非凸封禁）
RATE_LIMITER = Semaphore(10)
# 重试配置
MAX_RETRIES = 3
RETRY_DELAY_BASE = 2  # 指数退避基数（秒）

# 市场后缀映射
MARKET_SUFFIX = {
    "6": "XSHG",   # 沪市60xxxx
    "0": "XSHE",   # 深市00xxxx
    "1": "XSHE",   # 深市10xxxx
    "2": "XSHE",   # 深市20xxxx
    "3": "XSHE",   # 深市30xxxx
    "5": "XSHG",   # 沪市51xxxx (ETF)
    "9": "XSHG",   # 沪市9xxxxx
    "8": "BJ",     # 北交所
    "4": "BJ",     # 北交所
}


def code_to_market(code):
    """ETF代码 → 市场后缀"""
    code = str(code).strip()
    prefix = code[0] if code else ""
    suffix = MARKET_SUFFIX.get(prefix, "XSHG")
    return f"{code}.{suffix}"


def get_ohlcs(etf_market, limit=None):
    """调用非凸 OHLC API 获取ETF历史K线，不传limit则返回全部历史"""
    cmd = [
        sys.executable, str(FT_RUN_PY),
        "etf-ohlcs",
        "--etf", etf_market,
        "--span", "DAY1",
    ]
    if limit is not None:
        cmd.extend(["--limit", str(limit)])
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    if result.returncode != 0:
        raise RuntimeError(f"API调用失败: {result.stderr[:200]}")
    return json.loads(result.stdout)


def save_history(code, ohlcs):
    """保存OHLC数据到 data/history/{code}.json"""
    history_file = HISTORY_DIR / f"{code}.json"

    prices = [o["c"] for o in ohlcs]
    dates = []
    for o in ohlcs:
        # otm 格式: "2026-05-14T00:00:00" → "2026-05-14"
        d = o["otm"][:10]
        dates.append(d)

    history_data = {
        "code": code,
        "prices": prices,
        "dates": dates,
        "count": len(prices),
        "ohlcs": ohlcs,  # 完整OHLC数据
        "source": "westock_ft",
        "updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }

    history_file.parent.mkdir(parents=True, exist_ok=True)
    with open(history_file, "w", encoding="utf-8") as f:
        json.dump(history_data, f, ensure_ascii=False)

    return len(prices)


def load_progress():
    """加载进度（已完成的ETF代码集合）"""
    if PROGRESS_FILE.exists():
        with open(PROGRESS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return set(data.get("completed", []))
    return set()


def save_progress(completed):
    """保存进度到文件"""
    PROGRESS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
        json.dump({
            "completed": sorted(list(completed)),
            "updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }, f, ensure_ascii=False)


def load_failed():
    """加载失败列表"""
    if FAILED_FILE.exists():
        with open(FAILED_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def save_failed(failed):
    """保存失败列表"""
    FAILED_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(FAILED_FILE, "w", encoding="utf-8") as f:
        json.dump(failed, f, ensure_ascii=False, indent=2)


def fetch_one_etf(etf_info):
    """
    获取单只ETF历史数据并保存（含限流保护和重试）
    
    Args:
        etf_info: dict with 'code', 'name', 'scale'
    
    Returns:
        (code, success, error_msg, count)
    """
    code = etf_info["code"]
    name = etf_info.get("name", "")
    
    # 重试循环（指数退避）
    for attempt in range(MAX_RETRIES):
        try:
            # 限流保护：获取信号量（最多10个并发）
            with RATE_LIMITER:
                etf_market = code_to_market(code)
                api_data = get_ohlcs(etf_market)
            
            # 稍微休眠， Spread 请求（防止瞬时 burst）
            time.sleep(0.05)
            
            ohlcs = api_data.get("ohlcs", [])
            if not ohlcs:
                return (code, False, "无K线数据", 0)
            
            count = save_history(code, ohlcs)
            return (code, True, None, count)
            
        except Exception as e:
            error = str(e)
            # 如果是最后一次重试，返回失败；否则继续重试
            if attempt == MAX_RETRIES - 1:
                return (code, False, error, 0)
            # 指数退避等待：2s, 4s, 8s...
            delay = RETRY_DELAY_BASE ** (attempt + 1)
            time.sleep(min(delay, 30))  # 最多等30秒
    
    # 理论上不会到这里
    return (code, False, "重试次数用尽", 0)


def main():
    # 解析参数
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    
    dry_run = "--dry-run" in sys.argv
    fill_all = "--all" in sys.argv
    resume = "--resume" in sys.argv
    limit = None
    
    # 解析 --workers 和 --limit 参数
    max_workers = 20  # 默认并行度
    i = 1
    while i < len(sys.argv):
        a = sys.argv[i]
        if a.startswith("--workers="):
            max_workers = int(a.split("=")[1])
        elif a == "--workers" and i + 1 < len(sys.argv):
            max_workers = int(sys.argv[i + 1])
            i += 1
        elif a.startswith("--limit="):
            limit = int(a.split("=")[1])
        elif a == "--limit" and i + 1 < len(sys.argv):
            limit = int(sys.argv[i + 1])
            i += 1
        i += 1
    
    if limit is None and not fill_all:
        limit = 200  # 默认 Top 200
    
    # 加载标准数据
    with open(STANDARD_FILE, "r", encoding="utf-8") as f:
        etfs = json.load(f)
    
    # 按规模降序排列
    etfs_sorted = sorted(etfs, key=lambda x: x.get("scale", 0) or 0, reverse=True)
    
    # 过滤已有历史
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    existing = set(f.stem for f in HISTORY_DIR.glob("*.json"))
    
    # 如果恢复模式，加载进度
    completed = load_progress() if resume else set()
    if resume:
        print(f"📂 恢复模式：已加载 {len(completed)} 只已完成ETF")
        # 从 existing 和 completed 中移除已完成的
        existing = existing.union(completed)
    
    pending = []
    for etf in etfs_sorted:
        if etf["code"] not in existing:
            pending.append(etf)
    
    # 限制数量
    if limit:
        pending = pending[:limit]
    
    total = len(pending)
    if total == 0:
        print("✅ 所有ETF已有历史数据，无需填充")
        return
    
    print(f"📊 ETF总数: {len(etfs)}, 已有历史: {len(existing)}, 待填充: {total}")
    print(f"🚀 并行度: {max_workers} 线程")
    if limit:
        print(f"📋 本次计划填充: Top {limit} (按规模)")
    if resume:
        print(f"🔄 恢复模式：将从进度恢复")
    print()
    
    if dry_run:
        print("🏃 Dry-run 模式 — 仅展示待处理ETF:")
        for i, etf in enumerate(pending[:20], 1):
            print(f"  {i:3d}. {etf['code']} {etf.get('name',''):20s} 规模: {etf.get('scale', 0):>8.1f}亿")
        if len(pending) > 20:
            print(f"      ... 还有 {len(pending)-20} 只")
        return
    
    # 开始填充（并行）
    ok = fail = skipped = 0
    failed_list = load_failed()
    start_time = time.time()
    
    print(f"🚀 开始并行填充（{max_workers} 线程）...")
    print(f"{'='*60}")
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # 提交所有任务
        future_to_etf = {
            executor.submit(fetch_one_etf, etf): etf
            for etf in pending
        }
        
        # 处理完成的任务
        for i, future in enumerate(as_completed(future_to_etf), 1):
            etf = future_to_etf[future]
            code = etf["code"]
            name = etf.get("name", "")
            scale = etf.get("scale", 0)
            
            try:
                result_code, success, error, count = future.result(timeout=30)
                
                if success:
                    ok += 1
                    completed.add(result_code)
                    elapsed = time.time() - start_time
                    remain = (elapsed / i) * (total - i) if i > 0 else 0
                    print(f"  [{i:3d}/{total}] {code} {name[:20]:20s} ✅ {count:4d}条 | "
                          f"已用{elapsed/60:.1f}分 预计剩余{remain/60:.1f}分")
                else:
                    if error == "无K线数据":
                        skipped += 1
                        print(f"  [{i:3d}/{total}] {code} {name[:20]:20s} ⚠️  无K线数据")
                    else:
                        fail += 1
                        failed_list.append({"code": code, "name": name, "error": error})
                        print(f"  [{i:3d}/{total}] {code} {name[:20]:20s} ❌ {error[:50]}")
                
                # 每完成10只保存一次进度
                if i % 10 == 0:
                    save_progress(completed)
                    if failed_list:
                        save_failed(failed_list)
                        
            except concurrent.futures.TimeoutError:
                fail += 1
                failed_list.append({"code": code, "name": name, "error": "超时(30s)"})
                print(f"  [{i:3d}/{total}] {code} {name[:20]:20s} ❌ 超时")
            except Exception as e:
                fail += 1
                failed_list.append({"code": code, "name": name, "error": str(e)})
                print(f"  [{i:3d}/{total}] {code} {name[:20]:20s} ❌ {e}")
    
    # 最终保存进度
    save_progress(completed)
    if failed_list:
        save_failed(failed_list)
    
    # 总报告
    total_elapsed = time.time() - start_time
    print(f"\n{'='*60}")
    print(f"填充完成!")
    print(f"  ✅ 成功: {ok} 只")
    print(f"  ⚠️  跳过: {skipped} 只（无K线）")
    print(f"  ❌ 失败: {fail} 只")
    print(f"  ⏱️  耗时: {total_elapsed/60:.1f} 分钟")
    print(f"  📂 位置: data/history/")
    print(f"  📊 进度: data/history_progress.json")
    if failed_list:
        print(f"  ❌ 失败列表: data/failed_etfs.json")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
