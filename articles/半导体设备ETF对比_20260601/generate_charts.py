#!/usr/bin/env python3
"""半导体设备ETF对比文章 - 多类型图表"""
from PIL import Image, ImageDraw, ImageFont
import math, os

WIDTH, HEIGHT = 640, 640
BG = "#F8F9FA"
GRID_COLOR = "#DEE2E6"
TEXT_DARK = "#2D3748"
TEXT_GRAY = "#718096"

COLORS = {
    "159516": "#3B82F6",
    "159558": "#EC4899",
    "560780": "#F59E0B",
    "561980": "#8B5CF6",
    "588710": "#10B981",
}

try:
    font_title = ImageFont.truetype("/System/Library/Fonts/PingFang.ttc", 22)
    font_axis = ImageFont.truetype("/System/Library/Fonts/PingFang.ttc", 13)
    font_value = ImageFont.truetype("/System/Library/Fonts/PingFang.ttc", 14)
    font_code = ImageFont.truetype("/System/Library/Fonts/PingFang.ttc", 11)
    font_footnote = ImageFont.truetype("/System/Library/Fonts/PingFang.ttc", 10)
    font_label = ImageFont.truetype("/System/Library/Fonts/PingFang.ttc", 13)
except:
    font_title = font_axis = font_value = font_code = font_footnote = font_label = ImageFont.load_default()

base = os.path.dirname(__file__) or "."

# ========== CHART 1: RING DONUT - 规模占比 ==========
def make_donut(title, items, subtitle="", outname=""):
    img = Image.new('RGB', (WIDTH, HEIGHT), BG)
    draw = ImageDraw.Draw(img, 'RGBA')

    bbox = draw.textbbox((0,0), title, font=font_title)
    draw.text((WIDTH//2 - (bbox[2]-bbox[0])//2, 30), title, font=font_title, fill=TEXT_DARK)
    if subtitle:
        bb = draw.textbbox((0,0), subtitle, font=font_axis)
        draw.text((WIDTH//2 - (bb[2]-bb[0])//2, 58), subtitle, font=font_axis, fill=TEXT_GRAY)

    labels = [x[0] for x in items]
    values = [x[1] for x in items]
    colors_list = [x[2] for x in items]
    total = sum(values)

    # Donut center and size
    cx, cy = WIDTH//2, 340
    outer_r = 140
    inner_r = 75

    start_angle = -90
    for i, (label, val, color) in enumerate(zip(labels, values, colors_list)):
        sweep = val / total * 360
        # Draw arc segments using PIL's pieslice (filled arc)
        end_angle = start_angle + sweep
        # pieslice takes bounding box
        draw.pieslice(
            [cx-outer_r, cy-outer_r, cx+outer_r, cy+outer_r],
            start=int(start_angle), end=int(end_angle),
            fill=color, outline='white', width=2
        )
        start_angle = end_angle

    # Inner circle (donut hole)
    draw.ellipse([cx-inner_r, cy-inner_r, cx+inner_r, cy+inner_r], fill=BG)
    # Total in center
    total_text = f"{total:.0f}亿"
    bb = draw.textbbox((0,0), total_text, font=font_title)
    draw.text((cx-(bb[2]-bb[0])//2, cy-8-(bb[3]-bb[1])//2), total_text, font=font_title, fill=TEXT_DARK)
    bb2 = draw.textbbox((0,0), "总规模", font=font_axis)
    draw.text((cx-(bb2[2]-bb2[0])//2, cy+12), "总规模", font=font_axis, fill=TEXT_GRAY)

    # Legend below donut
    ly = HEIGHT - 110
    lx = 60
    for i, (label, val, color) in enumerate(zip(labels, values, colors_list)):
        col = i % 3
        row = i // 3
        x = lx + col * 190
        y = ly + row * 30
        draw.rectangle([x, y+4, x+14, y+18], fill=color, outline=None)
        pct = val / total * 100
        draw.text((x+20, y), f"{label}  {val:.1f}亿 ({pct:.1f}%)", font=font_code, fill=TEXT_DARK)

    note = "数据来源：天天基金 2026Q1"
    bb = draw.textbbox((0,0), note, font=font_footnote)
    draw.text((WIDTH//2 - (bb[2]-bb[0])//2, HEIGHT-25), note, font=font_footnote, fill=TEXT_GRAY)

    img.save(outname, quality=95)
    print(f"✅ {outname}")

make_donut("半导体设备ETF规模分布", [
    ("159516 国泰", 193.22, COLORS["159516"]),
    ("159558 易方达", 46.40, COLORS["159558"]),
    ("560780 广发", 33.61, COLORS["560780"]),
    ("561980 招商", 32.73, COLORS["561980"]),
    ("588710 华泰柏瑞", 14.95, COLORS["588710"]),
], subtitle="基金资产净值（亿元，2026Q1）", outname=os.path.join(base,"charts","section_规模占比.png"))

# ========== CHART 2: LOLLIPOP - 近1年回报 ==========
def make_lollipop(title, items, unit, subtitle="", outname=""):
    img = Image.new('RGB', (WIDTH, HEIGHT), BG)
    draw = ImageDraw.Draw(img)

    bb = draw.textbbox((0,0), title, font=font_title)
    draw.text((WIDTH//2 - (bb[2]-bb[0])//2, 30), title, font=font_title, fill=TEXT_DARK)
    if subtitle:
        bb = draw.textbbox((0,0), subtitle, font=font_axis)
        draw.text((WIDTH//2 - (bb[2]-bb[0])//2, 58), subtitle, font=font_axis, fill=TEXT_GRAY)

    labels = [x[0] for x in items]
    values = [x[1] for x in items]
    colors_list = [x[2] for x in items]
    min_v = min(values)
    max_v = max(values)

    tick_min = math.floor(min_v / 5) * 5
    tick_max = math.ceil(max_v / 5) * 5 + 5

    ch_l, ch_r, ch_t, ch_b = 100, WIDTH-35, 80, HEIGHT-130
    ch_w, ch_h = ch_r-ch_l, ch_b-ch_t
    tick_range = tick_max - tick_min

    for tk in range(tick_min, tick_max+5, 5):
        y = ch_b - ((tk - tick_min)/tick_range)*ch_h if tick_range>0 else ch_b
        draw.line([(ch_l, y), (ch_r, y)], fill=GRID_COLOR, width=1)
        lbl = f"{tk}{unit}"
        bb = draw.textbbox((0,0), lbl, font=font_axis)
        draw.text((ch_l - (bb[2]-bb[0]) - 8, y - (bb[3]-bb[1])//2), lbl, font=font_axis, fill=TEXT_GRAY)

    n = len(items)
    span_x = ch_w - 40
    gap = span_x / (n - 1) if n > 1 else 0

    for i, (label, val, color) in enumerate(zip(labels, values, colors_list)):
        x = ch_l + 20 + i * gap
        bh = ((val - tick_min)/tick_range)*ch_h if tick_range>0 else 0
        y_top = ch_b - bh

        # Lollipop stick
        draw.line([(x, ch_b-1), (x, y_top)], fill=color, width=3)
        # Lollipop head (circle)
        r = 10
        draw.ellipse([x-r, y_top-r, x+r, y_top+r], fill=color, outline='white', width=2)

        # Value on top of circle
        vt = f"{val:.1f}{unit}"
        bb = draw.textbbox((0,0), vt, font=font_value)
        draw.text((x-(bb[2]-bb[0])//2, y_top-r-(bb[3]-bb[1])-4), vt, font=font_value, fill=TEXT_DARK)

        # Label below
        bb2 = draw.textbbox((0,0), label, font=font_code)
        draw.text((x-(bb2[2]-bb2[0])//2, ch_b+10), label, font=font_code, fill=TEXT_DARK)

    note = "越高越好"
    bb = draw.textbbox((0,0), note, font=font_footnote)
    draw.text((WIDTH//2 - (bb[2]-bb[0])//2, HEIGHT-25), note, font=font_footnote, fill=TEXT_GRAY)

    img.save(outname, quality=95)
    print(f"✅ {outname}")

make_lollipop("半导体设备ETF近1年回报对比", [
    ("159516 国泰", 115.9, COLORS["159516"]),
    ("159558 易方达", 118.0, COLORS["159558"]),
    ("560780 广发", 117.8, COLORS["560780"]),
    ("561980 招商", 118.2, COLORS["561980"]),
    ("588710 华泰柏瑞", 138.6, COLORS["588710"]),
], "%", subtitle="2025年5月—2026年6月1日区间涨跌幅", outname=os.path.join(base,"charts","section_回报对比.png"))

# ========== CHART 3: HORIZONTAL BAR - 日成交额 ==========
def make_hbar(title, items, unit, subtitle="", outname=""):
    img = Image.new('RGB', (WIDTH, HEIGHT), BG)
    draw = ImageDraw.Draw(img)

    bb = draw.textbbox((0,0), title, font=font_title)
    draw.text((WIDTH//2 - (bb[2]-bb[0])//2, 30), title, font=font_title, fill=TEXT_DARK)
    if subtitle:
        bb = draw.textbbox((0,0), subtitle, font=font_axis)
        draw.text((WIDTH//2 - (bb[2]-bb[0])//2, 58), subtitle, font=font_axis, fill=TEXT_GRAY)

    labels = [x[0] for x in items]
    values = [x[1] for x in items]
    colors_list = [x[2] for x in items]
    max_v = max(values)

    ch_l, ch_r, ch_t, ch_b = 130, WIDTH-35, 90, HEIGHT-38
    n = len(items)
    bar_h = min(50, (ch_b - ch_t - (n-1)*18) / n)
    gap = 18

    tick_max = math.ceil(max_v / 5) * 5 + 5
    for tk in range(0, int(tick_max)+5, 5):
        x = ch_l + (tk/tick_max)*(ch_r-ch_l)
        draw.line([(x, ch_t), (x, ch_b)], fill=GRID_COLOR, width=1)
        lbl = f"{tk}{unit}"
        draw.text((x, ch_b+10), lbl, font=font_code, fill=TEXT_GRAY, anchor='mt')

    for i, (label, val, color) in enumerate(zip(labels, values, colors_list)):
        y = ch_t + i * (bar_h + gap)
        bw = (val/tick_max)*(ch_r-ch_l)

        # Bar
        draw.rounded_rectangle([ch_l, y, ch_l+bw, y+bar_h], radius=5, fill=color)

        # Value right of bar
        vt = f"{val:.2f}{unit}"
        bb = draw.textbbox((0,0), vt, font=font_value)
        draw.text((ch_l+bw+10, y+bar_h/2-(bb[3]-bb[1])//2), vt, font=font_value, fill=TEXT_DARK)

        # Label left of bar
        bb2 = draw.textbbox((0,0), label, font=font_label)
        draw.text((ch_l-10, y+bar_h/2-(bb2[3]-bb2[1])//2), label, font=font_label, fill=TEXT_DARK, anchor='ra')

    note = "越高越好（流动性更强）"
    bb = draw.textbbox((0,0), note, font=font_footnote)
    draw.text((WIDTH//2 - (bb[2]-bb[0])//2, HEIGHT-8), note, font=font_footnote, fill=TEXT_GRAY)

    img.save(outname, quality=95)
    print(f"✅ {outname}")

make_hbar("半导体设备ETF日成交额对比", [
    ("159516 国泰", 29.72, COLORS["159516"]),
    ("159558 易方达", 8.05, COLORS["159558"]),
    ("560780 广发", 5.47, COLORS["560780"]),
    ("561980 招商", 4.45, COLORS["561980"]),
    ("588710 华泰柏瑞", 4.64, COLORS["588710"]),
], "亿", subtitle="2026年6月1日单日成交额", outname=os.path.join(base,"charts","section_成交额对比.png"))

# ========== CHART 4: FEE BREAKDOWN - 费率结构分解 ==========
def make_fee_breakdown(title, subtitle="", outname=""):
    W, H = 640, 460
    img = Image.new('RGB', (W, H), BG)
    draw = ImageDraw.Draw(img)

    try:
        f_title = ImageFont.truetype("/System/Library/Fonts/PingFang.ttc", 22)
        f_big = ImageFont.truetype("/System/Library/Fonts/PingFang.ttc", 48)
        f_sub = ImageFont.truetype("/System/Library/Fonts/PingFang.ttc", 14)
        f_body = ImageFont.truetype("/System/Library/Fonts/PingFang.ttc", 15)
        f_note = ImageFont.truetype("/System/Library/Fonts/PingFang.ttc", 11)
    except:
        f_title = f_big = f_sub = f_body = f_note = ImageFont.load_default()

    bb = draw.textbbox((0,0), title, font=f_title)
    draw.text((W//2 - (bb[2]-bb[0])//2, 30), title, font=f_title, fill=TEXT_DARK)
    if subtitle:
        bb = draw.textbbox((0,0), subtitle, font=f_sub)
        draw.text((W//2 - (bb[2]-bb[0])//2, 58), subtitle, font=f_sub, fill=TEXT_GRAY)

    # Big total number
    total_text = "0.60%"
    bb = draw.textbbox((0,0), total_text, font=f_big)
    draw.text((W//2 - (bb[2]-bb[0])//2, 100), total_text, font=f_big, fill='#1E3A5F')

    total_label = "年总费率（管理费+托管费）"
    bb = draw.textbbox((0,0), total_label, font=f_sub)
    draw.text((W//2 - (bb[2]-bb[0])//2, 155), total_label, font=f_sub, fill=TEXT_GRAY)

    # Stacked bar showing breakdown
    bar_x, bar_y, bar_w, bar_h = 80, 200, W-160, 50
    mgmt_w = bar_w * 0.5 / 0.6
    custody_w = bar_w * 0.1 / 0.6

    # Management fee portion
    draw.rounded_rectangle([bar_x, bar_y, bar_x+mgmt_w, bar_y+bar_h], radius=8, fill='#3B82F6')
    # Custody fee portion (stacked)
    draw.rounded_rectangle([bar_x+mgmt_w, bar_y, bar_x+mgmt_w+custody_w, bar_y+bar_h], radius=8, fill='#93C5FD')

    # Labels inside/above bar
    bb_m = draw.textbbox((0,0), "管理费 0.50%", font=f_body)
    draw.text((bar_x+mgmt_w//2 - (bb_m[2]-bb_m[0])//2, bar_y+bar_h//2 - (bb_m[3]-bb_m[1])//2), "管理费 0.50%", font=f_body, fill='white')

    bb_c = draw.textbbox((0,0), "托管费 0.10%", font=f_body)
    draw.text((bar_x+mgmt_w+custody_w//2 - (bb_c[2]-bb_c[0])//2, bar_y+bar_h//2 - (bb_c[3]-bb_c[1])//2), "托管费 0.10%", font=f_body, fill='#1E3A5F')

    # ETF issuer list
    etfs = ['159516 国泰', '159558 易方达', '560780 广发', '561980 招商', '588710 华泰柏瑞']
    issuer_y = 290
    draw.text((W//2, issuer_y), "五只ETF费率完全一致", font=f_body, fill=TEXT_DARK, anchor='mt')
    for i, etf in enumerate(etfs):
        col = i % 3
        row = i // 3
        x = 100 + col * 170
        y = issuer_y + 35 + row * 28
        draw.ellipse([x, y+3, x+8, y+11], fill=COLORS[etf.split()[0]], outline=None)
        draw.text((x+16, y), etf, font=f_note, fill=TEXT_DARK)

    # Cost example
    example_y = 380
    draw.text((W//2, example_y), "持有10万元/年，总费用约600元", font=f_body, fill='#64748B', anchor='mt')
    draw.text((W//2, example_y+25), "管理费500元 + 托管费100元", font=f_note, fill='#94A3B8', anchor='mt')

    note = "费率在ETF选择中不构成差异化因素"
    bb = draw.textbbox((0,0), note, font=f_note)
    draw.text((W//2 - (bb[2]-bb[0])//2, H-22), note, font=f_note, fill=TEXT_GRAY)

    img.save(outname, quality=95)
    print(f"✅ {outname}")

make_fee_breakdown("半导体设备ETF费率结构", subtitle="管理费+托管费分解（五只一致）", outname=os.path.join(base,"charts","section_费率结构.png"))

print("\n✅ 4张图表生成完成")
