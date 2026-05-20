#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
分批从 westock-data 吸收 ETF 数据
支持增量模式和分批处理，避免超时

使用方式：
  python3 absorb_batch.py --batch-size 50        # 每批50只，处理所有ETF
  python3 absorb_batch.py --incremental --batch-size 50  # 只处理缺失数据的ETF，每批50只
  python3 absorb_batch.py --start 0 --end 100   # 只处理第0-100只ETF
"""
import json
import subprocess
import re
import time
import sys
import argparse
from pathlib import Path

ROOT = Path(__file__).parent
STANDARD_DATA = ROOT / "etf_standard_data.json"
WESTOCK_SCRIPT = Path("/Users/apangduo/.workbuddy/plugins/marketplaces/cb_teams_marketplace/plugins/finance-data/skills/westock-data/scripts/index.js")

def format_code_to_westock(code):
    """转换代码格式：510300 → sh510300"""
    if code.startswith('5') or code.startswith('1'):
        return f'sh{code}'
    elif code.startswith('0') or code.startswith('3'):
        return f'sz{code}'
    elif code.startswith('8') or code.startswith('4'):
        return f'bj{code}'
    else:
        return f'sh{code}'

def query_westock_etf(codes):
    """查询 westock-data etf 命令"""
    formatted = [format_code_to_westock(c) for c in codes]
    cmd = ['node', str(WESTOCK_SCRIPT), 'etf'] + formatted
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120, encoding='utf-8')
        return result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return '', 'timeout'
    except Exception as e:
        return '', str(e)

def parse_westock_etf_output(output_text):
    """解析 westock-data etf 输出"""
    results = []
    blocks = re.split(r'^#### ', output_text, flags=re.MULTILINE)
    
    for block in blocks[1:]:
        lines = block.strip().split('\n')
        if not lines:
            continue
        etf_code = lines[0].strip()
        etf_data = {'code': etf_code, 'raw_block': block}
        
        for i, line in enumerate(lines):
            if '| code | name | date |' in line:
                if i + 2 < len(lines):
                    header_line = line
                    data_line = lines[i + 2]
                    headers = [h.strip() for h in header_line.split('|')[1:-1]]
                    values = [v.strip() for v in data_line.split('|')[1:-1]]
                    for j, header in enumerate(headers):
                        if j < len(values):
                            etf_data[header] = values[j]
                break
        
        results.append(etf_data)
    return results

def map_westock_to_our(westock_etf):
    """将 westock-data 格式映射到我们的格式"""
    our = {}
    code = westock_etf['code']
    for prefix in ['sh', 'sz', 'bj', 'hk', 'us']:
        if code.startswith(prefix):
            code = code[len(prefix):]
            break
    our['code'] = code
    
    our['name'] = westock_etf.get('name', '')
    our['issuer'] = westock_etf.get('manageInstitution', '')
    
    try:
        our['year_1_return'] = float(westock_etf.get('return1Y', 0))
    except:
        our['year_1_return'] = 0
    
    try:
        our['year_3_return'] = float(westock_etf.get('return3Y', 0))
    except:
        our['year_3_return'] = 0
    
    return our

def absorb_data(target, source):
    """填表式吸收：只填充缺失或空的字段"""
    updated_fields = []
    for key, value in source.items():
        if key in ['code', 'raw_block']:
            continue
        if value is None or value == '' or value == '0' or value == 0:
            continue
        if key not in target or target[key] is None or target[key] == '' or target[key] == 0:
            target[key] = value
            updated_fields.append(key)
    return updated_fields

def main():
    parser = argparse.ArgumentParser(description='分批吸收 westock-data ETF 数据')
    parser.add_argument('--batch-size', type=int, default=50, help='每批处理多少只ETF (默认50)')
    parser.add_argument('--start', type=int, default=0, help='起始索引 (默认0)')
    parser.add_argument('--end', type=int, default=None, help='结束索引 (默认全部)')
    parser.add_argument('--incremental', action='store_true', help='只处理缺失 year_3_return 的ETF')
    args = parser.parse_args()
    
    print("=== 分批吸收 westock-data ETF 数据 ===\n")
    
    # 加载数据
    print("【第1步】加载本地 ETF 数据...")
    with open(STANDARD_DATA, 'r', encoding='utf-8') as f:
        all_data = json.load(f)  # 全量数据
    print(f"  加载 {len(all_data)} 只 ETF\n")
    
    # 增量模式：只处理缺失数据的ETF
    if args.incremental:
        process_data = [etf for etf in all_data if not etf.get('year_3_return') or etf.get('year_3_return') == 0]
        print(f"  ⚡ 增量模式：只处理缺失 year_3_return 的 {len(process_data)} 只 ETF\n")
    else:
        process_data = all_data
    
    # 分批模式：只处理指定范围的ETF
    if args.end is None:
        args.end = len(process_data)
    process_data = process_data[args.start:args.end]
    print(f"  📦 分批模式：处理第 {args.start} - {args.end} 只 ETF (共 {len(process_data)} 只)\n")
    
    # 批量查询和吸收
    print("【第2步】批量查询和吸收...\n")
    batch_size = 5
    total_updated = 0
    
    for batch_idx in range(0, len(process_data), batch_size):
        batch = process_data[batch_idx:batch_idx + batch_size]
        batch_codes = [etf['code'] for etf in batch]
        
        print(f"[{batch_idx//batch_size + 1}/{(len(process_data)+batch_size-1)//batch_size}] 查询: {batch_codes}")
        
        stdout, stderr = query_westock_etf(batch_codes)
        if not stdout or stderr:
            print(f"  ⚠️  查询失败: {stderr[:100] if stderr else 'no output'}")
            time.sleep(2)
            continue
        
        try:
            westock_results = parse_westock_etf_output(stdout)
        except Exception as e:
            print(f"  ❌ 解析失败: {e}")
            time.sleep(2)
            continue
        
        batch_updated = 0
        for wr in westock_results:
            try:
                wr_mapped = map_westock_to_our(wr)
                # 在全量数据中找到对应的ETF（通过code匹配）
                our_etf = next((e for e in all_data if e['code'] == wr_mapped['code']), None)
                if not our_etf:
                    continue
                updated = absorb_data(our_etf, wr_mapped)
                if updated:
                    batch_updated += 1
                    print(f"  ✅ {wr_mapped['code']} - 更新 {len(updated)} 字段")
            except Exception as e:
                print(f"  ❌ 吸收失败: {e}")
        
        total_updated += batch_updated
        
        # 每10个批次保存一次
        if (batch_idx // batch_size) % 10 == 0:
            print(f"  💾 保存进度...")
            with open(STANDARD_DATA, 'w', encoding='utf-8') as f:
                json.dump(all_data, f, ensure_ascii=False, indent=2)
        
        time.sleep(3)
    
    # 最终保存
    print(f"\n【第3步】保存最终数据...")
    with open(STANDARD_DATA, 'w', encoding='utf-8') as f:
        json.dump(all_data, f, ensure_ascii=False, indent=2)
    print(f"  ✅ 完成！共更新 {total_updated} 只 ETF")
    
    # 统计覆盖率
    print(f"\n【第4步】统计覆盖率...")
    has_year_3_return = sum(1 for etf in all_data if etf.get('year_3_return') and etf.get('year_3_return') != 0)
    print(f"  📊 year_3_return 覆盖率: {has_year_3_return}/{len(all_data)} = {has_year_3_return/len(all_data)*100:.1f}%")

if __name__ == '__main__':
    main()
