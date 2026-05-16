#!/usr/bin/env python3
"""
重新生成 etf_data_generated.json 的真实 top_holdings
使用 etf-component 获取每只ETF的真实成份股名称
"""
import json
import subprocess
import sys
import time

# etf-component run.py 路径
RUN_PY = "/Users/apangduo/.workbuddy/skills/ftshare-market-data/sub-skills/etf-component/../../run.py"

# 读取现有数据
with open('/Users/apangduo/WorkBuddy/Claw/etf-tool-mvp/etf_data_generated.json', 'r', encoding='utf-8') as f:
    etfs = json.load(f)

# 生成带后缀的代码
def make_symbol(code):
    # 5开头深交所，其他上交所
    code_str = str(code)
    if code_str.startswith('5') or code_str.startswith('1'):
        return f"{code_str}.XSHE"
    else:
        return f"{code_str}.XSHG"

print(f"开始获取 {len(etfs)} 只ETF的真实成份股...")
updated = 0
failed = 0

for i, etf in enumerate(etfs):
    code = etf['code']
    symbol = make_symbol(code)
    
    try:
        result = subprocess.run(
            ['python3', RUN_PY, 'etf-component', '--symbol', symbol],
            capture_output=True, text=True, timeout=15
        )
        
        if result.returncode == 0:
            data = json.loads(result.stdout)
            components = data.get('components_name', [])
            # 取前5大持仓
            top5 = components[:5]
            # 暂不带权重（etf-component 不返回权重）
            etf['top_holdings'] = top5  # 先存名称列表
            updated += 1
            if (i + 1) % 10 == 0:
                print(f"  进度: {i+1}/{len(etfs)} 已更新 {updated} 只")
        else:
            print(f"  ✗ {code} ({symbol}) 失败: {result.stderr.strip()[:80]}")
            failed += 1
    except Exception as e:
        print(f"  ✗ {code} 异常: {e}")
        failed += 1
    
    # 避免请求过快
    time.sleep(0.3)

print(f"\n完成: 成功 {updated} 只, 失败 {failed} 只")

# 保存
output_path = '/Users/apangduo/WorkBuddy/Claw/etf-tool-mvp/etf_data_generated.json'
with open(output_path, 'w', encoding='utf-8') as f:
    json.dump(etfs, f, ensure_ascii=False, indent=2)

print(f"已保存到 {output_path}")
print("\n注意: top_holdings 目前只有股票名称，尚未包含权重%")
print("      需要额外数据源补充权重信息")
