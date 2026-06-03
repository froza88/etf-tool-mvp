#!/usr/bin/env python3
"""封面 v8 — 实物照片：金条 vs 金矿石"""
from PIL import Image, ImageDraw, ImageFont, ImageEnhance

W,H = 640, 480
bg = '#FEFCF8'
im = Image.new('RGB', (W,H), bg)
dr = ImageDraw.Draw(im, 'RGBA')

# Load real photos
gold_bar = Image.open('gold_bar.jpg').convert('RGBA')
gold_ore = Image.open('gold_ore.jpg').convert('RGBA')

# Resize to same square size
img_sz = 170
gold_bar = gold_bar.resize((img_sz, img_sz), Image.LANCZOS)
# Brighten + saturate the gold bar
gold_bar = ImageEnhance.Brightness(gold_bar).enhance(1.25)
gold_bar = ImageEnhance.Color(gold_bar).enhance(1.3)
gold_ore = gold_ore.resize((img_sz, img_sz), Image.LANCZOS)

# Create circular masks
def make_circle_mask(size):
    mask = Image.new('L', (size, size), 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse([0, 0, size-1, size-1], fill=255)
    return mask

circle_mask = make_circle_mask(img_sz)

# Positions
cxL, cxR = 155, W-155
cy = 148

# Paste circular photos
im.paste(gold_bar, (cxL-img_sz//2, cy-img_sz//2), circle_mask)
im.paste(gold_ore, (cxR-img_sz//2, cy-img_sz//2), circle_mask)

# Circle borders
dr.ellipse([cxL-img_sz//2-2, cy-img_sz//2-2, cxL+img_sz//2+2, cy+img_sz//2+2], outline='#D4A843', width=3)
dr.ellipse([cxR-img_sz//2-2, cy-img_sz//2-2, cxR+img_sz//2+2, cy+img_sz//2+2], outline='#64748B', width=3)

# Labels under photos
try:
    f22=ImageFont.truetype('/System/Library/Fonts/PingFang.ttc',22)
    f18=ImageFont.truetype('/System/Library/Fonts/PingFang.ttc',18)
    f16=ImageFont.truetype('/System/Library/Fonts/PingFang.ttc',16)
    f14=ImageFont.truetype('/System/Library/Fonts/PingFang.ttc',14)
    f13=ImageFont.truetype('/System/Library/Fonts/PingFang.ttc',13)
    f11=ImageFont.truetype('/System/Library/Fonts/PingFang.ttc',11)
    f72=ImageFont.truetype('/System/Library/Fonts/PingFang.ttc',72)
    f34=ImageFont.truetype('/System/Library/Fonts/PingFang.ttc',34)
except: f22=f18=f16=f14=f13=f11=f72=f34=ImageFont.load_default()

dr.text((cxL, cy+img_sz//2+16), u'实物金块', font=f22, fill='#B8860B', anchor='mt')
dr.text((cxR, cy+img_sz//2+16), u'金矿石', font=f22, fill='#475569', anchor='mt')

# Top labels
dr.text((cxL, 30), u'你以为买入了', font=f16, fill='#94A3B8', anchor='mt')
dr.text((cxR, 30), u'你买到的是', font=f16, fill='#94A3B8', anchor='mt')

# Big ≠
dr.text((W//2, cy+4), u'\u2260', font=f72, fill='#C41E3A', anchor='mm')

# Bottom
y1 = cy + img_sz//2 + 62
dr.text((W//2, y1), u'名字差一个字，买的却是两回事', font=f34, fill='#1E293B', anchor='mt')

y2 = y1 + 44
dr.line([(W//2-140, y2),(W//2+140, y2)], fill='#D4A843', width=3)

dr.text((W//2, y2+28), u'易混淆 ETF 系列 \u00b7 总纲', font=f18, fill='#D4A843', anchor='mt')

pairs = [u'消费ETF \u2260 消费电子ETF', u'红利ETF \u2260 红利低波ETF', u'医药ETF \u2260 医疗ETF']
for i,p in enumerate(pairs):
    dr.text((W//2, y2+58+i*26), p, font=f14, fill='#94A3B8', anchor='mt')

dr.text((W-40, H-22), u'不推荐 \u00b7 只给数据', font=f11, fill='#CBD5E1', anchor='ra')

# Photo credit
dr.text((12, H-22), u'Photo: BullionVault / Nevada Outback Gems (CC)', font=f11, fill='#CBD5E1')

im.save('cover.png', quality=95)
print('v8 done — real photos')
