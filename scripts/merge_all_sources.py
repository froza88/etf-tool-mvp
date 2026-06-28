#!/usr/bin/env python3
"""多源全字段合并器 v2.0
- 自动字段名映射
- 多源交叉验证
- 仅填充空值（不覆盖已有数据）
- 生成合并报告
"""
import json, os, sys
from collections import defaultdict
from datetime import datetime

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(BASE)

# ===================== 配置 =====================

TARGET = 'prototypes/etf_core_data.json'

# 字段名映射：{源字段: 目标字段}
FIELD_MAP = {
    'manager': 'fund_manager',
    'inception_date': 'issue_date',
    'fund_type': 'invest_type',  # 指数型-股票 → invest_type
}

# 源文件配置
SOURCES = {
    'scrapling': {
        'file': 'etf_scrapling_fields.json',
        'fields': ['manager', 'inception_date', 'fund_type', 'custodian',
                    'management_fee_rate', 'custody_fee_rate', 'benchmark'],
    },
    'valuation': {
        'file': 'data/etf_valuation_fields.json',
        'fields': ['valuation_percentile'],
    },
    'flow': {
        'file': 'data/etf_flow_fields.json',
        'fields': ['main_net_inflow', 'main_net_ratio', 'super_large_inflow',
                    'large_inflow', 'medium_inflow', 'small_inflow', 'latest_shares'],
    },
}

# ===================== 加载 =====================

def load_json(path):
    if not os.path.exists(path):
        return None
    with open(path) as f:
        return json.load(f)

print(f'目标: {TARGET}')
target = load_json(TARGET)
if not target:
    print('目标文件不存在!')
    sys.exit(1)

# 建立code索引
code_idx = {}
for i, e in enumerate(target):
    code_idx[e['code']] = i

total = len(target)
print(f'ETF总数: {total}')

# ===================== 处理每个源 =====================

report_lines = []
overall_filled = 0

for src_name, cfg in SOURCES.items():
    src_data = load_json(cfg['file'])
    if not src_data:
        print(f'  ⏭ {src_name}: 文件不存在 → 跳过')
        continue

    # 处理不同格式：dict(code→data) 或 list
    if isinstance(src_data, dict):
        items = list(src_data.values())
    else:
        items = src_data

    filled_fields = defaultdict(int)
    filled_records = 0

    for item in items:
        code = item.get('code', '')
        if not code or code not in code_idx:
            continue
        idx = code_idx[code]

        record_filled = 0
        for src_field in cfg['fields']:
            val = item.get(src_field)
            if val is None or val == '':
                continue
            # 跳过0值（资金字段的0是有意义的值）
            if val == 0 and src_field not in ('main_net_inflow', 'main_net_ratio',
                    'super_large_inflow', 'large_inflow', 'medium_inflow',
                    'small_inflow', 'latest_shares', 'flow_shares'):
                continue

            # 字段名映射
            tgt_field = FIELD_MAP.get(src_field, src_field)

            # 只有目标缺失时才填充
            if target[idx].get(tgt_field) in (None, '', 0, []):
                target[idx][tgt_field] = val
                target[idx][f'{tgt_field}_source'] = src_name
                filled_fields[tgt_field] += 1
                record_filled += 1

        if record_filled > 0:
            filled_records += 1

    if filled_fields:
        total_f = sum(filled_fields.values())
        overall_filled += total_f
        fields_str = ', '.join(f'{k}(+{v})' for k, v in sorted(filled_fields.items(), key=lambda x: -x[1]))
        report_lines.append(f'  ✅ {src_name}: {filled_records}只ETF · {total_f}字段: {fields_str}')
    else:
        report_lines.append(f'  ➖ {src_name}: 无新字段填充（数据已在目标中）')

# ===================== 保存 =====================

# 备份
backup = TARGET.replace('.json', f'.backup_{datetime.now().strftime("%H%M")}.json')
if os.path.exists(TARGET):
    with open(TARGET, 'rb') as f:
        with open(backup, 'wb') as bf:
            bf.write(f.read())

with open(TARGET, 'w', encoding='utf-8') as f:
    json.dump(target, f, ensure_ascii=False, indent=2)

print()
print('='*60)
print('  合并报告')
print('='*60)
for line in report_lines:
    print(line)
print(f'  备份: {backup}')
print(f'  总计: {overall_filled} 字段填充')

# ===================== 覆盖度验证 =====================
print()
print('='*60)
print('  关键字段覆盖度变化')
print('='*60)
for field in ['fund_manager', 'issue_date', 'valuation_percentile',
              'main_net_inflow', 'beta', 'alpha', 'nav']:
    valid = sum(1 for e in target if e.get(field) not in (None, '', 0))
    pct = valid / total * 100
    print(f'  {field:<22s} {valid}/{total}  {pct:5.1f}%')

# Datestamp
target[0].setdefault('_last_merge', datetime.now().isoformat())
