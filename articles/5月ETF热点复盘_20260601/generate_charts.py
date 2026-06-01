#!/usr/bin/env python3
"""生成5月ETF热点复盘文章的图表"""
from PIL import Image, ImageDraw, ImageFont
import math, os

WIDTH, HEIGHT = 640, 640
BG = "#F8F9FA"
BAR_BG = "#E9ECEF"
GRID_COLOR = "#DEE2E6"
TEXT_DARK = "#2D3748"
TEXT_GRAY = "#718096"

COLORS = {
    "半导体": "#3B82F6", "AI算力": "#EC4899", "机器人": "#F59E0B",
    "通信": "#8B5CF6", "创新药": "#10B981", "黄金": "#EF4444",
    "科创": "#6366F1", "科创综指": "#3B82F6", "信创": "#EC4899",
    "机器人ETF": "#F59E0B", "红利": "#84CC16",
}

try:
    font_title = ImageFont.truetype("/System/Library/Fonts/PingFang.ttc", 22)
    font_axis = ImageFont.truetype("/System/Library/Fonts/PingFang.ttc", 13)
    font_value = ImageFont.truetype("/System/Library/Fonts/PingFang.ttc", 14)
    font_label = ImageFont.truetype("/System/Library/Fonts/PingFang.ttc", 13)
    font_code = ImageFont.truetype("/System/Library/Fonts/PingFang.ttc", 11)
    font_footnote = ImageFont.truetype("/System/Library/Fonts/PingFang.ttc", 10)
    font_body = ImageFont.truetype("/System/Library/Fonts/PingFang.ttc", 12)
except:
    font_title = font_axis = font_value = font_label = font_code = font_footnote = font_body = ImageFont.load_default()

def make_chart(title, items, unit, subtitle="", higher_better=True, decimals=2, outname=""):
    img = Image.new('RGB', (WIDTH, HEIGHT), BG)
    draw = ImageDraw.Draw(img)
    
    bbox = draw.textbbox((0,0), title, font=font_title)
    draw.text((WIDTH//2 - (bbox[2]-bbox[0])//2, 30), title, font=font_title, fill=TEXT_DARK)
    if subtitle:
        bbox = draw.textbbox((0,0), subtitle, font=font_axis)
        draw.text((WIDTH//2 - (bbox[2]-bbox[0])//2, 58), subtitle, font=font_axis, fill=TEXT_GRAY)
    
    labels = [x[0] for x in items]
    values = [x[1] for x in items]
    colors_list = [x[2] if len(x) > 2 else "#6366F1" for x in items]
    min_v = min(values)
    max_v = max(v for v in values if v > 0) if values else 1
    
    # Smart axis: use actual data range, pad to nice numbers
    tick_min_est = min_v - abs(min_v)*0.1 if min_v < 0 else 0
    tick_max_est = max(20, max_v * 1.1)  # 纵轴至少到20
    
    span = tick_max_est - tick_min_est
    raw_step = span / 5
    mag = 10 ** math.floor(math.log10(raw_step)) if raw_step > 0 else 1
    norm = raw_step / mag
    if norm <= 1.5: step = mag
    elif norm <= 3: step = 2 * mag
    elif norm <= 7: step = 5 * mag
    else: step = 10 * mag
    if step == 0: step = mag
    
    # Generate ticks from tick_min to tick_max
    ticks = []
    t = math.floor(tick_min_est / step) * step
    while t <= tick_max_est + step/2:
        ticks.append(t)
        t += step
    
    ch_l, ch_r, ch_t, ch_b = 100, WIDTH-35, 85, HEIGHT-125
    ch_w, ch_h = ch_r-ch_l, ch_b-ch_t
    tick_range_min = min(ticks) if ticks else 0
    tick_range_max = max(ticks) if ticks else max_v
    tick_range = tick_range_max - tick_range_min
    
    for tk in ticks:
        y = ch_b - ((tk - tick_range_min)/tick_range)*ch_h if tick_range>0 else ch_b
        draw.line([(ch_l, y), (ch_r, y)], fill=GRID_COLOR, width=1)
        lbl = f"{tk:.{decimals}f}{unit}"
        bb = draw.textbbox((0,0), lbl, font=font_axis)
        draw.text((ch_l - (bb[2]-bb[0]) - 8, y - (bb[3]-bb[1])//2), lbl, font=font_axis, fill=TEXT_GRAY)
    
    draw.line([(ch_l, ch_b), (ch_r, ch_b)], fill=TEXT_DARK, width=2)
    
    n = len(items)
    bar_w = min(70, (ch_w - 16*(n+1))/n)
    gap = 16
    start_x = ch_l + (ch_w - (n*bar_w + (n-1)*gap))/2
    
    for i, (label, val, color) in enumerate(zip(labels, values, colors_list)):
        x = start_x + i*(bar_w+gap)
        bh = ((val - tick_range_min)/tick_range)*ch_h if tick_range>0 else 0
        bh = max(bh, 2)  # Minimum bar height
        y = ch_b - bh
        draw.rectangle([x, y, x+bar_w, ch_b], fill=color)
        
        vt = f"{val:.{decimals}f}{unit}"
        bb = draw.textbbox((0,0), vt, font=font_value)
        draw.text((x+bar_w/2-(bb[2]-bb[0])/2, y-(bb[3]-bb[1])-5), vt, font=font_value, fill=TEXT_DARK)
        
        # 长标签自动换行
        bb2 = draw.textbbox((0,0), label, font=font_code)
        label_w = bb2[2] - bb2[0]
        if label_w > bar_w + 10:
            parts = label.split(' ', 1)
            if len(parts) == 2:
                bb3 = draw.textbbox((0,0), parts[0], font=font_code)
                bb4 = draw.textbbox((0,0), parts[1], font=font_code)
                draw.text((x+bar_w/2-(bb3[2]-bb3[0])/2, ch_b+8), parts[0], font=font_code, fill=TEXT_DARK)
                draw.text((x+bar_w/2-(bb4[2]-bb4[0])/2, ch_b+25), parts[1], font=font_code, fill=TEXT_GRAY)
            else:
                draw.text((x+bar_w/2-label_w/2, ch_b+12), label, font=font_code, fill=TEXT_DARK)
        else:
            draw.text((x+bar_w/2-label_w/2, ch_b+12), label, font=font_code, fill=TEXT_DARK)
    
    note = "越高越好" if higher_better else "越低越好"
    bb = draw.textbbox((0,0), note, font=font_footnote)
    draw.text((WIDTH//2 - (bb[2]-bb[0])//2, HEIGHT-25), note, font=font_footnote, fill=TEXT_GRAY)
    
    img.save(outname, quality=95)
    print(f"✅ {outname}")

base = os.path.dirname(__file__) or "."

# Chart 1: 5月ETF热点板块涨幅
make_chart("5月ETF热点板块涨幅榜", [
    ("半导体设备", 15.2, COLORS["半导体"]),
    ("通信/AI算力", 13.8, COLORS["通信"]),
    ("机器人", 10.5, COLORS["机器人"]),
    ("科创综指", 8.3, COLORS["科创"]),
    ("创新药", 6.7, COLORS["创新药"]),
    ("黄金", -3.2, COLORS["黄金"]),
], "%", subtitle="2026年5月1日—30日区间涨幅（部分核心品种）", decimals=1, outname=os.path.join(base,"charts","section_5月板块涨幅.png"))

# Chart 2: AI算力产业链ETF资金流入
make_chart("5月AI产业链ETF资金净流入TOP5", [
    ("通信ETF 515050", 20.91, COLORS["通信"]),
    ("科创综指ETF 589880", 5.24, COLORS["科创综指"]),
    ("信创ETF 562030", 3.15, COLORS["信创"]),
    ("科创半导体ETF 589020", 0.85, COLORS["半导体"]),
    ("机器人ETF 562500", 0.72, COLORS["机器人"]),
], "亿", subtitle="5月资金净流入（估算值，来源：Wind/各基金公告）", decimals=2, outname=os.path.join(base,"charts","section_资金流入.png"))

# Chart 3: 跑道型时间线
def make_racetrack(title, nodes, outname):
    W, H = 640, 240
    img = Image.new('RGB', (W, H), '#FEFCF8')
    draw = ImageDraw.Draw(img)
    
    try:
        f_title = ImageFont.truetype("/System/Library/Fonts/PingFang.ttc", 16)
        f_date = ImageFont.truetype("/System/Library/Fonts/PingFang.ttc", 13)
        f_event = ImageFont.truetype("/System/Library/Fonts/PingFang.ttc", 12)
        f_detail = ImageFont.truetype("/System/Library/Fonts/PingFang.ttc", 9)
    except:
        f_title = f_date = f_event = f_detail = ImageFont.load_default()
    
    bb = draw.textbbox((0,0), title, font=f_title)
    draw.text((W//2 - (bb[2]-bb[0])//2, 18), title, font=f_title, fill='#1E3A5F')
    
    n = len(nodes)
    node_w = 90
    gap = 6
    total_w = n * node_w + (n-1) * gap
    start_x = (W - total_w) // 2
    line_y = 78
    
    # Track
    draw.rounded_rectangle([start_x-10, line_y-18, start_x+total_w+10, line_y+110], radius=12, fill='#F8FAFC', outline='#E2E8F0', width=1)
    
    # Racetrack line
    draw.line([(start_x, line_y), (start_x+total_w, line_y)], fill='#CBD5E1', width=3)
    draw.rectangle([start_x-3, line_y-6, start_x+total_w+3, line_y+6], outline='#3B82F6', width=1, fill='#3B82F6')
    draw.line([(start_x, line_y), (start_x+total_w, line_y)], fill='#CBD5E1', width=3)
    
    for i, (date, event, detail, color) in enumerate(nodes):
        cx = start_x + i*(node_w+gap) + node_w//2
        
        # Circle
        r = 6
        draw.ellipse([cx-r, line_y-r, cx+r, line_y+r], fill=color, outline='white', width=2)
        
        # Date above
        bb2 = draw.textbbox((0,0), date, font=f_date)
        draw.text((cx-(bb2[2]-bb2[0])//2, line_y-28), date, font=f_date, fill='#1E293B')
        
        # Event below
        bb3 = draw.textbbox((0,0), event, font=f_event)
        draw.text((cx-(bb3[2]-bb3[0])//2, line_y+12), event, font=f_event, fill='#334155')
        
        # Detail subtitle
        bb4 = draw.textbbox((0,0), detail, font=f_detail)
        draw.text((cx-(bb4[2]-bb4[0])//2, line_y+34), detail, font=f_detail, fill='#94A3B8')
    
    # Note
    nt = '← 月初                          月末 →'
    bb5 = draw.textbbox((0,0), nt, font=f_detail)
    draw.text((W//2 - (bb5[2]-bb5[0])//2, H-20), nt, font=f_detail, fill='#CBD5E1')
    
    img.save(outname, quality=95)
    print(f"✅ {outname}")

make_racetrack("5月行情节奏", [
    ("5.6", "节后开门红", "AI延续强势", "#3B82F6"),
    ("5.12", "芯片出口+100%", "半导体霸屏", "#EC4899"),
    ("5.15", "机器人爆发", "政策密集催化", "#F59E0B"),
    ("5.20", "十大ETF揭晓", "格隆汇发布", "#10B981"),
    ("5.25", "DeepSeek降价75%", "API价格地震", "#8B5CF6"),
    ("5.27", "创业板利好", "冲击4连涨", "#6366F1"),
], os.path.join(base,"charts","section_行情节奏跑道.png"))

print("\n✅ 3张图表生成完成")
