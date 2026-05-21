#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
获取货币ETF的债券持仓数据（通过NeoData API）

货币ETF（如511880银华日利）持有债券而非股票，AKShare无法获取其持仓。
本脚本调用NeoData API获取这些ETF的债券持仓，并更新etf_standard_data.json。

用法：
  python3 fetch_money_etf_holdings.py          # 获取所有缺失持仓的ETF（默认跳过已有数据）
  python3 fetch_money_etf_holdings.py --dry-run  # 仅预览，不修改数据
  python3 fetch_money_etf_holdings.py --force    # 强制重新获取所有（包括已有持仓的）
  python3 fetch_money_etf_holdings.py --limit=5  # 限制处理数量（测试用）
"""

import json
import subprocess
import sys
import os
import time
from pathlib import Path

# NeoData skill 目录
NEODATA_SKILL_DIR = Path.home() / ".workbuddy/plugins/marketplaces/cb_teams_marketplace/plugins/finance-data/skills/neodata-financial-search"

ROOT = Path(__file__).parent


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def call_neodata_api(query):
    """调用 NeoData query.py 脚本，返回解析后的JSON响应"""
    if not NEODATA_SKILL_DIR.is_dir():
        log(f"NeoData skill目录不存在: {NEODATA_SKILL_DIR}")
        return None
    
    try:
        result = subprocess.run(
            ['python3', 'scripts/query.py', '--query', query],
            capture_output=True, text=True, cwd=str(NEODATA_SKILL_DIR), timeout=30
        )
        
        if result.returncode != 0:
            log(f"  NeoData调用失败 (code={result.returncode}): {result.stderr[:100]}")
            return None
        
        # 从stdout解析JSON（跳过警告行）
        lines = result.stdout.strip().split('\n')
        json_started = False
        json_lines = []
        for line in lines:
            if line.strip().startswith('{'):
                json_started = True
            if json_started:
                json_lines.append(line)
        
        if not json_lines:
            log(f"  NeoData响应中未找到JSON")
            return None
            
        data = json.loads('\n'.join(json_lines))
        
        if data.get('code') != '200' or not data.get('suc'):
            log(f"  NeoData返回错误: code={data.get('code')}, msg={data.get('msg')}")
            return None
            
        return data
        
    except subprocess.TimeoutExpired:
        log(f"  NeoData调用超时")
        return None
    except json.JSONDecodeError as e:
        log(f"  NeoData响应JSON解析失败: {e}")
        return None
    except Exception as e:
        log(f"  NeoData调用异常: {e}")
        return None


def parse_holdings_from_response(api_response):
    """从NeoData API响应中解析持仓数据（债券名称和权重）"""
    api_recall = api_response.get('data', {}).get('apiData', {}).get('apiRecall', [])
    
    for item in api_recall:
        # 尝试解析所有item的content，不只是特定type
        content = item.get('content', '')
        if not content:
            continue
        holdings = _parse_markdown_table(content)
        if holdings:
            return holdings
    
    return []


def _parse_markdown_table(markdown_text):
    """解析markdown表格，提取持仓（支持债券和股票）"""
    lines = markdown_text.split('\n')
    holdings = []
    header = None
    
    for line in lines:
        line = line.strip()
        if not line.startswith('|'):
            continue
        
        # 跳过分隔线（包含 :--- 或 ---）
        if ':---' in line or '---' in line:
            continue
            
        # 分割单元格
        parts = line.split('|')
        cols = [p.strip() for p in parts[1:-1]]
        
        if header is None:
            header = cols
        else:
            # 数据行
            if len(cols) != len(header):
                continue
                
            row = dict(zip(header, cols))
            
            # 提取名称（债券名称/股票名称/证券名称/基金名称/名称）
            name = (row.get('债券名称', '') or row.get('股票名称', '') or 
                    row.get('证券名称', '') or row.get('基金名称', '') or
                    row.get('名称', '') or '')
            
            # 提取代码（债券代码/股票代码/证券代码/基金代码/代码）
            code = (row.get('债券代码', '') or row.get('股票代码', '') or 
                    row.get('证券代码', '') or row.get('基金代码', '') or
                    row.get('代码', '') or '')
            
            # 提取权重：尝试多个列名，跳过 "--" 和非数字
            weight = 0
            for weight_col in ['占净值比例', '持仓比例', '权重', '持仓数量', '比例']:
                val = row.get(weight_col, '')
                if val and val != '--':
                    val_clean = val.replace('%', '').strip()
                    try:
                        weight = float(val_clean)
                        break
                    except:
                        continue
            
            if name and weight > 0:
                holdings.append({
                    'name': name,
                    'code': code,
                    'weight': f"{weight:.2f}%"
                })
    
    return holdings


def fetch_etf_holdings(code, name):
    """获取单只ETF的持仓数据"""
    # 通用查询：不指定债券/股票，让NeoData自己返回
    query = f"{code} {name} 持仓成分"
    log(f"  查询 {code} {name}...")
    
    resp = call_neodata_api(query)
    if not resp:
        return []
    
    holdings = parse_holdings_from_response(resp)
    log(f"  获取到 {len(holdings)} 个持仓")
    return holdings


def main():
    dry_run = '--dry-run' in sys.argv
    force = '--force' in sys.argv
    limit = None
    for arg in sys.argv:
        if arg.startswith('--limit='):
            limit = int(arg.split('=')[1])
    
    if dry_run:
        log("=== DRY RUN 模式（仅预览，不修改数据）===")
    if force:
        log("=== FORCE 模式（强制重新获取所有，包括已有持仓的）===")
    
    # 加载 ETF 数据
    data_file = ROOT / 'etf_standard_data.json'
    with open(data_file, 'r', encoding='utf-8') as f:
        etfs = json.load(f)
    
    # 找出 top_holdings 为空的 ETF
    all_missing = [e for e in etfs if not e.get('top_holdings')]
    
    if force:
        # 强制模式：处理所有 ETF
        missing = etfs
        log(f"强制模式：处理所有 {len(missing)} 只ETF")
    else:
        missing = all_missing
        # 断点续传：已排除 {len(etfs) - len(missing)} 只有持仓的ETF
        skipped = len(etfs) - len(missing)
        if skipped > 0:
            log(f"断点续传：跳过 {skipped} 只已有持仓的 ETF")
    
    if not all_missing and not force:
        log("所有ETF都已有持仓数据，无需补充")
        return
    
    # 限制数量（用于测试）
    if limit:
        missing = missing[:limit]
        log(f"限制处理前 {limit} 只")
    
    # 为每只ETF获取持仓
    updated_count = 0
    failed_codes = []
    
    for i, etf in enumerate(missing):
        code = etf.get('code', '')
        name = etf.get('name', '')
        
        log(f"\n[{i+1}/{len(missing)}] 处理 {code} {name}")
        
        holdings = fetch_etf_holdings(code, name)
        
        if holdings:
            if not dry_run:
                etf['top_holdings'] = holdings
                # 同时更新 _meta（如果有的话）
                if '_meta' in etf:
                    etf['_meta']['top_holdings'] = {
                        'sources': ['neodata'],
                        'updated_at': time.strftime('%Y-%m-%dT%H:%M:%S'),
                        'quality': 'high'
                    }
            updated_count += 1
            log(f"  ✓ 更新成功: {len(holdings)} 个持仓")
        else:
            failed_codes.append(code)
            log(f"  ✗ 未获取到持仓数据")
        
        # 限速：避免API调用过快
        if i < len(missing) - 1:
            time.sleep(1)
    
    # 保存结果
    if not dry_run and updated_count > 0:
        log(f"\n保存更新后的数据到 {data_file}...")
        with open(data_file, 'w', encoding='utf-8') as f:
            json.dump(etfs, f, ensure_ascii=False, indent=2)
        log(f"✓ 保存完成，更新了 {updated_count} 只ETF")
    
    # 输出失败列表
    if failed_codes:
        log(f"\n未获取到持仓的ETF ({len(failed_codes)}只):")
        for code in failed_codes:
            log(f"  {code}")
    
    log(f"\n=== 完成 ===")
    log(f"成功: {updated_count}/{len(missing)}")
    log(f"失败: {len(failed_codes)}/{len(missing)}")


if __name__ == '__main__':
    main()
