#!/usr/bin/env python3
"""封面 - 暖白+跑道时间线"""
from PIL import Image, ImageDraw, ImageFont
W, H = 640, 460

img = Image.new('RGB', (W, H), '#FEFCF8')
draw = ImageDraw.Draw(img)

try:
    f_title = ImageFont.truetype('/System/Library/Fonts/PingFang.ttc', 28)
    f_month = ImageFont.truetype('/System/Library/Fonts/PingFang.ttc', 68)
    f_sub = ImageFont.truetype('/System/Library/Fonts/PingFang.ttc', 13)
    f_node = ImageFont.truetype('/System/Library/Fonts/PingFang.ttc', 11)
    f_small = ImageFont.truetype('/System/Library/Fonts/PingFang.ttc', 10)
except:
    f_title = f_month = f_sub = f_node = f_small = ImageFont.load_default()

# Top section - title area
draw.text((40, 50), '5月', font=f_month, fill='#3B82F6')
t1 = 'ETF市场热点复盘'
bb = draw.textbbox((0,0), t1, font=f_title)
draw.text((148, 72), t1, font=f_title, fill='#1E3A5F')
draw.rectangle([148, 110, 380, 112], fill='#3B82F6')

st = 'AI狂飙  机器人接力  半导体霸屏  黄金洗盘'
bb = draw.textbbox((0,0), st, font=f_sub)
draw.text((148, 124), st, font=f_sub, fill='#64748B')

# Data source line
ds = '数据区间 2026.05.01—05.30  ·  来源 Wind · 东方财富 · 雪球 · 格隆汇'
bb = draw.textbbox((0,0), ds, font=f_small)
draw.text((40, 148), ds, font=f_small, fill='#9CA3AF')

# Separator
draw.line([(40, 168), (W-40, 168)], fill='#E2E8F0', width=1)

# ======== RACETRACK TIMELINE ========
tl_y = 195
node_w = 90
gap = 8
total_w = 6 * node_w + 5 * gap
start_x = (W - total_w) // 2

# Track background
draw.rounded_rectangle([start_x-8, tl_y-12, start_x+total_w+8, tl_y+105], radius=14, fill='#F0F4F8', outline='#E2E8F0', width=1)

# Main track line
line_y = tl_y + 18
draw.line([(start_x, line_y), (start_x+total_w, line_y)], fill='#CBD5E1', width=3)
# Track border (racetrack effect)
draw.rectangle([start_x-4, line_y-8, start_x+total_w+4, line_y+8], outline='#3B82F6', width=1)
draw.rectangle([start_x-4, line_y-8, start_x+total_w+4, line_y+8], fill='#3B82F6')

# Also restore the line over the fill
draw.line([(start_x, line_y), (start_x+total_w, line_y)], fill='#CBD5E1', width=3)

nodes = [
    ('5.6', '节后开门红', '#3B82F6'),
    ('5.12', '芯片出口+100%', '#EC4899'),
    ('5.15', '机器人爆发', '#F59E0B'),
    ('5.20', '格隆汇十大ETF', '#10B981'),
    ('5.25', 'DeepSeek降价75%', '#8B5CF6'),
    ('5.27', '创业板利好', '#6366F1'),
]

for i, (date, event, color) in enumerate(nodes):
    cx = start_x + i * (node_w + gap) + node_w//2
    
    # Node circle
    r = 8
    draw.ellipse([cx-r, line_y-r, cx+r, line_y+r], fill=color, outline='white', width=3)
    
    # Date above
    bb = draw.textbbox((0,0), date, font=f_node)
    draw.text((cx-(bb[2]-bb[0])//2, tl_y-8), date, font=f_node, fill='#1E293B')
    
    # Event below
    bb = draw.textbbox((0,0), event, font=f_node)
    draw.text((cx-(bb[2]-bb[0])//2, line_y+18), event, font=f_node, fill='#334155')

# Bottom note
draw.text((W-150, H-22), '不推荐 · 只给数据', font=f_small, fill='#CBD5E1')

img.save('cover.png', quality=95)
print('✅ cover.png (warm + racetrack)')
