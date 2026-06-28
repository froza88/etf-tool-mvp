import akshare as ak
import json
import time
from datetime import datetime

SYMBOLS = [
    '上证50', '沪深300', '上证380', '创业板50', '中证500',
    '上证180', '深证红利', '深证100', '中证1000',
    '上证红利', '中证100', '中证800'
]

def temp_label(pct):
    if pct <= 20: return '低估'
    if pct <= 40: return '偏低'
    if pct <= 60: return '适中'
    if pct <= 80: return '偏高'
    return '高估'

def temp_color(pct):
    if pct <= 20: return '#2e7d32'
    if pct <= 40: return '#66bb6a'
    if pct <= 60: return '#ff9800'
    if pct <= 80: return '#ef5350'
    return '#d32f2f'

rows = []

for s in SYMBOLS:
    try:
        time.sleep(2)
        df_pe = ak.stock_index_pe_lg(symbol=s)
        cur_pe = float(df_pe['滚动市盈率'].iloc[-1])
        hist_pe = df_pe['滚动市盈率'].dropna()
        pe_pct = round((hist_pe < cur_pe).sum() / len(hist_pe) * 100, 1)

        time.sleep(2)
        df_pb = ak.stock_index_pb_lg(symbol=s)
        cur_pb = float(df_pb['市净率'].iloc[-1])
        hist_pb = df_pb['市净率'].dropna()
        pb_pct = round((hist_pb < cur_pb).sum() / len(hist_pb) * 100, 1)

        rows.append({
            'benchmark': s,
            'pe': cur_pe,
            'pe_percentile': pe_pct,
            'pb': cur_pb,
            'pb_percentile': pb_pct,
            'level': temp_label(pe_pct),
            'level_color': temp_color(pe_pct),
            'pe_days': len(hist_pe),
            'pb_days': len(hist_pb),
        })
        print(f'✅ {s}: PE={cur_pe:.2f}(分位{pe_pct}%) PB={cur_pb:.2f}(分位{pb_pct}%)')
    except Exception as e:
        print(f'❌ {s}: {str(e)[:80]}')

# Sort by PE percentile
rows.sort(key=lambda r: r['pe_percentile'])

result = {
    'count': len(rows),
    'updated': datetime.now().isoformat(),
    'source': 'legulegu.com via AKShare',
    'rows': rows
}

out = '/Users/apangduo/WorkBuddy/Claw/etf-tool-mvp/v2_deploy_pkg/valuation.json'
with open(out, 'w') as f:
    json.dump(result, f, ensure_ascii=False, indent=2)

print(f'\n共 {len(rows)} 条 → {out}')
