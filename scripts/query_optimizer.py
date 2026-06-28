#!/usr/bin/env python3
"""
ETF 全能查询优化器 — 缓存优先 · 多源择优 · 断点续传 · 余额估算
用法:
  python query_optimizer.py flow       # 资金流入
  python query_optimizer.py valuation  # 估值分位
  python query_optimizer.py missing    # 所有缺失字段
  python query_optimizer.py status     # 统计面板
"""
import json, os, sys, subprocess, time, argparse
from datetime import datetime, timedelta
from collections import Counter

# ── 路径配置 ───────────────────────────────────
BASE = os.path.expanduser('~/WorkBuddy/Claw/etf-tool-mvp')
DATA_FILE = f'{BASE}/prototypes/etf_core_data.json'
SCRAPLING_SCRIPT = f'{BASE}/scripts/scrapling_fetch.py'
WIND_CACHE = f'{BASE}/data/wind_full'
NODE = os.path.expanduser('~/.workbuddy/binaries/node/versions/22.12.0/bin/node')
WIND_CLI = os.path.expanduser('~/.agents/skills/wind-mcp-skill/scripts/cli.mjs')

# ── 源优先级 (0=最快/免费, 越大越贵/慢) ──────
SOURCE_PRIORITY = ['wind_cache', 'scrapling', 'wind_mcp', 'ifind_mcp']

# ── 资金流入: 东方财富 F10 仓位变动页 ──────────
FLOW_URL = 'https://fundf10.eastmoney.com/ccmx_{code}.html'
FLOW_REGEX = r'近1周[：:]?\s*\|?([\-\d,.]+\s*[万亿]?份)'  # 需验证

# ── Wind MCP 查询模板 ──────────────────────────
WIND_QUERIES = {
    'flow': '{code}.OF {name} 最近一周 净申购赎回 份额变动',
    'risk': '{code}.OF {name} 风险指标 贝塔 阿尔法 信息比率 跟踪误差',
    'fee': '{code}.OF {name} 管理费率 托管费率',
    'valuation': '{code}.OF {name} 估值 市盈率',
}

def log(msg):
    print(f'[{datetime.now():%H:%M:%S}] {msg}', flush=True)

def log_progress(msg):
    print(f'[{datetime.now():%H:%M:%S}] {msg}', end=' ', flush=True)

def load_data():
    with open(DATA_FILE, encoding='utf-8') as f:
        return json.load(f)

def save_data(data):
    bak = f'{DATA_FILE}.bak.{datetime.now():%Y%m%d_%H%M}'
    import shutil
    shutil.copy2(DATA_FILE, bak)
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    log(f'已保存 + 备份: {bak}')

# ── 缓存管理 ───────────────────────────────────
def check_wind_cache(code):
    """检查 Wind 本地缓存是否有效（7天内）"""
    today = datetime.now().strftime('%Y%m%d')
    cache_file = f'{WIND_CACHE}/{code}_{today}.json'
    if os.path.exists(cache_file):
        with open(cache_file) as f:
            raw = json.load(f)
        return raw
    # 检查近7天
    for d in range(1, 8):
        dt = (datetime.now() - timedelta(days=d)).strftime('%Y%m%d')
        cf = f'{WIND_CACHE}/{code}_{dt}.json'
        if os.path.exists(cf):
            with open(cf) as f:
                return json.load(f)
    return None

def parse_wind_flow(raw):
    """从 Wind 缓存解析资金流入"""
    try:
        inner = json.loads(raw['content'][0]['text'])
        cols = [c['name'] for c in inner['data']['data'][0]['columns']]
        row = inner['data']['data'][0]['rows'][0]
        for i, c in enumerate(cols):
            if '净申购' in c and row[i] is not None:
                return float(row[i])
    except:
        pass
    return None

# ── Wind MCP 实时查询 ──────────────────────────
def query_wind(code, name, qtype='flow'):
    """单次 Wind MCP 查询"""
    q = WIND_QUERIES[qtype].format(code=code, name=name)
    cmd = [NODE, WIND_CLI, 'call', 'fund_data', 'get_fund_info', json.dumps({'question': q})]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=25)
        raw = result.stdout.strip()
        resp = json.loads(raw)
        if resp.get('isError'):
            return None
        # 缓存到 wind_full
        os.makedirs(WIND_CACHE, exist_ok=True)
        today = datetime.now().strftime('%Y%m%d')
        with open(f'{WIND_CACHE}/{code}_{today}.json', 'w') as f:
            f.write(raw)
        return resp
    except Exception as e:
        return None

# ── Scrapling 免费抓取 ─────────────────────────
def fetch_scrapling(code, field_rules, cache_dir='data/cache/scrapling'):
    """通用 Scrapling 字段抓取"""
    import requests, re
    url = f'https://fundf10.eastmoney.com/jbgk_{code}.html'
    try:
        resp = requests.get(url, headers={
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)',
            'Referer': 'https://fundf10.eastmoney.com/'
        }, timeout=10)
        text = resp.text
        # Strip HTML
        text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.DOTALL)
        text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL)
        text = re.sub(r'<[^>]+>', '|', text)
        text = re.sub(r'\|+', '|', text)
        text = re.sub(r'\s+', ' ', text)
        
        result = {}
        for rule_name, pattern, field, postprocess in field_rules:
            match = re.search(pattern, text)
            if match:
                try:
                    result[field] = postprocess(match.group(1).strip())
                except (ValueError, TypeError):
                    pass
        return result if result else None
    except:
        return None

# ── 主流程: 资金流入全源查询 ───────────────────
def optimize_flow(args):
    data = load_data()
    total = len(data)
    
    # Step 1: 统计现状
    existing = sum(1 for e in data if e.get('net_inflow_5d'))
    todo = [(i, e) for i, e in enumerate(data) if not e.get('net_inflow_5d')]
    # 按规模降序 → 大的先查
    todo.sort(key=lambda x: x[1].get('scale', 0) or 0, reverse=True)
    
    log(f'资金流入: 已有 {existing}/{total} ({existing/total*100:.0f}%), 待补 {len(todo)} 只')
    log(f'按规模排序, 预估 {len(todo)*args.interval/60:.0f} 分钟\n')
    
    # Step 2: 源选择策略
    cache_hits = 0
    scrapling_hits = 0
    wind_hits = 0
    fails = 0
    processed = 0
    
    for pos, (idx, etf) in enumerate(todo):
        code, name = etf['code'], etf.get('name', '')
        scale = etf.get('scale', 0) or 0
        
        # 源1: 检查本地缓存 (最快, 免费)
        cached = check_wind_cache(code)
        if cached:
            flow = parse_wind_flow(cached)
            if flow is not None:
                data[idx]['net_inflow_5d'] = round(flow, 2)
                data[idx]['net_inflow_source'] = 'wind_cache'
                cache_hits += 1
                processed += 1
                if processed % 50 == 0:
                    log(f'  缓存命中: {cache_hits}, Scrapling: {scrapling_hits}, Wind: {wind_hits}, 失败: {fails}  [{processed}/{len(todo)}]')
                continue
        
        # 源2: Scrapling 东方财富 (免费)
        if args.use_scrapling:
            scrapling_rules = [
                ('flow', FLOW_REGEX, 'net_inflow_5d', lambda v: float(v.replace(',','').replace('亿','').replace('万','').replace('份',''))),
            ]
            scraped = fetch_scrapling(code, scrapling_rules)
            if scraped and scraped.get('net_inflow_5d'):
                data[idx]['net_inflow_5d'] = scraped['net_inflow_5d']
                data[idx]['net_inflow_source'] = 'scrapling'
                scrapling_hits += 1
                processed += 1
                time.sleep(0.3)
                continue
        
        # 源3: Wind MCP (付费)
        if args.use_wind:
            log_progress(f'  [{pos+1}/{len(todo)}] Wind: {code} {name} (规模:{scale:.0f}亿)')
            result = query_wind(code, name, 'flow')
            if result:
                flow = parse_wind_flow(result)
                if flow is not None:
                    data[idx]['net_inflow_5d'] = round(flow, 2)
                    data[idx]['net_inflow_source'] = 'wind_mcp'
                    wind_hits += 1
                    log(f'✅ {flow:+.0f}份')
                else:
                    fails += 1
                    log('⚠️ 格式不匹配')
            else:
                fails += 1
                log('❌')
            processed += 1
        
        # 断点续传: 每 20 条存盘
        if processed % 20 == 0:
            save_data(data)
            log(f'  💾 已保存 [{processed}/{len(todo)}] '
                f'缓存:{cache_hits} Scrapling:{scrapling_hits} Wind:{wind_hits} 失败:{fails}')
        
        # 间隔
        if pos < len(todo) - 1:
            time.sleep(args.interval)
    
    # 最终保存
    save_data(data)
    final_cov = sum(1 for e in data if e.get('net_inflow_5d'))
    log(f'\n{"="*50}')
    log(f'完成! 覆盖率: {final_cov}/{total} ({final_cov/total*100:.1f}%)')
    log(f'来源分布: 缓存{cache_hits} Scrapling{scrapling_hits} Wind{wind_hits} 失败{fails}')
    
    if args.use_wind:
        est_balance_used = wind_hits
        log(f'Wind MCP 估算消耗: ~{est_balance_used} 次查询')

# ── 统计面板 ───────────────────────────────────
def show_status(args):
    data = load_data()
    total = len(data)
    
    # 所有字段覆盖率
    all_fields = set()
    for e in data[:100]:
        all_fields.update(e.keys())
    
    print(f"\n╔══════════════════════════════════════════╗")
    print(f"║   ETF 查询优化器 · 统计面板              ║")
    print(f"║   {datetime.now():%Y-%m-%d %H:%M} · {total}只             ║")
    print(f"╚══════════════════════════════════════════╝")
    
    # 缓存统计
    wind_cache_count = len(os.listdir(WIND_CACHE)) if os.path.exists(WIND_CACHE) else 0
    fresh = 0
    today = datetime.now().strftime('%Y%m%d')
    for f in (os.listdir(WIND_CACHE) if os.path.exists(WIND_CACHE) else []):
        if today in f:
            fresh += 1
    
    print(f"\n─── 缓存状态 ───")
    print(f"  Wind 缓存: {wind_cache_count} 文件 ({fresh} 今日)")
    print(f"  Scrapling: {'已启用' if os.path.exists(f'{BASE}/scripts/scrapling_fetch.py') else '❌'}")
    
    print(f"\n─── 字段覆盖率 ───")
    fields_check = {
        '行情': ['close','change_pct','volume'],
        '收益': ['year_1_return','sharpe_ratio','max_drawdown'],
        '费率': ['management_fee_rate','custody_fee_rate','fee_rate'],
        '风控': ['beta','alpha','tracking_error','info_ratio'],
        '基本面': ['issue_date','custodian','fund_manager','benchmark'],
        '估值资金': ['valuation_percentile','net_inflow_5d'],
    }
    for cat, fs in fields_check.items():
        covs = []
        for f in fs:
            if f in all_fields:
                valid = sum(1 for e in data if e.get(f) not in (None, '', 0.0))
                covs.append(valid/total*100)
        if covs:
            avg = sum(covs)/len(covs)
            bar = '█'*int(avg/5) + '░'*(20-int(avg/5))
            print(f"  {cat:<10} {avg:>5.1f}% {bar}")
    
    # 数据来源分布
    sources = Counter()
    for e in data:
        for k in e.keys():
            if k.endswith('_source'):
                sources[e[k]] += 1
    if sources:
        print(f"\n─── 数据来源 ───")
        for src, cnt in sources.most_common():
            print(f"  {src}: {cnt} ({cnt/total*100:.0f}%)")
    
    print(f"\n─── 待补任务 ───")
    missing_flow = sum(1 for e in data if not e.get('net_inflow_5d'))
    missing_val = sum(1 for e in data if not e.get('valuation_percentile'))
    missing_beta = sum(1 for e in data if not e.get('beta'))
    if missing_flow:
        print(f"  🔴 资金流入: {missing_flow}只 → python query_optimizer.py flow")
    if missing_val:
        print(f"  🔴 估值分位: {missing_val}只 → python query_optimizer.py valuation")
    if missing_beta:
        print(f"  🔴 贝塔: {missing_beta}只 → python query_optimizer.py risk")

# ── CLI ────────────────────────────────────────
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='ETF 全能查询优化器')
    parser.add_argument('command', nargs='?', default='status',
                       choices=['status','flow','valuation','risk','fee','missing'])
    parser.add_argument('--interval', type=float, default=5.0, help='查询间隔秒数')
    parser.add_argument('--use-scrapling', action='store_true', default=True)
    parser.add_argument('--use-wind', action='store_true', default=True)
    parser.add_argument('--no-scrapling', dest='use_scrapling', action='store_false')
    parser.add_argument('--no-wind', dest='use_wind', action='store_false')
    parser.add_argument('--top', type=int, default=0, help='只处理前N只')
    args = parser.parse_args()
    
    if args.command == 'status':
        show_status(args)
    elif args.command == 'flow':
        optimize_flow(args)
    elif args.command in ('valuation', 'risk', 'fee'):
        log(f'模式 {args.command} 待实现')
    elif args.command == 'missing':
        log('扫描所有缺失字段...')
        show_status(args)
        # TODO: 自动选择最紧急的补
