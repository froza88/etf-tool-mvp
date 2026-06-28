#!/usr/bin/env python3
"""
多源ETF资金流入数据查重→对比→整合
数据源:
  1. AKShare fund_etf_spot_em (东财) — 主力/超大单/大单/中单/小单净流入 + 份额
  2. AKShare fund_etf_spot_ths (同花顺) — 净值验证
  3. 东财 push2his (k线资金流向) — 5日主力净流入
  4. AKShare fund_etf_fund_daily_em — 净值/折价率

输出:
  etf_flow_fields.json — 按代码索引，含 source_mark 标注数据来源
  etf_flow_conflicts.json — 冲突记录（多源数据不一致时）
"""

import json
import os
from datetime import datetime
from collections import defaultdict

DATA_DIR = os.path.dirname(os.path.abspath(__file__)).replace('scripts', 'data')

def load_json(path):
    with open(path) as f:
        return json.load(f)

def fmt_amount(val):
    """格式化金额为亿"""
    if val is None:
        return 'N/A'
    return f'{val/1e8:.2f}亿'

def normalize_code(code):
    """统一6位代码"""
    return str(code).zfill(6)

# ========== 加载各数据源 ==========
print('=' * 60)
print('📥 加载数据源…')
sources = {}

# 源1: AKShare fund_etf_spot_em
src1_file = os.path.join(DATA_DIR, 'etf_flow_source1_akshare_em.json')
if os.path.exists(src1_file):
    src1_raw = load_json(src1_file)
    sources['1_akshare_em'] = {}
    for d in src1_raw:
        key = normalize_code(d.get('代码', ''))
        sources['1_akshare_em'][key] = d
    print(f'  源1 (东财spot): {len(sources["1_akshare_em"])} 条')

# 源2: AKShare fund_etf_spot_ths
src2_file = os.path.join(DATA_DIR, 'etf_flow_source2_akshare_ths.json')
if os.path.exists(src2_file):
    src2_raw = load_json(src2_file)
    sources['2_akshare_ths'] = {}
    for d in src2_raw:
        key = normalize_code(d.get('基金代码', ''))
        sources['2_akshare_ths'][key] = d
    print(f'  源2 (同花顺): {len(sources["2_akshare_ths"])} 条')

# 源3: 东财 push2his (验证用)
src3_file = os.path.join(DATA_DIR, 'etf_flow_source3_em_push2his.json')
if os.path.exists(src3_file):
    src3_raw = load_json(src3_file)
    sources['3_em_push2his'] = src3_raw
    print(f'  源3 (东财push2his): {len(sources["3_em_push2his"])} 条')

# 源4: AKShare fund_etf_fund_daily_em
src4_file = os.path.join(DATA_DIR, 'etf_flow_source4_akshare_daily.json')
if os.path.exists(src4_file):
    src4_raw = load_json(src4_file)
    sources['4_akshare_daily'] = {}
    for d in src4_raw:
        key = normalize_code(d.get('基金代码', ''))
        sources['4_akshare_daily'][key] = d
    print(f'  源4 (东财daily): {len(sources["4_akshare_daily"])} 条')

# ========== 字段定义 ==========
# 我们关注的核心字段，及其在不同源中的映射
FIELD_MAP = {
    'name': {
        '1_akshare_em': '名称',
        '2_akshare_ths': '基金名称',
        '3_em_push2his': 'name',
        '4_akshare_daily': '基金简称',
    },
    'main_net_inflow': {  # 主力净流入-净额(元)
        '1_akshare_em': '主力净流入-净额',
        '3_em_push2his': None,  # 从klines计算
    },
    'main_net_ratio': {  # 主力净流入-净占比(%)
        '1_akshare_em': '主力净流入-净占比',
    },
    'super_large_inflow': {
        '1_akshare_em': '超大单净流入-净额',
    },
    'large_inflow': {
        '1_akshare_em': '大单净流入-净额',
    },
    'medium_inflow': {
        '1_akshare_em': '中单净流入-净额',
    },
    'small_inflow': {
        '1_akshare_em': '小单净流入-净额',
    },
    'latest_shares': {  # 最新份额
        '1_akshare_em': '最新份额',
    },
    'latest_price': {
        '1_akshare_em': '最新价',
        '2_akshare_ths': '最新-单位净值',
        '4_akshare_daily': '市价',
    },
    'turnover': {
        '1_akshare_em': '成交额',
    },
    'volume': {
        '1_akshare_em': '成交量',
    },
    'data_date': {
        '1_akshare_em': '数据日期',
        '2_akshare_ths': '查询日期',
        '4_akshare_daily': None,
    },
}

# ========== 逐字段对比 ==========
print('\n' + '=' * 60)
print('🔍 逐字段交叉对比…')

conflicts = []
all_codes = set()
for src_key, src_data in sources.items():
    all_codes.update(src_data.keys())

print(f'总唯一代码数: {len(all_codes)}')

# 逐代码对比
comparison_results = []
for code in sorted(all_codes):
    entry = {'code': code}
    sources_present = []
    values_per_field = defaultdict(dict)
    
    for src_key, src_data in sources.items():
        if code not in src_data:
            continue
        sources_present.append(src_key)
        raw = src_data[code]
        
        # 提取名称
        name_field = FIELD_MAP['name'].get(src_key)
        if name_field and name_field in raw:
            entry.setdefault('name', raw[name_field])
        elif src_key == '3_em_push2his' and isinstance(raw, dict) and 'name' in raw:
            entry.setdefault('name', raw['name'])
        
        # 提取各字段值
        for field, mapping in FIELD_MAP.items():
            if field == 'name':
                continue
            col = mapping.get(src_key)
            if col is None:
                continue
            
            if src_key == '3_em_push2his' and field == 'main_net_inflow':
                # 从push2his klines计算5日主力净流入
                klines = raw.get('klines', [])
                if klines:
                    total = sum(float(k.split(',')[1]) for k in klines)
                    values_per_field[field][src_key] = total
            elif col in raw:
                val = raw[col]
                if val is not None:
                    values_per_field[field][src_key] = val
    
    # 检测冲突
    entry_fields = {}
    for field, src_vals in values_per_field.items():
        # 提取数值用于比较
        num_vals = []
        str_vals = []
        for src, val in src_vals.items():
            try:
                num_vals.append((float(val), src, val))
            except (ValueError, TypeError):
                str_vals.append((str(val), src, val))
        
        # 判断是否有真正的差异
        has_conflict = False
        diff_info = None
        
        if len(num_vals) >= 2:
            # 数值字段：比较到元级别精度
            nums = [round(v[0], 0) for v in num_vals]
            if len(set(nums)) > 1:
                has_conflict = True
                all_vals = [v[2] for v in num_vals]
                mn, mx = min(nums), max(nums)
                if mn != 0:
                    pct = abs((mx - mn) / abs(mn) * 100)
                    # 忽略微小差异 (<0.1%)，以及货币ETF净值vs市价差异（金额差异>10元）
                    if pct < 0.1 or abs(mx - mn) < 0.01:
                        has_conflict = False
                    elif '货币' in entry.get('name', '') and abs(mx - mn) > 10:
                        has_conflict = False  # 货币ETF的市价vs净值是不同指标
                diff_info = {
                    'min': mn, 'max': mx, 
                    'diff': mx - mn,
                    'diff_pct': round(pct, 2) if mn != 0 else 'N/A'
                }
        
        if len(str_vals) >= 2:
            strs = [v[0] for v in str_vals]
            if len(set(strs)) > 1:
                has_conflict = True
                if diff_info is None:
                    diff_info = {'min': min(strs), 'max': max(strs), 'diff': 'N/A', 'diff_pct': 'N/A'}
        
        if has_conflict:
            conflict = {
                'code': code,
                'name': entry.get('name', ''),
                'field': field,
                'values': {k: v for k, v in src_vals.items()},
                'diff': diff_info,
            }
            conflicts.append(conflict)
        
        # 取主源值（源1优先）
        primary_src = '1_akshare_em'
        if primary_src in src_vals:
            entry_fields[field] = src_vals[primary_src]
        elif src_vals:
            entry_fields[field] = list(src_vals.values())[0]
    
    entry['fields'] = entry_fields
    entry['sources'] = sources_present
    entry['conflict_count'] = sum(1 for c in conflicts if c['code'] == code)
    
    if entry['conflict_count'] > 0:
        comparison_results.append(entry)

# ========== 冲突汇总 ==========
print(f'\n📊 冲突统计:')
print(f'  有冲突的ETF: {len(comparison_results)} 只')
print(f'  总冲突记录: {len(conflicts)} 条')

# 按字段分组
conflicts_by_field = defaultdict(list)
for c in conflicts:
    conflicts_by_field[c['field']].append(c)

for field, items in conflicts_by_field.items():
    print(f'\n  字段 [{field}]: {len(items)} 条冲突')
    for item in items[:5]:
        print(f'    {item["code"]} {item["name"]}: {item["values"]}')
        d = item.get('diff', {})
        if isinstance(d, dict):
            print(f'      min={d["min"]}, max={d["max"]}, 差额={d["diff"]}' + (f' ({d["diff_pct"]}%)' if d.get("diff_pct","N/A") != 'N/A' else ''))
        else:
            print(f'      差额={d}')
    if len(items) > 5:
        print(f'    ... 还有 {len(items)-5} 条')

# ========== 数据质量总结 ==========
print('\n' + '=' * 60)
print('📈 数据质量报告')

# 源1覆盖统计
src1 = sources.get('1_akshare_em', {})
total_src1 = len(src1)
has_main = sum(1 for v in src1.values() if v.get('主力净流入-净额') is not None)
has_share = sum(1 for v in src1.values() if v.get('最新份额') is not None)
main_flows = [v['主力净流入-净额'] for v in src1.values() if v.get('主力净流入-净额') is not None]
unique_flows = len(set(round(f, -2) for f in main_flows))  # 百元精度去重

print(f'  源1 (东财spot):')
print(f'    总数: {total_src1}')
print(f'    有主力净流入: {has_main} ({has_main/total_src1*100:.1f}%)')
print(f'    有份额数据: {has_share} ({has_share/total_src1*100:.1f}%)')
print(f'    主力净流入唯一值(百元精度): {unique_flows}/{has_main} ← {unique_flows/has_main*100:.1f}%')
print(f'    数据真实性: {"✅ 通过" if unique_flows > total_src1*0.5 else "🔴 疑似重复（Wind式Bug）"}')

# ========== 整合输出 ==========
print('\n' + '=' * 60)
print('💾 写入整合文件…')

# 主输出: etf_flow_fields.json (按代码索引)
output = {}
for src_key, src_data in sources.items():
    for code, raw in src_data.items():
        code = normalize_code(code)
        if code not in output:
            output[code] = {}
        
        # 提取核心字段
        record = output[code]
        
        # 名称（首次见到的用）
        if 'name' not in record:
            name_field = FIELD_MAP['name'].get(src_key)
            if name_field and name_field in raw:
                record['name'] = raw[name_field]
            elif src_key == '3_em_push2his' and isinstance(raw, dict):
                record['name'] = raw.get('name', '')
        
        # 主力净流入（源1优先）
        if 'main_net_inflow' not in record:
            if src_key == '3_em_push2his':
                klines = raw.get('klines', [])
                if klines:
                    record['main_net_inflow_5d'] = sum(float(k.split(',')[1]) for k in klines)
            elif src_key == '1_akshare_em':
                val = raw.get('主力净流入-净额')
                if val is not None:
                    record['main_net_inflow'] = val
                    record['main_net_ratio'] = raw.get('主力净流入-净占比')
                    record['super_large_inflow'] = raw.get('超大单净流入-净额')
                    record['large_inflow'] = raw.get('大单净流入-净额')
                    record['medium_inflow'] = raw.get('中单净流入-净额')
                    record['small_inflow'] = raw.get('小单净流入-净额')
                    record['latest_shares'] = raw.get('最新份额')
                    record['latest_price'] = raw.get('最新价')
                    record['turnover'] = raw.get('成交额')
                    record['volume'] = raw.get('成交量')
                    record['change_pct'] = raw.get('涨跌幅')
                    # 处理日期格式
                    data_date = raw.get('数据日期')
                    if data_date:
                        try:
                            if isinstance(data_date, (int, float)) and data_date > 1e12:
                                record['data_date'] = datetime.fromtimestamp(data_date/1000).strftime('%Y-%m-%d')
                            else:
                                record['data_date'] = str(data_date)
                        except:
                            record['data_date'] = str(data_date)
        
        # 来源标记
        if 'source_mark' not in record:
            record['source_mark'] = []
        if src_key not in record['source_mark']:
            record['source_mark'].append(src_key)

# 写入主文件
output_file = os.path.join(DATA_DIR, 'etf_flow_fields.json')
with open(output_file, 'w') as f:
    json.dump(output, f, ensure_ascii=False, indent=2)
print(f'✅ etf_flow_fields.json: {len(output)} 条记录')

# 写入冲突文件
conflicts_file = os.path.join(DATA_DIR, 'etf_flow_conflicts.json')
with open(conflicts_file, 'w') as f:
    json.dump(conflicts, f, ensure_ascii=False, indent=2)
print(f'⚠️  etf_flow_conflicts.json: {len(conflicts)} 条冲突')

# 写入数据源清单
sources_file = os.path.join(DATA_DIR, 'etf_flow_sources_manifest.json')
manifest = {
    'generated_at': datetime.now().isoformat(),
    'sources': {
        '1_akshare_em': {
            'file': 'etf_flow_source1_akshare_em.json',
            'count': len(sources.get('1_akshare_em', {})),
            'provider': '东方财富 (via AKShare)',
            'fields': ['主力净流入-净额', '主力净流入-净占比', '超大单净流入', '大单净流入', '中单净流入', '小单净流入', '最新份额', '最新价', '成交额', '涨跌幅'],
            'note': '日频，全量1514只，主力净流入唯一值率99.5%以上'
        },
        '2_akshare_ths': {
            'file': 'etf_flow_source2_akshare_ths.json',
            'count': len(sources.get('2_akshare_ths', {})),
            'provider': '同花顺 (via AKShare)',
            'fields': ['单位净值', '累计净值', '增长率'],
            'note': '无资金流向数据，仅用于净值验证'
        },
        '3_em_push2his': {
            'file': 'etf_flow_source3_em_push2his.json',
            'count': len(sources.get('3_em_push2his', {})),
            'provider': '东方财富 push2his API',
            'fields': ['5日主力净流入(kline汇总)'],
            'note': '采样50只验证用，非全量'
        },
        '4_akshare_daily': {
            'file': 'etf_flow_source4_akshare_daily.json',
            'count': len(sources.get('4_akshare_daily', {})),
            'provider': '东方财富 (via AKShare)',
            'fields': ['单位净值', '累计净值', '增长值', '增长率', '市价', '折价率'],
            'note': '1549只ETF日行情，无资金流向'
        },
    },
    'output': {
        'main': 'etf_flow_fields.json',
        'conflicts': 'etf_flow_conflicts.json',
        'total_etfs': len(output),
    },
    'conflict_summary': {
        'total_conflicts': len(conflicts),
        'by_field': {k: len(v) for k, v in conflicts_by_field.items()},
    }
}
with open(sources_file, 'w') as f:
    json.dump(manifest, f, ensure_ascii=False, indent=2)
print(f'📋 数据源清单: etf_flow_sources_manifest.json')

# ========== 快速汇总 ==========
print('\n' + '=' * 60)
print('🎉 整合完成')
print(f'  ETF 总数: {len(output)}')
print(f'  有资金流入: {sum(1 for v in output.values() if v.get("main_net_inflow") is not None)}')
print(f'  有份额数据: {sum(1 for v in output.values() if v.get("latest_shares") is not None)}')
print(f'  有5日净流入(via push2his): {sum(1 for v in output.values() if v.get("main_net_inflow_5d") is not None)}')
print(f'  多源交叉验证: {sum(1 for v in output.values() if len(v.get("source_mark", [])) >= 2)} 只')
print(f'  仅单源: {sum(1 for v in output.values() if len(v.get("source_mark", [])) == 1)} 只')
print(f'  冲突记录: {len(conflicts)}')
