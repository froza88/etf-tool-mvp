#!/usr/bin/env python3
"""
update_data_version.py - 更新数据版本信息

功能：
1. 读取 etf_standard_data.json
2. 计算数据 checksum 和字段覆盖率
3. 更新 data_version.json
4. 标记同步状态 (local/github/pythonanywhere)

使用方式：
    python3 update_data_version.py [--source local|github|pythonanywhere]
"""

import json
import hashlib
import argparse
from datetime import datetime, timezone, timedelta
from pathlib import Path

def calculate_checksum(data):
    """计算数据 checksum"""
    data_str = json.dumps(data, ensure_ascii=False, sort_keys=True)
    return hashlib.md5(data_str.encode('utf-8')).hexdigest()

def calculate_coverage(data, fields):
    """计算字段覆盖率"""
    total = len(data)
    if total == 0:
        return {field: 0 for field in fields}
    
    coverage = {}
    for field in fields:
        count = sum(1 for e in data if e.get(field) is not None and e.get(field) != '')
        coverage[field] = round(count / total, 4)
    return coverage

def update_version(data_file='etf_standard_data.json', 
                   version_file='data_version.json',
                   source='local'):
    """
    更新数据版本信息
    
    Args:
        data_file: 数据文件路径
        version_file: 版本信息文件路径
        source: 数据来源 (local/github/pythonanywhere)
    """
    # 读取数据
    with open(data_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # 计算覆盖率 (检查关键字段)
    key_fields = ['year_3_return', 'issuer', 'shares', 'scale', 
                  'holdings', 'return_1y', 'sharp_ratio']
    coverage = calculate_coverage(data, key_fields)
    
    # 读取现有版本信息 (如果存在)
    version_path = Path(version_file)
    if version_path.exists():
        with open(version_file, 'r', encoding='utf-8') as f:
            old_version = json.load(f)
    else:
        old_version = {}
    
    # 创建新版本信息（合并已有的 sync_status）
    now = datetime.now(timezone(timedelta(hours=8)))
    
    # 合并 sync_status：保留旧状态，只更新当前 source 为 True
    old_sync_status = old_version.get('sync_status', {})
    new_sync_status = {
        'local': old_sync_status.get('local', False) or source == 'local',
        'github': old_sync_status.get('github', False) or source == 'github',
        'pythonanywhere': old_sync_status.get('pythonanywhere', False) or source == 'pythonanywhere'
    }
    
    new_version = {
        'version': now.isoformat(),
        'source': source,
        'checksum': calculate_checksum(data),
        'etf_count': len(data),
        'fields_coverage': coverage,
        'sync_status': new_sync_status
    }
    
    # 保存
    with open(version_file, 'w', encoding='utf-8') as f:
        json.dump(new_version, f, ensure_ascii=False, indent=2)
    
    print(f"✅ Updated {version_file}")
    print(f"   Version: {new_version['version']}")
    print(f"   Source: {new_version['source']}")
    print(f"   ETF Count: {new_version['etf_count']}")
    print(f"   Checksum: {new_version['checksum'][:16]}...")
    print(f"   Coverage: {coverage}")
    
    return new_version

def main():
    parser = argparse.ArgumentParser(description='更新数据版本信息')
    parser.add_argument('--source', choices=['local', 'github', 'pythonanywhere'],
                       default='local', help='数据来源')
    parser.add_argument('--data-file', default='etf_standard_data.json',
                       help='数据文件路径')
    parser.add_argument('--version-file', default='data_version.json',
                       help='版本信息文件路径')
    
    args = parser.parse_args()
    
    update_version(
        data_file=args.data_file,
        version_file=args.version_file,
        source=args.source
    )

if __name__ == '__main__':
    main()
