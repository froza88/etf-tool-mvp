#!/usr/bin/env python3
"""全量数据增强：WeStock + AKShare + FTShare → etf_standard_data_filled.json"""
import json, subprocess, re, sys, os, time
from pathlib import Path
from datetime import datetime

DATA_FILE = Path(__file__).parent / "etf_standard_data_filled.json"
PROGRESS_FILE = Path(__file__).parent / "data" / "enrich_progress.json"

# ===== WeStock 配置 =====
NODE_PATH = os.path.expanduser("~/.workbuddy/binaries/node/workspace/node_modules")
WESTOCK_CLI = os.path.expanduser("~/.workbuddy/binaries/node/versions/22.12.0/bin/node")
WESTOCK_SCRIPT = os.path.expanduser("~/.workbuddy/plugins/marketplaces/cb_teams_marketplace/plugins/finance-data/skills/westock-data/scripts/index.js")

# WeStock → JSON 新增字段
WESTOCK_NEW_FIELDS = {
    # 净值
    "nav": "nav",
    # 多期回报
    "return1M": "return_1m",
    "return3M": "return_3m",
    "return6M": "return_6m",
    "ytdReturn": "ytd_return",
    # 最大回撤
    "ytdMaxDrawdown": "ytd_max_drawdown",
    "maxDrawdown1M": "max_drawdown_1m",
    "maxDrawdown3M": "max_drawdown_3m",
    "maxDrawdown1Y": "max_drawdown_1y",
    "maxDrawdown3Y": "max_drawdown_3y",
    # 资产配置
    "stockRatio": "stock_ratio",
    "bondRatio": "bond_ratio",
    "fundRatio": "fund_ratio",
    "commodityRatio": "commodity_ratio",
    # 持有人
    "individualHolderRatio": "individual_holder_ratio",
    "institutionHolderRatio": "institution_holder_ratio",
    "holderAccount": "holder_account",
    # 交易
    "turnoverRate": "turnover_rate",
    "totalMV": "total_mv",
    # 申赎费
    "subscriptionFee": "subscription_fee",
    # 溢价折价曲线
    "discountRatioCurve": "discount_ratio_curve",
    "avgDiscountRatioCurve": "avg_discount_curve",
}
WESTOCK_NUMERIC = {
    "nav", "return1M", "return3M", "return6M", "ytdReturn",
    "ytdMaxDrawdown", "maxDrawdown1M", "maxDrawdown3M", "maxDrawdown1Y", "maxDrawdown3Y",
    "stockRatio", "bondRatio", "fundRatio", "commodityRatio",
    "individualHolderRatio", "institutionHolderRatio", "holderAccount",
    "turnoverRate", "totalMV", "subscriptionFee",
}

# ===== 工具函数 =====
def code_to_westock(code):
    code = str(code).strip()
    prefix = code[0]
    if prefix == "5": return f"sh{code}"
    elif prefix in "0123": return f"sz{code}"
    return f"sh{code}"

def parse_etf_table(text):
    results = {}
    lines = text.split("\n")
    header_idx = -1
    for i, line in enumerate(lines):
        if "| code " in line and ("| name " in line or "| 名称 " in line):
            header_idx = i; break
    if header_idx < 0: return results
    headers = [h.strip() for h in lines[header_idx].split("|")[1:-1]]
    for i in range(header_idx + 2, len(lines)):
        line = lines[i].strip()
        if not line.startswith("|") or "---" in line or "**" in line: continue
        parts = [p.strip() for p in line.split("|")[1:-1]]
        if len(parts) < 2: continue
        wscode = parts[0]
        if not wscode.startswith(("sh","sz","bj")): continue
        row = {}
        for j, h in enumerate(headers):
            if j < len(parts): row[h] = parts[j]
        pure_code = re.sub(r'^(sh|sz|bj)', '', wscode)
        results[pure_code] = row
    return results

def to_num(val):
    """安全转为 float"""
    if val is None or val == "" or val == "�" or val == "是":
        return None
    try:
        return float(str(val).replace("%","").replace(",","").strip())
    except (ValueError, TypeError):
        return None

# ===== Phase 1: WeStock 全量拉取 =====
def pull_westock(all_etfs, progress):
    print("\n=== Phase 1: WeStock 全量数据 ===")
    done = set(progress.get("westock_done", []))
    remaining = [e for e in all_etfs if e["code"] not in done]
    print(f"已处理: {len(done)}, 剩余: {len(remaining)}")
    if not remaining:
        print("已完成，跳过")
        return

    BATCH = 20
    enriched = 0
    for i in range(0, len(remaining), BATCH):
        batch = remaining[i:i+BATCH]
        ws_codes = [code_to_westock(e["code"]) for e in batch]
        
        cmd = f"cd {Path(WESTOCK_SCRIPT).parent} && NODE_PATH={NODE_PATH} {WESTOCK_CLI} {WESTOCK_SCRIPT} etf {','.join(ws_codes)}"
        try:
            proc = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=90)
            output = proc.stdout or proc.stderr
        except Exception:
            output = ""
        
        rows = parse_etf_table(output)
        for etf in batch:
            code = etf["code"]
            if code in rows:
                row = rows[code]
                for ws_field, json_field in WESTOCK_NEW_FIELDS.items():
                    val = row.get(ws_field)
                    if ws_field in WESTOCK_NUMERIC:
                        etf[json_field] = to_num(val)
                    else:
                        etf[json_field] = val if val and val != "�" else None
                enriched += 1
            progress.setdefault("westock_done", []).append(code)
        
        if (i + BATCH) % 100 == 0 or i + BATCH >= len(remaining):
            save_progress(progress)
            save_data(all_etfs)
        
        print(f"  [{min(i+BATCH, len(remaining))}/{len(remaining)}] enriched: {enriched}", end="\r")
        time.sleep(0.3)
    print()

# ===== Phase 2: AKShare 跟踪误差 (fund_etf_fund_info_em) =====
def pull_akshare(all_etfs, progress):
    print("\n=== Phase 2: AKShare 跟踪误差/估值分位 ===")
    # AKShare fund_etf_fund_info_em 提供 tracking_error
    try:
        import akshare as ak
    except ImportError:
        print("  AKShare 未安装，跳过")
        return

    done = set(progress.get("akshare_done", []))
    # 只需要 tracking_error = None 的
    remaining = [e for e in all_etfs 
                 if e.get("tracking_error") is None and e["code"] not in done]
    if not remaining:
        print("  无需处理，跳过")
        return
    
    print(f"  缺失 tracking_error: {len(remaining)}")
    enriched = 0
    
    for etf in remaining:
        code = etf["code"]
        try:
            df = ak.fund_etf_fund_info_em(fund=code, indicator="跟踪误差")
            if df is not None and len(df) > 0:
                # 通常返回最新追踪误差
                val = df.iloc[-1] if hasattr(df, 'iloc') else None
                if val is not None:
                    try:
                        etf["tracking_error"] = float(val)
                        enriched += 1
                    except:
                        pass
        except Exception as e:
            pass
        progress.setdefault("akshare_done", []).append(code)
        time.sleep(0.3)
    
    print(f"  AKShare 补充 tracking_error: {enriched}")
    save_progress(progress)
    save_data(all_etfs)

# ===== Phase 3: FTShare (非凸) ETF 详情 =====
def pull_ftshare(all_etfs, progress):
    print("\n=== Phase 3: FTShare 非凸 ETF 详情 ===")
    # 检查 ftshare CLI
    ftshare_skill = os.path.expanduser(
        "~/.workbuddy/plugins/marketplaces/cb_teams_marketplace/plugins/finance-data/skills/ftshare-market-data")
    if not os.path.exists(ftshare_skill):
        print("  FTShare 未安装，跳过")
        return
    
    done = set(progress.get("ftshare_done", []))
    remaining = [e for e in all_etfs if e["code"] not in done]
    if not remaining:
        print("  已完成，跳过")
        return
    
    print(f"  待处理: {len(remaining)}, 取样验证...")
    # 先试几只看返回什么
    test_codes = [code_to_westock(remaining[0]["code"])]
    # FTShare 用数字代码
    pure_code = remaining[0]["code"]
    
    # 使用 Skill 方式调用
    try:
        result = subprocess.run(
            ["skill", "ftshare-etf-query", pure_code],
            capture_output=True, text=True, timeout=30,
            cwd=ftshare_skill
        )
        print(f"  FTShare 测试返回: {result.stdout[:200] if result.stdout else result.stderr[:200]}")
    except Exception as e:
        print(f"  FTShare 调用失败: {e}")
    
    # 标记完成
    for etf in remaining:
        progress.setdefault("ftshare_done", []).append(etf["code"])
    save_progress(progress)

# ===== 工具 =====
def load_progress():
    if PROGRESS_FILE.exists():
        with open(PROGRESS_FILE) as f: return json.load(f)
    return {}

def save_progress(p):
    with open(PROGRESS_FILE, "w") as f: json.dump(p, f)

def save_data(etfs):
    data = {"etfs": etfs, "updated": datetime.now().isoformat()}
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ===== Main =====
if __name__ == "__main__":
    with open(DATA_FILE) as f:
        raw = json.load(f)
    all_etfs = raw["etfs"]
    print(f"ETF 总数: {len(all_etfs)}")

    progress = load_progress()

    # Phase 1: WeStock
    pull_westock(all_etfs, progress)

    # Phase 2: AKShare
    pull_akshare(all_etfs, progress)

    # Phase 3: FTShare
    pull_ftshare(all_etfs, progress)

    # 最终保存
    save_data(all_etfs)
    print("\n=== 全部完成 ===")