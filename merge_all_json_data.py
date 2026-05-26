#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
合并所有JSON数据文件，取并集，计算数据完整度
"""

import json
import os
from collections import defaultdict

def load_json(filepath):
    """加载JSON文件"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ 读取失败 {filepath}: {e}")
        return None

def analyze_json_structure(data, name):
    """分析JSON文件结构"""
    result = {
        'name': name,
        'type': type(data).__name__,
        'total': 0,
        'fields': [],
        'sample_keys': []
    }
    
    if isinstance(data, list):
        result['total'] = len(data)
        if len(data) > 0 and isinstance(data[0], dict):
            result['fields'] = list(data[0].keys())
            result['sample_keys'] = list(data[0].keys())[:10]
    elif isinstance(data, dict):
        result['total'] = len(data)
        result['sample_keys'] = list(data.keys())[:10]
        
        # 尝试获取第一个值的字段
        if len(data) > 0:
            first_key = list(data.keys())[0]
            first_val = data[first_key]
            if isinstance(first_val, dict):
                result['fields'] = list(first_val.keys())
    
    return result

def merge_data_union(standard_data, other_files):
    """
    合并数据取并集
    standard_data: 主数据（list of dicts）
    other_files: 其他JSON文件（dict of dicts，key是ETF代码）
    """
    # 创建以code为key的字典
    merged = {}
    for etf in standard_data:
        code = etf.get('code', '')
        if code:
            merged[code] = dict(etf)  # 复制
    
    print(f"✅ 主数据加载: {len(merged)} 只ETF")
    
    # 合并其他文件
    for file_info in other_files:
        fname = file_info['name']
        data = file_info['data']
        
        if data is None:
            continue
        
        if isinstance(data, dict):
            # dict格式，key是ETF代码
            count = 0
            for code, etf_data in data.items():
                if code not in merged:
                    merged[code] = {'code': code}  # 新建
                
                # 合并字段（取并集，不覆盖已有数据）
                if isinstance(etf_data, dict):
                    for key, value in etf_data.items():
                        if key not in merged[code] or merged[code][key] is None or merged[code][key] == '':
                            merged[code][key] = value
                            count += 1
            
            print(f"✅ {fname}: 合并 {len(data)} 只ETF，更新 {count} 个字段")
        
        elif isinstance(data, list):
            # list格式
            count = 0
            for etf_data in data:
                code = etf_data.get('code', '')
                if not code:
                    continue
                
                if code not in merged:
                    merged[code] = {'code': code}
                
                # 合并字段
                for key, value in etf_data.items():
                    if key != 'code' and (key not in merged[code] or merged[code][key] is None or merged[code][key] == ''):
                        merged[code][key] = value
                        count += 1
            
            print(f"✅ {fname}: 合并 {len(data)} 只ETF，更新 {count} 个字段")
    
    return merged

def calculate_completeness(merged_data):
    """计算数据完整度"""
    # 收集所有字段
    all_fields = set()
    for code, etf_data in merged_data.items():
        all_fields.update(etf_data.keys())
    
    # 排除code字段
    if 'code' in all_fields:
        all_fields.remove('code')
    
    all_fields = sorted(list(all_fields))
    
    # 计算每个字段的完整度
    completeness = {}
    total_etfs = len(merged_data)
    
    for field in all_fields:
        valid_count = 0
        for code, etf_data in merged_data.items():
            value = etf_data.get(field)
            if value is not None and value != '' and value != 0:
                valid_count += 1
        
        completeness[field] = {
            'valid': valid_count,
            'total': total_etfs,
            'rate': valid_count / total_etfs if total_etfs > 0 else 0
        }
    
    return completeness, all_fields

def classify_fields(completeness, all_fields):
    """按完整度分类字段（初级/中级/高级）"""
    classified = {
        '初级': [],  # ≥90%
        '中级': [],  # 10-89%
        '高级': []   # <10%
    }
    
    for field in all_fields:
        rate = completeness[field]['rate']
        if rate >= 0.9:
            classified['初级'].append(field)
        elif rate >= 0.1:
            classified['中级'].append(field)
        else:
            classified['高级'].append(field)
    
    return classified

def main():
    print("=" * 60)
    print("合并所有JSON数据文件，取并集，计算数据完整度")
    print("=" * 60)
    print()
    
    base_dir = '/Users/apangduo/WorkBuddy/Claw/etf-tool-mvp'
    
    # 1. 加载主数据
    print("【步骤1】加载主数据文件...")
    standard_data_file = os.path.join(base_dir, 'etf_standard_data.json')
    standard_data = load_json(standard_data_file)
    
    if standard_data is None:
        print("❌ 主数据文件读取失败，退出")
        return
    
    # 2. 加载其他JSON文件
    print("\n【步骤2】加载其他JSON数据文件...")
    other_files = []
    
    json_files = [
        'etf_wind_data.json',
        'etf_yingmi_metrics.json',
        'etf_calculated_metrics.json',
        'etf_risk_metrics.json',
        'etf_complete_all.json',
        'etf_data_generated.json',
        'etf_history_cache.json',
        'etf_prices.json'
    ]
    
    for fname in json_files:
        fpath = os.path.join(base_dir, fname)
        if os.path.exists(fpath):
            data = load_json(fpath)
            other_files.append({'name': fname, 'data': data})
        else:
            print(f"⚠️  {fname}: 文件不存在")
    
    # 3. 合并数据取并集
    print("\n【步骤3】合并数据取并集...")
    merged = merge_data_union(standard_data, other_files)
    print(f"✅ 合并完成: 共 {len(merged)} 只ETF")
    
    # 4. 计算数据完整度
    print("\n【步骤4】计算数据完整度...")
    completeness, all_fields = calculate_completeness(merged)
    print(f"✅ 共 {len(all_fields)} 个字段")
    
    # 5. 分类字段
    print("\n【步骤5】按完整度分类字段...")
    classified = classify_fields(completeness, all_fields)
    print(f"✅ 初级(≥90%): {len(classified['初级'])} 个")
    print(f"✅ 中级(10-89%): {len(classified['中级'])} 个")
    print(f"✅ 高级(<10%): {len(classified['高级'])} 个")
    
    # 6. 生成报告
    print("\n【步骤6】生成数据完整度报告...")
    
    # 控制台输出
    print("\n" + "=" * 60)
    print("数据完整度报告（合并后）")
    print("=" * 60)
    print()
    
    print(f"总ETF数: {len(merged)}")
    print(f"总字段数: {len(all_fields)}")
    print()
    
    # 按级别展示
    for level in ['初级', '中级', '高级']:
        fields = classified[level]
        print(f"{'🟢' if level=='初级' else '🟡' if level=='中级' else '🔴'} {level}（{len(fields)}字段，完整度{'≥90%' if level=='初级' else '10-89%' if level=='中级' else '<10%'}）")
        print("-" * 60)
        
        # 按完整度降序排列
        fields_sorted = sorted(fields, key=lambda x: completeness[x]['rate'], reverse=True)
        
        for field in fields_sorted:
            info = completeness[field]
            rate_pct = info['rate'] * 100
            print(f"  {field:30s} {info['valid']:4d}/{info['total']:4d}  {rate_pct:6.2f}%")
        
        print()
    
    # 保存详细报告到JSON
    report = {
        'total_etfs': len(merged),
        'total_fields': len(all_fields),
        'completeness': {k: v for k, v in completeness.items()},
        'classified': classified
    }
    
    report_file = os.path.join(base_dir, 'merged_data_completeness_report.json')
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    print(f"✅ 详细报告已保存: {report_file}")
    
    # 保存合并后的数据（可选）
    merged_file = os.path.join(base_dir, 'etf_merged_all_data.json')
    merged_list = list(merged.values())
    with open(merged_file, 'w', encoding='utf-8') as f:
        json.dump(merged_list, f, ensure_ascii=False, indent=2)
    
    print(f"✅ 合并数据已保存: {merged_file}")
    print()
    print("=" * 60)
    print("完成！")
    print("=" * 60)

if __name__ == '__main__':
    main()
