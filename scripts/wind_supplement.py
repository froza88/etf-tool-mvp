#!/usr/bin/env python3
"""
从 Wind API 补充 ETF 数据

此脚本会：
1. 加载当前 ETF 数据
2. 对每只 ETF 调用 Wind API (get_fund_info)
3. 解析所有返回字段并存储
4. 保存更新后的数据

用法：
  python scripts/wind_supplement.py --dry-run  # 模拟运行
  python scripts/wind_supplement.py --limit 10  # 只处理 10 只
  python scripts/wind_supplement.py  # 全量运行
"""

import json
import os
import sys
import argparse
import subprocess
import time
from datetime import datetime, timedelta
from pathlib import Path

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
ETF_DATA_FILE = PROJECT_ROOT / "etf_standard_data.json"
WIND_CACHE_DIR = DATA_DIR / "cache" / "wind"

# Wind CLI 路径
WIND_CLI = Path.home() / ".agents" / "skills" / "wind-mcp-skill" / "scripts" / "cli.mjs"

# Wind API 单次调用成本（积分）
WIND_COST_PER_CALL = 6.67  # 40积分 / 6次 = 6.67积分/次


def load_etf_data():
    """加载 ETF 标准数据"""
    with open(ETF_DATA_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_etf_data(data):
    """保存 ETF 标准数据"""
    # 备份
    backup_file = DATA_DIR / f"etf_standard_data_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    import shutil
    shutil.copy2(ETF_DATA_FILE, backup_file)
    print(f"✓ 已备份到: {backup_file}")
    
    # 保存
    with open(ETF_DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"✓ 数据已写入: {ETF_DATA_FILE}")


def load_wind_cache():
    """加载 Wind 缓存"""
    cache_dir = WIND_CACHE_DIR
    cache = {}
    if cache_dir.exists():
        for f in cache_dir.glob("*.json"):
            try:
                with open(f, 'r', encoding='utf-8') as fp:
                    cache_data = json.load(fp)
                    code = cache_data.get('code')
                    if code:
                        cache[code] = cache_data
            except:
                pass
    return cache


def save_wind_cache(code, endpoint, data):
    """保存 Wind 缓存"""
    cache_file = WIND_CACHE_DIR / f"{code}.json"
    WIND_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    
    cache_item = {
        'code': code,
        'source': 'wind',
        'endpoint': endpoint,
        'fetched_at': datetime.now().isoformat(),
        'data': data,
        'ttl_days': 7
    }
    with open(cache_file, 'w', encoding='utf-8') as f:
        json.dump(cache_item, f, ensure_ascii=False, indent=2)


def is_cache_valid(cache_item, valid_days=7):
    """检查缓存是否有效"""
    if not cache_item:
        return False
    fetch_time_str = cache_item.get('fetched_at')
    if not fetch_time_str:
        return False
    try:
        fetch_time = datetime.fromisoformat(fetch_time_str)
        return datetime.now() - fetch_time < timedelta(days=valid_days)
    except:
        return False


def call_wind_api_fund_info(code, name, cache, force_refresh=False):
    """
    调用 Wind API 获取基金档案信息
    
    Args:
        cache: Wind 缓存 dict
        force_refresh: 是否强制刷新
    
    Returns:
        tuple: (data_or_None, api_called: bool)
    """
    # 检查缓存
    if not force_refresh and code in cache and is_cache_valid(cache[code]):
        print(f"  ✓ 缓存有效，使用缓存数据")
        return cache[code]['data'], False  # api_called = False
    
    cmd = [
        "node",
        str(WIND_CLI),
        "call",
        "fund_data",
        "get_fund_info",
        json.dumps({"question": f"{code}{name}基金档案", "lang": "中文"})
    ]
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
            cwd=str(WIND_CLI.parent)
        )
        
        if result.returncode != 0:
            # 解析错误信息
            try:
                err = json.loads(result.stdout)
                print(f"  ✗ Wind API 错误: {err.get('error', {}).get('code', 'UNKNOWN')}")
            except:
                print(f"  ✗ Wind API 调用失败 (exit {result.returncode})")
            return None, True  # api_called = True (我们尝试了调用)
        
        # 解析返回数据
        output = json.loads(result.stdout)
        text = output['content'][0]['text']
        inner_data = json.loads(text)
        
        columns = inner_data['data']['data'][0]['columns']
        rows = inner_data['data']['data'][0]['rows']
        
        if not rows:
            print(f"  ✗ Wind API 返回空数据")
            return None, True
        
        # 提取第一行数据，映射字段名
        row = rows[0]
        data = {}
        for i, col in enumerate(columns):
            field_name = col['name']
            value = row[i]
            data[field_name] = value
        
        # 更新缓存（内存+磁盘）
        cache_item = {
            'code': code,
            'source': 'wind',
            'endpoint': 'get_fund_info',
            'fetched_at': datetime.now().isoformat(),
            'data': data,
            'ttl_days': 7
        }
        cache[code] = cache_item
        
        # 立即保存到磁盘（查询即存储）
        save_wind_cache(code, 'get_fund_info', data)
        
        return data, True  # api_called = True
        
    except subprocess.TimeoutExpired:
        print(f"  ✗ Wind API 调用超时")
        return None, True
    except Exception as e:
        print(f"  ✗ Wind API 调用异常: {e}")
        return None, True
        
    except subprocess.TimeoutExpired:
        print(f"  ✗ Wind API 调用超时")
        return None
    except Exception as e:
        print(f"  ✗ Wind API 调用异常: {e}")
        return None


def map_wind_fields_to_our_fields(wind_data):
    """
    将 Wind 字段映射到我们的字段名
    
    策略：
    1. 所有 Wind 原始字段都保存，加 wind_ 前缀（不用 wind_raw_，直接用 wind_）
    2. 关键字段同时映射到我们的标准字段名（issuer, issue_date, benchmark 等）
    
    Wind 返回字段 -> 我们字段：
      基金管理人 -> issuer
      基金成立日 -> issue_date
      业绩比较基准 -> benchmark
      管理费率_支持历史 -> management_fee_rate
      托管费率_支持历史 -> custody_fee_rate
      现任基金经理姓名 -> fund_manager
      投资类型_二级分类 -> investment_type_2nd
      基金类型 -> fund_type
      销售服务费率_支持历史 -> sales_service_fee_rate
      单位净值币种 -> nav_currency
      基金规模合计 -> wind_scale
      单位净值 -> wind_nav
      Wind代码 -> wind_code
      证券简称 -> wind_short_name
    """
    # 关键字段映射（映射到我们的标准字段名）
    critical_mapping = {
        '基金管理人': 'issuer',
        '基金成立日': 'issue_date',
        '业绩比较基准': 'benchmark',  # 修复拼写：benchmark 不是 benchmark
        '管理费率_支持历史': 'management_fee_rate',
        '托管费率_支持历史': 'custody_fee_rate',
        '现任基金经理姓名': 'fund_manager',
        '投资类型_二级分类': 'investment_type_2nd',
        '基金类型': 'fund_type',
        '销售服务费率_支持历史': 'sales_service_fee_rate',
        '单位净值币种': 'nav_currency',
        '基金规模合计': 'wind_scale',
        '单位净值': 'wind_nav',
        'Wind代码': 'wind_code',
        '证券简称': 'wind_short_name',
    }
    
    result = {}
    
    # 1. 保存所有 Wind 原始字段（加 wind_ 前缀）
    for wind_field, value in wind_data.items():
        safe_field = wind_field.replace(' ', '_').replace('(', '').replace(')', '').replace('/', '_').replace('（', '').replace('）', '')
        result[f'wind_{safe_field}'] = value
    
    # 2. 映射关键字段到标准字段名（覆盖 wind_ 前缀的版本）
    for wind_field, our_field in critical_mapping.items():
        if wind_field in wind_data:
            result[our_field] = wind_data[wind_field]
    
    return result


def update_etf_with_wind(etf_list, cache, dry_run=False, limit=None, max_api_calls=83):
    """
    用 Wind 数据更新 ETF 列表
    
    Args:
        etf_list: ETF 列表
        cache: Wind 缓存 dict
        dry_run: 是否只模拟
        limit: 限制处理数量（用于测试）
        max_api_calls: 最大 API 调用次数（默认83=415积分）
    
    Returns:
        tuple: (updated_count, api_call_count, error_count)
    """
    if limit:
        etf_list = etf_list[:limit]
    
    updated_count = 0
    api_call_count = 0
    error_count = 0
    
    for i, etf in enumerate(etf_list):
        code = str(etf['code'])
        name = etf.get('name', '')
        
        print(f"\n[{i+1}/{len(etf_list)}] {code} | {name}")
        
        # 调用 Wind API（会先查缓存）
        wind_data, api_called = call_wind_api_fund_info(code, name, cache)
        if api_called:
            api_call_count += 1
        
        # 检查是否达到 API 调用上限
        if api_call_count >= max_api_calls:
            print(f"  ⚠️  已达到 API 调用上限 ({max_api_calls})，停止处理")
            break
        
        if not wind_data:
            error_count += 1
            print(f"  ✗ 获取失败，跳过")
            continue
        
        # 映射字段
        mapped_data = map_wind_fields_to_our_fields(wind_data)
        
        # 更新 ETF 数据（只填充缺失字段）
        updated_fields = []
        for field, value in mapped_data.items():
            if field.startswith('wind_'):
                # Wind 原始字段
                if field not in etf or etf[field] is None:
                    if not dry_run:
                        etf[field] = value
                    updated_fields.append(field)
            else:
                # 映射字段：只填充缺失/空值
                if field not in etf or etf[field] is None or etf[field] == '' or etf[field] == 0:
                    if not dry_run:
                        etf[field] = value
                    updated_fields.append(field)
        
        if updated_fields:
            print(f"  ✓ 更新字段: {', '.join(updated_fields[:5])}{'...' if len(updated_fields) > 5 else ''}")
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
    print(f"失败次数: {error_count}")
    print(f"预估消耗积分: {api_call_count * WIND_COST_PER_CALL:.0f}")
    
    return updated_count, api_call_count, error_count


def main():
    parser = argparse.ArgumentParser(description='从 Wind API 补充 ETF 数据')
    parser.add_argument('--dry-run', action='store_true', help='只模拟，不实际修改数据')
    parser.add_argument('--limit', type=int, help='限制处理数量（用于测试）')
    parser.add_argument('--code', type=str, help='指定单个 ETF 代码（用于测试）')
    parser.add_argument('--max-api-calls', type=int, default=83, help='最大 API 调用次数（默认83=415积分）')
    parser.add_argument('--yes', '-y', action='store_true', help='跳过确认提示')
    
    args = parser.parse_args()
    
    # 加载数据
    print("=== Wind ETF 数据补充脚本 ===\n")
    print("加载 ETF 数据...")
    etf_data = load_etf_data()
    print(f"✓ 加载 {len(etf_data)} 只 ETF")
    
    print("\n加载 Wind 缓存...")
    cache = load_wind_cache()
    print(f"✓ 缓存中有 {len(cache)} 只 ETF")
    
    # 确定要处理的 ETF 列表
    if args.code:
        etf_list = [etf for etf in etf_data if str(etf['code']) == args.code]
        print(f"\n指定处理 1 只 ETF: {args.code}")
    elif args.limit:
        etf_list = etf_data[:args.limit]
        print(f"\n限制处理 {args.limit} 只 ETF")
    else:
        etf_list = etf_data
        print(f"\n处理全部 {len(etf_list)} 只 ETF")
    
    # 按规模排序（降序），优先处理头部 ETF
    etf_list.sort(key=lambda x: float(x.get('scale', 0) or 0), reverse=True)
    print(f"✓ 已按规模排序（降序），头部 ETF 优先")
    
    if not etf_list:
        print("没有需要处理的 ETF，退出")
        return
    
    # 确认（非 dry-run 模式）
    if not args.dry_run and not args.code and not args.yes:
        estimated_calls = min(len(etf_list), args.max_api_calls)
        confirm = input(f"\n⚠️  将调用 Wind API 最多 {estimated_calls} 次，消耗约 {estimated_calls * 5} 积分。确认继续？(y/N): ")
        if confirm.lower() != 'y':
            print("已取消")
            return
    
    # 更新数据
    print(f"\n{'='*50}")
    print("开始处理...")
    print(f"{'='*50}\n")
    
    updated_count, api_call_count, error_count = update_etf_with_wind(
        etf_list, 
        cache,
        dry_run=args.dry_run,
        limit=args.limit,
        max_api_calls=args.max_api_calls
    )
    
    # 保存结果
    if not args.dry_run and updated_count > 0:
        print(f"\n{'='*50}")
        print("保存结果...")
        print(f"{'='*50}\n")
        
        # 保存 ETF 数据
        save_etf_data(etf_data)
        
        # 保存缓存
        print(f"✓ 缓存已更新（{len(cache)} 只 ETF）")
        
        print(f"\n✓ 全部完成！")
    elif args.dry_run:
        print(f"\n⚠️  dry-run 模式，未实际修改数据")
    else:
        print(f"\n⚠️  没有更新任何数据")


if __name__ == '__main__':
    main()
