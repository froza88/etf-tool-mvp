#!/usr/bin/env python3
"""综合四股深度分析 - 数据采集 + 四引擎计算 + HTML报告"""
import json, os, subprocess, math, time
from datetime import datetime

STOCKS = [
    ("600673", "东阳光"),
    ("600391", "航发科技"),
    ("600207", "安彩高科"),
    ("515880", "通信ETF国泰"),
]

WESTOCK = "/Users/apangduo/.workbuddy/binaries/node/versions/22.12.0/bin/node"
WESTOCK_SCRIPT = "/Users/apangduo/.workbuddy/plugins/marketplaces/cb_teams_marketplace/plugins/finance-data/skills/westock-data/scripts/index.js"
OUTPUT = "/Users/apangduo/WorkBuddy/Claw/report/四引擎深度分析.html"

def run_westock(cmd):
    """Execute westock-data command"""
    result = subprocess.run([WESTOCK, WESTOCK_SCRIPT] + cmd.split(), capture_output=True, text=True, timeout=30)
    return result.stdout

def parse_quote(text):
    """Parse westock quote table output"""
    lines = text.strip().split('\n')
    if len(lines) < 4:
        return {}
    # Find header row
    header = [h.strip() for h in lines[2].split('|') if h.strip()]
    data = [d.strip() for d in lines[3].split('|') if d.strip()]
    result = {}
    for i, key in enumerate(header):
        if i < len(data):
            result[key] = data[i]
    return result

def parse_technical(text):
    """Parse technical indicator output"""
    lines = text.strip().split('\n')
    result = {}
    for line in lines:
        if '|' not in line or 'code' in line.lower():
            continue
        parts = [p.strip() for p in line.split('|') if p.strip()]
        if len(parts) >= 2:
            result[parts[0]] = parts[1:]
    return result

def calc_tech_score(q, kline_len=0):
    """Technical score based on quote data"""
    sc = 50
    bu, be = [], []
    chg = float(q.get('change_percent', 0))
    chg5d = float(q.get('chg_5d', 0))
    chg20d = float(q.get('chg_20d', 0))
    
    if chg > 0: sc += 8; bu.append('当日上涨')
    else: sc -= 5; be.append('当日下跌')
    if chg5d > 0: sc += 5; bu.append(f'5日{chg5d:.1f}%')
    else: sc -= 3; be.append(f'5日跌{chg5d:.1f}%')
    if chg20d < -15: sc += 10; bu.append('超卖可能')
    elif chg20d > 15: sc -= 5; be.append('涨幅过大')
    
    turnover = float(q.get('turnover_rate', 0))
    if turnover < 1: sc -= 5; be.append('换手低')
    elif turnover > 10: sc -= 3; be.append('换手偏高')
    
    sc = max(0, min(100, sc))
    return sc, bu, be

def calc_fund_score(q):
    """Fundamental score"""
    sc = 50; bu, be = [], []
    pe = q.get('pe_ratio', '0')
    pb = q.get('pb_ratio', '0')
    cap = q.get('total_market_cap', '0')
    
    try:
        pe_f = float(pe)
        if pe_f < 0: sc -= 20; be.append('亏损')
        elif pe_f < 20: sc += 15; bu.append(f'PE={pe_f:.1f}偏低')
        elif pe_f < 40: sc += 5; bu.append('PE合理')
        elif pe_f > 100: sc -= 10; be.append(f'PE={pe_f:.0f}虚高')
    except: pass
    
    try:
        pb_f = float(pb)
        if pb_f < 2: sc += 10; bu.append(f'PB={pb_f:.1f}低')
        elif pb_f > 10: sc -= 5
    except: pass
    
    sc = max(0, min(100, sc))
    return sc, bu, be

results = []

for code, name in STOCKS:
    print(f"\n======== {name} ({code}) ========")
    ts = time.time()
    
    # 1. Quote
    print(f"  [quote] ", end='')
    q_text = run_westock(f"quote {code}")
    q = parse_quote(q_text)
    if not q:
        print("FAILED")
        continue
    print(f"¥{q.get('price','?')} {q.get('change_percent','?')}%")
    
    # 2. Technical (if available)
    print(f"  [technical] ", end='')
    try:
        tech_text = run_westock(f"technical {code} --group ma,rsi,kdj,boll")
        tech = parse_technical(tech_text)
        t_len = len(tech) if tech else 0
        print(f"{t_len} indicators OK" if t_len > 0 else "empty")
    except:
        print("skip")
    
    # 3. Scores
    ts_score, bu, be = calc_tech_score(q)
    fs_score, fu, fe = calc_fund_score(q)
    final = round(ts_score * 0.4 + fs_score * 0.6)
    
    if final > 60: verdict = "BUY"; conf = min(85, final)
    elif final < 40: verdict = "SELL"; conf = min(80, 100-final)
    else: verdict = "HOLD"; conf = 55
    
    results.append({
        'code': code, 'name': name,
        'price': q.get('price',''), 'chg': q.get('change_percent',''),
        'pe': q.get('pe_ratio',''), 'pb': q.get('pb_ratio',''),
        'cap': q.get('total_market_cap',''), 'turnover': q.get('turnover_rate',''),
        'chg5d': q.get('chg_5d',''), 'chg20d': q.get('chg_20d',''),
        'tech_score': ts_score, 'fund_score': fs_score,
        'final_score': final, 'verdict': verdict, 'confidence': conf,
        'tech_bulls': bu, 'tech_bears': be,
        'fund_bulls': fu, 'fund_bears': fe,
    })
    print(f"  Finished: {verdict} ({conf}%) [{time.time()-ts:.0f}s]")


# Generate HTML
def fmt(v, d=2):
    try: return f"{float(v):.{d}f}"
    except: return str(v)

colors = [('#C41230','#FFF0F0'), ('#1A5FB4','#EEF4FF'), ('#1A7A3A','#EEF8EE'), ('#D97706','#FFF3E0')]

html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="UTF-8"><title>四引擎深度分析 {datetime.now().strftime('%Y-%m-%d')}</title>
<style>
:root{{--bg:#FEFCF8;--card:#fff;--text:#1a1a1a;--red:#C41230;--green:#1A7A3A;--blue:#1A5FB4;--border:#E6E4E0}}
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:"Helvetica Neue","PingFang SC",sans-serif;background:var(--bg);color:var(--text);padding:24px}}
h1{{font-size:24px;font-weight:700;margin-bottom:20px}}
.divider{{width:36px;height:3px;background:var(--red);margin:8px 0 20px}}
table{{width:100%;border-collapse:collapse;margin:16px 0;font-size:13px}}
th,td{{padding:10px 12px;border-bottom:1px solid var(--border);text-align:center}}
th{{background:#f8f8f8;font-weight:500;color:#555;font-size:11px}}
.best{{background:#FFF9F0;font-weight:700}}
.red{{color:var(--red);font-weight:600}}
.green{{color:var(--green);font-weight:600}}
.verdict{{display:inline-block;padding:3px 12px;border-radius:10px;font-size:12px;font-weight:700}}
.verdict.BUY{{background:#dcfce7;color:var(--green)}}
.verdict.SELL{{background:#fee2e2;color:var(--red)}}
.verdict.HOLD{{background:#fef3c7;color:#92400e}}
.card-grid{{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin:16px 0}}
.card{{border:1px solid var(--border);padding:16px;background:var(--card)}}
.card h3{{font-size:14px;margin-bottom:8px}}
.score-bar{{height:6px;border-radius:3px;background:#eee;margin:6px 0;overflow:hidden}}
.score-fill{{height:100%;border-radius:3px}}
.footer{{text-align:center;color:#888;font-size:11px;margin-top:32px;padding-top:16px;border-top:1px solid var(--border)}}
</style></head>
<body>
<h1>四引擎深度分析 · {datetime.now().strftime('%Y-%m-%d')}</h1>
<div class="divider"></div>

<h2>对比总表</h2>
<table><thead><tr>
<th>标的</th><th>现价</th><th>涨跌</th><th>PE</th><th>PB</th><th>市值(亿)</th><th>换手%</th><th>5日%</th><th>20日%</th><th>技术面</th><th>基本面</th><th>综合</th><th>建议</th>
</tr></thead><tbody>
{''.join(f'''<tr>
<td style="font-weight:700">{r['name']}<br><span style=font-size:10px;color:#888>{r['code']}</span></td>
<td>{r['price']}</td>
<td class="{'red' if float(r['chg'])>0 else 'green'}">{fmt(r['chg'],2)}%</td>
<td>{r['pe']}</td>
<td>{r['pb']}</td>
<td>{fmt(float(r['cap'])/1e8,0) if r['cap'] and float(r['cap'])>0 else '--'}</td>
<td>{r['turnover']}</td>
<td class="{'red' if float(r.get('chg5d',0))>0 else 'green'}">{fmt(r.get('chg5d',0),2)}%</td>
<td class="{'red' if float(r.get('chg20d',0))>0 else 'green'}">{fmt(r.get('chg20d',0),2)}%</td>
<td>{r['tech_score']}/100</td><td>{r['fund_score']}/100</td>
<td style="font-weight:700">{r['final_score']}/100</td>
<td><span class="verdict {r['verdict']}">{r['verdict']} ({r['confidence']}%)</span></td>
</tr>''' for r in results)}
</tbody></table>

<h2>各标详情</h2>
<div class="card-grid">
{''.join(f'''<div class="card">
<h3>{r['name']} ({r['code']}) <span class="verdict {r['verdict']}">{r['verdict']} ({r['confidence']}%)</span></h3>
<div style="margin:8px 0">
<div style="font-size:11px;color:#888;margin-bottom:2px">技术面 {r['tech_score']}/100</div>
<div class="score-bar"><div class="score-fill" style="width:{r['tech_score']}%;background:{'var(--red)' if r['tech_score']>60 else 'var(--green)' if r['tech_score']<40 else '#ccc'}"></div></div>
<div style="font-size:11px;margin:4px 0">{' '.join('✅'+b for b in r['tech_bulls'])} {' '.join('⚠️'+b for b in r['tech_bears'])}</div>
</div>
<div style="margin:8px 0">
<div style="font-size:11px;color:#888;margin-bottom:2px">基本面 {r['fund_score']}/100</div>
<div class="score-bar"><div class="score-fill" style="width:{r['fund_score']}%;background:{'var(--red)' if r['fund_score']>60 else 'var(--green)' if r['fund_score']<40 else '#ccc'}"></div></div>
<div style="font-size:11px;margin:4px 0">{' '.join('✅'+b for b in r['fund_bulls'])} {' '.join('⚠️'+b for b in r['fund_bears'])}</div>
</div>
<div style="font-size:11px;color:#888;margin-top:8px">PE {r['pe']} | PB {r['pb']} | 市值{fmt(float(r['cap'])/1e8,0) if r['cap'] and float(r['cap'])>0 else '0'}亿</div>
</div>''' for r in results)}
</div>

<div class="footer">
<p>数据来源：腾讯行情 (westock-data) · 分析时间 {datetime.now().strftime('%Y-%m-%d %H:%M')} · ⚠️ 仅供参考，不构成投资建议</p>
</div>
</body></html>"""

with open(OUTPUT, 'w') as f:
    f.write(html)
print(f"\n✅ HTML报告已生成: {OUTPUT}")
print(f"   共分析 {len(results)} 只标的")
