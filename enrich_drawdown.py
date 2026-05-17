#!/usr/bin/env python3
"""
并行脚本B v2：仅计算回撤/夏普
数据源改用 非凸科技 etf-ohlcs API（AKShare SSL 在macOS上有兼容问题）
逐步增量保存，不依赖其他步骤
"""
import sys, os, json, time, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from modules.data_source import FTSource
from modules.metrics import calc_max_drawdown, calc_sharpe_ratio

ROOT = os.path.dirname(os.path.abspath(__file__))
FULL_FILE = os.path.join(ROOT, "etf_complete_all.json")
OUTPUT_FILE = os.path.join(ROOT, "etf_temp_metrics.json")
LOG_FILE = os.path.join(ROOT, "enrich_drawdown.log")

def log(msg, f=None):
    ts = time.strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    if f:
        f.write(line + "\n")
        f.flush()

def get_exchange(code):
    c = str(code)
    return 'XSHG' if c.startswith('5') else 'XSHE'

with open(LOG_FILE, "w", encoding="utf-8") as lf:
    log("=== 并行Bv2: 回撤/夏普（非凸etf-ohlcs 150日K线） ===", lf)

    with open(FULL_FILE, "r", encoding="utf-8") as f:
        full_data = json.load(f)
    log(f"ETF总数: {len(full_data)}", lf)

    ft_source = FTSource()
    results = {}
    calc_ok = 0
    calc_fail = 0

    for i, etf in enumerate(full_data):
        code = str(etf["code"])
        exch = get_exchange(code)
        try:
            ohlc = ft_source.get_etf_ohlcs(code, exch, limit=150)
            if ohlc and len(ohlc.get("prices", [])) >= 30:
                prices = ohlc["prices"]
                results[code] = {
                    "max_drawdown": round(calc_max_drawdown(prices), 1),
                    "sharpe_ratio": round(calc_sharpe_ratio(prices), 2),
                }
                calc_ok += 1
            else:
                if ohlc:
                    log(f"  {code}: OHLC数据不足({len(ohlc.get('prices',[]))}条)", lf)
                results[code] = {"max_drawdown": 0, "sharpe_ratio": 0}
                calc_fail += 1
        except Exception as e:
            results[code] = {"max_drawdown": 0, "sharpe_ratio": 0}
            calc_fail += 1
            if (i + 1) % 100 == 0:
                log(f"  {code} Error: {type(e).__name__}", lf)

        if (i + 1) % 100 == 0:
            existing = {}
            if os.path.exists(OUTPUT_FILE):
                with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
                    existing = json.load(f)
            existing.update(results)
            with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
                json.dump(existing, f, ensure_ascii=False)
            log(f"进度: {i+1}/{len(full_data)}  已计算={calc_ok} 无效={calc_fail}  已保存", lf)

        time.sleep(0.15)

    # 最终保存
    existing = {}
    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
            existing = json.load(f)
    existing.update(results)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(existing, f, ensure_ascii=False)

    log(f"完成! 已计算={calc_ok} 无效={calc_fail} 保存到 {OUTPUT_FILE}", lf)
