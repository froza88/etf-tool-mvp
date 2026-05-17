#!/usr/bin/env python3
"""
修正持仓：直接用 AKShare fund_portfolio_hold_em 的完整数据替换
不依赖非凸成分股，直接用基金真实前10持仓
"""
import json, os, time, warnings
warnings.filterwarnings('ignore')
import akshare as ak

ROOT = os.path.dirname(os.path.abspath(__file__))
GEN_FILE = os.path.join(ROOT, "etf_data_generated.json")
OUTPUT = os.path.join(ROOT, "etf_holdings_v2.json")

with open(GEN_FILE, encoding='utf-8') as f:
    gen = json.load(f)

updated = 0
results = {}

for i, item in enumerate(gen):
    code = str(item['code'])
    try:
        df = ak.fund_portfolio_hold_em(symbol=code, date="2026")
        if df is not None and len(df) > 0:
            holdings = []
            for _, r in df.iterrows():
                try:
                    name = str(r.iloc[2]).strip()
                    weight = float(r.iloc[3])
                    holdings.append({"name": name, "weight": f"{weight:.2f}%"})
                except:
                    pass
                if len(holdings) >= 5:
                    break
            if holdings:
                results[code] = holdings
                updated += 1
                item['top_holdings'] = holdings
    except:
        pass
    time.sleep(0.15)

    if (i + 1) % 100 == 0:
        print(f"进度: {i+1}/{len(gen)}  updated={updated}")
        # 保存到输出文件 + 同步到 gen
        with open(OUTPUT, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False)
        with open(GEN_FILE, 'w', encoding='utf-8') as f:
            json.dump(gen, f, ensure_ascii=False, indent=2)

# 最终保存
with open(OUTPUT, 'w', encoding='utf-8') as f:
    json.dump(results, f, ensure_ascii=False)
with open(GEN_FILE, 'w', encoding='utf-8') as f:
    json.dump(gen, f, ensure_ascii=False, indent=2)

print(f"完成! 更新了 {updated}/{len(gen)} 只ETF的持仓")
