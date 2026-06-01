#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成缺失的4张对比图表：贝塔、阿尔法、信息比率、年化波动率"""

from PIL import Image, ImageDraw, ImageFont
import math, os

WIDTH, HEIGHT = 640, 640
BG = "#F8F9FA"
BAR_BG = "#E9ECEF"
GRID_COLOR = "#DEE2E6"
TEXT_DARK = "#2D3748"
TEXT_GRAY = "#718096"

# ETF 配色
ETF_COLORS = {
    "513310": "#3B82F6",  # 蓝
    "515200": "#EC4899",  # 粉
    "562550": "#F59E0B",  # 橙
    "561170": "#8B5CF6",  # 紫
    "513520": "#10B981",  # 绿
}
ETF_NAMES = {
    "513310": "中韩半导体",
    "515200": "创新100",
    "562550": "绿电",
    "561170": "绿色电力",
    "513520": "日经",
}
ETF_CODES = ["513310", "515200", "562550", "561170", "513520"]

try:
    font_title = ImageFont.truetype("/System/Library/Fonts/PingFang.ttc", 22)
    font_axis = ImageFont.truetype("/System/Library/Fonts/PingFang.ttc", 13)
    font_value = ImageFont.truetype("/System/Library/Fonts/PingFang.ttc", 14)
    font_label = ImageFont.truetype("/System/Library/Fonts/PingFang.ttc", 13)
    font_code = ImageFont.truetype("/System/Library/Fonts/PingFang.ttc", 12)
    font_footnote = ImageFont.truetype("/System/Library/Fonts/PingFang.ttc", 10)
except:
    font_title = font_axis = font_value = font_label = font_code = font_footnote = ImageFont.load_default()

def nice_ticks(max_val, n_ticks=6):
    """生成美观的轴刻度（支持负值）"""
    abs_max = abs(max_val) if max_val != 0 else 1
    rough_step = abs_max / (n_ticks - 1)
    mag = 10 ** math.floor(math.log10(rough_step))
    normalized = rough_step / mag
    if normalized <= 1:
        step = mag
    elif normalized <= 2:
        step = 2 * mag
    elif normalized <= 5:
        step = 5 * mag
    else:
        step = 10 * mag
    
    ticks = []
    i = 0
    ceiling = abs_max * 1.15
    while True:
        t = i * step
        if t > ceiling:
            break
        tick_val = -t if max_val < 0 else t
        # 始终包含0
        if tick_val not in ticks:
            ticks.append(tick_val)
        i += 1
    return sorted(ticks)

def draw_chart(title, subtitle, data, unit="", output_name="", 
               higher_better=True, decimal_places=2, best_code=None):
    """生成柱状对比图"""
    img = Image.new('RGB', (WIDTH, HEIGHT), BG)
    draw = ImageDraw.Draw(img)
    
    # 标题
    bbox = draw.textbbox((0, 0), title, font=font_title)
    tw = bbox[2] - bbox[0]
    draw.text((WIDTH//2 - tw//2, 36), title, font=font_title, fill=TEXT_DARK)
    
    # 副标题
    if subtitle:
        bbox = draw.textbbox((0, 0), subtitle, font=font_axis)
        sw = bbox[2] - bbox[0]
        draw.text((WIDTH//2 - sw//2, 66), subtitle, font=font_axis, fill=TEXT_GRAY)
    
    # 图表区域（加大底部空间避免遮挡）
    chart_left = 105
    chart_right = WIDTH - 35
    chart_top = 110
    chart_bottom = HEIGHT - 110
    chart_width = chart_right - chart_left
    chart_height = chart_bottom - chart_top
    
    # 数据
    codes = list(data.keys())
    values = list(data.values())
    max_val = max(values) if values else 0
    min_val = min(values) if values else 0
    all_negative = all(v < 0 for v in values)
    
    # Y轴刻度（负值用绝对值计算）
    display_max = abs(max_val) if all_negative else max_val
    ticks = nice_ticks(display_max if not all_negative else max_val, 6)
    
    # 对于全部为负的数据，用绝对值的刻度
    if all_negative:
        ticks_sorted = sorted(ticks)
        # 确保刻度覆盖全部数据
        step = ticks_sorted[1] - ticks_sorted[0] if len(ticks_sorted) > 1 else abs(max_val)/3
        tick_min = min(ticks_sorted[0], min_val) - step
        tick_max = 0
        tick_range = tick_max - tick_min
    else:
        ticks_sorted = ticks
        tick_min = 0
        tick_max = ticks[-1] if ticks else max_val
        step = ticks[1] - ticks[0] if len(ticks) > 1 else max_val/3
        if tick_max < max_val:
            tick_max += step
        tick_range = tick_max - tick_min
    
    if tick_range == 0:
        tick_range = 1
    
    # 网格线 + Y轴标签
    for t in ticks_sorted if all_negative else ticks:
        y = chart_bottom - ((t - tick_min) / tick_range) * chart_height if all_negative else chart_bottom - (t / tick_range) * chart_height
        draw.line([(chart_left, y), (chart_right, y)], fill=GRID_COLOR, width=1)
        label = f"{t:.{decimal_places}f}{unit}"
        bbox = draw.textbbox((0, 0), label, font=font_axis)
        lw = bbox[2] - bbox[0]
        lh = bbox[3] - bbox[1]
        draw.text((chart_left - lw - 10, y - lh//2), label, font=font_axis, fill=TEXT_GRAY)
    
    # 基线
    draw.line([(chart_left, chart_bottom), (chart_right, chart_bottom)], fill=TEXT_DARK, width=2)
    
    # 柱状图
    bar_count = len(codes)
    bar_gap = 16
    total_gap = bar_gap * (bar_count + 1)
    bar_width = (chart_width - total_gap) / bar_count
    bar_width = min(bar_width, 75)
    
    total_bar_width = bar_count * bar_width + (bar_count - 1) * bar_gap
    start_x = chart_left + (chart_width - total_bar_width) / 2
    
    for i, code in enumerate(codes):
        x = start_x + i * (bar_width + bar_gap)
        val = values[i]
        if all_negative:
            bar_height = ((val - tick_min) / tick_range) * chart_height if tick_range > 0 else 0
        else:
            bar_height = (val / tick_range) * chart_height if tick_range > 0 else 0
        y = chart_bottom - bar_height
        
        color = ETF_COLORS[code]
        # 柱体
        draw.rectangle([x, y, x + bar_width, chart_bottom], fill=color, outline=None)
        # 顶部圆角效果
        draw.rectangle([x, y, x + bar_width, min(y + 4, chart_bottom)], fill=color, outline=None)
        
        # 数值标签
        val_text = f"{val:.{decimal_places}f}{unit}"
        bbox = draw.textbbox((0, 0), val_text, font=font_value)
        vw = bbox[2] - bbox[0]
        vh = bbox[3] - bbox[1]
        val_x = x + bar_width/2 - vw/2
        val_y = y - vh - 6
        draw.text((val_x, val_y), val_text, font=font_value, fill=TEXT_DARK)
        
        # ETF代码 + 名称
        code_text = code
        bbox = draw.textbbox((0, 0), code_text, font=font_code)
        cw = bbox[2] - bbox[0]
        draw.text((x + bar_width/2 - cw/2, chart_bottom + 10), code_text, font=font_code, fill=TEXT_DARK)
        
        name_text = ETF_NAMES.get(code, "")
        bbox = draw.textbbox((0, 0), name_text, font=font_code)
        nw = bbox[2] - bbox[0]
        draw.text((x + bar_width/2 - nw/2, chart_bottom + 28), name_text, font=font_code, fill=TEXT_GRAY)
    
    # 脚注（底部留足够空间）
    if all_negative:
        note = "负得越少越好（越接近0越好）"
    else:
        note = "越高越好" if higher_better else "越低越好"
    bbox = draw.textbbox((0, 0), note, font=font_footnote)
    nw = bbox[2] - bbox[0]
    draw.text((WIDTH//2 - nw//2, HEIGHT - 25), note, font=font_footnote, fill=TEXT_GRAY)
    
    # 高亮最佳
    if best_code is None:
        if higher_better:
            best_code = max(data, key=data.get)
        else:
            best_code = min(data, key=data.get)
    
    # 保存
    out_path = os.path.join(os.path.dirname(__file__), output_name)
    img.save(out_path, quality=95)
    print(f"✅ {output_name}")
    return out_path


# ===== 1. 贝塔 =====
draw_chart(
    title="贝塔（近1年）",
    subtitle="衡量相对市场指数的波动敏感度",
    data={"513310": 1.92, "515200": 1.51, "562550": 0.59, "561170": 0.59, "513520": 0.80},
    output_name="section_贝塔对比_640x640.png",
    higher_better=True,
    decimal_places=2,
)

# ===== 2. 阿尔法 =====
draw_chart(
    title="阿尔法（近1年）",
    subtitle="衡量基金经理的超额收益能力",
    data={"513310": 1.72, "515200": 0.52, "562550": 0.27, "561170": 0.27, "513520": 0.52},
    unit="%",
    output_name="section_阿尔法对比_640x640.png",
    higher_better=True,
    decimal_places=2,
)

# ===== 3. 信息比率 =====
draw_chart(
    title="信息比率（近1年）",
    subtitle="衡量承担单位主动风险获得的超额回报",
    data={"513310": 0.48, "515200": 0.32, "562550": 0.04, "561170": 0.04, "513520": 0.16},
    output_name="section_信息比率对比_640x640.png",
    higher_better=True,
    decimal_places=2,
)

# ===== 4. 年化波动率 =====
draw_chart(
    title="年化波动率（近1年）",
    subtitle="衡量价格波动幅度，越低持有体验越平稳",
    data={"513310": 36.65, "515200": 22.67, "562550": 20.05, "561170": 20.03, "513520": 22.15},
    unit="%",
    output_name="section_年化波动率对比_640x640.png",
    higher_better=False,
    decimal_places=2,
)

print("\n✨ 4张图表全部生成完成！")

# ===== 也重生成6张老图（统一刻度和间距） =====
# 5. 涨幅
draw_chart(
    title="1-5月涨幅",
    subtitle="2026年1月2日至5月29日区间回报",
    data={"513310": 113.92, "515200": 23.94, "562550": 23.67, "561170": 23.59, "513520": 23.14},
    unit="%",
    output_name="section_涨幅对比_640x640.png",
    higher_better=True,
    decimal_places=2,
)

# 6. 规模
draw_chart(
    title="基金规模（AUM）",
    subtitle="基金资产净值，反映ETF体量和流动性",
    data={"513310": 6.57, "515200": 2.93, "562550": 0.96, "561170": 2.32, "513520": 1.12},
    unit="亿",
    output_name="section_规模对比_640x640.png",
    higher_better=True,
    decimal_places=2,
)

# 7. 费率
draw_chart(
    title="费率合计（管理费+托管费）",
    subtitle="持有成本中唯一确定的部分，越低越好",
    data={"513310": 0.95, "515200": 0.60, "562550": 0.60, "561170": 0.60, "513520": 0.25},
    unit="%",
    output_name="section_费率对比_640x640.png",
    higher_better=False,
    decimal_places=2,
)

# 8. 跟踪误差
draw_chart(
    title="跟踪误差（近1年）",
    subtitle="衡量ETF净值与指数的偏离程度，越低越紧密",
    data={"513310": 4.38, "515200": 2.27, "562550": 2.70, "561170": 2.70, "513520": 2.83},
    unit="%",
    output_name="section_跟踪误差对比_640x640.png",
    higher_better=False,
    decimal_places=2,
)

# 9. 夏普比率
draw_chart(
    title="夏普比率（近1年）",
    subtitle="衡量承担单位风险获得多少超额回报",
    data={"513310": 0.49, "515200": 0.35, "562550": 0.18, "561170": 0.18, "513520": 0.27},
    output_name="section_夏普比率对比_640x640.png",
    higher_better=True,
    decimal_places=2,
)

# 10. 最大回撤
draw_chart(
    title="最大回撤（近1年）",
    subtitle="过去1年从高点至低点的最大跌幅，越低越好",
    data={"513310": -21.31, "515200": -12.99, "562550": -11.52, "561170": -11.52, "513520": -14.44},
    unit="%",
    output_name="section_最大回撤对比_640x640.png",
    higher_better=False,
    decimal_places=2,
)

print("\n🎉 全部10张图表生成完成！")
