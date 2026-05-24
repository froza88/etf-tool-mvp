#!/usr/bin/env python3
"""
批量从 Wind API 拉取所有 ETF 数据并缓存到本地
用法: python3 fetch_wind_etf_cache.py [--resume]
"""

import json
import os
import sys
import time
import subprocess
from datetime import datetime

# 路径配置
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
WIND_SKILL_DIR = os.path.expanduser("~/.agents/skills/wind-mcp-skill")
WIND_CLI = os.path.join(WIND_SKILL_DIR, "scripts", "cli.mjs")
DATA_FILE = os.path.join(SCRIPT_DIR, "etf_standard_data_filled.json")
CACHE_FILE = os.path.join(SCRIPT_DIR, "wind_etf_cache.json")
LOG_FILE = "/tmp/fetch_wind_etf_cache.log"

# Wind API 指标名（基金/ETF 相关，待验证）
# 格式: (wind_indicator, json_field, description)
PRICE_INDICATORS = [
    ("TRACKING_ERROR", "tracking_error", "跟踪误差"),
    ("VALUATION_PERCENTILE", "valuation_percentile", "估值分位数"),
    ("NET_INFLOW_5D", "net_inflow_5d", "5日净流入额(元)"),
    ("INDIVIDUAL_HOLDER_RATIO", "individual_holder_ratio", "个人持有人占比"),
    ("INSTITUTION_HOLDER_RATIO", "institution_holder_ratio", "机构持有人占比"),
    ("HOLDER_ACCOUNT", "holder_account", "持有人户数"),
    ("FEE_RATE_SERVICE", "fee_rate_service", "服务费率"),
    ("PREMIUM_DISCOUNT", "premium_discount", "溢价折价率"),
    ("NET_INFLOW_RATIO", "net_inflow_ratio", "净流入比例"),
    ("ANNUAL_VOL", "annual_vol", "年化波动率"),
    ("MAX_DRAWDOWN", "max_drawdown", "最大回撤"),
    ("SHARPE_RATIO", "sharpe_ratio", "夏普比率"),
    ("CALMAR_RATIO", "calmar_ratio", "卡玛比率"),
]

def log(msg):
    """写日志到文件和控制台"""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")

def run_wind_api(server_type, tool_name, params):
    """调用 Wind MCP CLI，返回 (ok, result)"""
    cmd = ["node", WIND_CLI, "call", server_type, tool_name, json.dumps(params)]
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30
        )
        stdout = result.stdout.strip()
        stderr = result.stderr.strip()
        
        if result.returncode != 0:
            log(f"  CLI error (exit={result.returncode}): {stderr[:200]}")
            return False, {"error": stderr}
        
        # 解析 stdout JSON
        try:
            resp = json.loads(stdout)
        except json.JSONDecodeError:
            log(f"  JSON parse error, stdout: {stdout[:200]}")
            return False, {"error": "JSON parse error", "stdout": stdout[:200]}
        
        if not resp.get("ok", False):
            error = resp.get("error", {})
            code = error.get("code", "UNKNOWN")
            log(f"  Wind API error: {code} - {error.get('agent_action', '')[:100]}")
            return False, resp
        
        # 提取 result content
        result_content = resp.get("result", {}).get("content", [])
        if result_content and len(result_content) > 0:
            text = result_content[0].get("text", "")
            try:
                data = json.loads(text)
                return True, data
            except json.JSONDecodeError:
                log(f"  Result text not JSON: {text[:200]}")
                return True, {"raw_text": text}
        return True, {}
        
    except subprocess.TimeoutExpired:
        log(f"  Timeout calling Wind API")
        return False, {"error": "timeout"}
    except Exception as e:
        log(f"  Exception: {e}")
        return False, {"error": str(e)}

def fetch_price_indicators(wind_code, indicator_names):
    """
    批量获取价格指标（一次调用多个指标）
    返回: {indicator_name: value_or_None}
    """
    indexes_str = ",".join(indicator_names)
    params = {
        "windcode": wind_code,
        "indexes": indexes_str
    }
    ok, data = run_wind_api("fund_data", "get_fund_price_indicators", params)
    if not ok:
        return {name: None for name in indicator_names}
    
    # 解析返回数据，格式可能是 {"data": [...]} 或 {"result": [...]}
    # 尝试多种格式
    result_data = None
    if isinstance(data, dict):
        result_data = data.get("data") or data.get("result") or data.get("indicators")
    elif isinstance(data, list):
        result_data = data
    
    if not result_data:
        # 可能返回的是文本格式，尝试解析
        log(f"  Unexpected response format: {str(data)[:200]}")
        return {name: None for name in indicator_names}
    
    # 假设 result_data 是列表，每个元素包含指标名和值
    # 格式可能是 [{"indicator": "TRACKING_ERROR", "value": 0.05}, ...]
    result = {}
    for item in result_data:
        if isinstance(item, dict):
            ind_name = item.get("indicator") or item.get("index") or item.get("name")
            ind_value = item.get("value") or item.get("val") or item.get("data")
            if ind_name and ind_name in indicator_names:
                result[ind_name] = ind_value
    return result

def fetch_fund_info_nl(wind_code, etf_name, question):
    """用 NL 工具查询单个问题（备用方案）"""
    params = {
        "question": f"{wind_code}{etf_name}{question}",
        "lang": "中文"
    }
    ok, data = run_wind_api("fund_data", "get_fund_info", params)
    if not ok:
        return None
    
    # 从返回中提取数值
    if isinstance(data, dict):
        # 尝试找到数值
        for key in ["value", "result", "data", "answer"]:
            if key in data:
                return data[key]
    return data

def load_cache():
    """加载已有缓存"""
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_cache(cache):
    """保存缓存到文件"""
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)

def get_wind_code(etf):
    """构造 Wind 格式代码"""
    code = etf.get("code", "")
    exchange = etf.get("exchange", "")
    if not code:
        return None
    if exchange:
        return f"{code}.{exchange}"
    # 根据代码推导 exchange
    if code.startswith("5"):
        return f"{code}.SH"
    elif code[0] in "0123":
        return f"{code}.SZ"
    elif code.startswith("8"):
        return f"{code}.BJ"
    return f"{code}.SH"  # 默认

def main():
    resume = "--resume" in sys.argv
    
    log("=" * 60)
    log("开始批量拉取 Wind ETF 数据")
    log(f"Resume mode: {resume}")
    
    # 加载数据
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    etfs = data["etfs"]
    total = len(etfs)
    log(f"总 ETF 数: {total}")
    
    # 加载缓存
    cache = load_cache() if resume else {}
    log(f"缓存中已有 {len(cache)} 只 ETF 数据")
    
    # 获取要查询的指标名列表
    indicator_names = [ind[0] for ind in PRICE_INDICATORS]
    log(f"将查询 {len(indicator_names)} 个指标: {indicator_names}")
    
    success_count = 0
    fail_count = 0
    skip_count = 0
    
    for i, etf in enumerate(etfs):
        code = etf.get("code", "")
        name = etf.get("name", "")
        wind_code = get_wind_code(etf)
        
        if not wind_code:
            log(f"[{i+1}/{total}] {code} - 无 Wind 代码，跳过")
            skip_count += 1
            continue
        
        # 检查是否已缓存
        if wind_code in cache and resume:
            log(f"[{i+1}/{total}] {code} ({wind_code}) - 已缓存，跳过")
            skip_count += 1
            continue
        
        log(f"[{i+1}/{total}] {code} ({wind_code}) - {name[:20]}")
        
        # 方法1: 尝试 get_fund_price_indicators（批量）
        indicators_result = fetch_price_indicators(wind_code, indicator_names)
        
        if indicators_result and any(v is not None for v in indicators_result.values()):
            # 成功获取到数据
            cache[wind_code] = {
                "code": code,
                "name": name,
                "wind_code": wind_code,
                "indicators": indicators_result,
                "fetched_at": datetime.now().isoformat()
            }
            log(f"  成功获取 {sum(1 for v in indicators_result.values() if v is not None)}/{len(indicator_names)} 个指标")
            success_count += 1
        else:
            # 方法1失败，尝试方法2: get_fund_info NL（逐个问题）
            log(f"  get_fund_price_indicators 失败，尝试 NL 工具...")
            nl_data = {}
            for ind_name, json_field, desc in PRICE_INDICATORS:
                # 构造问题
                if "净流入" in desc:
                    question = f"近5日主力净流入额"
                elif "跟踪误差" in desc:
                    question = f"跟踪误差"
                elif "估值分位" in desc:
                    question = f"当前估值分位数"
                elif "个人持有" in desc:
                    question = f"个人持有人占比"
                elif "机构持有" in desc:
                    question = f"机构持有人占比"
                elif "持有人户" in desc:
                    question = f"持有人户数"
                elif "服务费率" in desc:
                    question = f"服务费率"
                else:
                    question = desc
                
                val = fetch_fund_info_nl(wind_code, name, question)
                nl_data[ind_name] = val
                time.sleep(0.5)  # 避免请求过快
            
            cache[wind_code] = {
                "code": code,
                "name": name,
                "wind_code": wind_code,
                "indicators": nl_data,
                "fetched_at": datetime.now().isoformat(),
                "method": "nl_fallback"
            }
            log(f"  NL 工具获取完成")
            success_count += 1
        
        # 每10只保存一次
        if (i + 1) % 10 == 0:
            save_cache(cache)
            log(f"  已保存缓存 ({len(cache)} 条)")
        
        # 避免请求过快
        time.sleep(1)
    
    # 最终保存
    save_cache(cache)
    
    log("=" * 60)
    log(f"完成！成功: {success_count}, 失败: {fail_count}, 跳过: {skip_count}")
    log(f"缓存文件: {CACHE_FILE}")
    log(f"日志文件: {LOG_FILE}")

if __name__ == "__main__":
    main()
