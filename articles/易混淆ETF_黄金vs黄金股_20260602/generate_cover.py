#!/usr/bin/env python3
"""黄金vs黄金股 #1 — 封面 v2: 实物金条 vs 金矿石, 带删除线逻辑"""
from PIL import Image, ImageDraw, ImageFont, ImageEnhance

W,H=640,480; bg='#FEFCF8'
im=Image.new('RGB',(W,H),bg); dr=ImageDraw.Draw(im,'RGBA')

gold_bar=Image.open('gold_bar.jpg').convert('RGBA')
gold_ore=Image.open('gold_ore.jpg').convert('RGBA')
isz=170
gold_bar=gold_bar.resize((isz,isz),Image.LANCZOS)
gold_bar=ImageEnhance.Brightness(gold_bar).enhance(1.25)
gold_bar=ImageEnhance.Color(gold_bar).enhance(1.3)
gold_ore=gold_ore.resize((isz,isz),Image.LANCZOS)

def circle_mask(sz):
    m=Image.new('L',(sz,sz),0);d=ImageDraw.Draw(m);d.ellipse([0,0,sz-1,sz-1],fill=255);return m
cm=circle_mask(isz)

cxL,cxR=155,W-155;cy=142
im.paste(gold_bar,(cxL-isz//2,cy-isz//2),cm)
im.paste(gold_ore,(cxR-isz//2,cy-isz//2),cm)
dr.ellipse([cxL-isz//2-2,cy-isz//2-2,cxL+isz//2+2,cy+isz//2+2],outline='#D4A843',width=3)
dr.ellipse([cxR-isz//2-2,cy-isz//2-2,cxR+isz//2+2,cy+isz//2+2],outline='#64748B',width=3)

try:
    f72=ImageFont.truetype('/System/Library/Fonts/PingFang.ttc',72)
    f34=ImageFont.truetype('/System/Library/Fonts/PingFang.ttc',34)
    f22=ImageFont.truetype('/System/Library/Fonts/PingFang.ttc',22)
    f18=ImageFont.truetype('/System/Library/Fonts/PingFang.ttc',18)
    f16=ImageFont.truetype('/System/Library/Fonts/PingFang.ttc',16)
    f14=ImageFont.truetype('/System/Library/Fonts/PingFang.ttc',14)
    f11=ImageFont.truetype('/System/Library/Fonts/PingFang.ttc',11)
except: f72=f34=f22=f18=f16=f14=f11=ImageFont.load_default()

dr.text((cxL,28),u'你以为买入了',font=f16,fill='#94A3B8',anchor='mt')
dr.text((cxR,28),u'实际买到的是',font=f16,fill='#94A3B8',anchor='mt')
dr.text((cxL,cy+isz//2+16),u'实物黄金',font=f22,fill='#B8860B',anchor='mt')
dr.text((cxR,cy+isz//2+16),u'金矿股票',font=f22,fill='#475569',anchor='mt')
dr.text((W//2,cy+4),u'\u2260',font=f72,fill='#C41E3A',anchor='mm')

y1=cy+isz//2+60
dr.text((W//2,y1),u'名字差一字，买的却是两回事',font=f34,fill='#1E293B',anchor='mt')
y2=y1+44
dr.line([(W//2-140,y2),(W//2+140,y2)],fill='#D4A843',width=3)
dr.text((W//2,y2+28),u'易混淆 ETF 系列 #1',font=f18,fill='#D4A843',anchor='mt')

dr.text((W//2,y2+62),u'黄金ETF 518880 \u2260 黄金股ETF 517520',font=f14,fill='#94A3B8',anchor='mt')
dr.text((W-40,H-22),u'用数字，辨真相',font=f11,fill='#CBD5E1',anchor='ra')
dr.text((12,H-22),u'Photo: BullionVault / Nevada Outback Gems (CC)',font=f11,fill='#CBD5E1')
im.save('cover.png',quality=95)
print('cover v2 done')
