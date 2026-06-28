#!/usr/bin/env python3
"""Scrapling 数据源 —— 爬东方财富 F10 页面补全费率/基准/规模等字段
用法:
  python scripts/scrapling_fetch.py check              # 快速检查缺失
  python scripts/scrapling_fetch.py fill               # 补全缺失字段 (断点续传)
  python scripts/scrapling_fetch.py fill --force       # 强制全量刷新
  python scripts/scrapling_fetch.py test 510300        # 测试单只ETF
"""

import json, re, os, sys, time, argparse
from datetime import datetime
from collections import Counter

DATA_FILE = 'etf_standard_data.json'
CACHE_DIR = 'data/cache/scrapling'
F10_URL = 'https://fundf10.eastmoney.com/jbgk_{code}.html'
DELAY = 0.3  # 300ms between requests

sys.path.insert(0, '/Users/apangduo/.workbuddy/binaries/python/envs/default/lib/python3.13/site-packages')

# ── 提取规则 ──────────────────────────────────────────
FIELD_RULES = [
    # (行匹配关键词列表, 正则提取, 目标字段名, 后处理)
    # 注意: 数据模型使用百分比值 (0.5 = 0.5%), 不除以100
    # F10页面HTML剥离后格式: key|value| 或 key：|value| 或 key：&nbsp;|value|
    ('管理费率', r'管理费率[：:]?\s*(?:&nbsp;)*\|(\d+\.?\d*)%', 'management_fee_rate', lambda v: float(v)),
    ('托管费率', r'托管费率[：:]?\s*(?:&nbsp;)*\|(\d+\.?\d*)%', 'custody_fee_rate', lambda v: float(v)),
    ('跟踪标的', r'跟踪标的\|([^|]+)', 'benchmark', str),
    ('业绩比较基准', r'业绩比较基准\|([^|]+)', 'benchmark_alt', str),
    ('成立日期', r'成立日期[：:]?\s*(?:&nbsp;)*\|(\d{4}-\d{2}-\d{2})', 'inception_date', str),
    ('净资产规模', r'净资产规模[：:]?\s*(?:&nbsp;)*\|([\d,.]+\s*[亿万]元)', 'fund_size_str', str),
    ('基金经理', r'基金经理[：:][^|]*\|([^|]+)', 'manager', str, '基金经理：'),  # use colon version to avoid nav match
    ('基金托管人', r'基金托管人[：:]?\s*(?:&nbsp;)*\|([^|]+)', 'custodian', str),
    ('基金类型', r'类型[：:]?\s*(?:&nbsp;)*\|([^|]+)', 'fund_type', str),
]

def strip_html(html):
    """Remove HTML tags, scripts, styles"""
    html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL)
    html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL)
    html = re.sub(r'<[^>]+>', '|', html)
    html = re.sub(r'\|+', '|', html)
    html = re.sub(r'\s+', ' ', html)
    return html

def fetch_one(code):
    """Scrape single ETF F10 page, return dict of extracted fields"""
    from scrapling import Fetcher
    f = Fetcher(headers={
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
    })

    url = F10_URL.format(code=code)
    try:
        page = f.get(url, timeout=15)
        if page.status != 200 or len(page.body) < 1000:
            return None
        html = page.body.decode('utf-8', errors='ignore')
        text = strip_html(html)

        result = {}
        for rule in FIELD_RULES:
            keyword = rule[0] if len(rule) <= 4 else rule[4]  # optional search-keyword override
            pattern = rule[1]
            field = rule[2]
            postprocess = rule[3]
            # Find section containing keyword
            idx = text.find(keyword)
            if idx >= 0:
                snippet = text[idx:idx+200]
            else:
                snippet = text

            match = re.search(pattern, snippet)
            if match:
                try:
                    result[field] = postprocess(match.group(1).strip())
                except (ValueError, TypeError):
                    pass

        # Cache raw response
        os.makedirs(CACHE_DIR, exist_ok=True)
        cache_file = os.path.join(CACHE_DIR, f'{code}.json')
        result['_cached_at'] = datetime.now().isoformat()
        with open(cache_file, 'w', encoding='utf-8') as fout:
            json.dump(result, fout, ensure_ascii=False, indent=2)

        return result
    except Exception as e:
        return None

def save_data(etfs):
    """Save etf list back to json"""
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(etfs, f, ensure_ascii=False, indent=2)

def cmd_check():
    """Check which fields are missing"""
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        etfs = json.load(f)

    total = len(etfs)
    fields = {
        'management_fee_rate': ('管理费率', lambda e: e.get('management_fee_rate') not in (None, '', 0)),
        'custody_fee_rate': ('托管费率', lambda e: e.get('custody_fee_rate') not in (None, '', 0)),
        'benchmark': ('跟踪指数', lambda e: bool(e.get('benchmark'))),
        'inception_date': ('成立日期', lambda e: bool(e.get('inception_date'))),
        'manager': ('基金经理', lambda e: bool(e.get('manager'))),
    }

    print(f'ETF总数: {total}\n')
    print(f'{"字段":<16} {"有值":>6} {"覆盖率":>8} {"缺少"}')
    print('-' * 50)
    for fname, (label, check_fn) in fields.items():
        with_val = sum(1 for e in etfs if check_fn(e))
        missing = total - with_val
        pct = with_val / total * 100
        print(f'{label:<12} ({fname:<20}) {with_val:>6} {pct:>7.1f}% {missing:>5}只')
    print()

    # Also show non-fee rate ETFs that might need special handling
    print('ETF类型分布（缺少费率的前5类）:')
    type_missing = Counter()
    for e in etfs:
        if not e.get('management_fee_rate'):
            ft = e.get('fund_type', e.get('type', '未知'))
            type_missing[ft] += 1
    for ft, cnt in type_missing.most_common(5):
        print(f'  {ft}: {cnt}只')

def cmd_test(code):
    """Test single ETF"""
    print(f'测试 {code} ...')
    result = fetch_one(code)
    if result:
        print(json.dumps({k:v for k,v in result.items() if not k.startswith('_')},
                        ensure_ascii=False, indent=2))
    else:
        print(f'❌ 获取失败')

def cmd_fill(force=False):
    """Fill missing fields using Scrapling"""
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        etfs = json.load(f)

    total = len(etfs)

    # Determine which ETFs need filling (prioritize fee rate gaps)
    needs = []
    for i, e in enumerate(etfs):
        need = force
        if not force:
            # Priority 1: missing fee rates (small gap, quick win)
            # Priority 2: missing benchmark or all other fields
            need = (
                not e.get('management_fee_rate') or
                not e.get('custody_fee_rate') or
                not e.get('benchmark')
            )
        if need:
            needs.append((i, e['code']))

    if not needs:
        print('✅ 无缺失字段，跳过')
        return

    print(f'需补全: {len(needs)} / {total} 只')
    print(f'预估: {len(needs) * (DELAY + 1):.0f} 秒\n')

    ok = fail = skip = 0
    filled_fields = Counter()

    for idx, (i, code) in enumerate(needs):
        e = etfs[i]
        name = e.get('name', code)
        cache_file = os.path.join(CACHE_DIR, f'{code}.json')

        # Check cache (1 day TTL)
        if not force and os.path.exists(cache_file):
            mtime = os.path.getmtime(cache_file)
            if time.time() - mtime < 86400:
                with open(cache_file, 'r') as fc:
                    result = json.load(fc)
            else:
                result = fetch_one(code)
        else:
            result = fetch_one(code)

        if not result:
            fail += 1
            if (idx+1) % 50 == 0:
                print(f'[{datetime.now():%H:%M:%S}] {idx+1}/{len(needs)} ⚠️ fail={fail}', flush=True)
            time.sleep(DELAY * 2)
            continue

        # Merge extracted fields (only if currently empty or force)
        merged = 0
        for field in ['management_fee_rate','custody_fee_rate','benchmark','inception_date','manager','custodian','fund_type']:
            val = result.get(field)
            if val is not None and val != '' and val != 0:
                if force or not etfs[i].get(field):
                    etfs[i][field] = val
                    merged += 1
                    filled_fields[field] += 1

        # benchmark_alt as fallback
        if not etfs[i].get('benchmark') and result.get('benchmark_alt') and result['benchmark_alt'] != '---':
            etfs[i]['benchmark'] = result['benchmark_alt']
            merged += 1
            filled_fields['benchmark'] += 1

        # fund_size: parse and store as raw string if useful
        if result.get('fund_size_str'):
            etfs[i]['fund_size_raw'] = result['fund_size_str']

        if merged:
            ok += 1
        else:
            skip += 1

        # Progress
        if (idx+1) % 100 == 0:
            save_data(etfs)
            print(f'[{datetime.now():%H:%M:%S}] {idx+1}/{len(needs)} ok={ok} skip={skip} fail={fail}', flush=True)

        time.sleep(DELAY)

    # Final save
    save_data(etfs)

    # Stats
    print(f'\n{"="*50}')
    print(f'完成: ok={ok} skip={skip} fail={fail}')
    print(f'字段填充:')
    for field, cnt in filled_fields.most_common():
        print(f'  {field}: +{cnt}')
    print(f'\n数据保存至 {DATA_FILE}')

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Scrapling 东方财富数据采集')
    parser.add_argument('cmd', choices=['check','fill','test'])
    parser.add_argument('code', nargs='?', help='ETF code for test')
    parser.add_argument('--force', action='store_true', help='强制全量刷新')
    args = parser.parse_args()

    os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    if args.cmd == 'check':
        cmd_check()
    elif args.cmd == 'fill':
        cmd_fill(force=args.force)
    elif args.cmd == 'test':
        cmd_test(args.code)
