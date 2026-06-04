#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量从非凸API获取ETF静态信息，合并到etf_standard_data.json

获取字段：
- tracking_index_symkey → track_index_code（去掉交易所后缀）
- issue_date → list_date（上市日期）
- custodian（托管人）
- manager（管理人）
- invest_kind（投资品种）
"""
import json
import subprocess
import sys
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).parent
STANDARD_FILE = ROOT / 'etf_standard_data.json'
OUTPUT_FILE = ROOT / 'data/etf_fex_static_bulk.json'

def run_fex_api(page_size=200, page_no=1):
    """调用非凸API获取ETF列表（分页）"""
    result = subprocess.run(
        ['/usr/bin/python3', 
         '/Users/apangduo/.workbuddy/skills/ftshare-market-data/run.py',
         'etf-list-paginated',
         '--page_size', str(page_size),
         '--page_no', str(page_no)],
        capture_output=True, text=True, timeout=30
    )
    if result.returncode != 0:
        print(f"  ❌ 第{page_no}页失败: {result.stderr[:200]}")
        return None
    try:
        data = json.loads(result.stdout)
        return data
    except json.JSONDecodeError:
        print(f"  ❌ 第{page_no}页JSON解析失败")
        return None

def fetch_all_etfs(page_size=200):
    """获取全部ETF数据"""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 获取第1页...")
    data = run_fex_api(page_size=page_size, page_no=1)
    if not data:
        return None
    
    # 解析响应格式
    if isinstance(data, dict):
        total_size = data.get('total_size', 0)
        total_pages = data.get('total_pages', 1)
        etfs = data.get('etfs', [])
        print(f"  总数: {total_size}, 总页数: {total_pages}, 第1页: {len(etfs)}条")
    elif isinstance(data, list):
        etfs = data
        total_size = len(etfs)
        total_pages = 1
        print(f"  返回list: {len(etfs)}条（仅1页）")
    else:
        print(f"  ❌ 未知格式: {type(data)}")
        return None
    
    all_etfs = etfs
    
    # 获取剩余页
    for page in range(2, total_pages + 1):
        print(f"  获取第{page}/{total_pages}页...", end=' ', flush=True)
        data_page = run_fex_api(page_size=page_size, page_no=page)
        if data_page:
            if isinstance(data_page, dict):
                etfs_page = data_page.get('etfs', [])
            elif isinstance(data_page, list):
                etfs_page = data_page
            else:
                etfs_page = []
            all_etfs.extend(etfs_page)
            print(f"✅ {len(etfs_page)}条（累计{len(all_etfs)}）")
        else:
            print("❌ 失败，跳过")
    
    print(f"\n  共获取: {len(all_etfs)}只ETF")
    return all_etfs

def extract_static_info(etf_list):
    """从非凸ETF数据中提取静态信息"""
    result = {}
    for etf in etf_list:
        code = etf.get('symbol_id', '')
        if not code:
            continue
        
        info = {}
        
        # 1. 跟踪指数代码（去掉交易所后缀）
        track_symkey = etf.get('tracking_index_symkey', '')
        if track_symkey and '.' in track_symkey:
            track_code = track_symkey.split('.')[0]
            info['track_index_code'] = track_code
        
        # 2. 上市日期
        issue_date = etf.get('issue_date', '')
        if issue_date:
            info['list_date'] = issue_date
        
        # 3. 托管人
        custodian = etf.get('custodian', '')
        if custodian:
            info['custodian'] = custodian
        
        # 4. 管理人
        manager = etf.get('manager', '')
        if manager:
            info['manager'] = manager
        
        # 5. 投资品种
        invest_kind = etf.get('invest_kind', '')
        if invest_kind:
            info['invest_kind'] = invest_kind
        
        if info:
            result[code] = info
    
    return result

def merge_to_standard(static_data):
    """将静态数据合并到etf_standard_data.json"""
    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 合并到标准数据...")
    print(f"  加载 {STANDARD_FILE}...", end=' ', flush=True)
    with open(STANDARD_FILE, 'r', encoding='utf-8') as f:
        etfs = json.load(f)
    print(f"✅ {len(etfs)}只")
    
    std_map = {e['code']: e for e in etfs}
    updated = 0
    updated_fields = {}
    
    for code, info in static_data.items():
        if code not in std_map:
            continue
        etf = std_map[code]
        for key, value in info.items():
            if key not in etf or not etf[key]:
                etf[key] = value
                updated += 1
                updated_fields[key] = updated_fields.get(key, 0) + 1
    
    print(f"  更新字段数: {updated}")
    for k, v in sorted(updated_fields.items(), key=lambda x: -x[1]):
        print(f"    - {k}: +{v}")
    
    print(f"  保存...", end=' ', flush=True)
    with open(STANDARD_FILE, 'w', encoding='utf-8') as f:
        json.dump(etfs, f, ensure_ascii=False, indent=2)
    size = STANDARD_FILE.stat().st_size
    print(f"✅ ({size:,} bytes)")
    
    return updated

def main():
    print("=" * 60)
    print("非凸API批量获取ETF静态信息")
    print("=" * 60)
    
    # 1. 获取全部ETF
    print("\n[1/3] 从非凸API获取全部ETF...")
    all_etfs = fetch_all_etfs(page_size=200)
    if not all_etfs:
        print("❌ 无法获取数据")
        sys.exit(1)
    
    # 2. 提取静态信息
    print(f"\n[2/3] 提取静态信息...")
    static_data = extract_static_info(all_etfs)
    print(f"  成功提取: {len(static_data)}只ETF")
    
    # 统计
    for field in ['track_index_code', 'list_date', 'custodian', 'manager', 'invest_kind']:
        cnt = sum(1 for v in static_data.values() if v.get(field))
        print(f"    - {field}: {cnt}")
    
    # 3. 保存
    print(f"\n[3/3] 保存...")
    OUTPUT_FILE.parent.mkdir(exist_ok=True)
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(static_data, f, ensure_ascii=False, indent=2)
    print(f"  ✅ 保存到 {OUTPUT_FILE} ({OUTPUT_FILE.stat().st_size:,} bytes)")
    
    # 4. 合并到标准数据
    updated = merge_to_standard(static_data)
    
    print(f"\n✅ 完成！更新了{updated}个字段")
    print(f"   下次运行 supplement_data.py --report-html 可查看新的完整度报告")

if __name__ == '__main__':
    main()
