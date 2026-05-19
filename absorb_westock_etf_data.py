#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从 westock-data 吸收 ETF 数据到本地数据库
填表式吸收：只填充缺失或空的字段

使用方式：
  python3 absorb_westock_etf_data.py           # 处理所有ETF
  python3 absorb_westock_etf_data.py --incremental  # 只处理缺失year_3_return的ETF
"""
import json
import subprocess
import re
import time
import sys
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).parent
STANDARD_DATA = ROOT / "etf_standard_data.json"
WESTOCK_SCRIPT = Path("/Users/apangduo/.workbuddy/plugins/marketplaces/cb_teams_marketplace/plugins/finance-data/skills/westock-data/scripts/index.js")

print("=== 从 westock-data 吸收 ETF 数据 ===\n")

# ============================================================
# 第1步：加载本地数据
# ============================================================
print("【第1步】加载本地 ETF 数据...")

with open(STANDARD_DATA, 'r', encoding='utf-8') as f:
    etf_data = json.load(f)

print(f"  加载 {len(etf_data)} 只 ETF\n")

# 检查是否增量模式
incremental = '--incremental' in sys.argv
if incremental:
    etf_data = [etf for etf in etf_data if not etf.get('year_3_return') or etf.get('year_3_return') == 0]
    print(f"  ⚡ 增量模式：只处理缺失 year_3_return 的 {len(etf_data)} 只 ETF\n")

# ============================================================
# 第2步：定义工具和函数
# ============================================================

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
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,
            encoding='utf-8'
        )
        return result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return '', 'timeout'
    except Exception as e:
        return '', str(e)

def parse_westock_etf_output(output_text):
    """解析 westock-data etf 输出"""
    results = []
    
    # 按 #### 分割每个ETF的数据块
    blocks = re.split(r'^#### ', output_text, flags=re.MULTILINE)
    
    for block in blocks[1:]:  # 第一个是空字符串
        lines = block.strip().split('\n')
        if not lines:
            continue
            
        etf_code = lines[0].strip()  # 第一行是ETF代码
        
        etf_data = {'code': etf_code, 'raw_block': block}
        
        # 查找主表格
        for i, line in enumerate(lines):
            if '| code | name | date |' in line:
                # 找到header行，下一行是分隔线，再下一行是数据行
                if i + 2 < len(lines):
                    header_line = line
                    data_line = lines[i + 2]
                    
                    # 解析header和data
                    headers = [h.strip() for h in header_line.split('|')[1:-1]]
                    values = [v.strip() for v in data_line.split('|')[1:-1]]
                    
                    # 创建字段映射
                    for j, header in enumerate(headers):
                        if j < len(values):
                            etf_data[header] = values[j]
                
                break
        
        # 查找持仓明细表格
        holdings = []
        for i, line in enumerate(lines):
            if '**持仓' in line or '**持仓明细' in line:
                # 跳过表头和分隔线，解析持仓行
                for j in range(i + 3, min(i + 25, len(lines))):
                    line_content = lines[j]
                    if line_content.startswith('|') and '---' not in line_content:
                        parts = [p.strip() for p in line_content.split('|')[1:-1]]
                        if len(parts) >= 3 and parts[0] and parts[0][0].isdigit():
                            holdings.append({
                                'code': parts[0],
                                'name': parts[1],
                                'ratio': parts[2]
                            })
                    elif not line_content.startswith('|'):
                        break
                break
        
        etf_data['holdings'] = holdings
        results.append(etf_data)
    
    return results

def map_westock_to_our(westock_etf):
    """将 westock-data 格式映射到我们的格式"""
    our = {}
    
    # 代码（去掉市场前缀）
    code = westock_etf['code']
    for prefix in ['sh', 'sz', 'bj', 'hk', 'us']:
        if code.startswith(prefix):
            code = code[len(prefix):]
            break
    our['code'] = code
    
    # 基础信息
    our['name'] = westock_etf.get('name', '')
    our['issuer'] = westock_etf.get('manageInstitution', '')
    our['issue_date'] = westock_etf.get('establishDate', '')
    our['custodian'] = westock_etf.get('trusteeInstitution', '')
    our['track_index_code'] = westock_etf.get('trackIndexCode', '')
    our['track_index_name'] = westock_etf.get('trackIndexName', '')
    
    # 价格数据
    try:
        our['close'] = float(westock_etf.get('closePrice', 0))
    except:
        our['close'] = 0
    
    try:
        our['change_pct'] = float(westock_etf.get('changePct', 0))
    except:
        our['change_pct'] = 0
    
    try:
        our['volume'] = float(westock_etf.get('turnoverVolume', 0))
    except:
        our['volume'] = 0
    
    # 规模数据（元 → 亿元）
    try:
        size_yuan = float(westock_etf.get('size', 0))
        our['scale'] = size_yuan / 100000000
    except:
        our['scale'] = 0
    
    try:
        shares = float(westock_etf.get('shares', 0))
        our['shares'] = shares / 100000000  # 份 → 亿份
    except:
        our['shares'] = 0
    
    # 费用数据
    our['subscription_fee'] = westock_etf.get('subscriptionFee', '')
    our['management_fee'] = westock_etf.get('managementFee', '')
    our['custody_fee'] = westock_etf.get('custodyFee', '')
    our['service_fee'] = westock_etf.get('serviceFee', '')
    
    # 收益数据
    try:
        our['year_1_return'] = float(westock_etf.get('return1Y', 0))
    except:
        our['year_1_return'] = 0
    
    try:
        our['year_3_return'] = float(westock_etf.get('return3Y', 0))
    except:
        our['year_3_return'] = 0
    
    # 回撤数据
    try:
        our['max_drawdown'] = float(westock_etf.get('maxDrawdown1Y', 0))
    except:
        our['max_drawdown'] = 0
    
    # 持仓数据
    holdings = westock_etf.get('holdings', [])
    our['top_holdings'] = [{'name': h['name'], 'weight': f"{h['ratio']}%"} for h in holdings]
    
    return our

def absorb_data(target, source):
    """填表式吸收：只填充缺失或空的字段"""
    updated_fields = []
    
    for key, value in source.items():
        # 跳过code字段和内部字段
        if key in ['code', 'raw_block', 'holdings']:
            continue
        
        # 检查值是否有效
        if value is None or value == '' or value == '0' or value == 0:
            continue
        
        # 如果目标缺少这个字段，或者字段值为空/0，则吸收
        if key not in target or target[key] is None or target[key] == '' or target[key] == 0:
            target[key] = value
            updated_fields.append(key)
    
    return updated_fields

# ============================================================
# 第3步：批量查询和吸收
# ============================================================

print("【第3步】批量查询 westock-data 并吸收数据...\n")

batch_size = 5
total_updated = 0
failed_etfs = []

for batch_idx in range(0, len(etf_data), batch_size):
    batch = etf_data[batch_idx:batch_idx + batch_size]
    batch_codes = [etf['code'] for etf in batch]
    
    print(f"[{batch_idx//batch_size + 1}/{len(etf_data)//batch_size + 1}] 查询: {batch_codes}")
    
    # 查询 westock-data
    stdout, stderr = query_westock_etf(batch_codes)
    
    if not stdout or stderr:
        print(f"  ⚠️  查询失败: {stderr[:100] if stderr else 'no output'}")
        failed_etfs.extend(batch_codes)
        time.sleep(2)
        continue
    
    # 解析输出
    try:
        westock_results = parse_westock_etf_output(stdout)
        print(f"  解析到 {len(westock_results)} 只 ETF 数据")
    except Exception as e:
        print(f"  ❌ 解析失败: {e}")
        failed_etfs.extend(batch_codes)
        time.sleep(2)
        continue
    
    # 吸收数据
    batch_updated = 0
    for wr in westock_results:
        try:
            wr_mapped = map_westock_to_our(wr)
            
            # 找到对应的本地ETF
            our_etf = next((e for e in etf_data if e['code'] == wr_mapped['code']), None)
            if not our_etf:
                print(f"  ⚠️  未找到本地 ETF: {wr_mapped['code']}")
                continue
            
            # 吸收数据
            updated = absorb_data(our_etf, wr_mapped)
            if updated:
                batch_updated += 1
                print(f"  ✅ {wr_mapped['code']} - 更新字段: {len(updated)} 个")
            
        except Exception as e:
            print(f"  ❌ 吸收失败 {wr.get('code', '?')}: {e}")
    
    total_updated += batch_updated
    print(f"  批次完成: 更新 {batch_updated} 只 ETF\n")
    
    # 限速：避免请求过快
    time.sleep(3)

# ============================================================
# 第4步：保存数据
# ============================================================

print(f"\n【第4步】保存更新后的数据...")

with open(STANDARD_DATA, 'w', encoding='utf-8') as f:
    json.dump(etf_data, f, ensure_ascii=False, indent=2)

print(f"  ✅ 已保存: {STANDARD_DATA.name}")
print(f"  📊 文件大小: {STANDARD_DATA.stat().st_size / 1024:.0f} KB\n")

# ============================================================
# 第5步：输出报告
# ============================================================

print("=== 吸收报告 ===\n")

print(f"总 ETF 数: {len(etf_data)}")
print(f"更新 ETF 数: {total_updated}")
print(f"失败 ETF 数: {len(failed_etfs)}")

if failed_etfs:
    print(f"\n失败列表（前10只）: {failed_etfs[:10]}")

# 检查数据质量改善
print(f"\n数据质量检查:")

fields_to_check = ['issuer', 'scale', 'close', 'top_holdings', 'year_1_return']
for field in fields_to_check:
    if field == 'top_holdings':
        count = sum(1 for etf in etf_data if etf.get(field) and len(etf.get(field, [])) > 0)
    else:
        count = sum(1 for etf in etf_data if etf.get(field) and etf.get(field) != 0)
    pct = count / len(etf_data) * 100
    print(f"  {field}: {count}/{len(etf_data)} ({pct:.1f}%)")

print(f"\n=== 完成 ===")
print(f"下次运行建议：增量更新（只查询有变化的ETF）")
