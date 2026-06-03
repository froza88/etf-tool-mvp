#!/usr/bin/env python3
"""黄金vs黄金股 — 图表生成 (4张, 4种类型)"""
import os, math
from PIL import Image, ImageDraw, ImageFont

W,H=640,500; BG='#FAFAF9'
try:
    f36=ImageFont.truetype('/System/Library/Fonts/PingFang.ttc',36)
    f28=ImageFont.truetype('/System/Library/Fonts/PingFang.ttc',28)
    f22=ImageFont.truetype('/System/Library/Fonts/PingFang.ttc',22)
    f18=ImageFont.truetype('/System/Library/Fonts/PingFang.ttc',18)
    f15=ImageFont.truetype('/System/Library/Fonts/PingFang.ttc',15)
    f14=ImageFont.truetype('/System/Library/Fonts/PingFang.ttc',14)
    f13=ImageFont.truetype('/System/Library/Fonts/PingFang.ttc',13)
    f12=ImageFont.truetype('/System/Library/Fonts/PingFang.ttc',12)
    f11=ImageFont.truetype('/System/Library/Fonts/PingFang.ttc',11)
except: f36=f28=f22=f18=f15=f14=f13=f12=f11=ImageFont.load_default()

out_dir = 'charts'
os.makedirs(out_dir, exist_ok=True)

GOLD = '#D4A843'
STOCK = '#C41E3A'

def draw_title(dr, title, subtitle=''):
    dr.text((W//2, 24), title, font=f22, fill='#1E293B', anchor='mt')
    if subtitle:
        dr.text((W//2, 52), subtitle, font=f13, fill='#94A3B8', anchor='mt')
    dr.line([(W//2-80, 70),(W//2+80, 70)], fill='#E2E8F0', width=1)

def footer(dr):
    dr.text((W//2, H-18), u'用数字，辨真相', font=f11, fill='#CBD5E1', anchor='mt')

# ===== CHART 1: 规模对比 - 金条形状 =====
def chart_aum():
    im=Image.new('RGB',(W,H),BG); dr=ImageDraw.Draw(im,'RGBA')
    draw_title(dr, u'规模（AUM）对比', u'截至2026年6月，华安黄金ETF规模是永赢黄金股ETF的约9倍')
    
    items = [
        (u'黄金ETF 518880', 1045, True),
        (u'黄金股ETF 517520', 110, False),
    ]
    bar_w = 340
    max_v = 1100
    bar_h = 56
    start_y = 145
    gap = 100
    bar_x0 = 200
    
    for i,(label,val,is_gold) in enumerate(items):
        y = start_y + i*gap
        w_val = int(bar_w * val / max_v)
        
        if is_gold:
            # Gold bar style
            dr.rounded_rectangle([bar_x0, y, bar_x0+w_val, y+bar_h], radius=10, fill='#E8A817')
            dr.rounded_rectangle([bar_x0+3, y+3, bar_x0+w_val-3, y+bar_h-3], radius=8, outline='#BB8000', width=2)
            shine_h = int(bar_h * 0.38)
            dr.rounded_rectangle([bar_x0+12, y+7, bar_x0+w_val-12, y+7+shine_h], radius=8, fill=(255,255,240,80))
            val_clr = '#7A5C00'
        else:
            dr.rounded_rectangle([bar_x0, y, bar_x0+w_val, y+bar_h], radius=10, fill=STOCK)
            val_clr = '#FFFFFF'
        
        val_text = f'{val}\u4ebf'
        if w_val > 90:
            dr.text((bar_x0+w_val-16, y+bar_h//2), val_text, font=f22, fill=val_clr, anchor='rm')
        else:
            dr.text((bar_x0+w_val+12, y+bar_h//2), val_text, font=f22, fill='#1E293B', anchor='lm')
        
        dr.text((bar_x0-10, y+bar_h//2), label, font=f15, fill='#475569', anchor='rm')
    
    dr.text((W//2, H-42), u'AUM数据来源：天天基金', font=f12, fill='#CBD5E1', anchor='mt')
    footer(dr)
    im.save(os.path.join(out_dir,'section_aum.png'), quality=95)
    print('✅ section_aum.png')

# ===== CHART 2: 近1年回报 =====
def chart_returns():
    im=Image.new('RGB',(W,H),BG); dr=ImageDraw.Draw(im,'RGBA')
    draw_title(dr, u'近1年累计回报', u'价格口径，截至2026年6月2日')
    
    items = [
        ('黄金ETF\n518880', 27.2, GOLD),
        ('黄金股ETF\n517520', 48.5, STOCK),
    ]
    base_x = 200
    bar_w = 300
    max_v = 50
    bar_h = 50
    start_y = 150
    gap = 130
    dot_r = 18
    
    dr.line([(base_x, start_y-20),(base_x, start_y+gap+40)], fill='#CBD5E1', width=1)
    
    for i,(label,val,clr) in enumerate(items):
        y = start_y + i*gap
        w_val = int(bar_w * val / max_v)
        dr.line([(base_x, y+bar_h//2),(base_x+w_val, y+bar_h//2)], fill=clr, width=3)
        dr.ellipse([base_x+w_val-dot_r, y+bar_h//2-dot_r, base_x+w_val+dot_r, y+bar_h//2+dot_r], fill=clr)
        dr.text((base_x+w_val+28, y+bar_h//2), f'{val}%', font=f28, fill='#1E293B', anchor='lm')
        parts = label.split('\n')
        dr.text((base_x-16, y+bar_h//2-6), parts[0], font=f15, fill='#475569', anchor='rm')
        dr.text((base_x-16, y+bar_h//2+14), parts[1], font=f13, fill='#94A3B8', anchor='rm')
    
    dr.text((W//2, H-30), u'回报 = (最新价 - 1年前价) / 1年前价', font=f12, fill='#CBD5E1', anchor='mt')
    footer(dr)
    im.save(os.path.join(out_dir,'section_returns.png'), quality=95)
    print('✅ section_returns.png')

# ===== CHART 3: 风险对比 =====
def chart_risk():
    im=Image.new('RGB',(W,H),BG); dr=ImageDraw.Draw(im,'RGBA')
    draw_title(dr, u'风险指标对比', u'近1年 - 黄金股ETF波动和回撤显著大于黄金ETF')
    
    groups = [
        {'label': u'年化波动率', 'vals': [(u'黄金ETF', 28.1, GOLD), (u'黄金股ETF', 42.8, STOCK)]},
        {'label': u'最大回撤',   'vals': [(u'黄金ETF', 24.9, GOLD), (u'黄金股ETF', 36.2, STOCK)]},
    ]
    group_w = 220; start_x = 80; bar_w = 60; gap_within = 20; max_v = 50; chart_h = 240; chart_top = 110
    
    for gi, group in enumerate(groups):
        gx = start_x + gi * (group_w + 60)
        dr.text((gx+group_w//2, chart_top-16), group['label'], font=f18, fill='#1E293B', anchor='mt')
        b_y = chart_top + chart_h
        dr.line([(gx, b_y),(gx+group_w, b_y)], fill='#CBD5E1', width=1)
        for vi, (label, val, clr) in enumerate(group['vals']):
            bx = gx + 40 + vi*(bar_w + gap_within)
            h_val = int(chart_h * val / max_v)
            dr.rectangle([bx, b_y-h_val, bx+bar_w, b_y], fill=clr)
            dr.text((bx+bar_w//2, b_y-h_val-14), f'{val}%', font=f15, fill='#1E293B', anchor='mt')
            dr.text((bx+bar_w//2, b_y+16), label, font=f13, fill='#475569', anchor='mt')
    
    ly = H-60
    dr.rectangle([W//2-100, ly-7, W//2-80, ly+5], fill=GOLD)
    dr.text((W//2-72, ly), u'黄金ETF 518880', font=f12, fill='#475569', anchor='lm')
    dr.rectangle([W//2+20, ly-7, W//2+40, ly+5], fill=STOCK)
    dr.text((W//2+48, ly), u'黄金股ETF 517520', font=f12, fill='#475569', anchor='lm')
    footer(dr)
    im.save(os.path.join(out_dir,'section_risk.png'), quality=95)
    print('✅ section_risk.png')

# ===== CHART 4: 资产结构 =====
def chart_holdings():
    im=Image.new('RGB',(W,H),BG); dr=ImageDraw.Draw(im,'RGBA')
    draw_title(dr, u'底层资产对比', u'黄金ETF持有实物金条，黄金股ETF持有45只上市公司股票')
    
    lx_c=160; rx_c=W-160; cy_c=230; r_big=90
    
    dr.ellipse([lx_c-r_big,cy_c-r_big,lx_c+r_big,cy_c+r_big],fill=GOLD)
    dr.ellipse([lx_c-r_big+4,cy_c-r_big+4,lx_c+r_big-4,cy_c+r_big-4],outline='#FFF',width=1)
    dr.text((lx_c,cy_c-10),'100%',font=f36,fill='#FFF',anchor='mm')
    dr.text((lx_c,cy_c+30),u'黄金现货',font=f18,fill='#FFF',anchor='mt')
    dr.text((lx_c,cy_c+r_big+28),u'黄金ETF 518880',font=f15,fill=GOLD,anchor='mt')
    dr.text((lx_c,cy_c+r_big+48),u'持有 Au9999 实物金条',font=f12,fill='#94A3B8',anchor='mt')
    
    segs=[(u'矿业开采',38,STOCK),(u'冶炼加工',22,'#E05A3A'),(u'珠宝零售',18,'#F0935B'),(u'其他',22,'#F5C6A0')]
    ang=-90
    for name,pct,clr in segs:
        a=360.0*pct/100
        dr.pieslice([rx_c-r_big,cy_c-r_big,rx_c+r_big,cy_c+r_big],start=int(ang),end=int(ang+a),fill=clr)
        ang+=a
    dr.ellipse([rx_c-50,cy_c-50,rx_c+50,cy_c+50],fill=BG)
    dr.text((rx_c,cy_c),u'45只\n股票',font=f15,fill='#475569',anchor='mm')
    
    leg_y=cy_c+r_big+28
    for i,(name,pct,clr) in enumerate(segs):
        lx=rx_c-80+(i%2)*100; ly=leg_y+(i//2)*26
        dr.rectangle([lx,ly,lx+10,ly+10],fill=clr)
        dr.text((lx+14,ly+5),f'{name} ~{pct}%',font=f11,fill='#475569',anchor='lm')
    
    dr.text((rx_c,cy_c+r_big+28+40),u'黄金股ETF 517520',font=f15,fill=STOCK,anchor='mt')
    dr.text((rx_c,cy_c+r_big+28+58),u'跟踪中证沪深港黄金产业股票指数',font=f12,fill='#94A3B8',anchor='mt')
    footer(dr)
    im.save(os.path.join(out_dir,'section_holdings.png'), quality=95)
    print('✅ section_holdings.png')

chart_aum()
chart_returns()
chart_risk()
chart_holdings()
