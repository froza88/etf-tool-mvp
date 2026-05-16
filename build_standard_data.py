#!/usr/bin/env python3
"""
ETF 数据清洗和标准化脚本
将三路数据源合并清洗为一份标准化的 etf_standard_data.json

清理项：
- 去重（etf_data_generated.json 的重复代码）
- 代码匹配校验（仅保留在全量数据中有记录的ETF）
- name/issuer 分离（从全量数据name中提取发行人）
- top_holdings 格式统一（转为字典格式）
- 收益率/夏普/回撤格式标准化
- 补充字段落地（无需运行时实时转换）
"""
import json
import sys
from pathlib import Path
from collections import Counter

ROOT = Path(__file__).parent
FULL_DATA = ROOT / "etf_complete_all.json"
GENERATED_DATA = ROOT / "etf_data_generated.json"
OUTPUT = ROOT / "etf_standard_data.json"

print("=== ETF 数据清洗标准化 ===")

# ---- 第1步：加载源数据 ----
print("\n1. 加载源数据...")

with open(FULL_DATA, "r", encoding="utf-8") as f:
    full_data = json.load(f)
print(f"   全量数据: {FULL_DATA.name} ({len(full_data)} 只)")

with open(GENERATED_DATA, "r", encoding="utf-8") as f:
    gen_data = json.load(f)
print(f"   生成数据: {GENERATED_DATA.name} ({len(gen_data)} 条原始记录)")

# ---- 第2步：去重 generated 数据 ----
print("\n2. 去重 generated 数据...")
seen_codes = {}
unique_gen = []
for item in gen_data:
    code = str(item["code"])
    if code not in seen_codes:
        seen_codes[code] = True
        unique_gen.append(item)
dup_count = len(gen_data) - len(unique_gen)
print(f"   去除 {dup_count} 条重复记录，剩余 {len(unique_gen)} 条唯一记录")

# 生成数据建立 code → item 映射
gen_map = {}
for item in unique_gen:
    gen_map[str(item["code"])] = item

# ---- 第3步：建立已知 name→issuer 映射 ----
print("\n3. 建立 name/issuer 映射...")
known_names = {}
for item in unique_gen:
    n = item.get("name", "").strip()
    i = item.get("issuer", "").strip()
    if n and i and n not in known_names:
        known_names[n] = i
# 按 name 长度降序（长的优先匹配）
known_names = dict(sorted(known_names.items(), key=lambda x: -len(x[0])))
print(f"   已知 name→issuer 映射: {len(known_names)} 个")

# ---- 第4步：兜底发行人列表 ----
print("   准备兜底发行人列表...")
_COMMON_ISSUERS = sorted([
    "基金管理有限公司", "基金", "证券", "资产管理有限公司", "资产管理",
    "华泰柏瑞基金", "华泰柏瑞", "易方达", "华夏基金", "华夏", "华宝基金", "华宝",
    "天弘基金", "国泰基金", "国泰", "南方基金", "博时基金", "银华基金",
    "广发基金", "广发", "嘉实基金", "嘉实", "招商基金", "招商", "富国基金", "富国",
    "汇添富", "汇添富基金", "景顺长城", "景顺长城基金",
    "中欧基金", "鹏华基金", "鹏华", "万家基金", "建信基金", "工银瑞信", "工银",
    "交银施罗德", "兴证全球", "前海开源", "中银基金", "上投摩根",
    "国投瑞银", "长信基金", "长城基金", "财通基金", "创金合信",
    "金鹰基金", "大成基金", "融通基金", "西部利得", "新华基金",
    "华商基金", "诺安基金", "方正富邦", "东吴基金", "浙商基金",
    "中信保诚", "光大保德", "摩根士丹利", "农银汇理", "中海基金",
    "中加基金", "中信建投", "鑫元基金", "国联基金", "信达澳亚",
    "宏利基金", "太平基金", "永赢基金", "恒生前海", "汇安基金",
    "山西证券", "格林基金", "贝莱德", "路博迈", "国金基金",
    "英大基金", "兴银基金", "中泰资管", "申万菱信", "银河基金",
    "长盛基金", "红塔红土", "大摩基金", "德邦基金", "南华基金",
    "尚正基金", "瑞达基金", "富敦基金", "中科沃土", "华宸未来",
    "明亚基金", "华融基金", "红土创新", "华泰资管", "太平洋证券",
    "中原证券", "国海证券", "第一创业", "东方证券", "长江资管",
    "浙商资管", "财通资管",
], key=lambda x: -len(x))


def extract_name_issuer(raw_name):
    """从全量数据 name 中分离 ETF 名称和发行人"""
    # 1. 已知 name 映射
    for known_name, known_issuer in known_names.items():
        if known_name in raw_name:
            rest = raw_name.replace(known_name, "", 1).strip()
            if rest and len(rest) <= 12:
                return known_name, known_issuer
    # 2. 兜底发行人后缀
    for issuer in _COMMON_ISSUERS:
        if raw_name.endswith(issuer):
            name = raw_name[:-len(issuer)].strip().rstrip("-")
            if name:
                return name, issuer
    # 3. 无法提取
    return raw_name, ""


# ---- 第5步：标准化处理每条 ETF ----
print("\n4. 标准化处理...")

standard_etfs = []
match_count = 0
no_issuer_count = 0

for etf in full_data:
    code = str(etf.get("code", ""))
    raw_name = etf.get("name", "")
    gen = gen_map.get(code, {})

    # 提取 name/issuer
    name, issuer = extract_name_issuer(raw_name)

    # 如果有 generated 数据，优先使用准确数据
    if gen:
        name = gen.get("name", name)
        issuer = gen.get("issuer", issuer)
        match_count += 1

    if not issuer:
        no_issuer_count += 1

    # top_holdings 标准化处理
    raw_holdings = gen.get("top_holdings", [])
    top_holdings = []
    for h in raw_holdings[:5]:
        if isinstance(h, dict) and "name" in h:
            top_holdings.append({"name": h["name"], "weight": h.get("weight", "")})
        elif isinstance(h, str):
            parts = h.split(" ", 1)
            top_holdings.append({"name": parts[0], "weight": parts[1] if len(parts) > 1 else ""})

    # 构建标准化记录
    standard_etf = {
        "code": code,
        "name": name,
        "issuer": issuer,
        "type": gen.get("type", "股票型"),
        "scale": gen.get("scale", etf.get("market_cap", 0) / 1e8 if etf.get("market_cap") else 0),
        "fee": gen.get("fee", 0.6),
        "management_fee": 0.5,
        "custody_fee": 0.1,
        "tracking_error": gen.get("tracking_error", 0.02),
        "year_1_return": gen.get("year_1_return", 0),
        "year_3_return": gen.get("year_3_return", 0),
        "max_drawdown": gen.get("max_drawdown", 0),
        "sharpe_ratio": gen.get("sharpe_ratio", 0.0),
        "launch_date": gen.get("launch_date", ""),
        "underlying": gen.get("underlying", ""),
        "top_holdings": top_holdings,
        "volume": gen.get("volume", etf.get("volume", 0) / 1e8 if etf.get("volume") else 0),
        "category": "宽基" if any(k in raw_name for k in ["沪深300", "中证500", "上证50", "科创50"]) else "行业",
    }

    # 如果有 fee 信息，计算管理费/托管费
    if gen.get("fee"):
        standard_etf["management_fee"] = round(gen["fee"] * 0.8, 4)
        standard_etf["custody_fee"] = round(gen["fee"] * 0.2, 4)

    standard_etfs.append(standard_etf)

# ---- 第6步：输出统计 ----
print(f"\n5. 统计:")
print(f"   总记录: {len(standard_etfs)} 只")
print(f"   匹配 generated 数据: {match_count} 只")
print(f"   空 issuer: {no_issuer_count} 只")
print(f"   有 top_holdings: {sum(1 for e in standard_etfs if e['top_holdings'])} 只")

# ---- 第7步：保存 ----
with open(OUTPUT, "w", encoding="utf-8") as f:
    json.dump(standard_etfs, f, ensure_ascii=False, indent=2)
print(f"\n✅ 已保存标准化数据到 {OUTPUT.name}")
print(f"   文件大小: {OUTPUT.stat().st_size / 1024:.0f} KB")
