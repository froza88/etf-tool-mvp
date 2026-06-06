#!/usr/bin/env python3
"""半导体ETF vs 半导体设备ETF — 图表生成"""

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import numpy as np
import os

# Font setup
font_path = '/System/Library/Fonts/PingFang.ttc'
if not os.path.exists(font_path):
    font_path = '/System/Library/Fonts/STHeiti Light.ttc'
fm.fontManager.addfont(font_path)
prop = fm.FontProperties(fname=font_path)
plt.rcParams['font.family'] = prop.get_name()
plt.rcParams['axes.unicode_minus'] = False

OUT = '/Users/apangduo/WorkBuddy/2026-06-06-14-46-43/charts'
BG = '#F8F9FA'
DARK = '#2D3748'
GRAY = '#718096'
GRID = '#DEE2E6'
SIZE = (6.4, 6.4)

# Colors (ETF fixed order)
COLORS = ['#3B82F6', '#EC4899', '#F59E0B', '#8B5CF6', '#10B981']
# Extended for 6 items
COLORS6 = ['#3B82F6', '#EC4899', '#F59E0B', '#8B5CF6', '#10B981', '#EF4444']

def save(name):
    plt.tight_layout(pad=1.5)
    plt.savefig(f'{OUT}/{name}', dpi=100, bbox_inches='tight', facecolor=BG)
    plt.close()
    print(f'  ✓ {name}')

# ===== Chart 1: Returns Lollipop (YTD comparison, 5 equipment + 6 broad) =====
def chart_returns_lollipop():
    fig, ax = plt.subplots(figsize=SIZE, facecolor=BG)
    ax.set_facecolor(BG)
    
    # Data: equipment group (ytd)
    eq_names = ['159516\n国泰', '159558\n易方达', '560780\n广发', '562590\n华夏', '159327\n万家']
    eq_ytd = [47.40, 47.88, 47.89, 48.02, 47.99]
    
    br_names = ['512480\n国联安', '561980\n招商', '159813\n鹏华', '159665\n工银', '159325\n南方', '159582\n博时']
    br_ytd = [36.67, 40.08, 32.70, 34.07, 34.55, 40.33]
    
    all_names = eq_names + br_names
    all_vals = eq_ytd + br_ytd
    all_colors = COLORS[:5] + COLORS6
    
    y_pos = range(len(all_names))
    y_pos = list(y_pos)[::-1]  # top to bottom
    
    # Draw stems + dots
    for i, (n, v, c) in enumerate(zip(all_names[::-1], all_vals[::-1], all_colors)):
        y = i
        ax.plot([0, v], [y, y], color=c, linewidth=2.5, alpha=0.4, zorder=1)
        ax.scatter(v, y, s=180, color=c, zorder=3, edgecolors='white', linewidth=1.5)
        # value label
        offset = 1.2 if v > 40 else 1.2
        ax.text(v + offset, y, f'{v:.1f}%', va='center', fontsize=11, color=c, fontweight='bold')
    
    ax.set_yticks(range(len(all_names)))
    ax.set_yticklabels(all_names[::-1], fontsize=10, color=DARK)
    
    # Section labels
    ax.axhline(y=4.5, color=GRID, linewidth=1, linestyle='--', alpha=0.5)
    ax.text(51, 7.5, '半导体设备ETF', fontsize=13, color='#3B82F6', fontweight='bold', ha='center')
    ax.text(51, 2.5, '半导体ETF（全产业链）', fontsize=13, color='#EC4899', fontweight='bold', ha='center')
    
    ax.set_xlim(0, 56)
    ax.set_ylim(-0.8, len(all_names))
    ax.set_xlabel('YTD 回报 (%)', fontsize=12, color=GRAY)
    ax.set_title('2026年YTD回报：设备类全线碾压全链类', fontsize=16, color=DARK, fontweight='bold', pad=15)
    
    # Remove spines
    for spine in ['top', 'right', 'left']:
        ax.spines[spine].set_visible(False)
    ax.spines['bottom'].set_color(GRID)
    ax.tick_params(axis='y', length=0)
    
    save('lollipop_returns.png')

# ===== Chart 2: Scale Donut (AUM of two representatives vs others) =====
def chart_scale_donut():
    fig, axes = plt.subplots(1, 2, figsize=(12.8, 5.5), facecolor=BG)
    
    # Left: Equipment AUM
    ax = axes[0]
    eq_data = [193.22, 46.40, 33.61, 24.77, 9.52]
    eq_labels = ['159516\n国泰', '159558\n易方达', '560780\n广发', '562590\n华夏', '159327\n万家']
    eq_colors = COLORS[:5]
    
    wedges1, texts1, autotexts1 = ax.pie(
        eq_data, labels=eq_labels, colors=eq_colors, autopct='%1.0f%%',
        startangle=90, pctdistance=0.6, labeldistance=1.12,
        wedgeprops=dict(width=0.35, edgecolor='white', linewidth=2)
    )
    for t in autotexts1:
        t.set_fontsize(10); t.set_fontweight('bold'); t.set_color('white')
    for t in texts1:
        t.set_fontsize(9); t.set_color(DARK)
    ax.set_title('半导体设备ETF\nAUM分布（合计307.52亿）', fontsize=14, color=DARK, fontweight='bold', pad=15)
    
    # Right: Broad AUM
    ax = axes[1]
    br_data = [199.06, 57.00, 32.73, 3.83, 3.40, 3.35]
    br_labels = ['512480\n国联安', '159813\n鹏华', '561980\n招商', '159665\n工银', '159325\n南方', '159582\n博时']
    br_colors = COLORS6
    
    wedges2, texts2, autotexts2 = ax.pie(
        br_data, labels=br_labels, colors=br_colors, autopct='%1.0f%%',
        startangle=90, pctdistance=0.6, labeldistance=1.12,
        wedgeprops=dict(width=0.35, edgecolor='white', linewidth=2)
    )
    for t in autotexts2:
        t.set_fontsize(9); t.set_fontweight('bold'); t.set_color('white')
    for t in texts2:
        t.set_fontsize(9); t.set_color(DARK)
    ax.set_title('半导体ETF（全产业链）\nAUM分布（合计299.37亿）', fontsize=14, color=DARK, fontweight='bold', pad=15)
    
    fig.suptitle('规模分布：两个市场都高度集中', fontsize=17, color=DARK, fontweight='bold', y=1.02)
    save('donut_scale.png')

# ===== Chart 3: Turnover H-Bar =====
def chart_turnover_hbar():
    fig, ax = plt.subplots(figsize=SIZE, facecolor=BG)
    ax.set_facecolor(BG)
    
    all_names = [
        '159516 半导体设备ETF国泰',
        '512480 半导体ETF国联安',
        '159558 半导体设备ETF易方达',
        '159813 半导体ETF鹏华',
        '560780 半导体设备ETF广发',
        '562590 半导体设备ETF华夏',
        '561980 半导体设备ETF招商',
        '159325 半导体ETF南方',
        '159327 半导体设备ETF万家',
        '159582 半导体ETF博时',
        '159665 半导体龙头ETF工银',
    ]
    all_turnover = [20.54, 15.37, 6.67, 4.06, 3.98, 3.25, 3.06, 1.93, 1.40, 0.76, 0.54]
    
    # Equipment = blue tones, Broad = pink/other
    colors_bar = ['#3B82F6', '#EC4899', '#3B82F6', '#EC4899', '#3B82F6', '#3B82F6',
                  '#F59E0B', '#EC4899', '#3B82F6', '#EC4899', '#EC4899']
    
    # Highlight 561980 (the confusing one)
    colors_bar[6] = '#F59E0B'  # warning orange
    
    y_pos = list(range(len(all_names)))[::-1]
    vals_rev = all_turnover[::-1]
    names_rev = all_names[::-1]
    colors_rev = colors_bar[::-1]
    
    bars = ax.barh(y_pos, vals_rev, height=0.6, color=colors_rev, alpha=0.85, edgecolor='white', linewidth=1)
    
    for i, (v, c) in enumerate(zip(vals_rev, colors_rev)):
        ax.text(v + 0.5, i, f'{v:.1f}亿', va='center', fontsize=10, color=DARK, fontweight='bold')
    
    ax.set_yticks(y_pos)
    ax.set_yticklabels(names_rev, fontsize=9, color=DARK)
    
    ax.set_xlabel('日均成交额（亿元）', fontsize=12, color=GRAY)
    ax.set_title('流动性：159516和512480断层领先', fontsize=16, color=DARK, fontweight='bold', pad=15)
    ax.set_xlim(0, 26)
    
    # Legend
    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor='#3B82F6', alpha=0.85, label='半导体设备ETF（纯设备）'),
        Patch(facecolor='#EC4899', alpha=0.85, label='半导体ETF（全产业链）'),
        Patch(facecolor='#F59E0B', alpha=0.85, label='⚠️ 名义"设备"实非纯设备'),
    ]
    ax.legend(handles=legend_elements, loc='lower right', fontsize=9, framealpha=0.9)
    
    for spine in ['top', 'right', 'left']:
        ax.spines[spine].set_visible(False)
    ax.spines['bottom'].set_color(GRID)
    ax.tick_params(axis='y', length=0)
    
    save('hbar_turnover.png')

# ===== Chart 4: Index Coverage Comparison =====
def chart_index_coverage():
    """Show what each index covers - horizontal stacked bars"""
    fig, ax = plt.subplots(figsize=(6.4, 4.2), facecolor=BG)
    ax.set_facecolor(BG)
    
    indices = ['931743 中证半导体\n材料设备（纯设备）', '931865 中证半导体\n产业（偏设备）', 'h30184 中证全指\n半导体（全链）', '980017 国证半导体\n芯片（龙头）']
    
    # Approximate weights: [equipment+material, design+manufacturing, packaging+other]
    data = [
        [100, 0, 0],        # 931743: 100% equipment+material
        [63, 25, 12],       # 931865: ~63% equipment+material + 25% design + 12% other
        [20, 60, 20],       # h30184: ~15-20% equipment, 60% design+manufacture, 20% packaging
        [18, 72, 10],       # 980017: ~18% equipment, 72% design, 10% other
    ]
    
    colors_stack = ['#3B82F6', '#EC4899', '#10B981']
    labels_stack = ['设备+材料（上游）', '芯片设计+制造（中游）', '封测及其他（下游）']
    
    y_pos = range(len(indices))
    left = np.zeros(len(indices))
    
    for i, (vals, color, label) in enumerate(zip(zip(*data), colors_stack, labels_stack)):
        bars = ax.barh(y_pos, vals, left=left, height=0.5, color=color, alpha=0.85,
                       edgecolor='white', linewidth=1, label=label)
        # Add percentage text in middle of bar
        for j, (v, l) in enumerate(zip(vals, left)):
            if v > 10:
                ax.text(l + v/2, j, f'{v:.0f}%', ha='center', va='center', fontsize=10, color='white', fontweight='bold')
        left = left + np.array(vals)
    
    ax.set_yticks(y_pos)
    ax.set_yticklabels(indices, fontsize=10, color=DARK)
    ax.set_xlim(0, 105)
    ax.set_title('核心区别：指数覆盖范围完全不同', fontsize=15, color=DARK, fontweight='bold', pad=15)
    
    ax.legend(loc='lower right', fontsize=9, framealpha=0.9, ncol=1)
    
    for spine in ['top', 'right', 'left']:
        ax.spines[spine].set_visible(False)
    ax.spines['bottom'].set_color(GRID)
    ax.tick_params(axis='y', length=0)
    ax.set_xticks([])
    
    save('index_coverage.png')

# ===== Run all =====
if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    print("生成图表…")
    chart_returns_lollipop()
    chart_scale_donut()
    chart_turnover_hbar()
    chart_index_coverage()
    print("全部完成！")
