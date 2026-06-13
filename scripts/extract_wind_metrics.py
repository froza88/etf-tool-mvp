#!/usr/bin/env python3
"""
从 Wind 缓存 JSON 文件中批量提取全部 ETF 的基金级核心指标。
输出: /tmp/wind_enrichment.json
"""
import os, json, glob, re
from collections import OrderedDict

WIND_DIR = "/Users/apangduo/WorkBuddy/Claw/etf-tool-mvp/data/wind_full"
OUTPUT = "/tmp/wind_enrichment.json"

# === 30篇报告涉及的47只唯一ETF ===
# (名称, 代码, 所属分类)
ETF_LIST = [
    # 一、名字陷阱 (8篇, 16只)
    ("黄金ETF", "518880", "名字陷阱"),
    ("黄金股ETF", "517520", "名字陷阱"),
    ("消费ETF", "159928", "名字陷阱"),
    ("消费电子ETF", "159732", "名字陷阱"),
    ("医药ETF", "512010", "名字陷阱"),
    ("医疗ETF", "512170", "名字陷阱"),
    ("电力ETF", "159611", "名字陷阱"),
    ("电网设备ETF", "516420", "名字陷阱"),
    ("新能源ETF", "516160", "名字陷阱"),
    ("新能源车ETF", "515030", "名字陷阱"),
    ("军工ETF", "512660", "名字陷阱"),
    ("军工龙头ETF", "512710", "名字陷阱"),
    ("农业ETF", "159825", "名字陷阱"),
    ("养殖ETF", "516760", "名字陷阱"),
    ("煤炭ETF", "515220", "名字陷阱"),
    ("钢铁ETF", "515210", "名字陷阱"),
    # 二、市场错位 (7篇, 12只)
    ("创新药ETF", "159992", "市场错位"),
    ("港股创新药ETF", "513120", "市场错位"),
    ("芯片ETF", "159995", "市场错位"),
    ("科创芯片ETF", "588200", "市场错位"),
    ("AI ETF", "159819", "市场错位"),
    ("科创AI ETF", "588760", "市场错位"),
    ("互联网ETF", "513050", "市场错位"),
    ("港股通互联网ETF", "513040", "市场错位"),
    ("恒生科技ETF", "513180", "市场错位"),
    ("港股通科技ETF", "513360", "市场错位"),
    ("纳指ETF", "513100", "市场错位"),
    ("纳指100ETF", "159696", "市场错位"),
    # 三、策略变体 (6篇, 10只)
    ("红利ETF", "510880", "策略变体"),
    ("红利低波ETF", "512890", "策略变体"),
    ("沪深300ETF", "510300", "策略变体"),
    ("沪深300增强ETF", "510310", "策略变体"),
    ("创业板ETF", "159915", "策略变体"),
    ("创业板50ETF", "159949", "策略变体"),
    ("科创50ETF", "588000", "策略变体"),
    ("科创100ETF", "588190", "策略变体"),
    ("中证红利ETF", "515080", "策略变体"),
    ("碳中和ETF", "560550", "策略变体"),
    # 四、宽基迷思 (5篇, 7只)
    ("A500ETF", "563500", "宽基迷思"),
    ("中证500ETF", "510500", "宽基迷思"),
    ("中证1000ETF", "512100", "宽基迷思"),
    ("科创创业50ETF", "159781", "宽基迷思"),
    ("上证50ETF", "510050", "宽基迷思"),
    ("深证100ETF", "159901", "宽基迷思"),
    ("上证综指ETF", "510210", "宽基迷思"),
    # 五、跨境 (2只)
    ("日经225ETF", "513880", "跨境"),
    ("东证指数ETF", "513800", "跨境"),
]

def find_wind_file(code):
    """按代码查找最新 Wind 缓存文件"""
    pattern = os.path.join(WIND_DIR, f"{code}_*.json")
    files = glob.glob(pattern)
    if not files:
        return None
    # 按日期排序，取最新
    files.sort()
    return files[-1]

def safe_float(v):
    """安全转换为浮点数"""
    if v is None or v == '' or v == '-':
        return None
    try:
        return float(v)
    except (ValueError, TypeError):
        return None

def parse_wind_file(filepath):
    """解析单个 Wind 缓存文件，提取基金级核心指标"""
    try:
        with open(filepath, 'r') as f:
            raw = json.load(f)
        inner = json.loads(raw['content'][0]['text'])
        blocks = inner['data']['data']

        result = {}
        
        # Block 0: 基本资料
        if len(blocks) > 0 and blocks[0]['rows']:
            row = blocks[0]['rows'][0]
            cols = [c['name'] for c in blocks[0]['columns']]
            for c, v in zip(cols, row):
                if c == '证券简称': result['name'] = v
                elif c == '基金全称': result['full_name'] = v
                elif c == '基金管理人': result['manager'] = v
                elif c == '基金成立日': result['inception_date'] = str(v)[:10] if v else None
                elif c == '上市日期': result['list_date'] = str(v)[:10] if v else None
                elif c == '投资类型_二级分类': result['fund_type'] = v
        
        # Block 1: 规模份额
        if len(blocks) > 1 and blocks[1]['rows']:
            row = blocks[1]['rows'][0]
            cols = [c['name'] for c in blocks[1]['columns']]
            for c, v in zip(cols, row):
                if c == '基金规模合计': result['aum_yi'] = safe_float(v)
                elif c == '场内流通份额': result['circulating_shares'] = safe_float(v)
        
        # Block 2: 费率
        if len(blocks) > 2 and blocks[2]['rows']:
            row = blocks[2]['rows'][0]
            cols = [c['name'] for c in blocks[2]['columns']]
            for c, v in zip(cols, row):
                if '管理费率' in c: result['mgmt_fee_pct'] = safe_float(v)
                elif '托管费率' in c: result['custodian_fee_pct'] = safe_float(v)
                elif '销售服务费率' in c: result['service_fee_pct'] = safe_float(v)
        
        # Block 3: 净值
        if len(blocks) > 3 and blocks[3]['rows']:
            row = blocks[3]['rows'][0]
            cols = [c['name'] for c in blocks[3]['columns']]
            for c, v in zip(cols, row):
                if c == '最新单位净值': result['nav'] = safe_float(v)
                elif c == '最新累计单位净值': result['nav_cumulative'] = safe_float(v)
                elif c == '最新日回报': result['daily_return_pct'] = safe_float(v)
                elif c == '最新复权单位净值': result['nav_adjusted'] = safe_float(v)
                elif c == '单位净值币种': result['nav_currency'] = v
        
        # Block 4: 风险指标（最多23列）
        if len(blocks) > 4 and blocks[4]['rows']:
            row = blocks[4]['rows'][0]
            cols = [c['name'] for c in blocks[4]['columns']]
            for c, v in zip(cols, row):
                val = safe_float(v)
                if val is not None:
                    key = c.replace('(', '_').replace(')', '').replace(' ', '_')
                    result[key] = val
        
        return result
    except Exception as e:
        return {"_error": str(e), "_file": filepath}

def main():
    results = OrderedDict()
    missing = []
    errors = []
    
    for name, code, category in ETF_LIST:
        filepath = find_wind_file(code)
        if filepath is None:
            missing.append((code, name))
            results[code] = {
                "name": name,
                "category": category,
                "_error": "NO_WIND_CACHE",
                "code": code
            }
            continue
        
        parsed = parse_wind_file(filepath)
        parsed["code"] = code
        parsed["category"] = category
        parsed["_source_date"] = os.path.basename(filepath).replace(code + "_", "").replace(".json", "")
        
        if "_error" in parsed:
            errors.append((code, name, parsed["_error"]))
        
        results[code] = parsed
    
    # Summary
    total = len(ETF_LIST)
    cached = total - len(missing)
    error_count = len(errors)
    
    summary = {
        "_meta": {
            "extract_time": "2026-06-13",
            "total_etfs": total,
            "wind_cached": cached,
            "wind_missing": len(missing),
            "parse_errors": error_count,
            "available_metrics": [
                "aum_yi (基金规模_亿元)",
                "mgmt_fee_pct (管理费率_%)", 
                "custodian_fee_pct (托管费率_%)",
                "nav (最新净值)",
                "daily_return_pct (日回报_%)",
                "近1年/2年/3年: 夏普比率, 年化波动率, 最大回撤, 跟踪误差, 贝塔, 阿尔法, 信息比率"
            ],
            "missing_codes": [f"{code}({name})" for code, name in missing],
            "error_codes": [f"{code}({name}): {err}" for code, name, err in errors]
        }
    }
    
    # Merge meta into results
    output = {"_meta": summary["_meta"]}
    output["etfs"] = results
    
    with open(OUTPUT, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    
    print(f"\n{'='*60}")
    print(f"Wind 缓存指标提取完成")
    print(f"{'='*60}")
    print(f"  总 ETF 数: {total}")
    print(f"  有 Wind 缓存: {cached}")
    print(f"  缺 Wind 缓存: {len(missing)}")
    if missing:
        for code, name in missing:
            print(f"    ❌ {code} {name}")
    print(f"  解析异常: {error_count}")
    if errors:
        for code, name, err in errors:
            print(f"    ⚠️ {code} {name}: {err}")
    print(f"\n  输出文件: {OUTPUT}")
    print(f"  文件大小: {os.path.getsize(OUTPUT):,} bytes")
    
    # Print sample for 518880
    if "518880" in results:
        r = results["518880"]
        print(f"\n{'='*60}")
        print(f"样本: {r.get('name', '?')} ({r['code']})")
        print(f"{'='*60}")
        for k, v in r.items():
            if not k.startswith("_"):
                print(f"  {k}: {v}")

if __name__ == "__main__":
    main()
