#!/usr/bin/env python3
"""
补全快照和 API 数据中的缺失字段：
- tracking_error: 从 Wind MCP 缓存 (data/wind_full/*.json)
- premium_discount: 从 westock ETF 详情计算 (price-nav)/nav
用法: python3 enrich_missing_fields.py
"""
import json, os, sys, subprocess, time, re
from pathlib import Path

BASE = os.path.dirname(os.path.abspath(__file__))

def load_json(path):
    with open(path) as f:
        return json.load(f)

def save_json(path, data):
    with open(path, 'w') as f:
        json.dump(data, f, ensure_ascii=False)

def log(msg):
    print(f"[enrich] {msg}")

def parse_md_table(text):
    """解析 markdown 表格，返回 [{col_name: value}, ...]"""
    lines = [l.strip() for l in text.split('\n') if l.strip().startswith('|')]
    if len(lines) < 2:
        return []
    # 第一行是表头
    headers = [h.strip() for h in lines[0].split('|')[1:-1]]
    # 跳过第二行（分隔符），从第三行开始是数据
    rows = []
    for line in lines[2:]:
        cols = [c.strip() for c in line.split('|')[1:-1]]
        if len(cols) == len(headers):
            rows.append(dict(zip(headers, cols)))
    return rows

# ── 1. 从 Wind 缓存补 tracking_error ──
def enrich_tracking_error_from_wind(snapshot_path, wind_dir):
    sn = load_json(snapshot_path)
    sn_dict = {e['code']: e for e in sn['standard_data']}

    wind_path = os.path.join(BASE, wind_dir)
    if not os.path.exists(wind_path):
        log(f"Wind 缓存目录不存在: {wind_path}")
        return sn, 0

    count = 0
    for fname in sorted(os.listdir(wind_path)):
        if not fname.endswith('.json'):
            continue
        code = fname.split('_')[0]
        if code not in sn_dict:
            continue
        etf = sn_dict[code]
        if etf.get('tracking_error') not in (None, ''):
            continue

        try:
            with open(os.path.join(wind_path, fname)) as f:
                wind = json.load(f)
            te = wind.get('tracking_error')
            if te is not None:
                etf['tracking_error'] = round(float(te), 4)
                count += 1
        except Exception:
            continue

    log(f"Wind 缓存 → 补 {count} 只 ETF 的 tracking_error")
    sn['standard_data'] = list(sn_dict.values())
    return sn, count

# ── 2. 从 westock ETF 详情补 premium_discount ──
def enrich_premium_from_westock(snapshot_path, westock_skill_dir):
    sn = load_json(snapshot_path)
    sn_dict = {e['code']: e for e in sn['standard_data']}
    
    missing = [c for c, e in sn_dict.items() 
               if (e.get('premium_discount') in (None, '') or e.get('premium_discount') == None)]
    
    if not missing:
        log("所有 ETF 已有 premium_discount，跳过")
        return sn, 0

    log(f"premium_discount 缺失 {len(missing)} 只，批量查询 westock ETF 详情...")
    
    index_js = os.path.join(westock_skill_dir, 'scripts', 'index.js')
    count = 0
    batch_size = 20
    
    for i in range(0, len(missing), batch_size):
        batch = missing[i:i+batch_size]
        codes_str = ','.join([f"sh{c}" for c in batch])
        
        try:
            result = subprocess.run(
                ['node', index_js, 'etf', codes_str],
                capture_output=True, text=True, timeout=30,
                cwd=westock_skill_dir
            )
            if result.returncode != 0:
                continue
            
            rows = parse_md_table(result.stdout)
            for row in rows:
                code_raw = row.get('code', '').replace('sh','').replace('sz','')
                if code_raw in sn_dict:
                    try:
                        price = float(row.get('closePrice', 0))
                        nav = float(row.get('nav', 0))
                        if price > 0 and nav > 0:
                            prem = round((price - nav) / nav * 100, 1)
                            sn_dict[code_raw]['premium_discount'] = prem
                            count += 1
                    except (ValueError, TypeError):
                        continue
        except Exception as e:
            log(f"westock batch {i} 失败: {e}")
        
        if i + batch_size < len(missing):
            time.sleep(1)  # 避免请求过快

    log(f"westock ETF → 补 {count} 只 ETF 的 premium_discount")
    sn['standard_data'] = list(sn_dict.values())
    return sn, count

# ── 3. 同步到 etf_data.json ──
def sync_to_api_data(snapshot_path, api_data_path):
    sn = load_json(snapshot_path)
    api = load_json(api_data_path)
    
    sn_dict = {e['code']: e for e in sn['standard_data']}
    count = 0
    for code, e in api.items():
        if code in sn_dict:
            snap = sn_dict[code]
            for field in ['tracking_error', 'premium_discount']:
                val = snap.get(field)
                if val is not None and val != '':
                    if e.get(field) is None or e.get(field) == '':
                        e[field] = val
                        count += 1
    
    save_json(api_data_path, api)
    log(f"同步到 etf_data.json → 更新 {count} 字段")
    return count

def main():
    today = sorted([f.stem for f in Path(os.path.join(BASE, 'data/snapshots')).glob('v_*.json')])[-1]
    today = today.replace('v_', '')
    snapshot_path = os.path.join(BASE, f'data/snapshots/v_{today}.json')
    api_data_path = os.path.join(BASE, 'prototypes/etf_data.json')
    wind_dir = 'data/wind_full'
    westock_dir = os.path.expanduser(
        '~/.workbuddy/plugins/marketplaces/cb_teams_marketplace/plugins/finance-data/skills/westock-data'
    )

    log(f"快照: v_{today}")

    # Step 1: Wind tracking_error
    sn, n1 = enrich_tracking_error_from_wind(snapshot_path, wind_dir)
    if n1 > 0:
        save_json(snapshot_path, sn)

    # Step 2: westock premium_discount
    sn, n2 = enrich_premium_from_westock(snapshot_path, westock_dir)
    if n2 > 0:
        save_json(snapshot_path, sn)

    # Step 3: 同步到 API 数据
    n3 = sync_to_api_data(snapshot_path, api_data_path)

    log(f"✅ 完成: +{n1} tracking_error +{n2} premium_discount → 同步 {n3} 字段")

if __name__ == '__main__':
    main()
