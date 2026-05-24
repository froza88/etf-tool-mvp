#!/usr/bin/env python3
"""Phase1: WeStock 批量拉取 ETF 详情，写入 etf_standard_data_filled.json"""
import json, subprocess, re, sys, os, time
from pathlib import Path
from datetime import datetime

DATA_FILE = Path(__file__).parent / "etf_standard_data_filled.json"
PROGRESS_FILE = Path(__file__).parent / "data" / "enrich_westock_progress.json"

NODE_PATH = os.path.expanduser("~/.workbuddy/binaries/node/workspace/node_modules")
WESTOCK_CLI = os.path.expanduser("~/.workbuddy/binaries/node/versions/22.12.0/bin/node")
WESTOCK_SCRIPT = os.path.expanduser(
    "~/.workbuddy/plugins/marketplaces/cb_teams_marketplace/plugins/finance-data/skills/westock-data/scripts/index.js"
)

# WeStock etf 命令返回的字段 → JSON 字段名
WESTOCK_FIELD_MAP = {
    "nav": "nav",
    "return1M": "return_1m",
    "return3M": "return_3m",
    "return6M": "return_6m",
    "ytdReturn": "ytd_return",
    "ytdMaxDrawdown": "ytd_max_drawdown",
    "maxDrawdown1M": "max_drawdown_1m",
    "maxDrawdown3M": "max_drawdown_3m",
    "maxDrawdown1Y": "max_drawdown_1y",
    "maxDrawdown3Y": "max_drawdown_3y",
    "stockRatio": "stock_ratio",
    "bondRatio": "bond_ratio",
    "fundRatio": "fund_ratio",
    "commodityRatio": "commodity_ratio",
    "individualHolderRatio": "individual_holder_ratio",
    "institutionHolderRatio": "institution_holder_ratio",
    "holderAccount": "holder_account",
    "turnoverRate": "turnover_rate",
    "totalMV": "total_mv",
    "subscriptionFee": "subscription_fee",
    "isTPlus0": "is_t_plus_0",
    "discountRatioCurve": "discount_ratio_curve",
    "avgDiscountRatioCurve": "avg_discount_curve",
    "establishDate": "listing_date",
}
NUMERIC_FIELDS = {
    "nav", "return1M", "return3M", "return6M", "ytdReturn",
    "ytdMaxDrawdown", "maxDrawdown1M", "maxDrawdown3M", "maxDrawdown1Y", "maxDrawdown3Y",
    "stockRatio", "bondRatio", "fundRatio", "commodityRatio",
    "individualHolderRatio", "institutionHolderRatio", "holderAccount",
    "turnoverRate", "totalMV", "subscriptionFee",
}

def code_to_westock(code):
    code = str(code).strip()
    if code[0] == "5": return f"sh{code}"
    elif code[0] in "0123": return f"sz{code}"
    return f"sh{code}"

def parse_etf_table(text):
    results = {}
    lines = text.split("\n")
    header_idx = -1
    for i, line in enumerate(lines):
        if "| code " in line and ("| name " in line or "| 名称 " in line):
            header_idx = i
            break
    if header_idx < 0:
        return results
    headers = [h.strip() for h in lines[header_idx].split("|")[1:-1]]
    for i in range(header_idx + 2, len(lines)):
        line = lines[i].strip()
        if not line.startswith("|") or "---" in line or "**" in line:
            continue
        parts = [p.strip() for p in line.split("|")[1:-1]]
        if len(parts) < 2:
            continue
        wscode = parts[0]
        if not wscode.startswith(("sh", "sz", "bj")):
            continue
        row = {}
        for j, h in enumerate(headers):
            if j < len(parts):
                row[h] = parts[j]
        pure_code = re.sub(r'^(sh|sz|bj)', '', wscode)
        results[pure_code] = row
    return results

def to_num(val):
    if val is None or val == "" or val == "�" or val == "是":
        return None
    try:
        return float(str(val).replace("%", "").replace(",", "").strip())
    except (ValueError, TypeError):
        return None

def load_progress():
    if PROGRESS_FILE.exists():
        with open(PROGRESS_FILE) as f:
            return json.load(f)
    return {"done": []}

def save_progress(p):
    with open(PROGRESS_FILE, "w") as f:
        json.dump(p, f)

def save_data(etfs):
    data = {"etfs": etfs, "updated": datetime.now().isoformat()}
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"  💾 已保存 {len(etfs)} 只 ETF 到 {DATA_FILE.name}")

# ── 主逻辑 ────────────────────────────────────────────────────────────────────

with open(DATA_FILE) as f:
    raw = json.load(f)
all_etfs = raw["etfs"]
total = len(all_etfs)
print(f"ETF 总数: {total}")

progress = load_progress()
done = set(progress.get("done", []))
remaining = [e for e in all_etfs if e["code"] not in done]
print(f"已处理: {len(done)}, 剩余: {len(remaining)}")

if not remaining:
    print("✅ Phase1 已完成，跳过")
    sys.exit(0)

BATCH = 20
enriched = 0

for i in range(0, len(remaining), BATCH):
    batch = remaining[i:i+BATCH]
    ws_codes = [code_to_westock(e["code"]) for e in batch]

    cmd = f"cd {Path(WESTOCK_SCRIPT).parent} && NODE_PATH={NODE_PATH} {WESTOCK_CLI} {WESTOCK_SCRIPT} etf {','.join(ws_codes)}"
    try:
        proc = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=90)
        output = proc.stdout or proc.stderr
    except Exception as e:
        print(f"  ⚠️  批次查询失败: {e}")
        output = ""

    rows = parse_etf_table(output)
    for etf in batch:
        code = etf["code"]
        if code in rows:
            row = rows[code]
            for ws_field, json_field in WESTOCK_FIELD_MAP.items():
                val = row.get(ws_field)
                if ws_field in NUMERIC_FIELDS:
                    etf[json_field] = to_num(val)
                else:
                    etf[json_field] = val if val and val != "�" else None
            enriched += 1
        progress["done"].append(code)

    # 每 100 只保存一次 + 最后一批保存
    if (i + BATCH) % 100 == 0 or i + BATCH >= len(remaining):
        save_progress(progress)
        save_data(all_etfs)

    pct = min(i + BATCH, len(remaining)) / len(remaining) * 100
    print(f"  [{min(i+BATCH, len(remaining))}/{len(remaining)}] enriched: {enriched} ({pct:.0f}%)", end="\r")

print(f"\n✅ Phase1 完成！共补充 {enriched} 只 ETF 的 WeStock 数据")
save_data(all_etfs)
print("🎉 全部保存完毕")
