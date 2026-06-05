#!/usr/bin/env python3
"""
升级 history/*.json 文件格式：补日期维度（并行版）
旧格式: {"code": "518880", "prices": [...]}
新格式: {"code": "518880", "prices": [...], "dates": [...], "updated": "..."}
"""
import json
import subprocess
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

ROOT = Path("/Users/apangduo/WorkBuddy/Claw/etf-tool-mvp")
HISTORY_DIR = ROOT / "data" / "history"
RUN_PY = "/usr/bin/python3"
SKILL_SCRIPT = str(Path.home() / ".workbuddy/skills/ftshare-market-data/run.py")

MAX_WORKERS = 5
RATE_LIMIT = threading.Semaphore(MAX_WORKERS)

def fetch_ohlc(code):
    """从非凸API获取带日期的K线"""
    exch = "XSHG" if str(code).startswith("5") else "XSHE"
    symbol = f"{code}.{exch}"
    
    cmd = [RUN_PY, SKILL_SCRIPT, "etf-ohlcs", "--etf", symbol, "--span", "DAY1", "--limit", "1260"]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode != 0:
            return None, f"exit_code={result.returncode}"
        data = json.loads(result.stdout)
        ohlcs = data.get("ohlcs", [])
        if not ohlcs:
            return None, "empty_ohlcs"
        dates = [bar["otm"][:10] for bar in ohlcs]
        prices = [float(bar["c"]) for bar in ohlcs]
        return {"dates": dates, "prices": prices, "count": len(ohlcs)}, None
    except subprocess.TimeoutExpired:
        return None, "timeout"
    except Exception as e:
        return None, str(e)[:100]

def upgrade_one(code):
    """升级单个history文件"""
    filepath = HISTORY_DIR / f"{code}.json"
    if not filepath.exists():
        return {"code": code, "status": "no_file"}
    
    try:
        with open(filepath) as f:
            old = json.load(f)
    except:
        return {"code": code, "status": "bad_json"}
    
    old_prices = old.get("prices", [])
    if len(old_prices) < 30:
        return {"code": code, "status": "too_few", "old_count": len(old_prices)}
    
    fetched, error = fetch_ohlc(code)
    
    if fetched:
        new_data = {
            "code": code,
            "prices": fetched["prices"],
            "dates": fetched["dates"],
            "count": fetched["count"],
            "updated": time.strftime("%Y-%m-%d %H:%M:%S"),
            "source": "ft_api"
        }
        with open(filepath, "w") as f:
            json.dump(new_data, f, ensure_ascii=False)
        return {"code": code, "status": "ok", "old_count": len(old_prices), "new_count": fetched["count"]}
    else:
        return {"code": code, "status": "api_error", "error": error, "old_count": len(old_prices)}

def main():
    codes = sorted([f.stem for f in HISTORY_DIR.glob("*.json")])
    total = len(codes)
    print(f"共 {total} 个文件，{MAX_WORKERS}路并行\n")
    
    results = []
    ok = fail = skip = 0
    lock = threading.Lock()
    start_time = time.time()
    
    def track(future, code):
        nonlocal ok, fail, skip
        try:
            r = future.result()
            results.append(r)
            with lock:
                n = len(results)
                elapsed = time.time() - start_time
                eta = (elapsed / n) * (total - n) if n > 0 else 0
                if r["status"] == "ok":
                    ok += 1
                    print(f"[{n}/{total}] {code} ✅ {r['old_count']}→{r.get('new_count','?')}条 | {elapsed:.0f}s ETA {eta:.0f}s")
                elif r["status"] == "too_few":
                    skip += 1
                    print(f"[{n}/{total}] {code} ⏭️ 不足30条")
                else:
                    fail += 1
                    print(f"[{n}/{total}] {code} ❌ {r.get('error', r['status'])}")
        except Exception as e:
            with lock:
                fail += 1
                print(f"[{len(results)}/{total}] {code} ❌ {e}")
    
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {}
        for code in codes:
            f = executor.submit(upgrade_one, code)
            futures[f] = code
        
        for future in as_completed(futures):
            track(future, futures[future])
    
    elapsed = time.time() - start_time
    print(f"\n{'='*60}")
    print(f"完成: {ok} 成功 | {skip} 跳过 | {fail} 失败 | 耗时 {elapsed:.0f}s")
    
    # 保存报告
    report_path = ROOT / "data" / "history_upgrade_report.json"
    with open(report_path, "w") as f:
        json.dump({
            "time": time.strftime("%Y-%m-%d %H:%M:%S"),
            "total": total, "ok": ok, "skip": skip, "fail": fail,
            "elapsed_seconds": round(elapsed),
            "results": results
        }, f, ensure_ascii=False, indent=2)
    print(f"报告: {report_path}")

if __name__ == "__main__":
    main()
