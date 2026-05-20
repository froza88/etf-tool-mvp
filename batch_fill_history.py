#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量填充ETF历史K线到 data/history/{code}.json

数据源：非凸科技 market.ft.tech (etf-ohlcs API)
策略：按规模排序，从大到小填充

用法：
  python3 batch_fill_history.py                    # 填充 Top 200
  python3 batch_fill_history.py --limit 50          # 只填 Top 50
  python3 batch_fill_history.py --all               # 全部填充
  python3 batch_fill_history.py --dry-run           # 只展示，不执行
"""

import json
import os
import sys
import time
import subprocess
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).parent
STANDARD_FILE = ROOT / "etf_standard_data.json"
HISTORY_DIR = ROOT / "data" / "history"
FT_RUN_PY = Path(os.path.expanduser("~")) / ".workbuddy" / "skills" / "ftshare-market-data" / "run.py"

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


def get_ohlcs(etf_market, limit=500):
    """调用非凸 OHLC API 获取ETF历史K线"""
    cmd = [
        sys.executable, str(FT_RUN_PY),
        "etf-ohlcs",
        "--etf", etf_market,
        "--span", "DAY1",
        "--limit", str(limit),
    ]
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


def main():
    # 解析参数
    args = [a for a in sys.argv[1:] if not a.startswith("--")]

    dry_run = "--dry-run" in sys.argv
    fill_all = "--all" in sys.argv
    limit = None

    for a in sys.argv[1:]:
        if a.startswith("--limit="):
            limit = int(a.split("=")[1])
        elif a.startswith("--limit"):
            pass  # handled below

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
    if limit:
        print(f"📋 本次计划填充: Top {limit} (按规模)")
    print()

    if dry_run:
        print("🏃 Dry-run 模式 — 仅展示待处理ETF:")
        for i, etf in enumerate(pending[:20], 1):
            print(f"  {i:3d}. {etf['code']} {etf.get('name',''):20s} 规模: {etf.get('scale', 0):>8.1f}亿")
        if len(pending) > 20:
            print(f"      ... 还有 {len(pending)-20} 只")
        print(f"\n跳过 {existing} 已存在")
        return

    # 开始填充
    ok = fail = skipped = 0
    start_time = time.time()

    for i, etf in enumerate(pending, 1):
        code = etf["code"]
        name = etf.get("name", "")
        scale = etf.get("scale", 0)

        try:
            etf_market = code_to_market(code)
            api_data = get_ohlcs(etf_market)

            ohlcs = api_data.get("ohlcs", [])
            if not ohlcs:
                print(f"  [{i:3d}/{total}] {code} {name[:20]:20s} ⚠️  无K线数据")
                skipped += 1
                continue

            count = save_history(code, ohlcs)
            elapsed = time.time() - start_time
            remain = (elapsed / i) * (total - i) if i > 0 else 0
            print(f"  [{i:3d}/{total}] {code} {name[:20]:20s} ✅ {count:4d}条 / 规模{scale:.1f}亿 "
                  f"| 已用{elapsed/60:.1f}分 预计剩余{remain/60:.1f}分")
            ok += 1

        except Exception as e:
            print(f"  [{i:3d}/{total}] {code} {name[:20]:20s} ❌ {e}")
            fail += 1

        # 限速：每批暂停1.5秒
        if i < total:
            time.sleep(1.5)

    # 总报告
    total_elapsed = time.time() - start_time
    print(f"\n{'='*50}")
    print(f"填充完成!")
    print(f"  ✅ 成功: {ok} 只")
    print(f"  ⚠️  跳过: {skipped} 只（无K线）")
    print(f"  ❌ 失败: {fail} 只")
    print(f"  ⏱  耗时: {total_elapsed/60:.1f} 分钟")
    print(f"  📂 位置: data/history/")
    print(f"{'='*50}")


if __name__ == "__main__":
    main()
