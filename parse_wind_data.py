#!/usr/bin/env python3
"""
解析Wind下载的数据，生成数据完整度报告
"""
import json
from pathlib import Path
from collections import defaultdict

def parse_wind_file(json_file):
    """解析单个Wind数据文件，返回字段字典"""
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if data.get('isError') or not data.get('content'):
            return None
        
        inner = json.loads(data['content'][0]['text'])
        if 'data' not in inner or 'data' not in inner['data']:
            return None
        
        wind_data = inner['data']['data']
        fields = {}
        
        for ds in wind_data:
            columns = [col['name'] for col in ds['columns']]
            if ds.get('rows'):
                row = ds['rows'][0]
                for col_name, val in zip(columns, row):
                    if val is not None and val != '' and val != 0:
                        fields[col_name] = val
        
        return fields
    except:
        return None

def main():
    print("=" * 80)
    print("解析Wind数据 - 生成数据完整度报告")
    print("=" * 80)
    print()
    
    # 1. 加载所有已下载的Wind数据
    wind_dir = Path("/Users/apangduo/WorkBuddy/Claw/etf-tool-mvp/data/wind_full")
    wind_files = list(wind_dir.glob("*.json"))
    
    print(f"📂 已下载Wind数据: {len(wind_files)} 只ETF")
    print()
    
    # 2. 解析所有文件，统计字段完整度
    print("🔍 解析数据中...")
    field_stats = defaultdict(lambda: {'count': 0, 'sample': None, 'values': []})
    parsed_count = 0
    
    for json_file in wind_files:
        fields = parse_wind_file(json_file)
        if fields is None:
            continue
        
        parsed_count += 1
        for field_name, value in fields.items():
            field_stats[field_name]['count'] += 1
            if field_stats[field_name]['sample'] is None:
                field_stats[field_name]['sample'] = value
            field_stats[field_name]['values'].append(value)
    
    print(f"✅ 成功解析: {parsed_count} 只ETF")
    print()
    
    # 3. 生成报告
    print("=" * 80)
    print("Wind数据字段完整度报告")
    print("=" * 80)
    print()
    print(f"统计基于: {parsed_count} 只ETF")
    print(f"总字段数: {len(field_stats)}")
    print()
    
    # 按完整度排序
    sorted_fields = sorted(field_stats.items(), key=lambda x: -x[1]['count'])
    
    print(f"{'字段名(中文)':<40} {'有值数':<10} {'完整度':<12} {'示例值'}")
    print("-" * 120)
    
    for field_name, stats in sorted_fields:
        completeness = stats['count'] / parsed_count * 100
        sample = str(stats['sample'])[:60] if stats['sample'] else '(空)'
        print(f"{field_name:<40} {stats['count']:<10} {completeness:>10.1f}%  {sample}")
    
    print()
    print("=" * 80)
    
    # 4. 保存报告
    report_file = Path("/Users/apangduo/WorkBuddy/Claw/etf-tool-mvp/reports/wind_data_completeness_20260530.md")
    report_file.parent.mkdir(exist_ok=True)
    
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write("# Wind数据字段完整度报告\n\n")
        f.write(f"统计时间: 2026-05-30\n")
        f.write(f"统计基于: {parsed_count} 只ETF\n\n")
        f.write("## 字段完整度（按完整度降序）\n\n")
        f.write("| 字段名(中文) | 有值数 | 完整度 | 示例值 |\n")
        f.write("|-------------|--------|--------|--------|\n")
        
        for field_name, stats in sorted_fields:
            completeness = stats['count'] / parsed_count * 100
            sample = str(stats['sample'])[:50] if stats['sample'] else '(空)'
            f.write(f"| {field_name} | {stats['count']} | {completeness:.1f}% | {sample} |\n")
    
    print(f"📄 报告已保存: {report_file}")
    print()

if __name__ == "__main__":
    main()
