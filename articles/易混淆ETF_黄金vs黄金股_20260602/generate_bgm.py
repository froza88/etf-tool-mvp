#!/usr/bin/env python3
"""生成配乐 WAV 文件 — 舒缓金融科普风格背景音乐"""

import math, struct, wave
import numpy as np

SAMPLE_RATE = 44100
DURATION = 53  # 秒，匹配视频长度
OUTPUT = "/Users/apangduo/WorkBuddy/Claw/etf-tool-mvp/articles/易混淆ETF_黄金vs黄金股_20260602/bgm.wav"
VIDEO = "/Users/apangduo/WorkBuddy/Claw/etf-tool-mvp/articles/易混淆ETF_黄金vs黄金股_20260602/视频_黄金vs黄金股_v4.mp4"
OUTPUT_VIDEO = "/Users/apangduo/WorkBuddy/Claw/etf-tool-mvp/articles/易混淆ETF_黄金vs黄金股_20260602/视频_黄金vs黄金股_v4_有声.mp4"
FFMPEG = "/Users/apangduo/.workbuddy/binaries/python/versions/3.13.12/lib/python3.13/site-packages/imageio_ffmpeg/binaries/ffmpeg-macos-x86_64-v7.1"

total_samples = SAMPLE_RATE * DURATION
t = np.arange(total_samples, dtype=np.float64) / SAMPLE_RATE


def sine(freq, t):
    return np.sin(2 * np.pi * freq * t, dtype=np.float64)


def saw(freq, t):
    return 2 * ((freq * t) % 1) - 1


def envelope_adsr(t, attack=0.3, decay=0.1, sustain=0.7, release=0.5):
    """ADSR 包络"""
    env = np.zeros_like(t, dtype=np.float64)
    n = len(t)
    a_end = int(n * (attack / DURATION)) if attack < DURATION else n // 10
    d_end = a_end + int(n * (decay / DURATION)) if decay < DURATION else a_end + n // 20
    r_start = n - int(n * (release / DURATION))

    env[:a_end] = np.linspace(0, 1, a_end)
    env[a_end:d_end] = np.linspace(1, sustain, d_end - a_end)
    env[d_end:r_start] = sustain
    env[r_start:] = np.linspace(sustain, 0, n - r_start)
    return env


def low_pass(signal, cutoff=800, sr=SAMPLE_RATE):
    """简单一阶低通"""
    rc = 1.0 / (2 * np.pi * cutoff)
    dt = 1.0 / sr
    alpha = dt / (rc + dt)
    y = np.zeros_like(signal)
    y[0] = signal[0] * alpha
    for i in range(1, len(signal)):
        y[i] = y[i - 1] + alpha * (signal[i] - y[i - 1])
    return y


print("生成配乐中...")

# ─── Layer 1: 低频 Pad（氛围底音）───
pad = np.zeros(total_samples, dtype=np.float64)
for freq, amp in [(55, 0.08), (82.4, 0.06), (110, 0.04), (146.8, 0.03)]:
    s = sine(freq, t) * amp
    # 缓慢 LFO 调制
    lfo = 0.5 + 0.5 * sine(0.15, t)
    pad += s * lfo
pad = low_pass(pad, 400)

# ─── Layer 2: 中频和弦 Pad ───
chord = np.zeros(total_samples, dtype=np.float64)
# C大调和弦：C E G
for freq, amp in [(261.6, 0.04), (329.6, 0.03), (392, 0.025), (523.2, 0.02)]:
    s = sine(freq, t) * amp
    lfo = 0.3 + 0.7 * sine(0.12 + freq * 0.001, t)
    chord += s * lfo
chord = low_pass(chord, 1200)

# ─── Layer 3: 高音旋律（五声音阶，渐入渐出）───
pentatonic = [261.6, 293.7, 329.6, 392, 440, 523.2, 587.3, 659.3]
melody = np.zeros(total_samples, dtype=np.float64)

# 定义音符序列（音符索引, 开始时间, 时长, 力度）
# 场景1 (0-7s): 安静配角
notes = [
    (3, 1.2, 2.5, 0.3),
    (5, 3.8, 2.0, 0.25),
    # 场景2 (7-19s): 对比
    (2, 8.0, 1.5, 0.35),
    (4, 10.5, 1.5, 0.3),
    (6, 13.0, 2.0, 0.35),
    (3, 15.5, 1.0, 0.3),
    (5, 17.0, 1.5, 0.25),
    # 场景3 (19-31s): 渐强
    (1, 19.5, 1.8, 0.3),
    (3, 21.5, 1.5, 0.35),
    (5, 23.5, 2.5, 0.4),
    (7, 26.0, 2.0, 0.35),
    (4, 28.5, 1.5, 0.3),
    (6, 30.0, 1.0, 0.25),
    # 场景4 (31-43s): 紧张感
    (0, 31.5, 2.0, 0.35),
    (1, 34.0, 1.5, 0.3),
    (2, 36.5, 2.5, 0.4),
    (3, 39.0, 2.0, 0.35),
    (4, 41.5, 1.5, 0.3),
    # 场景5 (43-53s): 收尾
    (2, 44.0, 2.0, 0.3),
    (4, 46.5, 2.5, 0.35),
    (5, 49.0, 2.0, 0.25),
    (3, 51.5, 1.5, 0.2),
]

for note_idx, start, dur, vel in notes:
    freq = pentatonic[note_idx]
    start_sample = int(start * SAMPLE_RATE)
    end_sample = min(int((start + dur) * SAMPLE_RATE), total_samples)
    n = end_sample - start_sample

    note_t = np.arange(n, dtype=np.float64) / SAMPLE_RATE
    # 钢琴音色：基频 + 谐波
    sound = (
        sine(freq, note_t) * 0.6
        + sine(freq * 2, note_t) * 0.25
        + sine(freq * 3, note_t) * 0.1
        + sine(freq * 4, note_t) * 0.05
    )
    # 钢琴衰减
    note_env = np.exp(-note_t * 3.5) * 0.8 + np.exp(-note_t * 0.8) * 0.2
    sound = sound * note_env * vel

    melody[start_sample:end_sample] += sound

# ─── Layer 4: 轻柔打击（节拍）───
beat = np.zeros(total_samples, dtype=np.float64)
bpm = 80
beat_interval = 60 / bpm
# 只在每第4拍加一个轻击
for i in range(int(DURATION / beat_interval)):
    t_beat = i * beat_interval
    if t_beat > 0.5 and i % 4 == 0:  # 跳过第0拍
        start_s = int(t_beat * SAMPLE_RATE)
        n = min(int(0.3 * SAMPLE_RATE), total_samples - start_s)
        bt = np.arange(n, dtype=np.float64) / SAMPLE_RATE
        # 短促低频脉冲（模拟底鼓的柔和版）
        beat_sound = sine(60, bt) * np.exp(-bt * 20) * 0.15
        beat[start_s:start_s + n] += beat_sound

# ─── 混音 ───
mix = pad + chord + melody + beat

# 整体淡入淡出
fade_len = int(2 * SAMPLE_RATE)
mix[:fade_len] *= np.linspace(0, 1, fade_len)
mix[-fade_len:] *= np.linspace(1, 0, fade_len)

# 归一化并防止削波
peak = np.max(np.abs(mix))
if peak > 0:
    mix = mix / peak * 0.85

audio = (mix * 32767).astype(np.int16)

# ─── 写入 WAV ───
with wave.open(OUTPUT, "w") as wf:
    wf.setnchannels(1)
    wf.setsampwidth(2)
    wf.setframerate(SAMPLE_RATE)
    wf.writeframes(audio.tobytes())

print(f"✅ 配乐已生成: {OUTPUT}")

# ─── ffmpeg 混音 ───
import subprocess

cmd = [
    FFMPEG, "-y",
    "-i", VIDEO,
    "-i", OUTPUT,
    "-filter_complex",
    "[1:a]volume=0.35[a1];[0:a][a1]amix=inputs=2:duration=first:dropout_transition=2",
    "-c:v", "copy",
    "-shortest",
    OUTPUT_VIDEO,
]
print("ffmpeg 混音中...")
r = subprocess.run(cmd, capture_output=True)
if r.returncode != 0:
    stderr = r.stderr.decode()
    # 可能是视频无音轨，换个方式
    cmd2 = [
        FFMPEG, "-y",
        "-i", VIDEO,
        "-i", OUTPUT,
        "-filter_complex", "[1:a]volume=0.35[a1]",
        "-map", "0:v",
        "-map", "[a1]",
        "-c:v", "copy",
        "-shortest",
        OUTPUT_VIDEO,
    ]
    r2 = subprocess.run(cmd2, capture_output=True)
    if r2.returncode != 0:
        print(f"❌ 混音失败: {r2.stderr.decode()[-500:]}")
    else:
        print(f"✅ 有声视频已生成: {OUTPUT_VIDEO}")
else:
    print(f"✅ 有声视频已生成: {OUTPUT_VIDEO}")
