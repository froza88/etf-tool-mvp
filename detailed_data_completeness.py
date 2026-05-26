#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""精细数据完整度分析 - 区分缺失原因"""

import json
import os
from datetime import datetime, timedelta

def analyze_detailed_completeness():
    # 读取数据
    with open('etf_standard_data.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    total = len(data)
    today = datetime.now()
    
    print(f"总ETF数: {total}\n")
    
    # 定义分析字段
    fields = {
        'issuer': '发行人',
        'close': '最新价',
        'year_1_return': '收益率(1年)',
        'sharpe_ratio': '夏普比率',
        'top_holdings': '持仓',
        'year_3_return': '收益率(3年)',
        'max_drawdown': '最大回撤',
        'annual_vol': '年化波动率'
    }
    
    # 分析结果
    results = {}
    
    for field, label in fields.items():
        print(f"\n{'='*60}")
        print(f"分析字段: {label} ({field})")
        print(f"{'='*60}")
        
        # 分类统计
        categories = {
            'valid': [],  # 有效数据
            'insufficient_history': [],  # 历史不足（上市<1年）
            'data_source_missing': [],  # 数据源无数据
            'special_type': [],  # 特殊类型（货币ETF无持仓等）
            'calculation_error': [],  # 计算错误
            'unknown': []  # 未知原因
        }
        
        for etf in data:
            code = etf.get('code', 'unknown')
            name = etf.get('name', 'unknown')
            category = etf.get('category', '未知')
            issue_date = etf.get('issue_date', '')
            
            # 获取字段值
            if field == 'top_holdings':
                val = etf.get(field)
                has_data = (val and isinstance(val, list) and len(val) > 0)
            else:
                val = etf.get(field)
                has_data = (val is not None and val != '' and val != 0)
            
            if has_data:
                categories['valid'].append(etf)
            else:
                # 分析缺失原因
                # 1. 检查是否历史不足（上市<1年）
                if issue_date and issue_date != '':
                    try:
                        issue_dt = datetime.strptime(issue_date, '%Y-%m-%d')
                        days_listed = (today - issue_dt).days
                        if days_listed < 365:
                            categories['insufficient_history'].append(etf)
                            continue
                    except:
                        pass
                
                # 2. 检查是否特殊类型
                if field == 'top_holdings' and category == '货币':
                    categories['special_type'].append(etf)
                    continue
                
                # 3. 检查是否数据源问题（通过其他字段推断）
                # 如果有year_1_return但无sharpe_ratio，可能是计算问题
                if field == 'sharpe_ratio' and etf.get('year_1_return'):
                    categories['calculation_error'].append(etf)
                    continue
                
                # 4. 默认：数据源无数据
                categories['data_source_missing'].append(etf)
        
        # 计算完整度（刨除无法获得的）
        valid_count = len(categories['valid'])
        excludable = len(categories['insufficient_history']) + len(categories['special_type'])
        denominator = total - excludable
        completeness = valid_count / denominator * 100 if denominator > 0 else 0
        
        # 输出结果
        print(f"\n【{label}】数据完整度分析:")
        print(f"  有效数据: {valid_count}只 ({valid_count/total*100:.1f}%)")
        print(f"  完整度(刨除不可获得): {valid_count}/{denominator} = {completeness:.1f}%")
        print(f"\n  缺失原因分类:")
        print(f"    - 历史不足(<1年): {len(categories['insufficient_history'])}只")
        print(f"    - 特殊类型: {len(categories['special_type'])}只")
        print(f"    - 数据源无数据: {len(categories['data_source_missing'])}只")
        print(f"    - 计算错误: {len(categories['calculation_error'])}只")
        print(f"    - 未知原因: {len(categories['unknown'])}只")
        
        # 采样显示
        if categories['insufficient_history']:
            print(f"\n  [历史不足] 采样(前5只):")
            for etf in categories['insufficient_history'][:5]:
                print(f"    {etf.get('code')} {etf.get('name')} - 上市:{etf.get('issue_date')} - 分类:{etf.get('category')}")
        
        if categories['special_type']:
            print(f"\n  [特殊类型] 列表:")
            for etf in categories['special_type'][:10]:
                print(f"    {etf.get('code')} {etf.get('name')} - 分类:{etf.get('category')}")
        
        if categories['data_source_missing']:
            print(f"\n  [数据源无数据] 采样(前5只):")
            for etf in categories['data_source_missing'][:5]:
                print(f"    {etf.get('code')} {etf.get('name')} - 上市:{etf.get('issue_date')} - 分类:{etf.get('category')}")
        
        # 保存结果
        results[field] = {
            'label': label,
            'valid': valid_count,
            'total': total,
            'excludable': excludable,
            'denominator': denominator,
            'completeness': completeness,
            'categories': {k: len(v) for k, v in categories.items()}
        }
    
    # 生成完整报告
    print(f"\n\n{'='*60}")
    print("生成完整报告...")
    print(f"{'='*60}")
    
    report = f"""# ETF数据完整度精细分析报告

**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M')}  
**分析标准**: 区分缺失原因，刨除不可获得数据

---

## 数据完整度总览

| 指标 | 有效数 | 总数 | 刨除数 | 分母 | 完整度 | 状态 |
|------|--------|------|--------|------|--------|------|
"""
    
    for field, result in results.items():
        status = '✅' if result['completeness'] >= 95 else '⚠️' if result['completeness'] >= 80 else '❌'
        report += f"| {result['label']} | {result['valid']} | {result['total']} | {result['excludable']} | {result['denominator']} | {result['completeness']:.1f}% | {status} |\n"
    
    report += "\n---\n\n## 详细分析\n\n"
    
    for field, result in results.items():
        report += f"""### {result['label']} ({field})

- **有效数据**: {result['valid']}只 ({result['valid']/result['total']*100:.1f}%)
- **完整度(刨除不可获得)**: {result['valid']}/{result['denominator']} = {result['completeness']:.1f}%

#### 缺失原因分类

| 原因 | 数量 | 占比 |
|------|------|------|
"""
        for cat, cnt in result['categories'].items():
            pct = cnt / result['total'] * 100 if result['total'] > 0 else 0
            report += f"| {cat} | {cnt} | {pct:.1f}% |\n"
        
        report += "\n---\n\n"
    
    report += """## 改进建议

### P0 - 紧急
- 补充历史K线数据，减少"历史不足"的ETF数量
- 修复计算逻辑，解决"计算错误"问题

### P1 - 重要
- 检查数据源配置，解决"数据源无数据"问题
- 对于"特殊类型"，明确标记而非视为缺失

### P2 - 可选
- 优化数据获取策略，提高数据源覆盖率

---

*报告由 detailed_data_completeness.py 自动生成*
"""
    
    # 保存报告
    report_file = 'detailed_data_completeness_report.md'
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"\n报告已保存: {report_file}")
    return results

if __name__ == '__main__':
    results = analyze_detailed_completeness()
