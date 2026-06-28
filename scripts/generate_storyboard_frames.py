#!/usr/bin/env python3
"""生成军工ETF星球研究所风格视频分镜图"""
from PIL import Image, ImageDraw, ImageFont
import math, json, os

OUT = '/Users/apangduo/WorkBuddy/Claw/outputs/storyboard/'
os.makedirs(OUT, exist_ok=True)

W, H = 1920, 1080
BG = (10, 22, 40)       # 暗蓝底
ACCENT = (245, 158, 11)  # 暖橙
WHITE = (255, 255, 255)
GRAY = (100, 120, 150)
RED = (239, 68, 68)
GREEN = (34, 197, 94)
BLUE = (59, 130, 246)

# Try to load Chinese font
FONT_PATH = '/System/Library/Fonts/STHeiti Light.ttc'
font_bold = ImageFont.truetype(FONT_PATH, 48)
font_title = ImageFont.truetype(FONT_PATH, 72)
font_data = ImageFont.truetype(FONT_PATH, 36)
font_small = ImageFont.truetype(FONT_PATH, 24)
font_huge = ImageFont.truetype(FONT_PATH, 96)

def new_canvas():
    return Image.new('RGB', (W, H), BG)

def draw_text_center(draw, text, y, font=font_title, color=WHITE):
    bbox = draw.textbbox((0, 0), text, font=font)
    w = bbox[2] - bbox[0]
    draw.text(((W - w) // 2, y), text, font=font, fill=color)

def save(img, name):
    img.save(f'{OUT}{name}.png')
    print(f'  ✅ {name}.png')

# ── Shot 1: Opening title ──
img = new_canvas()
d = ImageDraw.Draw(img)
draw_text_center(d, "这个名字，", 200, font_title, GRAY)
draw_text_center(d, "叫军工ETF。", 280, font_title, WHITE)
draw_text_center(d, "另一个名字，", 500, font_title, GRAY)
draw_text_center(d, "也叫军工ETF。", 580, font_title, WHITE)
draw_text_center(d, "512660 ← → 512710", 740, font_data, ACCENT)
save(img, 'shot1_title')

# ── Shot 2: Return comparison with key numbers ──
img = new_canvas()
d = ImageDraw.Draw(img)
draw_text_center(d, "3 年前，各投 1 万块", 100, font_title, GRAY)
draw_text_center(d, "512660 → 12,601 元", 300, font_huge, GREEN)
draw_text_center(d, "512710 → 10,744 元", 460, font_huge, RED)
draw_text_center(d, f"差了 1,857 块", 640, font_title, ACCENT)
# Draw simple bar
bar_w = 200; bar_gap = 300; start_x = 760
# 512660 bar
bar_h1 = 280
d.rectangle([start_x, 300-bar_h1, start_x+bar_w, 300], fill=GREEN)
d.text((start_x+bar_w//2-50, 270-bar_h1), "12601元", font=font_data, fill=GREEN)
# 512710 bar
bar_h2 = 240
d.rectangle([start_x+bar_gap, 300-bar_h2, start_x+bar_gap+bar_w, 300], fill=RED)
d.text((start_x+bar_gap+bar_w//2-50, 270-bar_h2), "10744元", font=font_data, fill=RED)
save(img, 'shot2_returns')

# ── Shot 3: Holdings comparison ──
img = new_canvas()
d = ImageDraw.Draw(img)
draw_text_center(d, "持仓集中度：一张网 vs 一把刀", 60, font_title, GRAY)
# Left: 512660
d.text((200, 200), "512660 军工ETF", font=font_bold, fill=GREEN)
d.text((200, 280), "80 只成份股", font=font_data, fill=WHITE)
d.text((200, 340), "前 5 大持仓占比：22.9%", font=font_data, fill=GRAY)
# Right: 512710
d.text((1200, 200), "512710 军工龙头ETF", font=font_bold, fill=RED)
d.text((1200, 280), "30 只成份股", font=font_data, fill=WHITE)
d.text((1200, 340), "前 5 大持仓占比：37.9%", font=font_data, fill=GRAY)
# Visual: pie-like bars (many small vs few large)
sizes_660 = [900, 850, 800, 780, 750, 720, 680, 650, 600, 580, 550, 500, 480, 450, 430, 400]
sizes_710 = [1600, 1200, 1000, 850, 750, 650, 600]
for i, s in enumerate(sizes_660[:12]):
    d.rectangle([250, 450+i*40, 250+s//4, 450+i*40+30], fill=GREEN)
for i, s in enumerate(sizes_710[:7]):
    d.rectangle([1050, 450+i*50, 1050+s//3, 450+i*50+40], fill=RED)
save(img, 'shot3_holdings')

# ── Shot 4: Risk metrics ──
img = new_canvas()
d = ImageDraw.Draw(img)
draw_text_center(d, "风险指标：谁更稳？", 60, font_title, GRAY)

metrics = [
    ("年化波动率", "30.27%", "33.27%", True),
    ("最大回撤", "25.15%", "25.54%", True),
    ("夏普比率", "1.14", "0.84", False),
    ("卡玛比率", "1.49", "1.15", False),
]
for i, (name, v660, v710, lower_better) in enumerate(metrics):
    y = 250 + i * 180
    draw_text_center(d, name, y-60, font=font_data, color=GRAY)
    color660 = GREEN if (lower_better and float(v660.rstrip('%')) < float(v710.rstrip('%'))) or (not lower_better and float(v660) > float(v710)) else WHITE
    color710 = RED if color660 != GREEN else WHITE
    d.text((400, y), f"512660：{v660}", font=font_bold, fill=color660)
    d.text((1000, y), f"512710：{v710}", font=font_bold, fill=color710)
save(img, 'shot4_risk')

# ── Shot 5: Fund flow ──
img = new_canvas()
d = ImageDraw.Draw(img)
draw_text_center(d, "过去 5 天，资金用脚投票", 100, font_title, GRAY)
# 512660 inflow
arrow_up = [(W//2-300, 600), (W//2-300, 300), (W//2-360, 360), (W//2-300, 300), (W//2-240, 360)]
d.line(arrow_up, fill=GREEN, width=8)
d.text((W//2-420, 250), "+0.11%", font=font_huge, fill=GREEN)
d.text((W//2-400, 400), "512660 资金净流入", font=font_data, fill=GREEN)

# 512710 outflow
arrow_down = [(W//2+300, 300), (W//2+300, 600), (W//2+240, 540), (W//2+300, 600), (W//2+360, 540)]
d.line(arrow_down, fill=RED, width=8)
d.text((W//2+250, 500), "-1.35%", font=font_huge, fill=RED)
d.text((W//2+260, 700), "512710 资金净流出", font=font_data, fill=RED)
save(img, 'shot5_flow')

# ── Shot 6: Summary cards ──
img = new_canvas()
d = ImageDraw.Draw(img)
draw_text_center(d, "最后的答案", 80, font_title, GRAY)

# Left card
d.rectangle([100, 250, 900, 900], outline=GREEN, width=3)
d.text((200, 300), "512660 军工ETF", font=font_bold, fill=GREEN)
d.text((200, 400), "• 近1年收益 +37.37%", font=font_data, fill=WHITE)
d.text((200, 470), "• 近3年收益 +26.01%", font=font_data, fill=WHITE)
d.text((200, 540), "• 夏普比率 1.14", font=font_data, fill=WHITE)
d.text((200, 610), "• 分散持仓，稳健增长", font=font_data, fill=WHITE)
d.text((200, 700), "适合：长期持有，追求稳定复利", font=font_data, fill=ACCENT)

# Right card
d.rectangle([1020, 250, 1820, 900], outline=RED, width=3)
d.text((1120, 300), "512710 军工龙头ETF", font=font_bold, fill=RED)
d.text((1120, 400), "• 近1年收益 +29.26%", font=font_data, fill=WHITE)
d.text((1120, 470), "• 近3年收益 +7.44%", font=font_data, fill=WHITE)
d.text((1120, 540), "• 夏普比率 0.84", font=font_data, fill=WHITE)
d.text((1120, 610), "• 龙头集中，高弹性", font=font_data, fill=WHITE)
d.text((1120, 700), "适合：波段操作，捕捉龙头爆发", font=font_data, fill=ACCENT)
save(img, 'shot6_summary')

# ── Shot 7: Closing quote ──
img = new_canvas()
d = ImageDraw.Draw(img)
draw_text_center(d, "长期的秘密不是方向", 300, font_title, GRAY)
draw_text_center(d, "是波动在时间里的累积差", 400, font_title, ACCENT)
draw_text_center(d, "3‰ × 1000 天 = 很远的地方", 550, font_data, WHITE)
draw_text_center(d, "ETF 对比 · 每周拆开长得很像的基金", 800, font_small, GRAY)
save(img, 'shot7_ending')

# ── Shot 8: China map with military industry dots ──
img = new_canvas()
d = ImageDraw.Draw(img)
draw_text_center(d, "中国军工版图", 80, font_title, ACCENT)
# Simplified China outline + key cities
cities = [
    ("西安", 550, 420), ("成都", 470, 500), ("沈阳", 700, 250),
    ("北京", 620, 200), ("武汉", 600, 420), ("上海", 750, 380),
    ("哈尔滨", 800, 150), ("重庆", 500, 460), ("洛阳", 580, 370),
]
# Draw a rough China outline
outline_points = [(300, 150), (500, 120), (800, 140), (900, 180), (850, 250), (780, 380), (720, 500), (600, 580), (500, 600), (380, 550), (300, 450), (250, 350), (200, 250), (300, 150)]
for i in range(len(outline_points)-1):
    d.line([outline_points[i], outline_points[i+1]], fill=GRAY, width=2)
d.line([outline_points[-1], outline_points[0]], fill=GRAY, width=2)

for name, x, y in cities:
    d.ellipse([x-6, y-6, x+6, y+6], fill=ACCENT)
    d.text((x+12, y-12), name, font=font_small, fill=WHITE)

d.text((200, 750), "这 9 座城市，是中国军工产业的核心据点", font=font_data, fill=GRAY)
d.text((200, 820), "两只 ETF 的 110 家成分股，超过 70% 分布在这些城市", font=font_small, fill=GRAY)
save(img, 'shot8_map')

print(f"\n✅ 全部 8 张分镜图生成完毕 → {OUT}")
