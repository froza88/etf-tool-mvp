#!/usr/bin/env python3
"""
重新获取 etf_data_generated.json 中每只 ETF 的真实 top_holdings
调用 ftshare-market-data etf-component API 获取真实成份股名称
"""
import json
import os
import sys
import time

# 添加 ftshare-market-data 到 path
FTSHARE_ROOT = os.path.expanduser("~/.workbuddy/skills/ftshare-market-data")
sys.path.insert(0, FTSHARE_ROOT)

# 读取 generated 数据
GEN_FILE = "/Users/apangduo/WorkBuddy/Claw/etf-tool-mvp/etf_data_generated.json"
with open(GEN_FILE, "r", encoding="utf-8") as f:
    etfs = json.load(f)

print(f"读取 {len(etfs)} 条记录（含重复）")

# 去重：保留每个 code 第一次出现的记录
seen_codes = {}
unique_etfs = []
for e in etfs:
    code = str(e["code"])
    if code not in seen_codes:
        seen_codes[code] = len(unique_etfs)
        unique_etfs.append(e)
    else:
        print(f"  去重: code={code} 跳过重复记录")

print(f"去重后: {len(unique_etfs)} 条唯一记录")

# 对每个唯一 ETF 获取真实持仓
updated = 0
failed = 0
no_data = 0

for i, etf in enumerate(unique_etfs):
    code = str(etf["code"])
    # 判断交易所后缀（正确规则）
    # 5开头=上交所(XSHG)，1开头=深交所(XSHE)
    if code.startswith("5"):
        symbol = f"{code}.XSHG"
    elif code.startswith("1"):
        symbol = f"{code}.XSHE"
    else:
        # 6/0/3开头股票不应该是ETF，但兜底用XSHG
        symbol = f"{code}.XSHG"

    try:
        # 调用 ftshare-market-data run.py etf-component
        import subprocess
        result = subprocess.run(
            ["python3", os.path.join(FTSHARE_ROOT, "run.py"), "etf-component", "--symbol", symbol],
            capture_output=True, text=True, timeout=20,
            cwd=FTSHARE_ROOT
        )

        if result.returncode == 0:
            data = json.loads(result.stdout)
            comp_names = data.get("components_name", [])
            if comp_names:
                # 取前5大持仓，格式: "股票名称"（暂时不带权重）
                top5 = comp_names[:5]
                etf["top_holdings"] = top5
                updated += 1
            else:
                etf["top_holdings"] = []
                no_data += 1
        else:
            print(f"  ✗ {code} ({symbol}) API错误: {result.stderr.strip()[:100]}")
            failed += 1
    except Exception as e:
        print(f"  ✗ {code} ({symbol}) 异常: {e}")
        failed += 1

    # 进度
    if (i + 1) % 10 == 0 or (i + 1) == len(unique_etfs):
        print(f"  进度: {i+1}/{len(unique_etfs)}  成功={updated} 无数据={no_data} 失败={failed}")

    time.sleep(0.3)  # 避免请求过快

print(f"\n完成: 成功={updated} 无数据={no_data} 失败={failed}")

# 保存（只保存去重后的唯一记录）
with open(GEN_FILE, "w", encoding="utf-8") as f:
    json.dump(unique_etfs, f, ensure_ascii=False, indent=2)

print(f"已保存 {len(unique_etfs)} 条唯一记录到 {GEN_FILE}")
print("注意: top_holdings 目前只有股票名称，权重%待补充")
