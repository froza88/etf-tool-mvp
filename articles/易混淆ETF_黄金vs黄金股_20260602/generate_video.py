#!/usr/bin/env python3
"""
黄金ETF vs 黄金股ETF — 视频帧生成 + ffmpeg 合成
竖屏 9:16 (1080x1920), 30fps, ~62秒
优化版：numpy 梯度 + 字体预加载 + 背景复用
"""

import math, os, subprocess, sys, time
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

# ─── 配置 ─────────────────────────────────────────────
W, H = 1080, 1920
FPS = 30
OUT_DIR = Path(__file__).parent / "frames"
VIDEO_OUT = Path(__file__).parent / "视频_黄金vs黄金股_v4.mp4"
FFMPEG_BIN = "/Users/apangduo/.workbuddy/binaries/python/versions/3.13.12/lib/python3.13/site-packages/imageio_ffmpeg/binaries/ffmpeg-macos-x86_64-v7.1"

# 配色
BG_DARK = np.array([12, 12, 30])
BG_WARM = np.array([30, 18, 18])
GOLD = (212, 168, 67)
WHITE = (255, 255, 255)
RED = (196, 30, 58)
LIGHT_GRAY = (180, 180, 190)
DIM_GRAY = (120, 120, 140)

# 字体 — 预加载
FONT_BOLD = "/System/Library/Fonts/PingFang.ttc"
FONT_LIGHT = "/System/Library/Fonts/STHeiti Light.ttc"
FONT_MEDIUM = "/System/Library/Fonts/STHeiti Medium.ttc"

ASSETS = Path(__file__).parent
GOLD_BAR_IMG = ASSETS / "gold_bar.jpg"
GOLD_ORE_IMG = ASSETS / "gold_ore.jpg"
SECTION_RETURNS = ASSETS / "charts" / "section_returns.png"
SECTION_RISK = ASSETS / "charts" / "section_risk.png"

# 场景时长（帧数）
SCENE_NFRAMES = [210, 360, 360, 360, 300]  # 7s, 12s, 12s, 12s, 10s = 53s

# ─── 字体缓存 ─────────────────────────────────────────
FONTS = {}


def ff(size, bold=False):
    """获取字体（缓存）"""
    key = (size, bold)
    if key not in FONTS:
        FONTS[key] = ImageFont.truetype(FONT_BOLD if bold else FONT_LIGHT, size)
    return FONTS[key]


def make_gradient_bg(c1, c2):
    """numpy 垂直渐变背景，返回 Image"""
    c1, c2 = np.array(c1), np.array(c2)
    t = np.linspace(0, 1, H).reshape(H, 1, 1)
    bg_arr = ((1 - t) * c1 + t * c2).astype(np.uint8)
    bg_arr = np.tile(bg_arr, (1, W, 1))  # H x W x 3
    return Image.fromarray(bg_arr, "RGB")


def draw_text_center(draw, text, font, y, color, alpha=None):
    """居中绘制文字（支持alpha）"""
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    x = (W - tw) // 2
    fill = color if alpha is None else (*color[:3], alpha)
    draw.text((x, y), text, font=font, fill=fill)


def draw_card(draw, x, y, w, h, bg_color, main_text, sub_text, scale=1.0, alpha=1.0):
    """绘制数据卡片"""
    ws, hs = int(w * scale), int(h * scale)
    cx = x + (w - ws) // 2
    cy = y + (h - hs) // 2

    alpha_int = int(255 * alpha)
    # 半透明背景
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    od.rounded_rectangle([cx, cy, cx + ws, cy + hs], radius=20, fill=(*bg_color, alpha_int))
    draw._image.paste(overlay, (0, 0), overlay)

    # 主标题
    fm = ff(int(42 * scale), bold=True)
    fs = ff(int(22 * scale))
    bbox = draw.textbbox((0, 0), main_text, font=fm)
    tw = bbox[2] - bbox[0]
    draw.text((x + (w - tw) // 2, cy + 25), main_text, font=fm, fill=(*WHITE, alpha_int))
    bbox2 = draw.textbbox((0, 0), sub_text, font=fs)
    tw2 = bbox2[2] - bbox2[0]
    draw.text((x + (w - tw2) // 2, cy + 90), sub_text, font=fs, fill=(*LIGHT_GRAY, alpha_int))


def ease_out_elastic(t):
    if t <= 0 or t >= 1:
        return t
    c4 = (2 * math.pi) / 3
    return pow(2, -10 * t) * math.sin((t * 10 - 0.75) * c4) + 1


def ease_out_back(t):
    c1 = 1.70158
    c3 = c1 + 1
    return 1 + c3 * pow(t - 1, 3) + c1 * pow(t - 1, 2)


# ─── 预渲染背景 ────────────────────────────────────────
BG_DARK_IMG = None
BG_WARM_IMG = None
BG_RISK_IMG = None


def init_bgs():
    global BG_DARK_IMG, BG_WARM_IMG, BG_RISK_IMG
    BG_DARK_IMG = make_gradient_bg((8, 8, 22), (22, 14, 14))
    BG_WARM_IMG = make_gradient_bg((8, 8, 24), (26, 16, 14))
    BG_RISK_IMG = make_gradient_bg((12, 8, 8), (32, 8, 8))


# ─── 图片预加载 ────────────────────────────────────────
GOLD_BAR = None
GOLD_ORE = None
RETURNS_CHART = None
RISK_CHART = None


def init_assets():
    global GOLD_BAR, GOLD_ORE, RETURNS_CHART, RISK_CHART
    for name, var, path in [
        ("gold_bar", "GOLD_BAR", GOLD_BAR_IMG),
        ("gold_ore", "GOLD_ORE", GOLD_ORE_IMG),
        ("returns", "RETURNS_CHART", SECTION_RETURNS),
        ("risk", "RISK_CHART", SECTION_RISK),
    ]:
        try:
            img = Image.open(path).convert("RGBA")
            globals()[var] = img
        except Exception as e:
            print(f"  ⚠ 无法加载 {path}: {e}")


# ─── 场景渲染 ──────────────────────────────────────────

def scene1(frames_dir, n):
    """开场钩子"""
    for i in range(n):
        t = i / n
        draw = ImageDraw.Draw(BG_DARK_IMG.copy())

        # 装饰线
        if t > 0.1:
            a = int(255 * min(1, (t - 0.1) * 5))
            draw.line([(W // 4, 380), (3 * W // 4, 380)], fill=(*GOLD, a), width=2)

        # 标题行1
        if t > 0.15:
            a = int(255 * min(1, (t - 0.15) * 12))
            draw_text_center(draw, "你以为买的是黄金", ff(64, True), 430, GOLD, a)

        # 标题行2
        if t > 0.45:
            a = int(255 * min(1, (t - 0.45) * 12))
            draw_text_center(draw, "其实是金矿公司的股票", ff(50, True), 540, RED, a)

        # 副标题
        if t > 0.7:
            a = int(255 * min(1, (t - 0.7) * 8))
            draw_text_center(draw, "名字差一字，买的是两回事", ff(28), 1680, LIGHT_GRAY, a)

        draw._image.save(frames_dir / f"s1_{i:05d}.png")
        if i % 100 == 0:
            print(f"  S1: {i}/{n}")


def scene2(frames_dir, n):
    """并排对比"""
    for i in range(n):
        t = i / n
        draw = ImageDraw.Draw(BG_DARK_IMG.copy())

        # 标题
        if t > 0.04:
            a = int(255 * min(1, (t - 0.04) * 10))
            draw_text_center(draw, "你买的是什么？", ff(50, True), 100, GOLD, a)

        # 卡片参数
        cw, ch = 420, 560
        gap = 50
        left_x, right_x = 40, W - 40 - cw
        target_ly, target_ry = 300, 300

        if t > 0.08:
            p = min(1, (t - 0.08) * 4)
            ease = ease_out_back(p)
            ly = int(H + 200 + (target_ly - (H + 200)) * ease)
            ry = int(H + 200 + (target_ry - (H + 200)) * ease)
            ac = int(255 * min(1, p * 2))

            # 左侧黄金ETF卡片
            left_card = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
            ld = ImageDraw.Draw(left_card)
            ld.rounded_rectangle([0, 0, cw, ch], radius=24,
                                 fill=(*GOLD, int(20 * min(1, p))))
            ld.rounded_rectangle([3, 3, cw - 3, ch - 3], radius=22,
                                 outline=(*GOLD, int(100 * min(1, p))), width=2)
            ld.text((cw // 2, 50), "黄金ETF", font=ff(42, True), fill=(*GOLD, ac), anchor="mt")
            ld.text((cw // 2, 110), "商品型 ETF", font=ff(22), fill=(*LIGHT_GRAY, ac), anchor="mt")

            if GOLD_BAR:
                gb = GOLD_BAR.resize((cw - 80, ch - 260), Image.LANCZOS)
                left_card.paste(gb, (40, 150), gb)

            ld.text((cw // 2, ch - 40), "实物黄金 · 金条", font=ff(20),
                    fill=(*LIGHT_GRAY, ac), anchor="mt")

            # 右侧黄金股ETF卡片
            right_card = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
            rd = ImageDraw.Draw(right_card)
            rd.rounded_rectangle([0, 0, cw, ch], radius=24,
                                 fill=(*RED, int(20 * min(1, p))))
            rd.rounded_rectangle([3, 3, cw - 3, ch - 3], radius=22,
                                 outline=(*RED, int(100 * min(1, p))), width=2)
            rd.text((cw // 2, 50), "黄金股ETF", font=ff(40, True), fill=(*RED, ac), anchor="mt")
            rd.text((cw // 2, 110), "股票型 ETF", font=ff(22), fill=(*LIGHT_GRAY, ac), anchor="mt")

            if GOLD_ORE:
                go = GOLD_ORE.resize((cw - 80, ch - 260), Image.LANCZOS)
                right_card.paste(go, (40, 150), go)

            rd.text((cw // 2, ch - 40), "金矿公司 · 股票", font=ff(20),
                    fill=(*LIGHT_GRAY, ac), anchor="mt")

            draw._image.paste(left_card, (left_x, ly), left_card)
            draw._image.paste(right_card, (right_x, ry), right_card)

            # ≠ 符号
            if p > 0.5:
                na = int(255 * min(1, (p - 0.5) * 5))
                draw_text_center(draw, "≠", ff(80, True), 560, RED, na)

            # 底部说明
            if p > 0.85:
                sa = int(255 * min(1, (p - 0.85) * 10))
                draw_text_center(draw, "一个装的是金条，一个装的是公司股权证",
                                 ff(30), H - 130, GOLD, sa)

        draw._image.save(frames_dir / f"s2_{i:05d}.png")
        if i % 100 == 0:
            print(f"  S2: {i}/{n}")


def scene3(frames_dir, n):
    """数据卡片"""
    for i in range(n):
        t = i / n
        draw = ImageDraw.Draw(BG_WARM_IMG.copy())

        if t > 0.04:
            a = int(255 * min(1, (t - 0.04) * 10))
            draw_text_center(draw, "近1年回报对比", ff(46, True), 110, GOLD, a)

        # 黄金ETF卡片
        if t > 0.12:
            p = min(1, (t - 0.12) * 5)
            s = 0.3 + 0.7 * ease_out_elastic(p)
            al = min(1, p * 2)
            draw_card(draw, W // 2 - 400, 280, 400, 190, (35, 35, 55),
                      "27.2%", "黄金ETF · 华安518880", scale=s, alpha=al)

        # 黄金股ETF卡片
        if t > 0.35:
            p = min(1, (t - 0.35) * 4)
            s = 0.3 + 0.7 * ease_out_elastic(p)
            al = min(1, p * 2)
            draw_card(draw, W // 2 - 400, 550, 400, 190, (55, 18, 18),
                      "48.5%", "黄金股ETF · 永赢517520", scale=s, alpha=al)

        # 对比文字
        if t > 0.55:
            p = min(1, (t - 0.55) * 6)
            a = int(255 * p)
            draw_text_center(draw, "黄金股ETF回报是黄金ETF的 1.8 倍", ff(36, True), 830, RED, a)

        # 解释
        if t > 0.68:
            p = min(1, (t - 0.68) * 8)
            a = int(255 * p)
            draw_text_center(draw, "金矿公司自带经营杠杆", ff(26), 910, LIGHT_GRAY, a)
            draw_text_center(draw, "金价涨10%，矿企利润可能涨30%", ff(26), 960, LIGHT_GRAY, a)

        # 图表
        if t > 0.55 and RETURNS_CHART:
            ca = int(255 * min(1, (t - 0.55) * 4))
            chart = RETURNS_CHART.copy()
            chart = chart.resize((W - 80, 650), Image.LANCZOS)
            # 设置透明度
            r, g, b, a_ch = chart.split()
            a_ch = a_ch.point(lambda x: min(x, ca))
            chart = Image.merge("RGBA", (r, g, b, a_ch))
            draw._image.paste(chart, (40, 1100), chart)

        draw._image.save(frames_dir / f"s3_{i:05d}.png")
        if i % 100 == 0:
            print(f"  S3: {i}/{n}")


def scene4(frames_dir, n):
    """风险警示"""
    for i in range(n):
        t = i / n
        draw = ImageDraw.Draw(BG_RISK_IMG.copy())

        if t > 0.03:
            a = int(255 * min(1, (t - 0.03) * 10))
            draw_text_center(draw, "高回报的代价", ff(46, True), 100, RED, a)

        # 波动率行
        if t > 0.15:
            p = min(1, (t - 0.15) * 4)
            al = min(1, p * 2)
            draw_card(draw, 50, 270, 470, 170, (30, 38, 58), "28.1%", "黄金ETF · 年化波动率", alpha=al)
            draw_card(draw, W - 520, 270, 470, 170, (58, 18, 18), "42.8%", "黄金股ETF · 年化波动率", alpha=al)
            if p > 0.7:
                sa = int(255 * min(1, (p - 0.7) * 5))
                draw_text_center(draw, "波动率高 52%", ff(28), 470, LIGHT_GRAY, sa)

        # 回撤行
        if t > 0.4:
            p = min(1, (t - 0.4) * 4)
            al = min(1, p * 2)
            draw_card(draw, 50, 540, 470, 170, (30, 38, 58), "-24.9%", "黄金ETF · 最大回撤", alpha=al)
            draw_card(draw, W - 520, 540, 470, 170, (58, 18, 18), "-36.2%", "黄金股ETF · 最大回撤", alpha=al)
            if p > 0.7:
                sa = int(255 * min(1, (p - 0.7) * 5))
                draw_text_center(draw, "回撤深 11 个百分点", ff(28), 740, LIGHT_GRAY, sa)

        # 警示
        if t > 0.65:
            p = min(1, (t - 0.65) * 6)
            a = int(255 * p)
            draw_text_center(draw, "涨得猛，跌得更狠", ff(54, True), 880, RED, a)

        # 图表
        if t > 0.55 and RISK_CHART:
            ca = int(255 * min(1, (t - 0.55) * 4))
            chart = RISK_CHART.copy()
            chart = chart.resize((W - 80, 650), Image.LANCZOS)
            r, g, b, a_ch = chart.split()
            a_ch = a_ch.point(lambda x: min(x, ca))
            chart = Image.merge("RGBA", (r, g, b, a_ch))
            draw._image.paste(chart, (40, 1050), chart)

        draw._image.save(frames_dir / f"s4_{i:05d}.png")
        if i % 100 == 0:
            print(f"  S4: {i}/{n}")


def scene5(frames_dir, n):
    """结尾"""
    for i in range(n):
        t = i / n
        draw = ImageDraw.Draw(BG_DARK_IMG.copy())

        # 搜索框
        if t > 0.08:
            p = min(1, (t - 0.08) * 5)
            sy = int(380 + 30 * (1 - p))
            sa = int(255 * min(1, p * 2))

            bx_w, bx_h = 560, 76
            bx = (W - bx_w) // 2
            draw.rounded_rectangle([bx, sy, bx + bx_w, sy + bx_h],
                                   radius=38, outline=(*GOLD, sa), width=3)
            draw.text((bx + 45, sy + 18), "🔍", font=ff(30), fill=(*LIGHT_GRAY, sa))
            draw.text((bx + 100, sy + 18), "黄金ETF", font=ff(28), fill=(*LIGHT_GRAY, sa))

        # 警示
        if t > 0.3:
            p = min(1, (t - 0.3) * 5)
            a = int(255 * p)
            draw_text_center(draw, "看一眼全称，别买错了", ff(50, True), 560, RED, a)

        # 解释
        if t > 0.55:
            p = min(1, (t - 0.55) * 6)
            a = int(255 * p)
            draw_text_center(draw, '如果全称里有"黄金产业股票"几个字', ff(26), 680, LIGHT_GRAY, a)
            draw_text_center(draw, "你买的不是黄金本身，是金矿公司", ff(26), 730, LIGHT_GRAY, a)

        # 结尾品牌
        if t > 0.75:
            p = min(1, (t - 0.75) * 5)
            a = int(255 * p)
            draw_text_center(draw, "用数字，辨真相", ff(34, True), 1650, GOLD, a)
            draw_text_center(draw, "卡比兽比卡", ff(24), 1720, LIGHT_GRAY, a)

        draw._image.save(frames_dir / f"s5_{i:05d}.png")
        if i % 100 == 0:
            print(f"  S5: {i}/{n}")


def build_video(frames_dir, video_out):
    """ffmpeg 合成视频"""
    print("\n[6/6] ffmpeg 合成视频...")

    # 分别渲染5个场景为视频片段
    scene_vids = []
    for si in range(5):
        sv = frames_dir / f"scene{si+1}.mp4"
        scene_vids.append(sv)
        pattern = frames_dir / f"s{si+1}_%05d.png"
        cmd = [FFMPEG_BIN, "-y", "-framerate", str(FPS),
               "-i", str(pattern), "-c:v", "libx264",
               "-pix_fmt", "yuv420p", "-crf", "18", "-preset", "fast",
               str(sv)]
        print(f"  渲染 scene{si+1}...")
        r = subprocess.run(cmd, capture_output=True)
        if r.returncode != 0:
            print(f"  ❌ error: {r.stderr.decode()[-300:]}")

    # 拼接场景
    concat_file = frames_dir / "concat.txt"
    with open(concat_file, "w") as f:
        for sv in scene_vids:
            f.write(f"file '{sv.absolute()}'\n")

    cmd = [FFMPEG_BIN, "-y", "-f", "concat", "-safe", "0",
           "-i", str(concat_file), "-c:v", "libx264",
           "-pix_fmt", "yuv420p", "-crf", "18", "-preset", "fast",
           str(video_out)]
    print("  合成最终视频...")
    r = subprocess.run(cmd, capture_output=True)
    if r.returncode != 0:
        print(f"  ❌ concat error: {r.stderr.decode()[-500:]}")
    else:
        size_mb = video_out.stat().st_size / 1_000_000
        print(f"\n✅ 视频已生成: {video_out} ({size_mb:.1f}MB)")

    # 清理
    for sv in scene_vids:
        sv.unlink(missing_ok=True)


def main():
    global SCENE_NFRAMES

    frames_dir = OUT_DIR
    frames_dir.mkdir(exist_ok=True)

    total_frames = sum(SCENE_NFRAMES)
    print(f"配置: {W}x{H}, {FPS}fps")
    print(f"总帧数: {total_frames} ({total_frames/FPS:.0f}秒)\n")

    # 预渲染
    print("[0/6] 预加载资源和背景...")
    t0 = time.time()
    init_bgs()
    init_assets()
    print(f"  完成 ({time.time()-t0:.1f}s)\n")

    scenes = [
        ("场景1: 开场钩子", scene1),
        ("场景2: 并排对比", scene2),
        ("场景3: 数据卡片", scene3),
        ("场景4: 风险警示", scene4),
        ("场景5: 结尾号召", scene5),
    ]

    for idx, (name, func) in enumerate(scenes):
        nf = SCENE_NFRAMES[idx]
        print(f"[{idx+1}/6] {name} ({nf}帧, {nf/FPS:.0f}s)...")
        t0 = time.time()
        func(frames_dir, nf)
        elapsed = time.time() - t0
        print(f"  完成 ({elapsed:.1f}s, {nf/elapsed:.0f}fps)\n")

    build_video(frames_dir, VIDEO_OUT)


if __name__ == "__main__":
    main()
