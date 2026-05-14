#!/usr/bin/env python3
"""
全量ETF数据自动更新脚本 - 处理所有1645只ETF
使用方法：
  /usr/bin/python3 /Users/apangduo/WorkBuddy/Claw/etf-tool-mvp/auto_update_all_etfs.py
"""

import subprocess
import json
import sys
import time
from pathlib import Path
from datetime import datetime

# 配置
OUTPUT_FILE = Path(__file__).parent / "etf_complete_all.json"
SKILL_PATH = Path.home() / ".workbuddy/skills/ftshare-market-data"
RUN_PY = SKILL_PATH / "run.py"

def log(msg):
    """打印日志"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {msg}", file=sys.stderr)

def run_skill(sub_skill, *args):
    """运行ftshare-market-data skill"""
    cmd = ["/usr/bin/python3", str(RUN_PY), sub_skill] + list(args)
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        
        if result.returncode != 0:
            log(f"❌ {sub_skill} 失败: {result.stderr}")
            return {}
        
        output = result.stdout.strip()
        if not output:
            return {}
        
        return json.loads(output)
    
    except Exception as e:
        log(f"❌ {sub_skill} 异常: {e}")
        return {}

def get_all_etfs(page_size=200):
    """获取所有ETF列表（全量）"""
    log(f"📊 正在获取所有ETF列表（全量）...")
    
    all_etfs = []
    page_no = 1
    
    while True:
        result = run_skill(
            "etf-list-paginated",
            "--page_no", str(page_no),
            "--page_size", str(page_size)
        )
        
        if not result or "etfs" not in result:
            break
        
        etfs = result.get("etfs", [])
        total_pages = result.get("total_pages", 0)
        total_size = result.get("total_size", 0)
        
        all_etfs.extend(etfs)
        
        log(f"  已获取 {len(all_etfs)}/{total_size} 只ETF")
        
        if page_no >= total_pages:
            break
        
        page_no += 1
        time.sleep(0.3)
    
    log(f"✅ 共获取 {len(all_etfs)} 只ETF")
    return all_etfs

def get_etf_ohlcs(symbol, span="DAY1", limit=250):
    """获取ETF K线数据"""
    result = run_skill(
        "etf-ohlcs",
        "--etf", symbol,
        "--span", span,
        "--limit", str(limit)
    )
    
    if not result or "ohlcs" not in result:
        return []
    
    return result["ohlcs"]

def calculate_max_drawdown(ohlcs):
    """计算最大回撤"""
    if not ohlcs:
        return 0.0
    
    max_drawdown = 0.0
    peak = ohlcs[0]["c"]
    
    for bar in ohlcs:
        close = bar["c"]
        if close > peak:
            peak = close
        
        drawdown = (close - peak) / peak
        if drawdown < max_drawdown:
            max_drawdown = drawdown
    
    return max_drawdown

def enrich_with_drawdown(etfs, limit=250):
    """为ETF列表添加最大回撤数据"""
    log(f"📉 正在计算 {len(etfs)} 只ETF的最大回撤...")
    log(f"⚠️  预计耗时：{len(etfs) * 0.9 / 60:.1f} 分钟")
    
    success_count = 0
    fail_count = 0
    
    for i, etf in enumerate(etfs, 1):
        symkey = etf.get("symkey", "")
        
        if not symkey:
            fail_count += 1
            continue
        
        # 每10只显示一次进度
        if i % 10 == 0:
            log(f"  进度：{i}/{len(etfs)} ({i/len(etfs)*100:.1f}%), 成功：{success_count}, 失败：{fail_count}")
        
        # 获取K线数据
        ohlcs = get_etf_ohlcs(symkey, span="DAY1", limit=limit)
        
        if not ohlcs:
            fail_count += 1
            etf["max_drawdown"] = 0.0
            time.sleep(0.1)
            continue
        
        # 计算最大回撤
        max_drawdown = calculate_max_drawdown(ohlcs)
        etf["max_drawdown"] = max_drawdown
        success_count += 1
        
        time.sleep(0.2)  # 避免请求过快
    
    log(f"✅ 最大回撤计算完成：成功 {success_count}/{len(etfs)}, 失败 {fail_count}/{len(etfs)}")
    return etfs

def main():
    log("🚀 开始自动更新全量ETF数据...")
    start_time = time.time()
    
    # 检查依赖
    if not RUN_PY.exists():
        log(f"❌ 找不到run.py: {RUN_PY}")
        sys.exit(1)
    
    # 步骤1：获取所有ETF（实时数据 + 多周期收益率）
    step1_start = time.time()
    all_etfs = get_all_etfs(page_size=200)
    
    step1_time = time.time() - step1_start
    log(f"⏱️ 步骤1耗时: {step1_time:.1f}秒 ({step1_time/60:.1f}分钟)")
    
    # 步骤2：计算最大回撤
    step2_start = time.time()
    enriched_etfs = enrich_with_drawdown(all_etfs, limit=250)
    
    step2_time = time.time() - step2_start
    log(f"⏱️ 步骤2耗时: {step2_time:.1f}秒 ({step2_time/60:.1f}分钟)")
    
    # 保存结果
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(enriched_etfs, f, ensure_ascii=False, indent=2)
    
    total_time = time.time() - start_time
    log(f"✅ 数据已保存到: {OUTPUT_FILE}")
    log(f"⏱️ 总耗时: {total_time:.1f}秒 ({total_time/60:.1f}分钟)")
    
    # 打印统计信息
    log(f"\n📊 数据字段说明:")
    log(f"  实时数据: close, open, high, low, volume, turnover...")
    log(f"  多周期收益率: change_rate_5d/10d/20d/60d/6m/1y/2y/3y/ytd")
    log(f"  最大回撤: max_drawdown")
    log(f"  市值数据: market_cap_total, market_cap_circulating")
    log(f"  交易数据: turnover_rate, amplitude, order_ratio...")

if __name__ == "__main__":
    main()
