#!/usr/bin/env python3
"""
用 AKShare fund_portfolio_hold_em() 补充 ETF 持仓权重%
需要手动在本地终端运行（避免沙盒超时限制）

用法: python3 enrich_weights.py
"""
import json
import time
import warnings
warnings.filterwarnings('ignore')
import akshare as ak

GEN_FILE = "/Users/apangduo/WorkBuddy/Claw/etf-tool-mvp/etf_data_generated.json"

with open(GEN_FILE, "r", encoding="utf-8") as f:
    gen = json.load(f)

codes_with_holdings = [(i, e) for i, e in enumerate(gen) if e.get('top_holdings')]
print(f"有持仓的ETF: {len(codes_with_holdings)} 只")

updated = 0
failed = 0

for idx, (i, item) in enumerate(codes_with_holdings):
    code = str(item['code'])
    try:
        df = ak.fund_portfolio_hold_em(symbol=code, date="2025")
        if df is not None and len(df) > 0:
            # 构建 股票名称→权重 映射
            weight_map = {}
            for _, row in df.iterrows():
                try:
                    name = str(row.iloc[2]).strip()
                    weight = float(row.iloc[3])
                    weight_map[name] = f"{weight:.2f}%"
                except:
                    pass

            # 补充权重
            enriched = []
            for h in item['top_holdings']:
                n = h.get('name', '') if isinstance(h, dict) else str(h)
                w = weight_map.get(n, '')
                enriched.append({"name": n, "weight": w})

            item['top_holdings'] = enriched
            updated += 1
    except Exception as e:
        failed += 1

    if (idx + 1) % 10 == 0:
        print(f"进度: {idx+1}/{len(codes_with_holdings)}  成功={updated} 失败={failed}")

    time.sleep(0.5)

print(f"\n完成: 成功={updated} 失败={failed}")

# 保存
with open(GEN_FILE, "w", encoding="utf-8") as f:
    json.dump(gen, f, ensure_ascii=False, indent=2)
print(f"已保存到 {GEN_FILE}")

print("\n建议: 运行完后执行 python3 build_standard_data.py 重建标准化数据")
