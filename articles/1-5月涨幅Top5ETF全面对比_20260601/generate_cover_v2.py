#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成创意封面图 - 简约风格"""

from PIL import Image, ImageDraw, ImageFont
import os

# 尺寸
WIDTH = 640
HEIGHT = 395

# 颜色方案 - 简约高级灰+蓝色点缀
BG_COLOR = "#FAFAFA"  # 接近白的灰
PRIMARY_COLOR = "#1E3A5F"  # 深蓝
ACCENT_COLOR = "#378ADD"  # 亮蓝
TEXT_GRAY = "#4A5568"  # 深灰
LIGHT_GRAY = "#E2E8F0"  # 浅灰线条
CHIP_COLOR = "#2C5282"  # 芯片蓝

# 创建画布
img = Image.new('RGB', (WIDTH, HEIGHT), BG_COLOR)
draw = ImageDraw.Draw(img)

# 字体
try:
    font_title = ImageFont.truetype("/System/Library/Fonts/PingFang.ttc", 32)
    font_subtitle = ImageFont.truetype("/System/Library/Fonts/PingFang.ttc", 13)
    font_code = ImageFont.truetype("/System/Library/Fonts/PingFang.ttc", 15)
    font_large_num = ImageFont.truetype("/System/Library/Fonts/PingFang.ttc", 120)
    font_caption = ImageFont.truetype("/System/Library/Fonts/PingFang.ttc", 11)
except:
    font_title = ImageFont.load_default()
    font_subtitle = ImageFont.load_default()
    font_code = ImageFont.load_default()
    font_large_num = ImageFont.load_default()
    font_caption = ImageFont.load_default()

# ========== 左侧大数字 "5" ==========
# 巨大的半透明 "5" 作为背景视觉元素
num_text = "5"
bbox = draw.textbbox((0, 0), num_text, font=font_large_num)
text_w = bbox[2] - bbox[0]
text_h = bbox[3] - bbox[1]
num_x = 30
num_y = HEIGHT // 2 - text_h // 2 - 10
# 半透明灰色
num_layer = Image.new('RGBA', (WIDTH, HEIGHT), (0, 0, 0, 0))
num_draw = ImageDraw.Draw(num_layer)
num_draw.text((num_x, num_y), num_text, font=font_large_num, fill=(30, 58, 95, 18))
img = Image.alpha_composite(img.convert('RGBA'), num_layer).convert('RGB')
draw = ImageDraw.Draw(img)

# ========== 装饰线条 ==========
# 左侧竖线
draw.rectangle([8, 60, 10, HEIGHT-60], fill=ACCENT_COLOR)

# ========== 标题区域 ==========
title_text = "2026年1-5月涨幅最大"
bbox = draw.textbbox((0, 0), title_text, font=font_title)
title_w = bbox[2] - bbox[0]
draw.text((WIDTH//2 - title_w//2 + 30, 70), title_text, font=font_title, fill=PRIMARY_COLOR)

title_text2 = "5只ETF全面对比"
bbox = draw.textbbox((0, 0), title_text2, font=font_title)
title2_w = bbox[2] - bbox[0]
draw.text((WIDTH//2 - title2_w//2 + 30, 112), title_text2, font=font_title, fill=PRIMARY_COLOR)

# ========== 副标题 ==========
subtitle = "不推荐 · 只给数据 · 数据驱动决策"
bbox = draw.textbbox((0, 0), subtitle, font=font_subtitle)
sub_w = bbox[2] - bbox[0]
draw.text((WIDTH//2 - sub_w//2 + 30, 160), subtitle, font=font_subtitle, fill=TEXT_GRAY)

# ========== 分隔线 ==========
line_y = 190
draw.line([(120, line_y), (WIDTH-120, line_y)], fill=LIGHT_GRAY, width=1)

# ========== 5只ETF代码 - 水平排列带色块 ==========
codes = [
    ("513310", "#3B82F6"),  # 蓝
    ("515200", "#EC4899"),  # 粉
    ("562550", "#F59E0B"),  # 橙
    ("561170", "#8B5CF6"),  # 紫
    ("513520", "#10B981"),  # 绿
]

start_x = 70
spacing = 110
code_y = 220

for i, (code, color) in enumerate(codes):
    x = start_x + i * spacing
    # 小圆角矩形背景
    draw.rounded_rectangle([x-5, code_y-4, x+58, code_y+22], radius=3, fill=color)
    # 代码文字
    draw.text((x+6, code_y), code, font=font_code, fill="white")

# ========== 芯片装饰元素 ==========
# 右上角简化的芯片图案
chip_x, chip_y = 550, 55
chip_size = 50

# 芯片主体
draw.rectangle([chip_x, chip_y, chip_x+chip_size, chip_y+chip_size], 
               fill=CHIP_COLOR, outline=ACCENT_COLOR, width=2)

# 芯片引脚
pin_len = 6
pin_gap = 8
# 顶部引脚
for i in range(5):
    draw.rectangle([chip_x+5+i*pin_gap, chip_y-pin_len, chip_x+9+i*pin_gap, chip_y], 
                   fill=CHIP_COLOR)
# 底部引脚
for i in range(5):
    draw.rectangle([chip_x+5+i*pin_gap, chip_y+chip_size, chip_x+9+i*pin_gap, chip_y+chip_size+pin_len], 
                   fill=CHIP_COLOR)
# 左侧引脚
for i in range(5):
    draw.rectangle([chip_x-pin_len, chip_y+5+i*pin_gap, chip_x, chip_y+9+i*pin_gap], 
                   fill=CHIP_COLOR)
# 右侧引脚
for i in range(5):
    draw.rectangle([chip_x+chip_size, chip_y+5+i*pin_gap, chip_x+chip_size+pin_len, chip_y+9+i*pin_gap], 
                   fill=CHIP_COLOR)

# 芯片中心小方块
center_size = 16
center_x = chip_x + (chip_size - center_size) // 2
center_y = chip_y + (chip_size - center_size) // 2
draw.rectangle([center_x, center_y, center_x+center_size, center_y+center_size], 
               fill=ACCENT_COLOR)

# ========== 底部信息 ==========
footer_text = "数据来源：Wind金融终端 · 腾讯自选股 · 截至2026.05.31"
bbox = draw.textbbox((0, 0), footer_text, font=font_caption)
footer_w = bbox[2] - bbox[0]
draw.text((WIDTH//2 - footer_w//2, HEIGHT-35), footer_text, font=font_caption, fill="#9CA3AF")

# ========== 右上角装饰数字 ==========
# "TOP" 小标签
draw.text((520, 15), "TOP", font=font_subtitle, fill=ACCENT_COLOR)

# 保存
output_path = "/Users/apangduo/WorkBuddy/Claw/etf-tool-mvp/articles/etf_1-5月涨幅对比_20260601/cover_640x395.png"
img.save(output_path, quality=95)
print(f"封面已保存: {output_path}")
