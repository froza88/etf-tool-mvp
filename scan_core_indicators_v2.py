#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ETF核心指标完整度扫描 v2
扫描所有数据源，生成核心指标完整度表格（中英文对照）

v2 改进：
- 修复字段映射：year_1_return → return_1y, close → price 等
- 新增扫描：data/realtime/, data/history/, data/snapshots/
- 修复 JSON 序列化问题（set → list）
"""

import json
import os
import sys
from pathlib import Path
from datetime import datetime
from collections import defaultdict

# 配置
DATA_DIR = Path(__file__).parent
OUTPUT_DIR = DATA_DIR / 'core_indicator_db'

# 核心指标定义（中英文对照）
CORE_INDICATORS = [
    {'en': 'code', 'zh': '基金代码', 'required': True},
    {'en': 'name', 'zh': '基金名称', 'required': True},
    {'en': 'price', 'zh': '最新价格', 'required': False},
    {'en': 'change_pct', 'zh': '涨跌幅(%)', 'required': False},
    {'en': 'scale', 'zh': '规模(亿元)', 'required': False},
    {'en': 'management_fee', 'zh': '管理费率(%)', 'required': False},
    {'en': 'sharpe_ratio', 'zh': '夏普比率(近1年)', 'required': False},
    {'en': 'annual_vol', 'zh': '年化波动率(近1年)', 'required': False},
    {'en': 'max_drawdown', 'zh': '最大回撤(近1年)', 'required': False},
    {'en': 'tracking_error', 'zh': '跟踪误差(近1年)', 'required': False},
    {'en': 'calmar_ratio', 'zh': '卡玛比率(近1年)', 'required': False},
    {'en': 'sortino_ratio', 'zh': '索提诺比率(近1年)', 'required': False},
    {'en': 'return_1y', 'zh': '累计收益率(近1年)', 'required': False},
    {'en': 'return_3y', 'zh': '累计收益率(近3年)', 'required': False},
    {'en': 'return_5y', 'zh': '累计收益率(近5年)', 'required': False},
    {'en': 'top_holding_1', 'zh': '股票第一大持仓', 'required': False},
    {'en': 'top_holding_2', 'zh': '股票第二大持仓', 'required': False},
    {'en': 'top_holding_3', 'zh': '股票第三大持仓', 'required': False},
    {'en': 'updated_at', 'zh': '更新时间', 'required': False},
    {'en': 'data_source', 'zh': '数据来源', 'required': False},
]

# etf_standard_data.json 字段名 → 核心指标名 映射
ETF_STANDARD_MAPPING = {
    'close': 'price',
    'change_pct': 'change_pct',
    'scale': 'scale',
    'management_fee_rate': 'management_fee',
    'sharpe_ratio': 'sharpe_ratio',
    'annual_vol': 'annual_vol',
    'max_drawdown': 'max_drawdown',
    'tracking_error': 'tracking_error',
    'calmar_ratio': 'calmar_ratio',
    'year_1_return': 'return_1y',
    'year_3_return': 'return_3y',
    'top_holdings': 'top_holdings',  # 需要解析
}

def scan_etf_standard_data():
    """扫描etf_standard_data.json"""
    print("📊 扫描 etf_standard_data.json...")
    
    file_path = DATA_DIR / 'etf_standard_data.json'
    if not file_path.exists():
        print("   ❌ 文件不存在")
        return {}
    
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print(f"   ✅ ETF总数: {len(data)}")
    
    # 构建完整度字典
    completeness = {}
    for etf in data:
        code = etf.get('code', '')
        if not code:
            continue
        
        if code not in completeness:
            completeness[code] = {
                'code': code,
                'name': etf.get('name', ''),
                'indicators': {},
                'sources': [],
                'updated_at': None
            }
        
        # 检查每个核心指标（使用映射表）
        for indicator in CORE_INDICATORS:
            en = indicator['en']
            if en in ['code', 'name', 'updated_at', 'data_source']:
                continue
            
            # 查找映射的字段名
            value = None
            for src_key, dst_key in ETF_STANDARD_MAPPING.items():
                if dst_key == en:
                    value = etf.get(src_key)
                    break
            
            # 特殊处理：top_holdings 需要解析
            if en.startswith('top_holding_'):
                holdings = etf.get('top_holdings', [])
                if isinstance(holdings, list) and len(holdings) > 0:
                    idx = int(en.split('_')[-1]) - 1  # top_holding_1 → index 0
                    if idx < len(holdings):
                        holding = holdings[idx]
                        value = holding.get('name', holding.get('stock_name', ''))
            
            if value not in [None, '', 0, '0']:
                if en not in completeness[code]['indicators']:
                    completeness[code]['indicators'][en] = {
                        'value': value,
                        'source': 'etf_standard_data',
                        'updated_at': etf.get('updated_at', 'unknown')
                    }
                    if 'etf_standard_data' not in completeness[code]['sources']:
                        completeness[code]['sources'].append('etf_standard_data')
                    
                    if not completeness[code]['updated_at'] or str(etf.get('updated_at', '')) > str(completeness[code]['updated_at']):
                        completeness[code]['updated_at'] = etf.get('updated_at', '')
    
    print(f"   ✅ 扫描完成: {len(completeness)} 只ETF")
    return completeness

def scan_wind_cache():
    """扫描Wind缓存数据"""
    print("📊 扫描 Wind缓存...")
    
    wind_dir = DATA_DIR / 'data' / 'cache' / 'wind'
    if not wind_dir.exists():
        print("   ❌ 目录不存在")
        return {}
    
    completeness = {}
    
    for json_file in wind_dir.glob('*_risk.json'):
        code = json_file.stem.replace('_risk', '')
        
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except:
            continue
        
        if code not in completeness:
            completeness[code] = {
                'code': code,
                'name': data.get('name', ''),
                'indicators': {},
                'sources': [],
                'updated_at': None
            }
        
        # 提取指标
        indicators_map = {
            'sharpe_1y': 'sharpe_ratio',
            'volatility_1y': 'annual_vol',
            'max_drawdown_1y': 'max_drawdown',
            # TODO: 如果以后Wind返回tracking_error，在这里添加映射
        }
        
        for wind_key, our_key in indicators_map.items():
            value = data.get(wind_key)
            if value not in [None, '', 0]:
                if our_key not in completeness[code]['indicators']:
                    completeness[code]['indicators'][our_key] = {
                        'value': value,
                        'source': 'wind_cache',
                        'updated_at': data.get('fetched_at', 'unknown')
                    }
                    if 'wind_cache' not in completeness[code]['sources']:
                        completeness[code]['sources'].append('wind_cache')
                    
                    if not completeness[code]['updated_at'] or str(data.get('fetched_at', '')) > str(completeness[code]['updated_at']):
                        completeness[code]['updated_at'] = data.get('fetched_at', '')
    
    print(f"   ✅ 扫描完成: {len(completeness)} 只ETF")
    return completeness

def scan_realtime_data():
    """扫描data/realtime/实时数据"""
    print("📊 扫描 data/realtime/...")
    
    realtime_dir = DATA_DIR / 'data' / 'realtime'
    if not realtime_dir.exists():
        print("   ❌ 目录不存在")
        return {}
    
    completeness = {}
    
    # TODO: 根据realtime数据格式实现
    print(f"   ⚠️  待实现: realtime数据扫描")
    
    return completeness

def scan_history_data():
    """扫描data/history/历史K线数据"""
    print("📊 扫描 data/history/...")
    
    history_dir = DATA_DIR / 'data' / 'history'
    if not history_dir.exists():
        print("   ❌ 目录不存在")
        return {}
    
    completeness = {}
    
    # TODO: 根据history数据格式实现
    print(f"   ⚠️  待实现: history数据扫描")
    
    return completeness

def scan_snapshots_data():
    """扫描data/snapshots/版本快照数据"""
    print("📊 扫描 data/snapshots/...")
    
    snapshots_dir = DATA_DIR / 'data' / 'snapshots'
    if not snapshots_dir.exists():
        print("   ❌ 目录不存在")
        return {}
    
    completeness = {}
    
    # TODO: 根据snapshots数据格式实现
    print(f"   ⚠️  待实现: snapshots数据扫描")
    
    return completeness

def merge_completeness(*scans):
    """合并多个扫描结果"""
    print("\n🔄 合并扫描结果...")
    
    merged = {}
    
    for scan in scans:
        for code, data in scan.items():
            if code not in merged:
                merged[code] = {
                    'code': code,
                    'name': data['name'],
                    'indicators': {},
                    'sources': [],
                    'updated_at': None
                }
            
            # 合并指标（不覆盖已有数据）
            for indicator, info in data['indicators'].items():
                if indicator not in merged[code]['indicators']:
                    merged[code]['indicators'][indicator] = info
            
            # 合并来源
            for src in data['sources']:
                if src not in merged[code]['sources']:
                    merged[code]['sources'].append(src)
            
            # 更新时间
            if data['updated_at'] and (not merged[code]['updated_at'] or str(data['updated_at']) > str(merged[code]['updated_at'])):
                merged[code]['updated_at'] = data['updated_at']
    
    print(f"   ✅ 合并完成: {len(merged)} 只ETF")
    return merged

def generate_completeness_table(merged_data):
    """生成完整度表格"""
    print("\n📋 生成完整度表格...")
    
    # 转换为列表
    table = []
    
    for code, data in sorted(merged_data.items()):
        row = {
            'code': code,
            'name': data['name'],
            'updated_at': data['updated_at'],
            'sources': ','.join(sorted(data['sources'])),
        }
        
        # 添加每个核心指标的状态
        for indicator in CORE_INDICATORS:
            en = indicator['en']
            if en in ['code', 'name', 'updated_at', 'data_source']:
                continue
            
            if en in data['indicators']:
                info = data['indicators'][en]
                row[f'{en}_value'] = info['value']
                row[f'{en}_source'] = info['source']
                row[f'{en}_updated'] = info['updated_at']
            else:
                row[f'{en}_value'] = None
                row[f'{en}_source'] = ''
                row[f'{en}_updated'] = ''
        
        table.append(row)
    
    print(f"   ✅ 表格生成: {len(table)} 行")
    return table

def save_database(table, merged_data):
    """保存数据库"""
    print("\n💾 保存数据库...")
    
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # 1. 保存完整度表格（JSON）
    table_file = OUTPUT_DIR / 'etf_core_indicators_completeness.json'
    with open(table_file, 'w', encoding='utf-8') as f:
        json.dump(table, f, ensure_ascii=False, indent=2)
    print(f"   ✅ 完整度表格: {table_file}")
    
    # 2. 保存核心指标定义（中英文对照）
    def_file = OUTPUT_DIR / 'core_indicators_definition.json'
    with open(def_file, 'w', encoding='utf-8') as f:
        json.dump(CORE_INDICATORS, f, ensure_ascii=False, indent=2)
    print(f"   ✅ 指标定义: {def_file}")
    
    # 3. 保存按数据源分类的数据
    all_sources = set()
    for data in merged_data.values():
        all_sources.update(data['sources'])
    
    for source in all_sources:
        source_data = {}
        for code, data in merged_data.items():
            if source in data['sources']:
                source_data[code] = data
        
        source_file = OUTPUT_DIR / f'data_by_source_{source}.json'
        with open(source_file, 'w', encoding='utf-8') as f:
            json.dump(source_data, f, ensure_ascii=False, indent=2)
        print(f"   ✅ 数据源 {source}: {source_file} ({len(source_data)} 只ETF)")
    
    # 4. 生成Markdown报告
    report_file = OUTPUT_DIR / 'completeness_report.md'
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(f"# ETF核心指标完整度报告\n\n")
        f.write(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write(f"ETF总数: {len(table)}\n\n")
        
        f.write("## 核心指标完整度统计\n\n")
        f.write("| 指标(中文) | 指标(英文) | 完整度 | 有数据ETF数 |\n")
        f.write("|-----------|-----------|--------|-------------|\n")
        
        for indicator in CORE_INDICATORS:
            en = indicator['en']
            if en in ['code', 'name', 'updated_at', 'data_source']:
                continue
            
            count = sum(1 for row in table if row.get(f'{en}_value') not in [None, '', 0])
            pct = count / len(table) * 100 if len(table) > 0 else 0
            f.write(f"| {indicator['zh']} | {en} | {pct:.1f}% | {count}/{len(table)} |\n")
        
        f.write("\n## 数据来源统计\n\n")
        source_counts = defaultdict(int)
        for row in table:
            for src in row['sources'].split(','):
                if src:
                    source_counts[src] += 1
        
        for src, cnt in sorted(source_counts.items()):
            f.write(f"- {src}: {cnt} 只ETF\n")
    
    print(f"   ✅ 报告: {report_file}")

def main():
    print("="*60)
    print("ETF核心指标完整度扫描 v2")
    print("="*60)
    
    # 扫描各数据源
    scan1 = scan_etf_standard_data()
    scan2 = scan_wind_cache()
    scan3 = scan_realtime_data()
    scan4 = scan_history_data()
    scan5 = scan_snapshots_data()
    
    # 合并
    merged = merge_completeness(scan1, scan2, scan3, scan4, scan5)
    
    # 生成表格
    table = generate_completeness_table(merged)
    
    # 保存
    save_database(table, merged)
    
    print("\n" + "="*60)
    print("✅ 完成")
    print("="*60)

if __name__ == '__main__':
    main()
