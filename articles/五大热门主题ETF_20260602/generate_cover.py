#!/usr/bin/env python3
"""封面 v3 — 红金系 + 电网几何 + 黄金质感"""
from PIL import Image, ImageDraw, ImageFont
import math
W,H=640,460

# Warm off-white base
im=Image.new('RGB',(W,H),'#FBF9F4')
dr=ImageDraw.Draw(im,'RGBA')

try:
    f96=ImageFont.truetype('/System/Library/Fonts/PingFang.ttc',96)
    f34=ImageFont.truetype('/System/Library/Fonts/PingFang.ttc',34)
    f16=ImageFont.truetype('/System/Library/Fonts/PingFang.ttc',16)
    f13=ImageFont.truetype('/System/Library/Fonts/PingFang.ttc',13)
    f11=ImageFont.truetype('/System/Library/Fonts/PingFang.ttc',11)
    f10=ImageFont.truetype('/System/Library/Fonts/PingFang.ttc',10)
    f9=ImageFont.truetype('/System/Library/Fonts/PingFang.ttc',9)
    f15=ImageFont.truetype('/System/Library/Fonts/PingFang.ttc',15)
except: f96=f34=f16=f13=f11=f10=f9=f15=ImageFont.load_default()

# ----- POWER GRID PATTERN (subtle background) -----
# Diagonal transmission lines
for i in range(-20,40):
    x=i*40
    dr.line([(x,0),(x+200,H)],fill=(0,0,0,4),width=1)
# Horizontal lines with towers
for y in range(80,H-80,70):
    dr.line([(0,y),(W,y)],fill=(0,0,0,5),width=1)
    # tiny tower marks
    for x in range(60,W-60,120):
        dr.ellipse([x-2,y-2,x+2,y+2],fill=(0,0,0,8))
        dr.line([(x,y),(x,y-12)],fill=(0,0,0,5),width=1)
        dr.line([(x-8,y-12),(x+8,y-12)],fill=(0,0,0,5),width=1)

# ----- GOLD ELEMENT (right side circular accent) -----
cx,cy=W-100,140
for r in range(70,25,-3):
    alpha=max(3,15-r//8)
    a=int(alpha)
    shade=int(180+r*0.5)
    dr.ellipse([cx-r,cy-r,cx+r,cy+r],fill=(shade,int(shade*0.82),int(shade*0.55),a),outline=None)
# Gold center dot
dr.ellipse([cx-8,cy-8,cx+8,cy+8],fill=(212,175,55,180))

# ----- TOP BAR: Thin red accent -----
dr.rectangle([0,0,W,4],fill='#C41E3A')

# ----- LEFT CONTENT -----
lx=48
# Small label
dr.text((lx,30),'2026  HOT  THEMES',font=f9,fill='#C41E3A')

# Main title
dr.text((lx,55),'五大热门',font=f34,fill='#1A1A1A')
dr.text((lx,95),'主题ETF',font=f34,fill='#1A1A1A')

# Red accent underline
dr.line([(lx,135),(lx+64,135)],fill='#C41E3A',width=3)

# Subtitle line
dr.text((lx,158),'电网基建  ·  创新药出海  ·  黄金避险  ·  油气能源  ·  自由现金流',font=f11,fill='#8B7355')

# ----- DIVIDER -----
dr.line([(lx,190),(W-60,190)],fill=(0,0,0,10),width=1)

# ----- BOTTOM: 5 themes in compact row -----
themes=[
    ('电网设备','159326\n92.3%'),
    ('港股创新药','513120\n20.7%'),
    ('黄金','518880\n1,138亿'),
    ('标普油气','513350\n48.5%'),
    ('自由现金流','159201\n0.20%'),
]
tx=lx
for i,(nm,info) in enumerate(themes):
    if i>0:
        dr.line([(tx,215),(tx,278)],fill=(0,0,0,15),width=1)
        tx+=22
    # Small colored dot
    colors=[(196,30,58),(139,115,85),(212,175,55),(139,115,85),(196,30,58)]
    dr.ellipse([tx,216,tx+6,222],fill=colors[i])
    # Theme name
    dr.text((tx+14,212),nm,font=f15,fill='#2D2D2D')
    # Code + stat below
    for j,ln in enumerate(info.split('\n')):
        c='#8B7355' if j==0 else '#C41E3A'
        dr.text((tx+14,232+j*16),ln,font=f11 if j==0 else f10,fill=c)
    tx+=90

# ----- BOTTOM META -----
dr.text((lx,H-42),'数据区间 2025.05—2026.06  ·  来源 Wind · 天天基金 · 非凸科技',font=f9,fill='#C4B5A5')
dr.text((W-50,H-22),'不推荐 · 只给数据',font=f9,fill='#C4B5A5',anchor='ra')

# ----- WATERMARK "5" bottom-right -----
dr.text((W-15,H-10),'5',font=f96,fill=(0,0,0,5),anchor='rb')

im.save('cover.png',quality=95);print('✅ cover.png (红金电网v3)')
