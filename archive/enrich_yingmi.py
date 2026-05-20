#!/usr/bin/env python3
"""
用盈米 GetBatchFundPerformance API 批量获取ETF指标（收益率/波动率/夏普/回撤）
优化版：本地缓存 + 增量更新 + 断点续跑 + 原始响应保存
"""
import sys, os, json, time, subprocess, argparse

ROOT = os.path.dirname(os.path.abspath(__file__))
BIN = "/Users/apangduo/.workbuddy/binaries/node/versions/22.12.0/bin"
BATCH_SIZE = 12  # 降低批量大小避免限流
CACHE_DIR = os.path.join(ROOT, ".yingmi_cache")
PROGRESS_FILE = os.path.join(ROOT, ".yingmi_progress.json")
OUTPUT_FILE = os.path.join(ROOT, "etf_yingmi_metrics.json")
RAW_LOG_FILE = os.path.join(ROOT, ".yingmi_raw_responses.jsonl")

# 字段映射配置（支持多个可能的字段名）
FIELD_MAP = {
    "year_1_return": ["收益能力", "年化收益率", "收益率"],
    "year_3_return": ["收益能力", "年化收益率", "收益率"],
    "max_drawdown": ["抗回撤能力", "最大回撤", "回撤"],
    "sharpe_ratio": ["投资性价比", "夏普比率", "夏普", "性价比"],
    "annual_vol_1y": ["抗波动能力", "年化波动率", "波动率"],
    "annual_vol_3y": ["抗波动能力", "年化波动率", "波动率"],
    "sharpe_3y": ["投资性价比", "夏普比率", "夏普", "性价比"],
    "dd_3y": ["抗回撤能力", "最大回撤", "回撤"],
}

def get_exchange(code):
    return 'XSHG' if str(code).startswith('5') else 'XSHE'

def load_progress():
    """加载已处理的code列表"""
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, encoding="utf-8") as f:
            return set(json.load(f))
    return set()

def save_progress(codes):
    """保存已处理的code列表"""
    with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
        json.dump(list(codes), f, ensure_ascii=False)

def load_cache(code):
    """加载单只ETF的缓存"""
    cache_file = os.path.join(CACHE_DIR, f"{code}.json")
    if os.path.exists(cache_file):
        with open(cache_file, encoding="utf-8") as f:
            return json.load(f)
    return None

def save_cache(code, raw_response):
    """保存单只ETF的原始响应"""
    os.makedirs(CACHE_DIR, exist_ok=True)
    cache_file = os.path.join(CACHE_DIR, f"{code}.json")
    with open(cache_file, "w", encoding="utf-8") as f:
        json.dump(raw_response, f, ensure_ascii=False)

def save_raw_log(batch_idx, raw_text):
    """保存原始响应到日志文件（用于调试）"""
    with open(RAW_LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps({"batch": batch_idx, "time": time.strftime("%Y-%m-%d %H:%M:%S"), "raw": raw_text}, ensure_ascii=False))
        f.write("\n")

def extract_field(metrics_dict, field_names):
    """从指标字典中提取字段，支持多个可能的字段名"""
    for name in field_names:
        if name in metrics_dict:
            val = metrics_dict[name]
            if val and val != 0:
                return val
    return 0

def parse_fund_data(fund):
    """解析单只ETF的API返回数据"""
    code = fund.get("fundCode", "")
    if fund.get("error") or not code:
        return None
    
    da = fund.get("data", {})
    metrics = da.get("metricsAnalyzes", [])
    
    entry = {}
    
    # 调试：打印所有可用的字段名（仅第一次）
    debug_printed = False
    
    for period in ["oneYear", "twoYear", "threeYear"]:
        pm = next((m for m in metrics if m["stageType"] == period), None)
        if pm and pm.get("isValid", False):
            ms = {}
            for mm in pm.get("metrics", []):
                title = mm.get("title", "")
                vt = mm.get("metricsValueText", "")
                if vt:
                    try:
                        ms[title] = float(vt.replace("%", ""))
                    except:
                        ms[title] = 0
            entry[period] = ms
            
            # 调试输出
            if not debug_printed:
                debug_printed = True
                print(f"  调试 [{code}] {period} 可用字段: {list(ms.keys())}")
        else:
            entry[period] = {}
    
    result = {
        "year_1_return": extract_field(entry.get("oneYear", {}), FIELD_MAP["year_1_return"]),
        "year_3_return": extract_field(entry.get("threeYear", {}), FIELD_MAP["year_3_return"]),
        "max_drawdown": extract_field(entry.get("oneYear", {}), FIELD_MAP["max_drawdown"]),
        "sharpe_ratio": extract_field(entry.get("oneYear", {}), FIELD_MAP["sharpe_ratio"]),
        "annual_vol_1y": extract_field(entry.get("oneYear", {}), FIELD_MAP["annual_vol_1y"]),
        "annual_vol_3y": extract_field(entry.get("threeYear", {}), FIELD_MAP["annual_vol_3y"]),
        "sharpe_3y": extract_field(entry.get("threeYear", {}), FIELD_MAP["sharpe_3y"]),
        "dd_3y": extract_field(entry.get("threeYear", {}), FIELD_MAP["dd_3y"]),
        "_raw_fields_1y": list(entry.get("oneYear", {}).keys()),
        "_raw_fields_3y": list(entry.get("threeYear", {}).keys()),
    }
    
    return code, result

def call_api(batch):
    """调用盈米API"""
    codes_json = json.dumps(batch, ensure_ascii=False)
    cmd = f'export PATH="$PATH:{BIN}" && yingmi-skill-cli mcp call GetBatchFundPerformance --input \'{{"fundCodes":{codes_json}}}\' 2>/dev/null'
    
    for attempt in range(5):
        try:
            r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
            raw = r.stdout.strip()
            
            # 保存原始响应（用于调试）
            save_raw_log(0, raw[:5000])  # 限制长度避免日志过大
            
            if not (raw.startswith("{") or raw.startswith("[")):
                # 可能是限流或其他错误
                if "429" in raw or "限流" in raw:
                    print(f"  ⚠️ 触发限流(429)，暂停60秒...")
                    time.sleep(60)
                    continue
                if attempt < 4:
                    wait = 5 + attempt * 3
                    print(f"  重试({attempt+1}/5): 等待{wait}s")
                    time.sleep(wait)
                    continue
                return None
            
            return json.loads(raw)
        except Exception as e:
            if attempt < 4:
                time.sleep(5 + attempt * 3)
                continue
            print(f"  API调用失败: {e}")
            return None
    
    return None

def main():
    parser = argparse.ArgumentParser(description="获取盈米ETF指标数据")
    parser.add_argument("--force", action="store_true", help="强制刷新（忽略缓存）")
    parser.add_argument("--batch-size", type=int, default=BATCH_SIZE, help="每批ETF数量")
    args = parser.parse_args()
    
    # 加载ETF列表
    with open(os.path.join(ROOT, "etf_standard_data.json"), encoding="utf-8") as f:
        data = json.load(f)
    all_codes = [e["code"] for e in data]
    print(f"ETF总数: {len(all_codes)}")
    
    # 加载进度
    processed = load_progress()
    print(f"已缓存: {len(processed)}")
    
    # 确定需要请求的codes
    if args.force:
        codes_to_fetch = all_codes
        processed = set()
        print("模式: 强制刷新（忽略缓存）")
    else:
        codes_to_fetch = [c for c in all_codes if c not in processed]
        print(f"模式: 增量更新（需请求 {len(codes_to_fetch)}/{len(all_codes)}）")
    
    if not codes_to_fetch:
        print("所有ETF已有缓存，无需请求")
        # 直接合并缓存并退出
        merge_and_save()
        return
    
    # 分批处理
    batch_size = args.batch_size
    batches = [codes_to_fetch[i:i+batch_size] for i in range(0, len(codes_to_fetch), batch_size)]
    
    results = {}
    ok = fail = 0
    
    for bi, batch in enumerate(batches):
        print(f"\n批次 {bi+1}/{len(batches)} ({len(batch)}只)")
        
        funds = call_api(batch)
        if funds is None:
            print(f"  ❌ 批次失败，跳过 {len(batch)} 只")
            fail += len(batch)
            continue
        
        for fund in funds:
            parsed = parse_fund_data(fund)
            if parsed is None:
                fail += 1
                continue
            
            code, result = parsed
            results[code] = result
            processed.add(code)
            ok += 1
            
            # 保存缓存
            save_cache(code, fund)
        
        # 保存进度
        save_progress(processed)
        
        # 打印进度
        if (bi + 1) % 5 == 0 or bi == len(batches) - 1:
            print(f"  进度: {bi+1}/{len(batches)} 成功={ok} 失败={fail} 累计缓存={len(processed)}")
        
        # 延迟避免限流
        time.sleep(3)
    
    print(f"\n本批次完成! 成功={ok} 失败={fail}")
    
    # 合并并保存
    merge_and_save()

def merge_and_save():
    """合并所有缓存并保存到最终文件"""
    print("\n合并缓存数据...")
    
    merged = {}
    
    # 加载已有输出（保留旧数据）
    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE, encoding="utf-8") as f:
            merged = json.load(f)
        print(f"  加载已有数据: {len(merged)} 条")
    
    # 加载所有缓存
    if os.path.exists(CACHE_DIR):
        cache_files = [f for f in os.listdir(CACHE_DIR) if f.endswith(".json")]
        print(f"  缓存文件数: {len(cache_files)}")
        
        for cf in cache_files:
            code = cf.replace(".json", "")
            cache_file = os.path.join(CACHE_DIR, cf)
            with open(cache_file, encoding="utf-8") as f:
                fund = json.load(f)
            
            parsed = parse_fund_data(fund)
            if parsed:
                _, result = parsed
                merged[code] = result
    
    # 保存
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(merged, f, ensure_ascii=False)
    
    print(f"  保存完成: {len(merged)} 条 -> {OUTPUT_FILE}")
    
    # 统计
    sharpe_count = sum(1 for v in merged.values() if v.get("sharpe_ratio", 0) != 0)
    print(f"  sharpe_ratio 非零: {sharpe_count}/{len(merged)}")

if __name__ == "__main__":
    main()
