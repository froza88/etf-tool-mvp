#!/usr/bin/env python3
"""
Wind 数据获取 + 本地缓存脚本
每次查询 Wind 前先查缓存，有数据就用缓存，没有才调用 Wind API
调用成功后自动更新 etf_standard_data.json + wind_cache.json

用法：
  python scripts/wind_data_fetcher.py --codes 511670 512190  # 指定ETF代码
  python scripts/wind_data_fetcher.py --all                 # 全部ETF
  python scripts/wind_data_fetcher.py --missing issuer     # 只补 issuer 缺失的
"""

import json
import os
import sys
import argparse
import subprocess
import time
from datetime import datetime, timedelta

# 项目根目录
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
ETF_DATA_FILE = os.path.join(PROJECT_ROOT, "etf_standard_data.json")
WIND_CACHE_FILE = os.path.join(DATA_DIR, "wind_cache.json")

# Wind CLI 路径
WIND_CLI = os.path.expanduser("~/.agents/skills/wind-mcp-skill/scripts/cli.mjs")

# 缓存有效期（天）
CACHE_VALID_DAYS = 7

# Wind API 单次调用成本（积分）
WIND_COST_PER_CALL = 6.67  # 40积分 / 6次 = 6.67积分/次


def load_etf_data():
    """加载 ETF 标准数据"""
    with open(ETF_DATA_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_etf_data(data):
    """保存 ETF 标准数据"""
    # 备份
    backup_file = os.path.join(
        DATA_DIR, 
        f"etf_standard_data_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    )
    import shutil
    shutil.copy2(ETF_DATA_FILE, backup_file)
    print(f"✓ 已备份到: {backup_file}")
    
    # 保存
    with open(ETF_DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"✓ 数据已写入: {ETF_DATA_FILE}")


def load_wind_cache():
    """加载 Wind 缓存数据"""
    if os.path.exists(WIND_CACHE_FILE):
        with open(WIND_CACHE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


def save_wind_cache(cache):
    """保存 Wind 缓存数据"""
    os.makedirs(os.path.dirname(WIND_CACHE_FILE), exist_ok=True)
    with open(WIND_CACHE_FILE, 'w', encoding='utf-8') as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)


def is_cache_valid(cache_item, valid_days=CACHE_VALID_DAYS):
    """检查缓存是否有效（未过期）"""
    if not cache_item:
        return False
    
    fetch_time_str = cache_item.get('_wind_fetch_time')
    if not fetch_time_str:
        return False
    
    try:
        fetch_time = datetime.fromisoformat(fetch_time_str)
        return datetime.now() - fetch_time < timedelta(days=valid_days)
    except:
        return False


def call_wind_api(code, api_name, question):
    """
    调用 Wind API
    
    Args:
        code: ETF代码（如 511670）
        api_name: API名称（如 fund_data get_fund_info）
        question: 查询问题（如 "511670基金档案"）
    
    Returns:
        dict: 解析后的数据，或 None（如果失败）
    """
    cmd = [
        "node",
        WIND_CLI,
        "call",
        "fund_data",
        api_name,
        json.dumps({"question": question, "lang": "中文"})
    ]
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
            cwd=os.path.dirname(WIND_CLI)
        )
        
        if result.returncode != 0:
            print(f"  ✗ Wind API 调用失败 (exit code {result.returncode})")
            print(f"  stderr: {result.stderr[:200]}")
            return None
        
        # 解析返回数据
        output = json.loads(result.stdout)
        text = output['content'][0]['text']
        inner_data = json.loads(text)
        
        columns = inner_data['data']['data'][0]['columns']
        rows = inner_data['data']['data'][0]['rows']
        
        if not rows:
            print(f"  ✗ Wind API 返回空数据")
            return None
        
        # 提取第一行数据
        row = rows[0]
        data = {}
        for i, col in enumerate(columns):
            data[col['name']] = row[i]
        
        return data
        
    except subprocess.TimeoutExpired:
        print(f"  ✗ Wind API 调用超时")
        return None
    except Exception as e:
        print(f"  ✗ Wind API 调用异常: {e}")
        return None


def parse_wind_fund_info(wind_data):
    """
    解析 Wind get_fund_info 返回的数据，映射到我们的字段
    
    Wind 字段 -> 我们字段：
      基金管理人 -> issuer
      基金成立日 -> issue_date
      基金托管人 -> custodian
      管理费率 -> management_fee_rate
      托管费率 -> custody_fee_rate
      业绩比较基准 -> benchmark
      基金经理 -> fund_manager
    """
    mapping = {
        '基金管理人': 'issuer',
        '基金成立日': 'issue_date',
        '基金托管人': 'custodian',
        '管理费率': 'management_fee_rate',
        '托管费率': 'custody_fee_rate',
        '业绩比较基准': 'benchmark',
        '基金经理': 'fund_manager'
    }
    
    result = {}
    for wind_field, our_field in mapping.items():
        if wind_field in wind_data:
            value = wind_data[wind_field]
            # 处理费率（去掉 % 符号）
            if our_field in ['management_fee_rate', 'custody_fee_rate']:
                if isinstance(value, str):
                    value = value.replace('%', '').strip()
                    try:
                        value = float(value)
                    except:
                        value = None
            result[our_field] = value
    
    return result


def fetch_etf_from_wind(code, name, cache, dry_run=False):
    """
    从 Wind 获取单只 ETF 的数据（先查缓存，缓存未命中才调用 API）
    
    Args:
        dry_run: 如果 True，则不调用 Wind API，只模拟
    
    Returns:
        dict: 获取到的数据，或 None
    """
    # 检查缓存
    if code in cache and is_cache_valid(cache[code]):
        print(f"  ✓ 缓存有效，使用缓存数据")
        return cache[code]
    
    # 缓存无效
    if dry_run:
        print(f"  → [dry-run] 缓存无效，模拟调用 Wind API (get_fund_info)...")
        return None  # dry-run 模式下不返回真实数据
    
    # 非 dry-run 模式，调用 Wind API
    print(f"  → 调用 Wind API (get_fund_info)...")
    
    wind_data = call_wind_api(code, "get_fund_info", f"{code}{name}基金档案")
    
    if not wind_data:
        return None
    
    # 解析 Wind 数据
    parsed_data = parse_wind_fund_info(wind_data)
    
    # 更新缓存
    cache_item = parsed_data.copy()
    cache_item['_wind_fetch_time'] = datetime.now().isoformat()
    cache_item['_wind_fetch_days'] = CACHE_VALID_DAYS
    cache[code] = cache_item
    
    print(f"  ✓ Wind API 成功，获取到 {len(parsed_data)} 个字段")
    return parsed_data


def update_etf_data(etf_list, cache, dry_run=False):
    """
    更新 ETF 数据
    
    Args:
        etf_list: ETF 列表
        cache: Wind 缓存
        dry_run: 是否只模拟，不实际修改
    """
    updated_count = 0
    api_call_count = 0
    cache_hit_count = 0
    
    for i, etf in enumerate(etf_list):
        code = str(etf['code'])
        name = etf.get('name', '')
        
        print(f"\n[{i+1}/{len(etf_list)}] {code} | {name}")
        
        # 从 Wind 获取数据（或缓存）
        wind_data = fetch_etf_from_wind(code, name, cache, dry_run=dry_run)
        
        if not wind_data:
            print(f"  ✗ 获取失败，跳过")
            continue
        
        # 检查是 API 调用还是缓存命中
        if code in cache and is_cache_valid(cache[code]):
            cache_hit_count += 1
        else:
            api_call_count += 1
        
        # 更新 ETF 数据（只填充缺失字段）
        updated_fields = []
        for field, value in wind_data.items():
            if field.startswith('_'):
                continue  # 跳过内部字段
            
            if field not in etf or etf[field] is None or etf[field] == '':
                if not dry_run:
                    etf[field] = value
                updated_fields.append(field)
        
        if updated_fields:
            print(f"  ✓ 更新字段: {', '.join(updated_fields)}")
            updated_count += 1
        else:
            print(f"  - 无需更新（字段已存在）")
        
        # 避免 QPS 限制，等待 1 秒
        if api_call_count > 0 and api_call_count % 10 == 0:
            print(f"  (已调用 {api_call_count} 次 API，等待 1 秒...)")
            time.sleep(1)
    
    print(f"\n=== 更新完成 ===")
    print(f"处理 ETF 数量: {len(etf_list)}")
    print(f"更新 ETF 数量: {updated_count}")
    print(f"API 调用次数: {api_call_count}")
    print(f"缓存命中次数: {cache_hit_count}")
    print(f"预估消耗积分: {api_call_count * WIND_COST_PER_CALL:.0f}")
    
    return updated_count, api_call_count


def main():
    parser = argparse.ArgumentParser(description='Wind 数据获取 + 本地缓存脚本')
    parser.add_argument('--codes', nargs='+', help='指定 ETF 代码列表')
    parser.add_argument('--all', action='store_true', help='处理全部 ETF')
    parser.add_argument('--missing', type=str, help='只处理指定字段缺失的 ETF (如: issuer)')
    parser.add_argument('--dry-run', action='store_true', help='只模拟，不实际修改数据')
    parser.add_argument('--force', action='store_true', help='强制重新调用 Wind API（忽略缓存）')
    
    args = parser.parse_args()
    
    # 加载数据
    print("=== Wind 数据获取脚本 ===\n")
    print("加载 ETF 数据...")
    etf_data = load_etf_data()
    print(f"✓ 加载 {len(etf_data)} 只 ETF")
    
    print("\n加载 Wind 缓存...")
    cache = load_wind_cache()
    print(f"✓ 缓存中有 {len(cache)} 只 ETF")
    
    # 确定要处理的 ETF 列表
    if args.codes:
        etf_list = [etf for etf in etf_data if str(etf['code']) in args.codes]
        print(f"\n指定处理 {len(etf_list)} 只 ETF: {args.codes}")
    elif args.missing:
        field = args.missing
        etf_list = [etf for etf in etf_data if not etf.get(field) or etf.get(field) == '']
        print(f"\n字段 '{field}' 缺失的 ETF: {len(etf_list)} 只")
    elif args.all:
        etf_list = etf_data
        print(f"\n处理全部 {len(etf_list)} 只 ETF")
    else:
        print("\n错误: 请指定 --codes, --all 或 --missing")
        parser.print_help()
        return
    
    if not etf_list:
        print("没有需要处理的 ETF，退出")
        return
    
    # 如果 --force，清空缓存
    if args.force:
        print("\n--force 模式：清空缓存，强制重新调用 Wind API")
        cache = {}
    
    # 更新数据
    print(f"\n{'='*50}")
    print("开始处理...")
    print(f"{'='*50}\n")
    
    updated_count, api_call_count = update_etf_data(etf_list, cache, dry_run=args.dry_run)
    
    # 保存结果
    if not args.dry_run and updated_count > 0:
        print(f"\n{'='*50}")
        print("保存结果...")
        print(f"{'='*50}\n")
        
        # 保存 ETF 数据
        save_etf_data(etf_data)
        
        # 保存缓存
        save_wind_cache(cache)
        print(f"✓ 缓存已写入: {WIND_CACHE_FILE}")
        
        print(f"\n✓ 全部完成！")
    elif args.dry_run:
        print(f"\n⚠️  dry-run 模式，未实际修改数据")
    else:
        print(f"\n⚠️  没有更新任何数据")


if __name__ == '__main__':
    main()
