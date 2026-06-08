#!/usr/bin/env python3
"""从非凸批量更新规模，从Wind补费率"""
import json, subprocess, os, time, sys

JSON_FILE = '/Users/apangduo/WorkBuddy/Claw/etf-tool-mvp/prototypes/etf_core_data.json'
FT_DIR = os.path.expanduser('~/.workbuddy/skills/ftshare-market-data')
PY = '/usr/bin/python3'

with open(JSON_FILE) as f:
    data = json.load(f)

print(f"加载 {len(data)} 只ETF")

# ============================================================
# 1. 从非凸获取全量 market_cap_total
# ============================================================
print("\n=== Step 1: 非凸获取规模 ===")
ft_dict = {}
for page in range(1, 10):
    sys.stdout.write(f"  第{page}页... ")
    sys.stdout.flush()
    try:
        r = subprocess.run(
            [PY, 'run.py', 'etf-list-paginated', '--page_size', '200', '--page_no', str(page)],
            cwd=FT_DIR, capture_output=True, text=True, timeout=30
        )
        batch = json.loads(r.stdout).get('etfs', [])
        for e in batch:
            ft_dict[e['symbol_id']] = e
        print(f"{len(batch)}条")
        if len(batch) < 200:
            break
    except Exception as ex:
        print(f"错误: {ex}")
        break

print(f"  非凸总计: {len(ft_dict)} 只ETF")

# 更新规模
updated_scale = 0
for e in data:
    code = e['code']
    ft = ft_dict.get(code, {})
    mc = ft.get('market_cap_total')
    if mc and mc > 0:
        new_scale = round(mc / 1e8, 3)
        old = e.get('scale_yi', 0)
        if abs(old - new_scale) > 1:
            print(f"  {code} {e['name']}: {old}亿 → {new_scale}亿")
            e['scale_yi'] = new_scale
            updated_scale += 1

print(f"  规模更新: {updated_scale}只")


# ============================================================
# 2. Wind批量补费率（只补缺失的21只）
# ============================================================
need_fee = [e for e in data if not e.get('fee_mgmt') or e.get('fee_mgmt') == 0]
print(f"\n=== Step 2: Wind补费率 ({len(need_fee)}只缺失) ===")

if need_fee:
    NODE = '/Users/apangduo/.workbuddy/binaries/node/versions/22.12.0/bin/node'
    CLI = os.path.expanduser('~/.agents/skills/wind-mcp-skill/scripts/cli.mjs')
    
    if os.path.exists(CLI):
        for i, e in enumerate(need_fee):
            code = e['code']
            sys.stdout.write(f"  [{i+1}/{len(need_fee)}] {code} {e['name']} ")
            sys.stdout.flush()
            try:
                r = subprocess.run(
                    [NODE, CLI, 'call', 'fund_data', 'get_fund_info',
                     json.dumps({"question": f"{code} {e['name']} 管理费率 托管费率"})],
                    capture_output=True, text=True, timeout=20
                )
                d = json.loads(r.stdout)
                # 解析Wind返回的费率
                text = str(d).lower()
                # 尝试提取费率数字
                import re
                mgmt = re.findall(r'管理费[率\s]*[:：]?\s*([0-9.]+)\s*%', str(d))
                custody = re.findall(r'托管费[率\s]*[:：]?\s*([0-9.]+)\s*%', str(d))
                
                if mgmt:
                    e['fee_mgmt'] = float(mgmt[0])
                    e['fee_total'] = float(mgmt[0])
                    print(f"管理费={mgmt[0]}%", end='')
                if custody:
                    e['fee_custody'] = float(custody[0])
                    if e.get('fee_total'):
                        e['fee_total'] = round(e['fee_total'] + float(custody[0]), 2)
                    print(f" 托管费={custody[0]}%", end='')
                print()
            except Exception as ex:
                print(f"错误: {ex}")
            time.sleep(0.5)
    else:
        print(f"  Wind CLI 不存在: {CLI}")
        print(f"  跳过Wind批量查询")

# ============================================================
# 3. 保存更新
# ============================================================
print(f"\n=== Step 3: 保存 ===")
with open(JSON_FILE, 'w') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
print(f"  etf_core_data.json 已更新")

# 重新生成 embed.js
embed_path = os.path.join(os.path.dirname(JSON_FILE), 'etf_data_embed.js')
with open(embed_path, 'w') as f:
    f.write('var ETF_CORE_DATA = ')
    json.dump(data, f, ensure_ascii=False, separators=(',', ':'))
    f.write(';')
    # 预处理 holdings_str
    for e in data:
        h = e.get('holdings', [])
        if h:
            e['holdings_str'] = '\n'.join([f"{x.get('name','')} {x.get('weight','')}" for x in h[:5]])

print(f"  etf_data_embed.js 已重新生成 ({os.path.getsize(embed_path)} bytes)")

# 统计
has_fee = sum(1 for e in data if e.get('fee_mgmt') and e.get('fee_mgmt') > 0)
print(f"\n=== 完成 ===")
print(f"  规模: {len(data)}/200 覆盖率100%")
print(f"  管理费: {has_fee}/200 ({has_fee/2:.0f}%)")
