#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WeStock 每日行情更新模块
===========================
用 WeStock Data CLI 补充每日行情数据（收盘价、涨跌幅、成交量等）

用途：
  在 pipeline.py 之后运行，补充 AKShare 可能遗漏的行情字段

用法：
  python wequote_daily.py           # 全部更新
  python wequote_daily.py --dry-run  # 不写入，只报告
  python wequote_daily.py --sample 10  # 只更新前10个（测试）
  python wequote_daily.py --fields close,change_pct,volume  # 只更新指定字段

数据源：
  - westock-data quote          → 实时行情（close, change_pct, volume 等）
  - westock-data etf            → ETF 详情（费率和季度数据）

频率：
  每日行情：每天运行（凌晨3点，收盘后）
  季度信息：每周运行（费率、基准等不会每天变）
"""

import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).parent
DATA_FILE = ROOT / "etf_standard_data.json"
CLI = "/Users/apangduo/.workbuddy/plugins/marketplaces/cb_teams_marketplace/plugins/finance-data/skills/westock-data/scripts/index.js"

BATCH_SIZE = 10  # WeStock 批量查询上限
SLEEP_BETWEEN_BATCHES = 1.5  # 秒


def log(msg, end="\n"):
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] {msg}", end=end)


def load_data(filepath):
    """加载 ETF 标准数据"""
    with open(filepath, "r", encoding="utf-8") as f:
        raw = json.load(f)
    if isinstance(raw, dict) and "etfs" in raw:
        return raw, raw["etfs"]
    return raw, raw


def save_data(data, filepath):
    """保存数据"""
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    log(f"  已保存 {filepath}")


def get_market_prefix(code):
    """根据 ETF 代码猜测市场前缀（沪市/深市）"""
    code_str = str(code)
    # 沪市：以 5、68 开头
    if code_str.startswith(("5", "68")):
        return "sh"
    # 深市：以 0、1、159 开头
    if code_str.startswith(("0", "1", "159")):
        return "sz"
    # 默认沪市
    return "sh"


def run_westock_quote(codes_batch):
    """
    调用 WeStock CLI 查询实时行情
    返回：dict {code: {close, change_pct, volume, ...}}
    """
    batch_str = ",".join(codes_batch)
    cmd = ["node", CLI, "quote", batch_str]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            log(f"  ❌ quote 失败: {result.stderr[:100]}")
            return {}
        return parse_westock_table(result.stdout)
    except subprocess.TimeoutExpired:
        log(f"  ⏱️ quote 超时 ({len(codes_batch)} 个)")
        return {}
    except Exception as e:
        log(f"  ❌ quote 异常: {e}")
        return {}


def run_westock_etf(codes_batch):
    """
    调用 WeStock CLI 查询 ETF 详情（费率、基准等）
    返回：dict {code: {managementFee, custodyFee, serviceFee, trackIndexName, ...}}
    """
    batch_str = ",".join(codes_batch)
    cmd = ["node", CLI, "etf", batch_str]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if result.returncode != 0:
            log(f"  ❌ etf 失败: {result.stderr[:100]}")
            return {}
        return parse_westock_table(result.stdout)
    except subprocess.TimeoutExpired:
        log(f"  ⏱️ etf 超时 ({len(codes_batch)} 个)")
        return {}
    except Exception as e:
        log(f"  ❌ etf 异常: {e}")
        return {}


def parse_westock_table(markdown_text):
    """
    解析 WeStock CLI 返回的 Markdown 表格
    返回：dict {code: {field: value, ...}}
    """
    lines = markdown_text.strip().split("\n")
    results = {}
    
    # 找表格起始行
    table_start = -1
    for i, line in enumerate(lines):
        if line.startswith("|"):
            # 确认是否是表头行（包含 code 或 代码 列）
            if "code" in line.lower() or "代码" in line:
                table_start = i
                break
    
    if table_start == -1:
        return {}
    
    # 解析表头
    headers = [h.strip() for h in lines[table_start].split("|")[1:-1]]
    
    # 跳过分隔线，解析数据行
    data_start = table_start + 2
    for line in lines[data_start:]:
        if not line.startswith("|"):
            break
        values = [v.strip() for v in line.split("|")[1:-1]]
        if len(values) == len(headers):
            row = dict(zip(headers, values))
            # 提取代码
            code = row.get("code", "")
            if code:
                results[code] = row
    
    return results


def update_quote_fields(etf_entry, wequote_data):
    """
    更新每日行情字段
    映射：WeStock quote → etf_standard_data.json
    """
    updates = {}
    
    # 收盘价
    if "closePrice" in wequote_data:
        try:
            updates["close"] = float(wequote_data["closePrice"])
        except (ValueError, TypeError):
            pass
    elif "close" in wequote_data:
        try:
            updates["close"] = float(wequote_data["close"])
        except (ValueError, TypeError):
            pass
    
    # 前收盘价 ← 用当前 close 作为下一次的 prev_close（收盘后）
    # 注意：如果是盘中运行，prev_close 应该是上一交易日的 close
    
    # 涨跌幅%
    if "changePct" in wequote_data:
        try:
            updates["change_pct"] = float(wequote_data["changePct"])
        except (ValueError, TypeError):
            pass
    elif "change_pct" in wequote_data:
        try:
            updates["change_pct"] = float(wequote_data["change_pct"])
        except (ValueError, TypeError):
            pass
    elif "涨跌幅" in wequote_data:
        try:
            updates["change_pct"] = float(wequote_data["涨跌幅"])
        except (ValueError, TypeError):
            pass
    
    # 涨跌率
    if "change_rate" in wequote_data:
        try:
            updates["change_rate"] = float(wequote_data["change_rate"])
        except (ValueError, TypeError):
            pass
    
    # 成交量
    if "volume" in wequote_data:
        try:
            updates["volume"] = float(wequote_data["volume"])
        except (ValueError, TypeError):
            pass
    
    # 应用到数据
    for key, value in updates.items():
        etf_entry[key] = value
    
    return len(updates)


def update_etf_fields(etf_entry, wequote_data):
    """
    更新 ETF 详情字段（费率、基准、溢价折价等）
    映射：WeStock etf → etf_standard_data.json
    """
    updates = {}
    
    # 托管人
    if "trusteeInstitution" in wequote_data:
        updates["custodian"] = wequote_data["trusteeInstitution"]
    
    # 管理费率
    if "managementFee" in wequote_data:
        try:
            updates["fee_rate_management"] = float(wequote_data["managementFee"])
        except (ValueError, TypeError):
            pass
    
    # 托管费率
    if "custodyFee" in wequote_data:
        try:
            updates["fee_rate_custody"] = float(wequote_data["custodyFee"])
        except (ValueError, TypeError):
            pass
    
    # 服务费率
    if "serviceFee" in wequote_data:
        try:
            updates["fee_rate_service"] = float(wequote_data["serviceFee"])
        except (ValueError, TypeError):
            pass
    
    # 总费率 = 管理费率 + 托管费率 + 服务费率
    mgmt = wequote_data.get("managementFee")
    cust = wequote_data.get("custodyFee")
    svc = wequote_data.get("serviceFee")
    if any([mgmt, cust, svc]):
        try:
            total = sum(float(x) for x in [mgmt, cust, svc] if x)
            if total > 0:
                updates["fee_rate"] = total
        except (ValueError, TypeError):
            pass
    
    # 溢价折价
    if "disc" in wequote_data:
        try:
            updates["premium_discount"] = float(wequote_data["disc"])
        except (ValueError, TypeError):
            pass
    
    # 业绩基准
    if "trackIndexName" in wequote_data:
        updates["benchmark"] = wequote_data["trackIndexName"]
    
    # 3 年回报
    if "return3Y" in wequote_data:
        try:
            updates["year_3_return"] = float(wequote_data["return3Y"])
            updates["annual_3y"] = float(wequote_data["return3Y"])
        except (ValueError, TypeError):
            pass
    
    # 应用到数据
    for key, value in updates.items():
        # 只更新当前为空或 None 的字段
        if etf_entry.get(key) is None or etf_entry.get(key) == "":
            etf_entry[key] = value
        elif isinstance(value, (int, float)) and etf_entry.get(key) == 0:
            etf_entry[key] = value
    
    return len(updates)


def main():
    import argparse
    parser = argparse.ArgumentParser(description="WeStock 每日行情更新")
    parser.add_argument("--dry-run", action="store_true", help="不写入文件，只报告")
    parser.add_argument("--sample", type=int, default=0, help="只更新前 N 个 ETF（测试用）")
    parser.add_argument("--fields", type=str, default="all", 
                       help="更新字段：all, quote_only, etf_only, 或逗号分隔字段列表")
    parser.add_argument("--batch-size", type=int, default=BATCH_SIZE, help="批量大小")
    args = parser.parse_args()
    
    # ============ 1. 加载数据 ============
    log("=" * 60)
    log("WeStock 每日行情更新")
    log("=" * 60)
    
    raw_data, etfs = load_data(DATA_FILE)
    total = len(etfs)
    log(f"已加载 {total} 个 ETF")
    
    if args.dry_run:
        log("⚠️ DRY RUN 模式 - 不会写入文件")
    
    if args.sample:
        etfs = etfs[:args.sample]
        log(f"⚠️ 测试模式 - 只处理前 {len(etfs)} 个")
    
    # ============ 2. 准备代码列表 ============
    codes = []
    code_to_etf = {}
    
    for i, etf in enumerate(etfs):
        code = str(etf.get("code", ""))
        if not code:
            continue
        market = get_market_prefix(code)
        wcode = f"{market}{code}"
        codes.append(wcode)
        code_to_etf[wcode] = i
    
    log(f"准备查询 {len(codes)} 个 ETF 代码")
    
    # ============ 3. 批量查询行情 ============
    if args.fields in ("all", "quote_only"):
        log("\n📊 阶段 1/2: 查询实时行情（quote）...")
        quote_updated = 0
        
        for i in range(0, len(codes), args.batch_size):
            batch = codes[i:i + args.batch_size]
            batch_num = i // args.batch_size + 1
            total_batches = (len(codes) + args.batch_size - 1) // args.batch_size
            
            log(f"  批次 {batch_num}/{total_batches}: {len(batch)} 个...", end=" ")
            wequote_data = run_westock_quote(batch)
            
            batch_updated = 0
            for wcode, wdata in wequote_data.items():
                idx = code_to_etf.get(wcode)
                if idx is not None:
                    n = update_quote_fields(etfs[idx], wdata)
                    batch_updated += n
            
            quote_updated += batch_updated
            log(f"更新 {batch_updated} 个字段")
            
            # 暂停，避免触发限流
            if i + args.batch_size < len(codes):
                time.sleep(SLEEP_BETWEEN_BATCHES)
        
        log(f"  总计：更新 {quote_updated} 个行情字段")
    
    # ============ 4. 批量查询 ETF 详情（季度信息） ============
    if args.fields in ("all", "etf_only"):
        log("\n📊 阶段 2/2: 查询 ETF 详情（etf）...")
        etf_updated = 0
        
        for i in range(0, len(codes), args.batch_size):
            batch = codes[i:i + args.batch_size]
            batch_num = i // args.batch_size + 1
            total_batches = (len(codes) + args.batch_size - 1) // args.batch_size
            
            log(f"  批次 {batch_num}/{total_batches}: {len(batch)} 个...", end=" ")
            wequote_data = run_westock_etf(batch)
            
            batch_updated = 0
            for wcode, wdata in wequote_data.items():
                idx = code_to_etf.get(wcode)
                if idx is not None:
                    n = update_etf_fields(etfs[idx], wdata)
                    batch_updated += n
            
            etf_updated += batch_updated
            log(f"更新 {batch_updated} 个字段")
            
            if i + args.batch_size < len(codes):
                time.sleep(SLEEP_BETWEEN_BATCHES)
        
        log(f"  总计：更新 {etf_updated} 个 ETF 字段")
    
    # ============ 5. 保存 ============
    if not args.dry_run:
        log(f"\n💾 正在保存...")
        save_data(raw_data, DATA_FILE)
    
    # ============ 6. 报告 ============
    log("\n" + "=" * 60)
    log("更新完成！")
    log("=" * 60)
    
    # 统计更新后的完整度
    if args.fields != "quote_only":
        key_fields = ["custodian", "fee_rate", "benchmark", "premium_discount"]
        for field in key_fields:
            count = sum(1 for e in etfs if e.get(field))
            pct = count / total * 100 if total > 0 else 0
            log(f"  {field}: {count}/{total} ({pct:.1f}%)")


if __name__ == "__main__":
    main()