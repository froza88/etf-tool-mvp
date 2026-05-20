#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ETF数据完整度检查脚本"""

import json
import os
from datetime import datetime

def check_completeness():
    with open('etf_standard_data.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    total = len(data)
    report_time = datetime.now().strftime('%Y-%m-%d %H:%M')
    
    # 实际字段映射（基于数据结构）
    fields = {
        'code': '代码',
        'name': '名称',
        'issuer': '发行人',
        'scale': '规模',
        'shares': '份额',
        'issue_date': '上市日期',
        'custodian': '托管人',
        'top_holdings': '持仓',
        'change_pct': '涨跌幅',
        'close': '收盘价',
        'prev_close': '昨收',
        'change_rate': '涨跌额',
        'volume': '成交量',
        'year_1_return': '收益率(1年)',
        'year_3_return': '收益率(3年)',
        'max_drawdown': '最大回撤',
        'sharpe_ratio': '夏普比率',
        'annual_vol': '年化波动率',
        'category': '分类'
    }
    
    # 计算覆盖率
    results = []
    for field, label in fields.items():
        count = 0
        for etf in data:
            val = etf.get(field)
            if val is not None and val != '' and val != 0:
                if field == 'top_holdings':
                    if isinstance(val, list) and len(val) > 0:
                        count += 1
                elif field == 'volume':
                    # volume might be 0 for some ETFs, check if > 0
                    if val > 0:
                        count += 1
                else:
                    count += 1
        
        coverage = count / total * 100 if total > 0 else 0
        status = '✅' if coverage >= 95 else '⚠️' if coverage >= 80 else '❌'
        results.append((label, count, coverage, status))
    
    # 检查历史K线数据
    history_dir = 'data/history'
    history_count = 0
    if os.path.exists(history_dir):
        history_files = [f for f in os.listdir(history_dir) if f.endswith('.json')]
        history_count = len(history_files)
        # 采样检查数据点
        avg_points = 0
        if history_files:
            sample_file = os.path.join(history_dir, history_files[0])
            with open(sample_file, 'r') as f:
                sample_data = json.load(f)
                if isinstance(sample_data, list):
                    avg_points = len(sample_data)
    
    # 生成Markdown报告
    md = f"""# ETF数据完整度报告

**生成时间**: {report_time}  
**ETF总数**: {total}

---

## 字段覆盖率统计

| 字段 | 覆盖数 | 覆盖率 | 状态 |
|------|--------|--------|------|
"""
    
    for label, count, coverage, status in results:
        md += f"| {label} | {count} | {coverage:.1f}% | {status} |\n"
    
    md += f"""
---

## 历史K线数据

- **已填充ETF数**: {history_count}
- **覆盖率**: {history_count/total*100:.1f}%
- **平均数据点/只**: {avg_points}

---

## 数据质量评级

"""
    
    # 计算整体完整度（核心字段）
    core_fields = ['issuer', 'close', 'year_1_return', 'sharpe_ratio']
    complete_count = 0
    for etf in data:
        if all(etf.get(f) and etf.get(f) != 0 for f in core_fields if f in etf):
            complete_count += 1
    
    overall_rate = complete_count / total * 100 if total > 0 else 0
    rating = 'A(优秀)' if overall_rate >= 95 else 'B(良好)' if overall_rate >= 85 else 'C(一般)' if overall_rate >= 70 else 'D(较差)'
    
    md += f"""- **核心字段完整度**: {overall_rate:.1f}%
- **综合评级**: {rating}

### 评级标准
- **A级**: 核心字段覆盖率 ≥ 95%
- **B级**: 核心字段覆盖率 ≥ 85%
- **C级**: 核心字段覆盖率 ≥ 70%
- **D级**: 核心字段覆盖率 < 70%

---

## 待解决问题

"""
    
    # 识别问题
    problems = []
    if any(etf.get('issuer') is None or etf.get('issuer') == '' for etf in data):
        problems.append(f"- ❌ **发行人缺失**: {sum(1 for etf in data if not etf.get('issuer'))} 只")
    if any(etf.get('year_3_return') is None or etf.get('year_3_return') == 0 for etf in data):
        problems.append(f"- ⚠️ **3年收益率缺失**: {sum(1 for etf in data if not etf.get('year_3_return') or etf.get('year_3_return') == 0)} 只")
    if history_count < total:
        problems.append(f"- ⚠️ **历史K线缺失**: {total - history_count} 只ETF无历史数据")
    
    if problems:
        md += '\n'.join(problems)
    else:
        md += "- ✅ 无重大问题"
    
    md += "\n\n---\n\n*报告由 check_data_completeness.py 自动生成*"
    
    # 保存报告
    report_file = 'data_completeness_report.md'
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(md)
    
    print(f"报告已生成: {report_file}")
    return md

if __name__ == '__main__':
    report = check_completeness()
    print(report)
