#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
频率文件合并脚本：从5个频率文件合并生成 etf_standard_data.json

使用方法：
    python3 merge_frequency_to_standard.py

功能：
1. 从 etf_static.json, etf_annual.json, etf_quarterly.json, etf_monthly.json, etf_daily.json 读取数据
2. 合并成一个完整的数据集
3. 保存为 etf_standard_data.json

作者: AI Assistant
日期: 2026-05-28
"""

import json
import os
import sys
from datetime import datetime

# 频率文件列表
FREQUENCY_FILES = [
    'etf_static.json',
    'etf_annual.json',
    'etf_quarterly.json',
    'etf_monthly.json',
    'etf_daily.json'
]

# 输出文件
OUTPUT_FILE = 'etf_standard_data.json'

def load_frequency_files():
    """加载所有频率文件"""
    print(f"📂 加载频率文件...")
    
    frequency_data = {}
    for filename in FREQUENCY_FILES:
        if not os.path.exists(filename):
            print(f"  ⚠️  {filename} 不存在，跳过")
            frequency_data[filename] = []
            continue
        
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                data = json.load(f)
            print(f"  ✅ {filename}: {len(data)} 只ETF")
            frequency_data[filename] = data
        except Exception as e:
            print(f"  ❌ 加载 {filename} 失败: {e}")
            frequency_data[filename] = []
    
    return frequency_data

def merge_to_standard(frequency_data):
    """合并频率文件到标准格式"""
    print(f"\n🔄 合并数据...")
    
    # 以 etf_static.json 为基准（包含所有ETF的code）
    static_data = frequency_data.get('etf_static.json', [])
    if not static_data:
        print(f"  ❌ etf_static.json 为空，无法合并")
        return []
    
    # 创建 code->index 映射
    code_index = {etf['code']: i for i, etf in enumerate(static_data)}
    
    # 从其他频率文件合并数据
    for filename in FREQUENCY_FILES[1:]:  # 跳过 etf_static.json
        freq_data = frequency_data.get(filename, [])
        if not freq_data:
            continue
        
        print(f"  合并 {filename}...")
        merged_count = 0
        
        for freq_etf in freq_data:
            code = freq_etf.get('code')
            if code not in code_index:
                continue  # 跳过不在static中的ETF
            
            idx = code_index[code]
            # 增量合并：只填充缺失字段
            for key, value in freq_etf.items():
                if key == 'code':
                    continue
                if value is None or value == '' or value == 0:
                    continue  # 跳过空值
                if key not in static_data[idx] or static_data[idx][key] is None or static_data[idx][key] == '':
                    static_data[idx][key] = value
                    merged_count += 1
        
        print(f"    ✅ 合并 {merged_count} 个字段")
    
    print(f"✅ 合并完成: {len(static_data)} 只ETF")
    return static_data

def save_standard_data(standard_data):
    """保存为标准格式"""
    print(f"\n💾 保存为标准格式: {OUTPUT_FILE}")
    
    try:
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            json.dump(standard_data, f, ensure_ascii=False, indent=2)
        
        file_size = os.path.getsize(OUTPUT_FILE) / 1024 / 1024  # MB
        print(f"✅ 保存成功: {len(standard_data)} 只ETF, {file_size:.2f} MB")
        return True
    except Exception as e:
        print(f"❌ 保存失败: {e}")
        return False

def verify_data(standard_data):
    """验证合并后的数据质量"""
    print(f"\n📊 验证数据质量...")
    
    total = len(standard_data)
    if total == 0:
        print(f"  ❌ 数据为空")
        return
    
    # 统计关键字段的填充率
    key_fields = ['name', 'issuer', 'scale', 'close', 'year_1_return', 'max_drawdown', 'sharpe_ratio']
    stats = {}
    
    for field in key_fields:
        filled = sum(1 for etf in standard_data if etf.get(field) is not None and etf.get(field) != '' and etf.get(field) != 0)
        rate = filled / total * 100
        stats[field] = (filled, total, rate)
        print(f"  {field}: {filled}/{total} ({rate:.1f}%)")
    
    # 检查是否有ETF完全没有数据
    empty_etfs = [etf for etf in standard_data if len(etf) <= 1]  # 只有code字段
    if empty_etfs:
        print(f"  ⚠️  有 {len(empty_etfs)} 只ETF没有数据（只有code字段）")
    else:
        print(f"  ✅ 所有ETF都有数据")

def main():
    """主函数"""
    print("=" * 60)
    print("🔀 频率文件合并工具")
    print("=" * 60)
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # 1. 加载频率文件
    frequency_data = load_frequency_files()
    
    # 2. 合并为标准格式
    standard_data = merge_to_standard(frequency_data)
    
    if not standard_data:
        print(f"\n❌ 合并失败，退出")
        return
    
    # 3. 验证数据质量
    verify_data(standard_data)
    
    # 4. 保存为标准格式
    success = save_standard_data(standard_data)
    
    if success:
        print(f"\n🎉 合并完成！")
        print(f"下一步: 检查 {OUTPUT_FILE} 的数据质量，确认无误后可以部署")
    else:
        print(f"\n❌ 合并失败，请检查错误信息")

if __name__ == '__main__':
    main()
