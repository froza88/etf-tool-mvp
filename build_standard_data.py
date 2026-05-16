#!/usr/bin/env python3
"""
ETF 数据清洗和标准化脚本
将三路数据源合并清洗为一份标准化的 etf_standard_data.json

清理项：
- 去重（etf_data_generated.json 的重复代码）
- 代码匹配校验（仅保留在全量数据中有记录的ETF）
- name/issuer 分离（从全量数据name中提取发行人）
- top_holdings 格式统一（转为字典格式）+ AKShare 补充权重%
- 历史净值计算收益率/回撤/夏普
- 补充字段落地（无需运行时实时转换）
"""
import json
import sys
import time
import math
import warnings
from pathlib import Path
from collections import Counter
warnings.filterwarnings('ignore')

ROOT = Path(__file__).parent
FULL_DATA = ROOT / "etf_complete_all.json"
GENERATED_DATA = ROOT / "etf_data_generated.json"
OUTPUT = ROOT / "etf_standard_data.json"

try:
    import akshare as ak
    import pandas as pd
    HAS_AKSHARE = True
except ImportError:
    HAS_AKSHARE = False
    print("⚠️  akshare 未安装，将跳过权重补充和净值计算")

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
known_names = dict(sorted(known_names.items(), key=lambda x: -len(x[0])))
print(f"   已知 name→issuer 映射: {len(known_names)} 个")

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
    for known_name, known_issuer in known_names.items():
        if known_name in raw_name:
            rest = raw_name.replace(known_name, "", 1).strip()
            if rest and len(rest) <= 12:
                return known_name, known_issuer
    for issuer in _COMMON_ISSUERS:
        if raw_name.endswith(issuer):
            name = raw_name[:-len(issuer)].strip().rstrip("-")
            if name:
                return name, issuer
    return raw_name, ""


# ============ 新增：AKShare 补充持仓权重 ============
def enrich_holdings_weights(gen_map_codes):
    """
    用 AKShare fund_portfolio_hold_em() 获取 ETF 真实持仓权重
    匹配规则：通过股票代码匹配权重，补充到 top_holdings 中
    """
    if not HAS_AKSHARE:
        return gen_map_codes

    print("\n5. 补充持仓权重 (AKShare fund_portfolio_hold_em)...")
    updated = 0
    failed = 0
    # 只对已有持仓（成份股列表）的ETF补充权重
    target_codes = [c for c, item in gen_map_codes.items()
                    if item.get('top_holdings') and isinstance(item['top_holdings'], list)]

    for i, code in enumerate(target_codes):
        item = gen_map_codes[code]
        try:
            df = ak.fund_portfolio_hold_em(symbol=code, date="2025")
            if df is not None and len(df) > 0:
                # 构建 股票代码→权重 映射
                weight_map = {}
                for _, row in df.iterrows():
                    try:
                        stock_code = str(row.iloc[1]).strip().zfill(6)
                        weight = float(row.iloc[3])
                        weight_map[stock_code] = f"{weight:.2f}%"
                    except:
                        pass

                # 为 top_holdings 补充权重（用股票名匹配，兜底用代码）
                enriched = []
                for h in item.get('top_holdings', []):
                    name = h.get('name', '') if isinstance(h, dict) else str(h)
                    # 取权重（默认空）
                    weight = ""
                    for sc, w in weight_map.items():
                        if sc in str(h):
                            weight = w
                            break
                    enriched.append({"name": name, "weight": weight})
                item['top_holdings'] = enriched
                updated += 1
        except Exception as e:
            failed += 1

        if (i + 1) % 10 == 0:
            print(f"   进度: {i+1}/{len(target_codes)}  成功={updated} 失败={failed}")

        time.sleep(0.5)

    print(f"   权重补充完成: 成功={updated} 失败={failed}")
    return gen_map_codes


# ============ 新增：历史净值计算收益率/回撤/夏普 ============
def calc_returns_from_history(code, item, max_retries=3):
    """从历史净值计算收益率、最大回撤、夏普比率"""
    if not HAS_AKSHARE:
        return item

    for attempt in range(max_retries):
        try:
            df = ak.fund_etf_hist_em(
                symbol=code, period='daily',
                start_date='20230516', end_date='20260516',
                adjust='qfq'
            )
            if df is None or len(df) < 20:
                return item

            prices = [float(v) for v in list(df['收盘'])]
            if len(prices) < 20:
                return item

            n = len(prices)

            # 近1年收益
            if n >= 252:
                y1 = (prices[-1] - prices[-252]) / prices[-252] * 100
            else:
                y1 = (prices[-1] - prices[0]) / prices[0] * 100

            # 近3年收益（用全部数据，约3年）
            y3 = (prices[-1] - prices[0]) / prices[0] * 100

            # 最大回撤
            peak = prices[0]
            max_dd = 0.0
            for v in prices:
                if v > peak:
                    peak = v
                dd = (v - peak) / peak * 100
                if dd < max_dd:
                    max_dd = dd

            # 夏普比率 (年化收益-2%) / 年化波动率
            if n >= 30:
                daily_returns = [(prices[i] - prices[i-1]) / prices[i-1]
                                 for i in range(1, min(n, 253))]
                if daily_returns:
                    avg_ret = sum(daily_returns) / len(daily_returns)
                    vol = math.sqrt(sum((r - avg_ret)**2 for r in daily_returns) / len(daily_returns))
                    annual_ret = avg_ret * 252
                    annual_vol = vol * math.sqrt(252)
                    sharpe = (annual_ret - 0.02) / annual_vol if annual_vol > 0 else 0
                else:
                    sharpe = 0
            else:
                sharpe = 0

            item['year_1_return'] = round(y1, 1)
            item['year_3_return'] = round(y3, 1)
            item['max_drawdown'] = round(max_dd, 1)
            item['sharpe_ratio'] = round(sharpe, 2)

            if attempt > 0:
                time.sleep(1)
            return item

        except Exception:
            time.sleep(1)
            continue

    return item


# ---- 第4步（原第5步改）：标准化处理 ----
print("\n4. 标准化处理基础字段...")

standard_etfs = []
match_count = 0
no_issuer_count = 0

for etf in full_data:
    code = str(etf.get("code", ""))
    raw_name = etf.get("name", "")
    gen = gen_map.get(code, {})

    name, issuer = extract_name_issuer(raw_name)
    if gen:
        name = gen.get("name", name)
        issuer = gen.get("issuer", issuer)
        match_count += 1
    if not issuer:
        no_issuer_count += 1

    raw_holdings = gen.get("top_holdings", [])
    top_holdings = []
    for h in raw_holdings[:5]:
        if isinstance(h, dict) and "name" in h:
            top_holdings.append({"name": h["name"], "weight": h.get("weight", "")})
        elif isinstance(h, str):
            parts = h.split(" ", 1)
            top_holdings.append({"name": parts[0], "weight": parts[1] if len(parts) > 1 else ""})

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
        "launch_date": gen.get("launch_date", ""),
        "underlying": gen.get("underlying", ""),
        "top_holdings": top_holdings,
        "year_1_return": gen.get("year_1_return", 0),
        "year_3_return": gen.get("year_3_return", 0),
        "max_drawdown": gen.get("max_drawdown", 0),
        "sharpe_ratio": gen.get("sharpe_ratio", 0.0),
        "volume": gen.get("volume", etf.get("volume", 0) / 1e8 if etf.get("volume") else 0),
        "category": "宽基" if any(k in raw_name for k in ["沪深300", "中证500", "上证50", "科创50"]) else "行业",
    }
    standard_etfs.append(standard_etf)

# ---- 第5步：补充持仓权重 ----（可选，需要 AKShare）
if HAS_AKSHARE:
    gen_map = enrich_holdings_weights(gen_map)
    # 重新把带权重的持仓写回 standard_etfs
    match_count_weight = 0
    for etf in standard_etfs:
        gen = gen_map.get(etf['code'], {})
        enriched = gen.get('top_holdings', [])
        if enriched:
            etf['top_holdings'] = enriched[:5]
            match_count_weight += 1
    print(f"   {match_count_weight} 只已补充权重%")

# ---- 第6步：历史净值计算 --（可选，只对规模前500做）----
if HAS_AKSHARE:
    print("\n6. 计算收益率/回撤/夏普 (AKShare fund_etf_hist_em)...")
    # 按规模排序，只算前500只（占全市场ETF规模95%以上）
    sorted_by_scale = sorted(standard_etfs, key=lambda x: x.get('scale', 0) or 0, reverse=True)
    target_etfs = [e for e in sorted_by_scale if e['year_1_return'] == 0][:500]
    print(f"   需补充净值计算的ETF: {len(target_etfs)} 只（规模Top500且收益率=0）")
    calced = 0
    for i, etf in enumerate(target_etfs):
        code = etf['code']
        gen = gen_map.get(code, {})
        result = calc_returns_from_history(code, gen)
        if result.get('year_1_return', 0) != 0:
            etf['year_1_return'] = result['year_1_return']
            etf['year_3_return'] = result['year_3_return']
            etf['max_drawdown'] = result['max_drawdown']
            etf['sharpe_ratio'] = result['sharpe_ratio']
            calced += 1
        if (i + 1) % 50 == 0:
            print(f"   进度: {i+1}/{len(target_etfs)}  已计算={calced}")
        time.sleep(0.3)  # 避免请求过快

    print(f"   历史净值计算完成: {calced} 只")

# ---- 第7步：输出统计 ----
print(f"\n7. 统计:")
print(f"   总记录: {len(standard_etfs)} 只")
print(f"   空 issuer: {no_issuer_count} 只")
print(f"   有 top_holdings: {sum(1 for e in standard_etfs if e['top_holdings'])} 只")
print(f"   有收益率: {sum(1 for e in standard_etfs if e['year_1_return'] != 0)} 只")
print(f"   有夏普: {sum(1 for e in standard_etfs if e['sharpe_ratio'] != 0)} 只")

# ---- 第8步：保存 ----
with open(OUTPUT, "w", encoding="utf-8") as f:
    json.dump(standard_etfs, f, ensure_ascii=False, indent=2)
print(f"\n✅ 已保存标准化数据到 {OUTPUT.name}")
print(f"   文件大小: {OUTPUT.stat().st_size / 1024:.0f} KB")
