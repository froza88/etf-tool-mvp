#!/usr/bin/env python3
"""封面 v2 — 居中聚焦版"""
from PIL import Image, ImageDraw, ImageFont
W,H=640,460
im=Image.new('RGB',(W,H),'#F8FAFC');dr=ImageDraw.Draw(im)
try:
    fbig=ImageFont.truetype('/System/Library/Fonts/PingFang.ttc',60);ft26=ImageFont.truetype('/System/Library/Fonts/PingFang.ttc',26)
    f14=ImageFont.truetype('/System/Library/Fonts/PingFang.ttc',14);f11=ImageFont.truetype('/System/Library/Fonts/PingFang.ttc',11)
    fc=ImageFont.truetype('/System/Library/Fonts/PingFang.ttc',12);f40=ImageFont.truetype('/System/Library/Fonts/PingFang.ttc',40)
except: fbig=ft26=f14=f11=fc=f40=ImageFont.load_default()

# Subtle top gradient
for y in range(0,180):
    r=int(248+(3-248)*y/180);g=int(250+(130-250)*y/180);b=int(252+(239-252)*y/180)
    dr.line([(0,y),(W,y)],fill=(r,g,b))

# Large centered title
dr.text((W//2,70),'AI',font=fbig,fill='#3B82F6',anchor='mt')
bb=dr.textbbox((0,0),'主题ETF五强',font=ft26);dr.text((W//2-bb[2]//2+bb[0]//2,135),'主题ETF五强',font=ft26,fill='#1E293B')

# Decorative line
dr.line([(W//2-80,165),(W//2+80,165)],fill='#3B82F6',width=3)

# Subtitle - centered
st='每条AI投资路线，都有一个ETF代表'
bb=dr.textbbox((0,0),st,font=f14);dr.text((W//2-bb[2]//2+bb[0]//2,185),st,font=f14,fill='#94A3B8')

# 5 ETF cards in a row at the bottom
cards=[('159819','易方达\nAI综合','#3B82F6'),('515050','华夏\n算力基建','#EC4899'),('562500','华夏\n机器人','#F59E0B'),('159363','华宝\n创业板AI','#8B5CF6'),('588760','广发\n科创板AI','#10B981')]
cw=100;gap=(W-40-cw*5)//4;sx=40
for i,(cd,nm,co) in enumerate(cards):
    cx=sx+i*(cw+gap)
    dr.rounded_rectangle([cx,290,cx+cw,390],radius=12,fill='white',outline='#E2E8F0',width=1)
    # Color top bar
    dr.rectangle([cx+20,300,cx+cw-20,306],fill=co)
    bb=dr.textbbox((0,0),cd,font=fc);dr.text((cx+cw//2-bb[2]//2+bb[0]//2,318),cd,font=fc,fill='#334155')
    lines=nm.split('\n')
    for j,ln in enumerate(lines):
        bb=dr.textbbox((0,0),ln,font=f11);dr.text((cx+cw//2-bb[2]//2+bb[0]//2,340+j*18),ln,font=f11,fill='#94A3B8')

# Data source
ds='数据区间 2025.05—2026.06 · 来源 Wind · 天天基金 · 非凸科技'
dr.text((W//2,430),ds,font=f11,fill='#CBD5E1',anchor='mt')
dr.text((W-150,H-22),'不推荐 · 只给数据',font=f11,fill='#CBD5E1')
im.save('cover.png',quality=95);print('✅ cover.png (居中版)')
