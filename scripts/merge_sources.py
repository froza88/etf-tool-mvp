#!/usr/bin/env python3
"""合并各数据源的字段到 etf_standard_data.json
每个数据源写自己的域文件，此脚本安全合并，源文件不存在则跳过
"""
import json
import os
import argparse
from datetime import datetime

SOURCE_FILES = {
    'scrapling': 'etf_scrapling_fields.json',
    'ifind_valuation': 'etf_valuation_fields.json',
    'wind_flow': 'etf_flow_fields.json',
}

def load_json(path):
    if not os.path.exists(path):
        return None
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_json(path, data):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def merge(target_file='etf_standard_data.json', sources=None):
    if sources is None:
        sources = list(SOURCE_FILES.keys())

    if not os.path.exists(target_file):
        print(f'目标文件不存在: {target_file}')
        return

    with open(target_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    total = len(data)
    code_index = {}
    for i, e in enumerate(data):
        code_index[e['code']] = i

    merged_stats = {}
    for src_name in sources:
        fname = SOURCE_FILES.get(src_name)
        if not fname:
            continue
        src_data = load_json(fname)
        if not src_data:
            print(f'  跳过 {src_name}: 文件不存在')
            continue

        updated = 0
        fields_filled = set()
        for item in src_data:
            code = item.get('code')
            if not code or code not in code_index:
                continue
            idx = code_index[code]
            for key, val in item.items():
                if key == 'code':
                    continue
                if val not in (None, '', 0):
                    data[idx][key] = val
                    if key.endswith('_source'):
                        continue
                    fields_filled.add(key)
                    updated += 1

        merged_stats[src_name] = {'updated': updated, 'fields': list(fields_filled)}
        print(f'  {src_name}: +{len(src_data)}ETF, {updated}字段填充')

    save_json(target_file, data)

    # Print summary
    print(f'\n目标文件: {target_file}')
    print(f'ETF总数: {total}')
    for src_name, stats in merged_stats.items():
        print(f'  {src_name}: 源{len(load_json(SOURCE_FILES[src_name]))}只 → {stats["updated"]}个字段')

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='合并数据源域文件')
    parser.add_argument('--target', default='etf_standard_data.json', help='目标文件')
    parser.add_argument('--sources', nargs='+', help='要合并的源（默认全部）')
    args = parser.parse_args()

    os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    merge(args.target, args.sources)
