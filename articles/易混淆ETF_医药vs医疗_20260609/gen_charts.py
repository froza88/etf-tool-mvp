#!/usr/bin/env python3
"""生成医药vs医疗 ETF 对比图表"""
import json, os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import numpy as np

# Register Chinese font
font_path = '/System/Library/Fonts/PingFang.ttc'
fm.fontManager.addfont(font_path)
plt.rcParams['font.family'] = 'PingFang HK'
plt.rcParams['axes.unicode_minus'] = False

BASE = os.path.dirname(os.path.abspath(__file__))
CHART_DIR = os.path.join(BASE, 'charts')
os.makedirs(CHART_DIR, exist_ok=True)

with open(os.path.join(BASE, 'data.json'), 'r', encoding='utf-8') as f:
    data = json.load(f)

# Colors
RED = '#C0392B'
RED_LIGHT = '#E74C3C'
BLUE = '#2471A3'
BLUE_LIGHT = '#5DADE2'
GRAY = '#95A5A6'
GRAY_DARK = '#7F8C8D'
BG = '#FEFCF8'
GRAY_BG = '#F5F5F5'

# Representative ETFs
rep_pharma = data['医药'][0]  # 512010
rep_med = data['医疗'][0]     # 512170

print(f"医药代表: {rep_pharma['code']} {rep_pharma['name']}")
print(f"医疗代表: {rep_med['code']} {rep_med['name']}")

# ============================================================
# Chart 1: Scale Donut
# ============================================================
pharma_etfs = data['医药']
med_etfs = data['医疗']

pharma_total = sum(e['scale'] for e in pharma_etfs)
med_total = sum(e['scale'] for e in med_etfs)

fig, axes = plt.subplots(1, 2, figsize=(12, 6), facecolor=BG)
fig.suptitle('医药ETF vs 医疗ETF · 规模分布', fontsize=16, fontweight='bold', color='#212529', y=0.98)

# Left: 医药ETF donut
ax = axes[0]
sizes_left = [e['scale'] for e in pharma_etfs[:6]]
labels_left = [f"{e['name'][:6]}" for e in pharma_etfs[:6]]
other_left = sum(e['scale'] for e in pharma_etfs[6:])
if other_left > 0:
    sizes_left.append(other_left)
    labels_left.append('其他')
colors_left = ['#C0392B','#E74C3C','#EC7063','#F1948A','#F5B7B1','#FADBD8','#E8E8E8']

wedges1, texts1, autotexts1 = ax.pie(
    sizes_left, labels=None, autopct='%1.1f%%',
    colors=colors_left[:len(sizes_left)],
    startangle=90, pctdistance=0.82,
    wedgeprops=dict(width=0.35, edgecolor='white', linewidth=1)
)
for at in autotexts1:
    at.set_fontsize(9)
    at.set_fontweight('bold')

# Legend below chart, outside the pie area
ax.legend(wedges1, [f"{l} ({s:.0f}亿)" for l, s in zip(labels_left, sizes_left)],
          loc='upper center', bbox_to_anchor=(0.5, -0.12), fontsize=8.5, ncol=2, frameon=False)
ax.set_title(f'医药ETF\n合计 {pharma_total:.0f}亿', fontsize=13, fontweight='bold', color=RED, pad=15)

# Right: 医疗ETF donut
ax = axes[1]
sizes_right = [e['scale'] for e in med_etfs[:6]]
labels_right = [f"{e['name'][:6]}" for e in med_etfs[:6]]
other_right = sum(e['scale'] for e in med_etfs[6:])
if other_right > 0:
    sizes_right.append(other_right)
    labels_right.append('其他')
colors_right = ['#2471A3','#2E86C1','#5DADE2','#85C1E9','#AED6F1','#D4E6F1','#E8E8E8']

wedges2, texts2, autotexts2 = ax.pie(
    sizes_right, labels=None, autopct='%1.1f%%',
    colors=colors_right[:len(sizes_right)],
    startangle=90, pctdistance=0.82,
    wedgeprops=dict(width=0.35, edgecolor='white', linewidth=1)
)
for at in autotexts2:
    at.set_fontsize(9)
    at.set_fontweight('bold')

ax.legend(wedges2, [f"{l} ({s:.0f}亿)" for l, s in zip(labels_right, sizes_right)],
          loc='upper center', bbox_to_anchor=(0.5, -0.12), fontsize=8.5, ncol=2, frameon=False)
ax.set_title(f'医疗ETF\n合计 {med_total:.0f}亿', fontsize=13, fontweight='bold', color=BLUE, pad=15)

plt.tight_layout(rect=[0, 0.08, 1, 0.94])
plt.savefig(os.path.join(CHART_DIR, 'section_01_scale_donut.png'), dpi=150, bbox_inches='tight',
            facecolor=BG, edgecolor='none')
plt.close()
print("Chart 1 done: scale donut")

# ============================================================
# Chart 2: Return Lollipop
# ============================================================
fig, ax = plt.subplots(figsize=(12, 6), facecolor=BG)
ax.set_facecolor(BG)

# Combine top performers from both cats
all_etfs = []
for e in pharma_etfs:
    if e.get('year_1_return') is not None:
        all_etfs.append({'label': f"{e['name']}({e['code'][:6]})", 'y1': e['year_1_return'], 'cat': '医药', 'scale': e['scale']})
for e in med_etfs:
    if e.get('year_1_return') is not None:
        all_etfs.append({'label': f"{e['name']}({e['code'][:6]})", 'y1': e['year_1_return'], 'cat': '医疗', 'scale': e['scale']})

all_etfs.sort(key=lambda x: x['y1'], reverse=True)
labels = [e['label'] for e in all_etfs]
values = [e['y1'] for e in all_etfs]
cats = [e['cat'] for e in all_etfs]

colors = [RED if c == '医药' else BLUE for c in cats]
y_pos = range(len(labels))

# Horizontal lollipop
ax.barh(y_pos, values, height=0.4, color=colors, alpha=0.85)
ax.scatter(values, y_pos, s=80, c=colors, zorder=5, edgecolors='white', linewidth=1)

# Value labels
for i, (v, c) in enumerate(zip(values, cats)):
    color = RED if c == '医药' else BLUE
    ax.text(v + (0.5 if v >= 0 else -3.5), i, f'{v:+.2f}%', va='center', fontsize=9,
            fontweight='bold', color=color)

ax.set_yticks(y_pos)
ax.set_yticklabels(labels, fontsize=10)
ax.set_xlabel('近1年收益率 (%)', fontsize=11, color=GRAY_DARK)
ax.set_title('近1年回报对比', fontsize=16, fontweight='bold', color='#212529')
ax.axvline(0, color=GRAY, linewidth=0.8, linestyle='--')
ax.set_xlim(min(values) - 6, max(values) + 4)
ax.invert_yaxis()

# Grid
ax.grid(axis='x', alpha=0.3, linestyle='--')
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
ax.spines['left'].set_visible(False)

plt.tight_layout()
plt.savefig(os.path.join(CHART_DIR, 'section_02_return_lollipop.png'), dpi=150, bbox_inches='tight',
            facecolor=BG, edgecolor='none')
plt.close()
print("Chart 2 done: return lollipop")

# ============================================================
# Chart 3: Risk HBar - 夏普比率, 年化波动, 最大回撤
# ============================================================
fig, axes = plt.subplots(1, 3, figsize=(16, 6), facecolor=BG)
fig.suptitle('风险指标对比', fontsize=16, fontweight='bold', color='#212529', y=1.0)

# Pick top 6+6
top12 = sorted(all_etfs, key=lambda x: x['scale'], reverse=True)[:12]
top12.sort(key=lambda x: x.get('scale', 0), reverse=True)

# Subplot 1: Sharpe Ratio
ax = axes[0]
ax.set_facecolor(BG)
isharpe = []
for e in pharma_etfs[:6] + med_etfs[:6]:
    sr = e.get('sharpe_ratio')
    if sr is not None:
         isharpe.append({'label': f"{e['name']}({e['code'][:6]})", 'v': sr, 'cat': '医药' if e in pharma_etfs else '医疗'})

isharpe.sort(key=lambda x: x['v'], reverse=True)
labels_s = [e['label'] for e in isharpe]
vals_s = [e['v'] for e in isharpe]
colors_s = [RED if e['cat'] == '医药' else BLUE for e in isharpe]
y_s = range(len(labels_s))

bars = ax.barh(y_s, vals_s, height=0.45, color=colors_s, alpha=0.85)
for i, (v, c) in enumerate(zip(vals_s, [e['cat'] for e in isharpe])):
    color = RED if c == '医药' else BLUE
    offset = max(0.03, abs(v)*0.15)
    ha = 'left' if v >= 0 else 'right'
    x_pos = v + offset if v >= 0 else v - offset
    ax.text(x_pos, i, f'{v:.2f}', va='center', ha=ha, fontsize=9, fontweight='bold', color=color)
ax.set_yticks(y_s)
ax.set_yticklabels(labels_s, fontsize=9)
ax.set_title('夏普比率', fontsize=13, fontweight='bold', color='#212529')
ax.axvline(0, color=GRAY, linewidth=0.8, linestyle='--')
ax.grid(axis='x', alpha=0.3, linestyle='--')
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
ax.spines['left'].set_visible(False)
ax.invert_yaxis()
ax.set_xlim(-0.25, max(vals_s) * 1.4)

# Subplot 2: Annual Vol
ax = axes[1]
ax.set_facecolor(BG)
ivol = []
for e in pharma_etfs[:6] + med_etfs[:6]:
    av = e.get('annual_vol')
    if av is not None:
        ivol.append({'label': f"{e['name']}({e['code'][:6]})", 'v': av, 'cat': '医药' if e in pharma_etfs else '医疗'})

ivol.sort(key=lambda x: x['v'])
labels_v = [e['label'] for e in ivol]
vals_v = [e['v'] for e in ivol]
colors_v = [RED if e['cat'] == '医药' else BLUE for e in ivol]
y_v = range(len(labels_v))

bars_v = ax.barh(y_v, vals_v, height=0.45, color=colors_v, alpha=0.85)
for i, (v, c) in enumerate(zip(vals_v, [e['cat'] for e in ivol])):
    color = RED if c == '医药' else BLUE
    ax.text(v + 0.3, i, f'{v:.1f}%', va='center', fontsize=9, fontweight='bold', color=color)
ax.set_yticks(y_v)
ax.set_yticklabels(labels_v, fontsize=9)
ax.set_title('年化波动率 (越低越好)', fontsize=13, fontweight='bold', color='#212529')
ax.grid(axis='x', alpha=0.3, linestyle='--')
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
ax.spines['left'].set_visible(False)
ax.invert_yaxis()
ax.set_xlim(0, max(vals_v) * 1.2)

# Subplot 3: Max Drawdown
ax = axes[2]
ax.set_facecolor(BG)
idd = []
for e in pharma_etfs[:6] + med_etfs[:6]:
    md = e.get('max_drawdown')
    if md is not None:
        idd.append({'label': f"{e['name']}({e['code'][:6]})", 'v': md, 'cat': '医药' if e in pharma_etfs else '医疗'})

idd.sort(key=lambda x: x['v'])
labels_d = [e['label'] for e in idd]
vals_d = [e['v'] for e in idd]
colors_d = [RED if e['cat'] == '医药' else BLUE for e in idd]
y_d = range(len(labels_d))

bars_d = ax.barh(y_d, vals_d, height=0.45, color=colors_d, alpha=0.85)
for i, (v, c) in enumerate(zip(vals_d, [e['cat'] for e in idd])):
    color = RED if c == '医药' else BLUE
    ax.text(v - 1.2, i, f'{v:.1f}%', va='center', ha='right', fontsize=9, fontweight='bold', color=color)
ax.set_yticks(y_d)
ax.set_yticklabels(labels_d, fontsize=9)
ax.set_title('最大回撤 (越低越好)', fontsize=13, fontweight='bold', color='#212529')
ax.grid(axis='x', alpha=0.3, linestyle='--')
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
ax.spines['left'].set_visible(False)
ax.invert_yaxis()
ax.set_xlim(min(vals_d) * 1.3, 0)

plt.tight_layout(rect=[0, 0, 1, 0.93])
plt.savefig(os.path.join(CHART_DIR, 'section_03_risk_hbar.png'), dpi=150, bbox_inches='tight',
            facecolor=BG, edgecolor='none')
plt.close()
print("Chart 3 done: risk hbar")

# ============================================================
# Chart 4: Holdings comparison - side by side top 5
# ============================================================
fig, axes = plt.subplots(1, 2, figsize=(12, 5), facecolor=BG)
fig.suptitle('持仓对比：核心差异', fontsize=16, fontweight='bold', color='#212529', y=0.98)

holdings_pharma = rep_pharma.get('top_holdings', [])[:5]
holdings_med = rep_med.get('top_holdings', [])[:5]

# Left: 512010
ax = axes[0]
names_p = [h['name'] for h in holdings_pharma]
weights_p = [float(h['weight'].replace('%','')) for h in holdings_pharma]
bars1 = ax.bar(range(len(names_p)), weights_p, color=[RED, RED_LIGHT, '#EC7063', '#F1948A', '#F5B7B1'],
               edgecolor='white', linewidth=0.5)
ax.set_xticks(range(len(names_p)))
ax.set_xticklabels(names_p, fontsize=10, rotation=20, ha='right')
ax.set_title(f'{rep_pharma["name"]} ({rep_pharma["code"]})\n沪深300医药卫生指数', fontsize=12, fontweight='bold', color=RED)
ax.set_ylabel('持仓权重 (%)', fontsize=10, color=GRAY_DARK)
for bar, w in zip(bars1, weights_p):
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5, f'{w:.1f}%',
            ha='center', va='bottom', fontsize=10, fontweight='bold', color=RED)
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
ax.set_ylim(0, max(weights_p) * 1.25)

# Right: 512170
ax = axes[1]
names_m = [h['name'] for h in holdings_med]
weights_m = [float(h['weight'].replace('%','')) for h in holdings_med]
bars2 = ax.bar(range(len(names_m)), weights_m, color=[BLUE, BLUE_LIGHT, '#5DADE2', '#85C1E9', '#AED6F1'],
               edgecolor='white', linewidth=0.5)
ax.set_xticks(range(len(names_m)))
ax.set_xticklabels(names_m, fontsize=10, rotation=20, ha='right')
ax.set_title(f'{rep_med["name"]} ({rep_med["code"]})\n中证医疗指数', fontsize=12, fontweight='bold', color=BLUE)
for bar, w in zip(bars2, weights_m):
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5, f'{w:.1f}%',
            ha='center', va='bottom', fontsize=10, fontweight='bold', color=BLUE)
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
ax.set_ylim(0, max(weights_m) * 1.25)

plt.tight_layout(rect=[0, 0, 1, 0.92])
plt.savefig(os.path.join(CHART_DIR, 'section_04_holdings_bar.png'), dpi=150, bbox_inches='tight',
            facecolor=BG, edgecolor='none')
plt.close()
print("Chart 4 done: holdings bar")

print("\nAll charts generated!")
