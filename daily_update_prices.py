#!/usr/bin/env python3
"""每日价格更新 + 上传 PA（独立脚本，可被 crontab/automation 调用）"""
import json, subprocess, sys, os
from datetime import datetime
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

ROOT = Path(__file__).parent

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

# ── Step 1: 获取 AKShare 行情 ──
log("Step 1: 获取 AKShare 实时行情...")
import akshare as ak
df = ak.fund_etf_spot_em()
log(f"  AKShare 返回 {len(df)} 只 ETF")

price_map = {}
for _, row in df.iterrows():
    try:
        code = str(row['代码']).strip()
        price_map[code] = {
            'close': float(row['最新价']),
            'prev_close': float(row['昨收']),
            'volume': round(float(row.get('成交额', 0)) / 1e8, 2),
        }
    except:
        pass
log(f"  价格映射: {len(price_map)} 只")

# ── Step 2: 更新本地 JSON ──
files = [
    ROOT / 'etf_standard_data.json',
    ROOT / 'v2_deploy_pkg' / 'etf_core_data.json',
]
now_ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

for fp in files:
    if not fp.exists():
        log(f"  跳过: {fp.name}")
        continue
    with open(fp, encoding='utf-8') as f:
        data = json.load(f)
    updated = 0
    for e in data:
        code = e.get('code', '')
        if code in price_map:
            pm = price_map[code]
            e['close'] = pm['close']
            e['prev_close'] = pm['prev_close']
            e['volume'] = pm['volume']
            if pm['prev_close']:
                e['change_pct'] = round((pm['close'] - pm['prev_close']) / pm['prev_close'] * 100, 2)
                e['change_rate'] = round((pm['close'] - pm['prev_close']) / pm['prev_close'], 6)
            e['updated'] = now_ts
            updated += 1
    with open(fp, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    log(f"  {fp.name}: {updated}/{len(data)} 更新")

# ── Step 3: 上传 PA ──
log("Step 3: 上传到 PythonAnywhere...")
token_file = Path.home() / '.pythonanywhere_token'
if not token_file.exists():
    log("  无 PA token，跳过上传")
    sys.exit(0)

PA_TOKEN = token_file.read_text().strip()
USER = 'froza'
API = 'https://www.pythonanywhere.com/api/v0'
AUTH = f'Authorization: Token {PA_TOKEN}'

data_file = ROOT / 'v2_deploy_pkg' / 'etf_core_data.json'
if data_file.stat().st_size > 0:
    result = subprocess.run([
        'curl', '-s', '-w', '%{http_code}', '-H', AUTH,
        f'{API}/user/{USER}/files/path/home/{USER}/etf-tool-mvp/etf_core_data.json',
        '-F', f'content=@{data_file}'
    ], capture_output=True, text=True, timeout=60)
    log(f"  上传结果: HTTP {result.stdout[-3:]}")

# Reload
result = subprocess.run([
    'curl', '-s', '-H', AUTH,
    f'{API}/user/{USER}/webapps/{USER}.pythonanywhere.com/reload/',
    '-X', 'POST'
], capture_output=True, text=True, timeout=30)
log(f"  Reload: {result.stdout.strip()}")

# ── Step 4: 验证 ──
with open(ROOT / 'etf_standard_data.json') as f:
    data = json.load(f)
pos = sum(1 for e in data if float(e.get('change_pct', 0)) > 0)
neg = sum(1 for e in data if float(e.get('change_pct', 0)) < 0)
log(f"完成! 涨={pos}, 跌={neg}, 更新时间={now_ts}")
