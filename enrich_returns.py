#!/usr/bin/env python3
"""
并行脚本A：仅获取收益率（非凸科技 etf-detail API）
逐步保存，不依赖其他步骤
"""
import sys, os, json, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from modules.data_source import FTSource

ROOT = os.path.dirname(os.path.abspath(__file__))
FULL_FILE = os.path.join(ROOT, "etf_complete_all.json")
OUTPUT_FILE = os.path.join(ROOT, "etf_temp_returns.json")
LOG_FILE = os.path.join(ROOT, "enrich_returns.log")

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
    log("=== 并行A: 获取收益率（非凸etf-detail） ===", lf)

    # 加载ETF列表
    with open(FULL_FILE, "r", encoding="utf-8") as f:
        full_data = json.load(f)
    log(f"ETF总数: {len(full_data)}", lf)

    ft_source = FTSource()
    results = {}
    success = fail = 0

    for i, etf in enumerate(full_data):
        code = str(etf["code"])
        exch = get_exchange(code)
        try:
            detail = ft_source.get_etf_detail(code, exch)
            if detail and detail.get("return_1y") is not None:
                results[code] = {
                    "year_1_return": round(detail["return_1y"] * 100, 1),
                    "year_3_return": round((detail.get("return_3y") or 0) * 100, 1),
                }
                success += 1
            else:
                results[code] = None
                fail += 1
        except Exception:
            results[code] = None
            fail += 1

        if (i + 1) % 100 == 0:
            # 每100条保存一次（增量保存）
            existing = {}
            if os.path.exists(OUTPUT_FILE):
                with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
                    existing = json.load(f)
            existing.update(results)
            with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
                json.dump(existing, f, ensure_ascii=False)
            log(f"进度: {i+1}/{len(full_data)}  成功={success} 失败={fail}  已保存", lf)

        time.sleep(0.2)

    # 最终保存
    existing = {}
    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
            existing = json.load(f)
    existing.update(results)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(existing, f, ensure_ascii=False)

    log(f"完成! 成功={success} 失败={fail} 保存到 {OUTPUT_FILE}", lf)
