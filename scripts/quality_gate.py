#!/usr/bin/env python3
"""ETF Pipeline Quality Gate — 一键运行所有数据质量检查
vibe-coding-cn 工程闭环实践：硬门禁约束 AI 输出
用法: python scripts/quality_gate.py [--ci]
"""

import json
import sys
import os

SOURCE = 'etf_standard_data.json'

REQUIRED_FIELDS = ['code', 'name', 'management_fee_rate', 'custody_fee_rate', 'benchmark', 'close']
NUMERIC_FIELDS = ['management_fee_rate', 'custody_fee_rate', 'sharpe_ratio', 'annual_vol', 'max_drawdown',
                   'tracking_error', 'info_ratio', 'beta', 'alpha', 'year_1_return', 'valuation_percentile']
DATE_FIELDS = ['inception_date', 'manager']

EXIT_CODE = 0
CHECKS_PASSED = 0
CHECKS_FAILED = 0

def check(msg, ok):
    global EXIT_CODE, CHECKS_PASSED, CHECKS_FAILED
    if ok:
        CHECKS_PASSED += 1
        print(f'  ✅ {msg}')
    else:
        CHECKS_FAILED += 1
        EXIT_CODE = 1
        print(f'  ❌ {msg}')

def main():
    global EXIT_CODE, CHECKS_PASSED, CHECKS_FAILED
    ci_mode = '--ci' in sys.argv

    print('=' * 55)
    print('ETF Pipeline Quality Gate')
    print('=' * 55)

    # ── Load ──
    if not os.path.exists(SOURCE):
        print(f'❌ Fatal: {SOURCE} not found')
        sys.exit(1)

    with open(SOURCE) as f:
        data = json.load(f)

    total = len(data)
    print(f'\n📊 数据集: {total} ETFs')

    # ── 1. Structure ──
    print('\n── 结构检查 ──')
    check(f'数据是列表结构', isinstance(data, list))
    codes = [e.get('code') for e in data if isinstance(e, dict)]
    duplicates = len(codes) - len(set(codes))
    check(f'无重复 code ({len(codes)} unique)', duplicates == 0)
    if duplicates:
        from collections import Counter
        dup_codes = [k for k, v in Counter(codes).items() if v > 1]
        check(f'  重复: {dup_codes[:5]}', False)

    # ── 2. Required fields ──
    print('\n── 必填字段 ──')
    for field in REQUIRED_FIELDS:
        missing = sum(1 for e in data if not e.get(field))
        check(f'{field}: {total-missing}/{total}', missing == 0)

    # ── 3. Completeness ──
    print('\n── 完整度 ──')
    tier1_fields = ['management_fee_rate','custody_fee_rate','benchmark','close','scale',
                    'custodian','inception_date','manager','sharpe_ratio']
    for field in tier1_fields:
        count = sum(1 for e in data if e.get(field) not in (None, '', 0))
        pct = count / total * 100
        ok = pct >= 99
        check(f'{field}: {count}/{total} ({pct:.1f}%)', ok)

    # ── 4. Value ranges ──
    print('\n── 数值合理性 ──')
    range_checks = {
        '管理费率 0~2%': ('management_fee_rate', 0, 2),
        '托管费率 0~0.5%': ('custody_fee_rate', 0, 0.5),
        '夏普 -5~10': ('sharpe_ratio', -5, 10),
        '最大回撤 -100~0': ('max_drawdown', -100, 0),
        '估值分位 -5~110': ('valuation_percentile', -5, 110),
        '贝塔 -0.5~5': ('beta', -0.5, 5),
    }
    for label, (field, lo, hi) in range_checks.items():
        values = [e[field] for e in data if e.get(field) not in (None, '', 0) and isinstance(e.get(field), (int, float))]
        if not values:
            check(f'{label}: no data', not ci_mode)
            continue
        outliers = [v for v in values if v < lo or v > hi]
        ok = len(outliers) <= total * 0.02  # 2% threshold
        check(f'{label}: {min(values):.2f}~{max(values):.2f}, {len(outliers)} outliers', ok)

    # ── 5. Source tracking ──
    print('\n── 数据源追踪 ──')
    source_fields = ['management_fee_rate_source', 'custody_fee_rate_source', 
                     'benchmark_source', 'inception_date_source', 'manager_source']
    sources = {}
    for sf in source_fields:
        for e in data:
            src = e.get(sf, 'unknown')
            sources[src] = sources.get(src, 0) + 1
    for src, cnt in sorted(sources.items()):
        print(f'  {src}: {cnt} fields')

    # ── Report ──
    print(f'\n{"="*55}')
    total_checks = CHECKS_PASSED + CHECKS_FAILED
    score = CHECKS_PASSED / total_checks * 100 if total_checks > 0 else 0
    print(f'结果: {CHECKS_PASSED}/{total_checks} 通过 ({score:.0f}%)')
    if EXIT_CODE == 0:
        print('✅ All quality gates passed')
    else:
        print(f'❌ {CHECKS_FAILED} checks failed')
    print(f'{"="*55}')

    sys.exit(EXIT_CODE)

if __name__ == '__main__':
    main()
