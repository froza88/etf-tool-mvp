#!/usr/bin/env python3
"""从Wind缓存+非凸扩展ETF到500只，全字段解析"""
import json, os, sys, subprocess, time

WIND_DIR = '/Users/apangduo/WorkBuddy/Claw/etf-tool-mvp/data/wind_full'
JSON_FILE = '/Users/apangduo/WorkBuddy/Claw/etf-tool-mvp/prototypes/etf_core_data.json'
FT_DIR = os.path.expanduser('~/.workbuddy/skills/ftshare-market-data')

# ============================================================
# 1. 加载现有200只
# ============================================================
with open(JSON_FILE) as f:
    current = json.load(f)
existing_codes = {e['code'] for e in current}
print(f"现有: {len(current)} 只")

# ============================================================
# 2. 从Wind缓存中解析候选ETF（全字段）
# ============================================================
print("解析Wind缓存...")

def col_idx(cols, names):
    if isinstance(names, str): names = [names]
    for n in names:
        if n in cols: return cols.index(n)
    return -1

def parse_wind_file(fn):
    try:
        with open(os.path.join(WIND_DIR, fn)) as f:
            raw = json.load(f)
        inner = json.loads(raw['content'][0]['text'])
        blocks = inner['data']['data']
        result = {'code': fn.split('_')[0]}
        
        for blk in blocks:
            cols = [c['name'] for c in blk.get('columns', [])]
            rows = blk.get('rows', [])
            if not rows: continue
            row = rows[0]
            
            # Block 1: 基本资料
            idx_ld = col_idx(cols, ['基金成立日', '上市日期'])
            idx_mgr = col_idx(cols, ['基金管理人'])
            idx_type = col_idx(cols, ['投资类型_二级分类'])
            if idx_ld >= 0 and row[idx_ld]:
                result['listing_date'] = str(row[idx_ld])[:10]
            if idx_mgr >= 0 and row[idx_mgr]:
                result['issuer'] = str(row[idx_mgr]).replace('基金管理有限公司','').replace('基金','')
            if idx_type >= 0 and row[idx_type]:
                result['category'] = str(row[idx_type])
            
            # Block 2: 规模
            idx_sc = col_idx(cols, ['基金规模合计', '最新规模'])
            if idx_sc >= 0 and row[idx_sc]:
                result['scale_yi'] = round(float(row[idx_sc]), 3)
            
            # Block 3: 费率
            idx_m = col_idx(cols, ['管理费率_支持历史', '管理费率'])
            idx_c = col_idx(cols, ['托管费率_支持历史', '托管费率'])
            if idx_m >= 0 and row[idx_m] is not None:
                result['fee_mgmt'] = float(row[idx_m])
            if idx_c >= 0 and row[idx_c] is not None:
                result['fee_custody'] = float(row[idx_c])
            if 'fee_mgmt' in result and 'fee_custody' in result:
                result['fee_total'] = round(result['fee_mgmt'] + result['fee_custody'], 2)
            
            # Block 4: 净值
            idx_nav = col_idx(cols, ['最新单位净值'])
            if idx_nav >= 0 and row[idx_nav]:
                result['nav'] = float(row[idx_nav])
            
            # Block 5: 风险指标
            idx_te = col_idx(cols, ['近1年跟踪误差', '跟踪误差'])
            idx_sh = col_idx(cols, ['近1年夏普比率'])
            idx_vol = col_idx(cols, ['近1年年化波动率'])
            idx_dd = col_idx(cols, ['近1年最大回撤'])
            if idx_te >= 0 and row[idx_te] is not None:
                result['tracking_error'] = round(float(row[idx_te]), 4)
            if idx_sh >= 0 and row[idx_sh] is not None:
                result['sharpe_ratio'] = round(float(row[idx_sh]), 4)
            if idx_vol >= 0 and row[idx_vol] is not None:
                result['annual_vol'] = round(float(row[idx_vol]), 4)
            if idx_dd >= 0 and row[idx_dd] is not None:
                dd = float(row[idx_dd])
                result['max_drawdown'] = round(dd if dd < 0 else -dd, 2)
            
            # Block 6: 收益率
            idx_1y = col_idx(cols, ['近1年回报'])
            idx_3y = col_idx(cols, ['近3年回报'])
            if idx_1y >= 0 and row[idx_1y] is not None:
                result['year_1_return'] = round(float(row[idx_1y]), 2)
            if idx_3y >= 0 and row[idx_3y] is not None:
                result['year_3_return'] = round(float(row[idx_3y]), 2)
        
        # 必须有规模和名称
        if 'name' not in result:
            result['name'] = result.get('code', '')
        if result.get('scale_yi') and result.get('fee_mgmt') is not None:
            return result
    except:
        pass
    return None

# 解析所有Wind缓存
wind_etfs = {}
wind_files = sorted(os.listdir(WIND_DIR))
for fn in wind_files:
    code = fn.split('_')[0]
    if code in existing_codes: continue
    if code in wind_etfs: continue  # 已有更新的
    
    parsed = parse_wind_file(fn)
    if parsed and parsed.get('scale_yi'):
        wind_etfs[code] = parsed

print(f"Wind候选: {len(wind_etfs)} 只")

# ============================================================
# 3. 按规模降序取Top300
# ============================================================
candidates = sorted(wind_etfs.values(), key=lambda x: x.get('scale_yi', 0), reverse=True)
new_etfs = candidates[:300]

# 补充name（非凸获取）
print(f"\n补充名称和分类（非凸）...")

# 从非凸批量获取ETF列表用于补充名称/分类/跟踪指数
ft_dict = {}
for page in range(1, 10):
    try:
        r = subprocess.run(
            ['/usr/bin/python3', 'run.py', 'etf-list-paginated', '--page_size', '200', '--page_no', str(page)],
            cwd=FT_DIR, capture_output=True, text=True, timeout=45
        )
        batch = json.loads(r.stdout).get('etfs', [])
        for e in batch:
            ft_dict[e['symbol_id']] = e
        if len(batch) < 200: break
    except Exception as ex:
        print(f"  第{page}页错误: {ex}")
        break

print(f"  非凸: {len(ft_dict)} 只")

# 补充name/category/track_index
for e in new_etfs:
    code = e['code']
    ft = ft_dict.get(code, {})
    if ft:
        if not e.get('name') or e['name'] == code:
            e['name'] = ft.get('name', code)
        if not e.get('category'):
            e['category'] = ft.get('invest_kind', '')
        if not e.get('track_index'):
            ti = ft.get('tracking_index_symkey', '')
            if ti:
                e['track_index'] = ti.split('.')[0] if '.' in ti else ti
        if not e.get('issuer'):
            mgr = ft.get('manager', '')
            e['issuer'] = mgr.replace('基金管理有限公司','').replace('基金','')
        if not e.get('listing_date'):
            e['listing_date'] = ft.get('issue_date', '')

# ============================================================
# 4. 合并：现有200只 + 新增300只
# ============================================================
# 清理current中的非标准字段
std_keys = ['code','name','issuer','category','track_index','scale_yi',
            'fee_mgmt','fee_custody','fee_total','tracking_error',
            'sharpe_ratio','calmar_ratio','max_drawdown','annual_vol',
            'year_1_return','year_3_return','listing_date','holdings',
            'track_index_code','holdings_str']
for e in current:
    for k in list(e.keys()):
        if k not in std_keys:
            del e[k]

# 统一字段
for e in new_etfs:
    for k in list(e.keys()):
        if k not in std_keys:
            del e[k]
    # 确保必要字段存在
    for k in ['calmar_ratio','track_index_code','holdings_str']:
        if k not in e:
            e[k] = None
    if 'holdings' not in e:
        e['holdings'] = []

all_etfs = current + new_etfs
# 去重
seen = set()
deduped = []
for e in all_etfs:
    if e['code'] not in seen:
        seen.add(e['code'])
        deduped.append(e)
all_etfs = deduped

print(f"\n合并后: {len(all_etfs)} 只")

# ============================================================
# 5. 补充持仓（非凸NeoData，只补缺失的）
# ============================================================
print("\n补充持仓...")
need_holdings = [e for e in all_etfs if not e.get('holdings') or len(e.get('holdings',[])) == 0]
print(f"  缺失持仓: {len(need_holdings)} 只")

# 持仓数据从缓存的非凸etf-detail获取（如果有的话）
# 暂时跳过，后续可补充

# ============================================================
# 6. 预处理holdings_str
# ============================================================
for e in all_etfs:
    h = e.get('holdings', [])
    if h:
        e['holdings_str'] = '\n'.join([f"{x.get('name','')} {x.get('weight','')}" for x in h[:5]])
    else:
        e['holdings_str'] = ''

# ============================================================
# 7. 计算calmar_ratio（如果缺失）
# ============================================================
for e in all_etfs:
    if not e.get('calmar_ratio') and e.get('year_1_return') and e.get('max_drawdown'):
        dd = abs(e['max_drawdown'])
        if dd > 0:
            e['calmar_ratio'] = round(e['year_1_return'] / dd, 2)

# ============================================================
# 8. 保存
# ============================================================
with open(JSON_FILE, 'w') as f:
    json.dump(all_etfs, f, ensure_ascii=False, indent=2)

embed_path = os.path.join(os.path.dirname(JSON_FILE), 'etf_data_embed.js')
with open(embed_path, 'w') as f:
    f.write('var ETF_CORE_DATA = ')
    json.dump(all_etfs, f, ensure_ascii=False, separators=(',', ':'))
    f.write(';')

# ============================================================
# 9. 统计覆盖率
# ============================================================
print(f"\n{'='*50}")
print(f"扩展完成: {len(all_etfs)} 只")
print(f"etf_core_data.json: {os.path.getsize(JSON_FILE)/1024:.0f}KB")
print(f"etf_data_embed.js: {os.path.getsize(embed_path)/1024:.0f}KB")

for k in ['fee_mgmt','fee_custody','fee_total','tracking_error','scale_yi',
          'sharpe_ratio','max_drawdown','annual_vol','year_1_return','year_3_return',
          'calmar_ratio','holdings']:
    if k == 'holdings':
        cnt = sum(1 for e in all_etfs if e.get(k) and len(e.get(k,[])) > 0)
    else:
        cnt = sum(1 for e in all_etfs if e.get(k) is not None and e.get(k) != 0)
    
    # 修正year_3_return逻辑
    if k == 'year_3_return':
        old_enough = sum(1 for e in all_etfs if e.get('listing_date','') < '2023-06-08')
        print(f"  {k}: {cnt}/{len(all_etfs)} (成立>3年:{old_enough}只)")
    else:
        print(f"  {k}: {cnt}/{len(all_etfs)}")
PYEOF
