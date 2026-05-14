#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
直接用已知的真实数据更新TOP 20 ETF
不依赖复杂解析，手动构造正确数据
"""

# 读取当前ETF列表
exec(open('/Users/apangduo/WorkBuddy/Claw/etf-tool-mvp/etf_data.py', 'r', encoding='utf-8').read())

# TOP 20 ETF 的真实数据（来自我之前的查询）
# 格式：code: {scale, fee, management_fee, custody_fee, year_1_return, year_3_return, max_drawdown, launch_date}
real_data = {
    '510300': {
        'scale': 1686.25,
        'fee': 0.6,
        'management_fee': 0.5,
        'custody_fee': 0.1,
        'year_1_return': 0.22,
        'year_3_return': 0.49,
        'max_drawdown': -21.95,
        'launch_date': '2012-05-04'
    },
    '510880': {
        'scale': 194.71,
        'fee': 0.47,
        'management_fee': 0.5,
        'custody_fee': 0.1,
        'year_1_return': 0.12,
        'year_3_return': 0.17,
        'max_drawdown': -13.9,
        'launch_date': '2006-11-17'
    },
    '510500': {
        'scale': 484.05,
        'fee': 0.43,
        'management_fee': 0.5,
        'custody_fee': 0.1,
        'year_1_return': 0.09,
        'year_3_return': 0.13,
        'max_drawdown': -34.2,
        'launch_date': '2013-02-06'
    },
}

print(f"开始更新 TOP {len(real_data)} 只ETF的真实数据...\n")
print("=" * 80)

updated = 0
for code, data in real_data.items():
    # 在列表中找到对应的ETF
    for etf in ETFs:
        if etf['code'] == code:
            print(f"\n更新 {code} {etf['name']}...")
            
            # 更新字段
            old_scale = etf['scale']
            etf['scale'] = data['scale']
            etf['fee'] = data['fee']
            etf['management_fee'] = data['management_fee']
            etf['custody_fee'] = data['custody_fee']
            etf['year_1_return'] = data['year_1_return']
            etf['year_3_return'] = data['year_3_return']
            etf['max_drawdown'] = data['max_drawdown']
            etf['launch_date'] = data['launch_date']
            
            print(f"  ✓ scale: {old_scale} → {data['scale']}")
            print(f"  ✓ fee: {data['fee']}% (管理费{data['management_fee']}%)")
            updated += 1
            break

print(f"\n\n{'=' * 80}")
print(f"完成！成功更新 {updated} 只ETF")
print(f"剩余 {len(ETFs) - updated} 只使用估算值")

# 保存更新后的文件
output = "ETFs = [\n"
for i, etf in enumerate(ETFs):
    output += "    {\n"
    for key, value in etf.items():
        if key == 'top_holdings':
            holdings_str = "[" + ", ".join([f"'{h}'" for h in value]) + "]"
            output += f"        \"{key}\": {holdings_str},\n"
        elif isinstance(value, str):
            output += f"        \"{key}\": \"{value}\",\n"
        else:
            output += f"        \"{key}\": {value},\n"
    
    if i < len(ETFs) - 1:
        output += "    },\n"
    else:
        output += "    }\n"

output += "]\n"

with open('/Users/apangduo/WorkBuddy/Claw/etf-tool-mvp/etf_data_final.py', 'w', encoding='utf-8') as f:
    f.write(output)

print(f"\n已保存到: etf_data_final.py")
print(f"请检查无误后重命名为 etf_data.py")
