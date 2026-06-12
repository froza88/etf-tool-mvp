#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
后台 Wind MCP 数据抓取脚本

用途：对 etf_standard_data.json 中缺少 Wind 缓存的 ETF，
调用 Wind MCP CLI 抓取数据，存到 data/wind_full/。

特点：
- 后台运行，不阻塞其他任务
- 间隔 8s 避免限流
- 支持断点续传（跳过已有缓存）
- 兼容自动化（凌晨4点 supplement_data.py 之后运行）

用法：
  python fetch_wind_missing.py            # 抓取所有缺失的
  python fetch_wind_missing.py --code 159031  # 只抓单只
  python fetch_wind_missing.py --dry-run  # 仅列出缺失的
"""

import argparse
import json
import os
import subprocess
import sys
import time
import glob
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).parent
STANDARD_FILE = ROOT / 'etf_standard_data.json'
WIND_FULL_DIR = ROOT / 'data' / 'wind_full'
WIND_CLI = os.path.expanduser(
    '~/.agents/skills/wind-mcp-skill/scripts/cli.mjs'
)
NODE = '/Users/apangduo/.workbuddy/binaries/node/versions/22.12.0/bin/node'

# 每只 ETF 间隔
INTERVAL_SEC = 8
# 最大重试次数
MAX_RETRIES = 2


def load_json(path):
    if not Path(path).exists():
        return None
    with open(path) as f:
        return json.load(f)


def get_wind_codes():
    """返回 data/wind_full/ 中已有缓存的 ETF 代码"""
    codes = set()
    if WIND_FULL_DIR.is_dir():
        for f in glob.glob(str(WIND_FULL_DIR / '*.json')):
            codes.add(os.path.basename(f).split('_')[0])
    return codes


def call_wind(etf_code, etf_name, max_retries=MAX_RETRIES):
    """
    调用 Wind MCP CLI 查询单只 ETF 全部信息
    
    返回: (success, filepath) 或 (false, error_msg)
    """
    question = (
        f"{etf_code} {etf_name} 基本档案 规模 费率 净值 "
        f"风险指标 夏普比率 波动率 最大回撤 跟踪误差 收益率"
    )
    
    for attempt in range(max_retries):
        try:
            result = subprocess.run(
                [NODE, WIND_CLI, 'call', 'fund_data', 'get_fund_info',
                 json.dumps({'question': question})],
                capture_output=True, text=True, timeout=60,
                cwd=str(ROOT)
            )
            
            if result.returncode == 0 and result.stdout.strip():
                # 保存到 wind_full
                today = datetime.now().strftime('%Y%m%d')
                fpath = WIND_FULL_DIR / f'{etf_code}_{today}.json'
                fpath.parent.mkdir(parents=True, exist_ok=True)
                
                # 包装为标准格式
                raw_output = result.stdout.strip()
                try:
                    # 验证是有效 JSON
                    output_json = json.loads(raw_output)
                    with open(fpath, 'w') as f:
                        json.dump(output_json, f, ensure_ascii=False, indent=2)
                    return True, str(fpath)
                except json.JSONDecodeError:
                    # 非 JSON 输出，包装
                    wrapper = {
                        "content": [{"type": "text", "text": raw_output}]
                    }
                    with open(fpath, 'w') as f:
                        json.dump(wrapper, f, ensure_ascii=False)
                    return True, str(fpath)
            else:
                err = result.stderr.strip() or "Unknown error"
        except subprocess.TimeoutExpired:
            err = "Timeout (60s)"
        except Exception as e:
            err = str(e)
        
        if attempt < max_retries - 1:
            print(f"    重试 ({attempt+2}/{max_retries})...")
            time.sleep(INTERVAL_SEC)
    
    return False, err


def main():
    parser = argparse.ArgumentParser(description='后台 Wind MCP 数据抓取')
    parser.add_argument('--code', help='仅抓取指定ETF代码')
    parser.add_argument('--dry-run', action='store_true', help='仅列出缺失的，不抓取')
    parser.add_argument('--limit', type=int, default=0, help='最多抓取 N 只')
    args = parser.parse_args()
    
    # 检查 CLI 是否存在
    if not os.path.isfile(WIND_CLI):
        print(f"❌ Wind CLI 不存在: {WIND_CLI}")
        sys.exit(1)
    
    if not os.path.isfile(NODE):
        print(f"❌ Node 不存在: {NODE}")
        sys.exit(1)
    
    # 加载标准数据
    standard_etfs = load_json(STANDARD_FILE)
    if not standard_etfs:
        print("❌ 未找到标准数据文件")
        sys.exit(1)
    
    wind_codes = get_wind_codes()
    
    # 确定待抓取的 ETF
    if args.code:
        target = [e for e in standard_etfs if e['code'] == args.code]
        if not target:
            print(f"❌ ETF {args.code} 不在标准数据中")
            sys.exit(1)
        print(f"🎯 指定 ETF: {args.code} {target[0].get('name','')}")
    else:
        target = [e for e in standard_etfs if e['code'] not in wind_codes]
        # 按规模降序
        target.sort(key=lambda x: x.get('scale', 0) or 0, reverse=True)
        print(f"📊 总 ETF: {len(standard_etfs)}, 已有 Wind: {len(wind_codes)}, 缺失: {len(target)}")
    
    if args.limit > 0:
        target = target[:args.limit]
    
    if not target:
        print("✅ 所有 ETF 已有 Wind 缓存，无需抓取")
        return 0
    
    if args.dry_run:
        print("\n📋 待抓取 ETF (Dry Run):")
        for e in target:
            print(f"  {e['code']}  {e.get('name','')[:35]:35s}  规模:{e.get('scale','N/A')}")
        print(f"\n共 {len(target)} 只，预计耗时 {len(target) * INTERVAL_SEC}s = {len(target) * INTERVAL_SEC // 60}min")
        return 0
    
    # 开始抓取
    success_count = 0
    fail_count = 0
    start_time = time.time()
    
    print(f"\n🚀 开始抓取，共 {len(target)} 只，间隔 {INTERVAL_SEC}s")
    print(f"   预计耗时：{len(target) * INTERVAL_SEC // 60} 分钟")
    print()
    
    for i, etf in enumerate(target):
        code = etf['code']
        name = etf.get('name', '')
        elapsed = time.time() - start_time
        
        print(f"[{i+1}/{len(target)}] ({elapsed:.0f}s) {code} {name[:30]} ... ", end='', flush=True)
        
        success, info = call_wind(code, name)
        
        if success:
            print(f"✅ → {os.path.basename(info)}")
            success_count += 1
        else:
            print(f"❌ {info}")
            fail_count += 1
        
        # 最后一只不 sleep
        if i < len(target) - 1:
            time.sleep(INTERVAL_SEC)
    
    total_time = time.time() - start_time
    print(f"\n{'='*50}")
    print(f"📊 完成：成功 {success_count}/{len(target)}, 失败 {fail_count}/{len(target)}")
    print(f"⏱  总耗时：{total_time:.0f}s = {total_time/60:.1f}min")
    
    return 0 if fail_count == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
