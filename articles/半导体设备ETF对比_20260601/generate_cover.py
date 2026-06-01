#!/usr/bin/env python3
"""封面 - 半导体设备ETF对比 - 浅色版"""
from PIL import Image, ImageDraw, ImageFont
W, H = 640, 460

img = Image.new('RGB', (W, H), '#FEFCF8')
draw = ImageDraw.Draw(img)

try:
    f_title = ImageFont.truetype('/System/Library/Fonts/PingFang.ttc', 26)
    f_big = ImageFont.truetype('/System/Library/Fonts/PingFang.ttc', 52)
    f_num = ImageFont.truetype('/System/Library/Fonts/PingFang.ttc', 40)
    f_sub = ImageFont.truetype('/System/Library/Fonts/PingFang.ttc', 14)
    f_small = ImageFont.truetype('/System/Library/Fonts/PingFang.ttc', 11)
    f_code = ImageFont.truetype('/System/Library/Fonts/PingFang.ttc', 12)
    f_desc = ImageFont.truetype('/System/Library/Fonts/PingFang.ttc', 11)
except:
    f_title = f_big = f_num = f_sub = f_small = f_code = f_desc = ImageFont.load_default()

# Left blue accent bar
draw.rectangle([40, 55, 46, 330], fill='#3B82F6')

# Title
draw.text((70, 55), '半导体设备ETF', font=f_big, fill='#1E3A5F')
t2 = '五强全面对比'
bb = draw.textbbox((0,0), t2, font=f_title)
draw.text((70, 120), t2, font=f_title, fill='#64748B')

# Divider
draw.line([(70, 155), (200, 155)], fill='#3B82F6', width=2)

# Subtitle
st = '国泰 193亿王者  ·  易方达追兵  ·  华泰柏瑞科创独苗'
bb = draw.textbbox((0,0), st, font=f_sub)
draw.text((70, 172), st, font=f_sub, fill='#64748B')

# ETF code pills
codes = ['159516', '159558', '560780', '561980', '588710']
code_colors = ['#3B82F6', '#EC4899', '#F59E0B', '#8B5CF6', '#10B981']
cx = 70
for code, color in zip(codes, code_colors):
    bb = draw.textbbox((0,0), code, font=f_code)
    pw = bb[2]-bb[0]+16
    draw.rounded_rectangle([cx, 198, cx+pw, 222], radius=4, fill=color)
    draw.text((cx+8, 200), code, font=f_code, fill='#FFFFFF')
    cx += pw + 12

# Separator
draw.line([(40, 258), (W-40, 258)], fill='#E2E8F0', width=1)

# Bottom highlights - spaced apart
highlight_y = 280
items = [
    ('193亿', '国泰规模断层领先', '#3B82F6'),
    ('138.6%', '华泰柏瑞回报最高', '#10B981'),
    ('0.60%', '五只费率一致', '#64748B'),
]
for i, (num, desc, color) in enumerate(items):
    hx = 55 + i * 185
    # Number
    bb = draw.textbbox((0,0), num, font=f_num)
    draw.text((hx, highlight_y), num, font=f_num, fill=color)
    # Description in smaller font below
    bb2 = draw.textbbox((0,0), desc, font=f_desc)
    draw.text((hx, highlight_y + 48), desc, font=f_desc, fill='#94A3B8')

# Data source
ds = '数据区间 2025.05—2026.06  ·  来源 Wind · 天天基金 · 非凸科技'
draw.text((40, 380), ds, font=f_small, fill='#CBD5E1')

# Note
draw.text((W-150, 430), '不推荐 · 只给数据', font=f_small, fill='#CBD5E1')

img.save('cover.png', quality=95)
print('✅ cover.png (浅色版)')
