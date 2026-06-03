#!/usr/bin/env python3
"""
Wind API 批量补充 custodian 字段
- 读取 etf_standard_data.json
- 找出 custodian 为空的 ETF
- 逐个调用 Wind API 获取 custodian
- 更新 JSON 文件
- 支持断点续跑（progress.json）
- 请求间隔 3 秒，避免限流
"""
import sys
import json
import time
import argparse
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

from fetchers.wind_fetcher import WindFetcher

DATA_FILE = Path(__file__).parent / 'etf_standard_data.json'
PROGRESS_FILE = Path(__file__).parent / 'wind_update_progress.json'

def load_data():
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
    etfs = data if isinstance(data, list) else data['etfs']
    is_list = isinstance(data, list)
    return etfs, data, is_list

def save_data(etfs, original_data, is_list):
    if is_list:
        output = etfs
    else:
        original_data['etfs'] = etfs
        original_data['updated_at'] = datetime.now().isoformat()
        output = original_data
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"  💾 已保存 {DATA_FILE.name}")

def load_progress():
    if PROGRESS_FILE.exists():
        with open(PROGRESS_FILE, 'r') as f:
            return json.load(f)
    return {'processed': [], 'failed': [], 'last_index': 0}

def save_progress(progress):
    with open(PROGRESS_FILE, 'w') as f:
        json.dump(progress, f, ensure_ascii=False, indent=2)

def get_custodian_from_wind(wind_data):
    """从 Wind 返回数据中提取 custodian"""
    if not wind_data:
        return None
    # 优先取标准字段名
    custodian = wind_data.get('custodian')
    if not custodian:
        # 尝试取中文字段名
        custodian = wind_data.get('基金托管人')
    return custodian

def batch_update_custodian(dry_run=False, interval=3, limit=None):
    """
    Args:
        dry_run: 模拟运行，不实际修改
        interval: 请求间隔（秒）
        limit: 最大处理数量（测试用）
    """
    etfs, original_data, is_list = load_data()
    
    # 找出 custodian 为空的 ETF
    missing = []
    for i, etf in enumerate(etfs):
        custodian = etf.get('custodian')
        if not custodian or custodian == '':
            missing.append((i, etf['code'], etf.get('name', '')))
    
    print(f"📊 总 ETF 数: {len(etfs)}")
    print(f"❌ 缺失 custodian: {len(missing)}")
    
    if limit:
        missing = missing[:limit]
        print(f"🔪 限制处理: {len(missing)} 只（测试模式）")
    
    if dry_run:
        print(f"\n🔍 [DRY RUN] 将处理前 5 只作为样本:")
        for idx, code, name in missing[:5]:
            print(f"  - {code} {name}")
        return
    
    # 加载进度（断点续跑）
    progress = load_progress()
    processed_codes = set(progress.get('processed', []))
    failed_codes = set(progress.get('failed', []))
    
    # 过滤已处理的
    todo = [(i, c, n) for i, c, n in missing if c not in processed_codes]
    print(f"\n🚀 开始批量更新（待处理: {len(todo)}，已处理: {len(processed_codes)}）")
    print(f"⏱️  请求间隔: {interval}s，预计耗时: {len(todo) * interval / 60:.1f} 分钟")
    print(f"{'='*60}")
    
    fetcher = WindFetcher()
    updated_count = 0
    error_count = 0
    
    for batch_start in range(0, len(todo), 10):
        batch = todo[batch_start:batch_start+10]
        
        for idx, code, name in batch:
            print(f"\n[{batch_start + todo.index((idx, code, name)) + 1}/{len(todo)}] {code} {name}")
            
            try:
                # 调用 Wind API（使用缓存，避免重复调用）
                wind_data = fetcher.fetch_etf_info(code, name, force_refresh=False)
                
                custodian = get_custodian_from_wind(wind_data)
                
                if custodian:
                    etfs[idx]['custodian'] = custodian
                    print(f"  ✓ custodian: {custodian}")
                    updated_count += 1
                    progress['processed'].append(code)
                else:
                    print(f"  ⚠️  Wind 未返回 custodian")
                    failed_codes.add(code)
                    progress['failed'].append(code)
                
            except Exception as e:
                print(f"  ✗ 异常: {e}")
                failed_codes.add(code)
                progress['failed'].append(code)
                error_count += 1
            
            # 请求间隔
            if interval > 0:
                time.sleep(interval)
        
        # 每 10 只保存一次进度
        save_progress({
            'processed': list(set(progress['processed'])),
            'failed': list(set(progress['failed'])),
            'last_batch': batch_start + 10,
            'updated_count': updated_count,
            'error_count': error_count,
            'timestamp': datetime.now().isoformat()
        })
        
        # 每 10 只保存一次数据文件
        save_data(etfs, original_data, is_list)
        print(f"\n💾 批次保存完成（{batch_start + len(batch)}/{len(todo)}）")
    
    # 最终保存
    save_data(etfs, original_data, is_list)
    save_progress({
        'processed': list(set(progress['processed'])),
        'failed': list(set(progress['failed'])),
        'completed': True,
        'updated_count': updated_count,
        'error_count': error_count,
        'timestamp': datetime.now().isoformat()
    })
    
    print(f"\n{'='*60}")
    print(f"✅ 批量更新完成！")
    print(f"  ✓ 成功更新: {updated_count}")
    print(f"  ✗ 失败: {error_count}")
    print(f"  📁 数据已保存: {DATA_FILE}")
    print(f"  📋 进度已保存: {PROGRESS_FILE}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true', help='模拟运行')
    parser.add_argument('--interval', type=int, default=3, help='请求间隔（秒），默认3')
    parser.add_argument('--limit', type=int, default=None, help='最大处理数量（测试）')
    args = parser.parse_args()
    
    batch_update_custodian(dry_run=args.dry_run, interval=args.interval, limit=args.limit)
