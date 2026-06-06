#!/usr/bin/env python3
"""Cover v9: Real photos replacing hand-drawn icons, magazine editorial style"""
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
import os

W, H = 1200, 630
img = Image.new('RGB', (W, H), '#FEFCF8')
draw = ImageDraw.Draw(img)

f_title = ImageFont.truetype('/System/Library/Fonts/PingFang.ttc', 40)
f_big = ImageFont.truetype('/System/Library/Fonts/PingFang.ttc', 26)
f_sm = ImageFont.truetype('/System/Library/Fonts/PingFang.ttc', 14)

# ===== Load real photos =====
photo_maotai = Image.open('img_consumer_maotai.jpeg').convert('RGB')
photo_milk = Image.open('img_consumer_milk.jpeg').convert('RGB')
photo_robot = Image.open('img_consumer_electronics_robot.jpeg').convert('RGB')
photo_gears = Image.open('img_consumer_electronics_gears.jpeg').convert('RGB')

# ===== LEFT HALF: Consumer (warm) =====
# Background
draw.rectangle([0, 0, 599, H], fill='#FFF5F3')

# Paste 茅台 photo (top-left, large)
mw, mh = 300, 225
maotai_resized = photo_maotai.resize((mw, mh), Image.LANCZOS)
# Darken slightly for background feel
img.paste(maotai_resized, (30, 80))

# Paste 牛奶 photo (bottom-left, offset overlap)
mw2, mh2 = 280, 200
milk_resized = photo_milk.resize((mw2, mh2), Image.LANCZOS)
img.paste(milk_resized, (130, 320))

# Subtle overlay shapes for depth
for bx, by, bw, bh in [
    (20, 70, 320, 240),
    (120, 310, 300, 215),
]:
    draw.rectangle([bx, by, bx+bw, by+bh], outline='#E74C3C10', width=2)

# ===== RIGHT HALF: Consumer Electronics (cool) =====
draw.rectangle([601, 0, W, H], fill='#F5F9FF')

# Paste 机器人 photo (top-right)
rw, rh = 280, 200
robot_resized = photo_robot.resize((rw, rh), Image.LANCZOS)
img.paste(robot_resized, (850, 75))

# Paste 齿轮 photo (bottom-right, offset)
gw, gh = 310, 230
gears_resized = photo_gears.resize((gw, gh), Image.LANCZOS)
img.paste(gears_resized, (730, 310))

# Subtle overlay frames
for bx, by, bw, bh in [
    (840, 65, 300, 215),
    (720, 300, 330, 245),
]:
    draw.rectangle([bx, by, bx+bw, by+bh], outline='#2980B910', width=2)

# ===== Center divider =====
draw.line([600, 0, 600, H], fill='#1A202C', width=2)
draw.ellipse([594, 311, 606, 323], fill='#1A202C')

# ===== Title bar =====
title = '消费ETF vs 消费电子ETF'
tw = draw.textlength(title, font=f_title)
draw.rectangle([W//2-tw//2-28, 10, W//2+tw//2+28, 62], fill='#FFFFFFEE')
draw.text((W//2, 14), title, fill='#1A202C', font=f_title, anchor='ma')

# ===== Category labels (bottom) =====
draw.text((280, H-50), '消  费', fill='#922B21', font=f_big, anchor='ma')
draw.text((280, H-18), '白酒 · 乳业 · 食品 ｜ 持仓实拍', fill='#A93226', font=f_sm, anchor='ma')
draw.text((920, H-50), '消费电子', fill='#1A5276', font=f_big, anchor='ma')
draw.text((920, H-18), 'AI · 精密制造 · 半导体 ｜ 行业实拍', fill='#2471A3', font=f_sm, anchor='ma')
draw.text((600, H-34), '易 混 淆  E T F  系 列', fill='#94A3B8', font=f_sm, anchor='ma')

# Save
img.save('cover.png', 'PNG')
img.save('cover.jpg', 'JPEG', quality=95)
print(f'Cover v9 (real photos): PNG={os.path.getsize("cover.png")}B JPG={os.path.getsize("cover.jpg")}B')
