import akshare as ak
import pandas as pd
import json

# 获取 ETF 实时行情
print("正在获取 ETF 实时行情...")
df = ak.fund_etf_spot_em()

# 打印字段名（英文）
print("\n=== 字段名（英文）===")
print(list(df.columns))

# 保存为 CSV（避免终端编码问题）
output_file = "/Users/apangduo/WorkBuddy/Claw/etf-tool-mvp/akshare_etf_data.csv"
df.to_csv(output_file, index=False, encoding="utf-8-sig")
print(f"\n数据已保存到: {output_file}")
print(f"共 {len(df)} 条 ETF 数据")

# 显示前3条数据的字段名和值
print("\n=== 前3条数据示例 ===")
for i in range(min(3, len(df))):
    print(f"\n第 {i+1} 条:")
    for col in df.columns:
        print(f"  {col}: {df.iloc[i][col]}")
