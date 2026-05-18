#!/usr/bin/env python3
"""
用盈米 GetBatchFundPerformance API 批量获取ETF指标（收益率/波动率/夏普/回撤）
"""
import sys, os, json, time, subprocess

ROOT = os.path.dirname(os.path.abspath(__file__))
BIN = "/Users/apangduo/.workbuddy/binaries/node/versions/22.12.0/bin"
BATCH_SIZE = 15  # 降低批量大小避免限流

with open(os.path.join(ROOT, "etf_standard_data.json"), encoding="utf-8") as f:
    data = json.load(f)
codes = [e["code"] for e in data]
print(f"ETF总数: {len(codes)}")

results = {}
ok = fail = 0
batches = [codes[i:i+BATCH_SIZE] for i in range(0, len(codes), BATCH_SIZE)]

for bi, batch in enumerate(batches):
    codes_json = json.dumps(batch, ensure_ascii=False)
    cmd = f'export PATH="$PATH:{BIN}" && yingmi-skill-cli mcp call GetBatchFundPerformance --input \'{{"fundCodes":{codes_json}}}\' 2>/dev/null'
    
    success = False
    for attempt in range(5):
        try:
            r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
            raw = r.stdout.strip()
            if not (raw.startswith("{") or raw.startswith("[")):
                if attempt < 4:
                    wait = 3 + attempt * 2
                    print(f"  批次{bi+1} 重试({attempt+1}/5): 等待{wait}s")
                    time.sleep(wait)
                    continue
                else:
                    fail += len(batch)
                    break
            
            funds = json.loads(raw)
            for fund in funds:
                code = fund.get("fundCode", "")
                if fund.get("error") or not code:
                    fail += 1
                    continue
                da = fund.get("data", {})
                metrics = da.get("metricsAnalyzes", [])
                
                entry = {}
                # 调试：打印第一个ETF的API返回字段
                if bi == 0 and ok == 0:
                    print(f"  调试：盈米API返回示例 (code={code})")
                    for period in ["oneYear", "twoYear", "threeYear"]:
                        pm = next((m for m in metrics if m["stageType"] == period), None)
                        if pm and pm.get("isValid", False):
                            print(f"    {period}: {[mm.get('title') for mm in pm.get('metrics', [])]}")
                
                for period in ["oneYear", "twoYear", "threeYear"]:
                    pm = next((m for m in metrics if m["stageType"] == period), None)
                    if pm and pm.get("isValid", False):
                        ms = {}
                        for mm in pm.get("metrics", []):
                            title = mm.get("title", "")
                            vt = mm.get("metricsValueText", "")
                            if vt:
                                try:
                                    ms[title] = float(vt.replace("%", ""))
                                except:
                                    ms[title] = 0
                        entry[period] = ms
                    else:
                        entry[period] = {}
                
                results[code] = {
                    "year_1_return": entry.get("oneYear", {}).get("收益能力", 0),
                    "year_3_return": entry.get("threeYear", {}).get("收益能力", 0),
                    "max_drawdown": entry.get("oneYear", {}).get("抗回撤能力", 0),
                    "sharpe_ratio": entry.get("oneYear", {}).get("投资性价比", 0),
                    "annual_vol_1y": entry.get("oneYear", {}).get("抗波动能力", 0),
                    "annual_vol_3y": entry.get("threeYear", {}).get("抗波动能力", 0),
                    "sharpe_3y": entry.get("threeYear", {}).get("投资性价比", 0),
                    "dd_3y": entry.get("threeYear", {}).get("抗回撤能力", 0),
                }
                ok += 1
            success = True
            break
        except Exception as e:
            if attempt < 4:
                time.sleep(3 + attempt * 2)
                continue
            fail += len(batch)
    
    if (bi + 1) % 5 == 0:
        print(f"  进度: {bi+1}/{len(batches)} 成功={ok} 失败={fail}")
    
    time.sleep(2.5)

with open(os.path.join(ROOT, "etf_yingmi_metrics.json"), "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False)
print(f"\n完成! 成功={ok} 失败={fail}")
