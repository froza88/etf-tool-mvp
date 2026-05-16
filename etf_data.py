#!/usr/bin/env python3
"""
ETF数据模块 - 支持多数据源
逻辑：以全量数据(1461只)为底座，用 etf_data_generated.json(130只)补充优质字段（持仓、收益率等）
"""
import json
import os
import sys
from pathlib import Path
from datetime import datetime, timedelta

# 数据文件配置
FULL_DATA_FILE = Path(__file__).parent / "etf_complete_all.json"
GENERATED_DATA_FILE = Path(__file__).parent / "etf_data_generated.json"
SAMPLE_DATA_FILE = Path(__file__).parent / "etf_complete_130.json"
MAX_AGE_HOURS = 168  # 全量数据最大有效期（7天）


def _is_file_recent(filepath, max_age_hours):
    """检查文件是否存在且最近更新"""
    if not filepath.exists():
        return False
    mtime = datetime.fromtimestamp(os.path.getmtime(filepath))
    age = datetime.now() - mtime
    return age < timedelta(hours=max_age_hours)


def _build_known_names():
    """从 etf_data_generated.json 构建已知的 name → issuer 映射
    按 name 长度降序排序（长的先匹配，避免短名被长名误导）
    """
    known = {}
    if GENERATED_DATA_FILE.exists():
        try:
            with open(GENERATED_DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            for item in data:
                n = item.get("name", "").strip()
                i = item.get("issuer", "").strip()
                if n and i:
                    known[n] = i
        except:
            pass
    # 按 name 长度降序（长的优先匹配）
    return dict(sorted(known.items(), key=lambda x: -len(x[0])))


# 常见基金公司后缀列表（兜底匹配）
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
], key=lambda x: -len(x))  # 长的优先


def _extract_name_issuer(raw_name, known_names):
    """
    尝试从全量数据的 name（如"沪深300ETF易方达"）中分离出 ETF 名称和发行人。
    优先用已知 name 映射匹配，再用兜底发行人列表做后缀匹配。
    返回 (name, issuer)
    """
    # 1. 先用已知 name 匹配
    for known_name, known_issuer in known_names.items():
        if known_name in raw_name:
            rest = raw_name.replace(known_name, "", 1).strip()
            if rest and len(rest) <= 12:
                return known_name, known_issuer
    
    # 2. 用兜底发行人列表做后缀匹配
    for issuer in _COMMON_ISSUERS:
        if raw_name.endswith(issuer):
            name = raw_name[:-len(issuer)].strip().rstrip("-")
            if name:
                return name, issuer
    
    # 3. 无法提取，保持原样
    return raw_name, ""


def _load_etfs():
    """加载ETF数据：以全量数据(1461只)为底座，用生成数据(130只)补充优质字段"""
    
    raw_etfs = None
    
    # 第1步：加载全量数据作为底座
    if _is_file_recent(FULL_DATA_FILE, MAX_AGE_HOURS):
        try:
            with open(FULL_DATA_FILE, "r", encoding="utf-8") as f:
                raw_etfs = json.load(f)
            print(f"✅ 全量数据底座：{FULL_DATA_FILE.name} ({len(raw_etfs)} 只ETF)", file=sys.stderr)
        except Exception as e:
            print(f"⚠️  加载全量数据失败：{e}", file=sys.stderr)
            raw_etfs = None
    
    # 回退：全量数据不可用，用样本数据
    if raw_etfs is None:
        try:
            with open(SAMPLE_DATA_FILE, "r", encoding="utf-8") as f:
                raw_etfs = json.load(f)
            print(f"⚠️  使用样本数据：{SAMPLE_DATA_FILE.name} ({len(raw_etfs)} 只ETF)", file=sys.stderr)
        except Exception as e:
            print(f"❌ 无法加载数据文件：{e}", file=sys.stderr)
            return []
    
    # 第2步：加载生成数据（含 top_holdings 等优质字段），用于补充
    enriched = {}
    if GENERATED_DATA_FILE.exists():
        try:
            with open(GENERATED_DATA_FILE, "r", encoding="utf-8") as f:
                gen_data = json.load(f)
            # 建立 code → 优质数据的映射
            for item in gen_data:
                enriched[item["code"]] = item
            print(f"✅ 优质数据补充：{GENERATED_DATA_FILE.name} ({len(enriched)} 只含补充字段)", file=sys.stderr)
        except Exception as e:
            print(f"⚠️  加载优质数据失败（不影响底座）：{e}", file=sys.stderr)
    
    # 构建已知 name→issuer 映射（用于从全量数据 name 中提取发行人）
    known_names = _build_known_names()
    
    # 第3步：转换全量数据，并用优质数据补充字段
    etfs = []
    for etf in raw_etfs:
        code = etf.get("code", "")
        gen = enriched.get(code, {})  # 这只ETF的优质数据（如有）
        
        raw_name = etf.get("name", "")
        
        # 从全量数据的 name 中提取 ETF 名称和发行人
        name, issuer = _extract_name_issuer(raw_name, known_names)
        
        transformed = {
            "code": code,
            "name": name,
            "type": "股票型",
            "scale": etf.get("market_cap", 0) / 1e8 if etf.get("market_cap") else 0,
            "fee": 0.6,
            "management_fee": 0.5,
            "custody_fee": 0.1,
            "tracking_error": 0.02,
            "year_1_return": etf.get("change_pct", 0) / 100 if etf.get("change_pct") else 0,
            "year_3_return": 0,
            "max_drawdown": 0,
            "sharpe_ratio": 0.0,
            "launch_date": "",
            "issuer": issuer,
            "underlying": "",
            "top_holdings": [],
            "volume": etf.get("volume", 0) / 1e8 if etf.get("volume") else 0,
            "category": "宽基" if any(k in etf.get("name", "") for k in ["沪深300", "中证500", "上证50", "科创50"]) else "行业",
        }
        
        # 用优质数据补充/覆盖字段（如有）
        if gen:
            transformed["name"] = gen.get("name", transformed["name"])
            transformed["type"] = gen.get("type", transformed["type"])
            transformed["scale"] = gen.get("scale", transformed["scale"])
            transformed["fee"] = gen.get("fee", transformed["fee"])
            if gen.get("fee"):
                transformed["management_fee"] = round(gen["fee"] * 0.8, 4)
                transformed["custody_fee"] = round(gen["fee"] * 0.2, 4)
            transformed["tracking_error"] = gen.get("tracking_error", transformed["tracking_error"])
            transformed["year_1_return"] = gen.get("year_1_return", transformed["year_1_return"])
            transformed["year_3_return"] = gen.get("year_3_return", transformed["year_3_return"])
            transformed["max_drawdown"] = gen.get("max_drawdown", transformed["max_drawdown"])
            transformed["sharpe_ratio"] = gen.get("sharpe_ratio", transformed["sharpe_ratio"])
            transformed["launch_date"] = gen.get("launch_date", transformed["launch_date"])
            transformed["issuer"] = gen.get("issuer", transformed["issuer"])
            transformed["underlying"] = gen.get("underlying", transformed["underlying"])
        # top_holdings: 统一转为 [{"name": "xx", "weight": "xx%"}, ...] 格式
            raw_holdings = gen.get("top_holdings", transformed["top_holdings"])
            formatted_holdings = []
            if isinstance(raw_holdings, list):
                for h in raw_holdings[:5]:
                    if isinstance(h, dict) and "name" in h:
                        formatted_holdings.append(h)
                    elif isinstance(h, str):
                        # 尝试分割 "股票名称 权重%" 格式
                        parts = h.split(" ", 1)
                        name = parts[0]
                        weight = parts[1] if len(parts) > 1 else ""
                        formatted_holdings.append({"name": name, "weight": weight})
            transformed["top_holdings"] = formatted_holdings
            transformed["volume"] = gen.get("volume", transformed["volume"])
            transformed["category"] = gen.get("category", transformed["category"])
        
        etfs.append(transformed)
    
    print(f"✅ 最终加载：{len(etfs)} 只ETF（底座{len(raw_etfs)}只 + 补充{len(enriched)}只优质数据）", file=sys.stderr)
    return etfs


# 缓存ETF数据
_ETFs = None


def get_all_etfs():
    """获取所有ETF"""
    global _ETFs
    if _ETFs is None:
        _ETFs = _load_etfs()
    return _ETFs


def get_etf_by_code(code):
    """根据代码获取ETF"""
    etfs = get_all_etfs()
    for etf in etfs:
        if etf["code"] == code:
            return etf
    return None


def filter_etfs(filters):
    """筛选ETF"""
    etfs = get_all_etfs()
    result = []
    
    for etf in etfs:
        # 类型筛选
        if "type" in filters and filters["type"]:
            if etf["type"] != filters["type"]:
                continue
        
        # 规模筛选
        if "scale_min" in filters and filters["scale_min"]:
            if etf["scale"] < float(filters["scale_min"]):
                continue
        if "scale_max" in filters and filters["scale_max"]:
            if etf["scale"] > float(filters["scale_max"]):
                continue
        
        # 费率筛选
        if "fee_max" in filters and filters["fee_max"]:
            if etf["fee"] > float(filters["fee_max"]):
                continue
        
        # 收益率筛选
        if "return_min" in filters and filters["return_min"]:
            if etf["year_1_return"] < float(filters["return_min"]):
                continue
        
        # 分类筛选
        if "category" in filters and filters["category"]:
            if etf["category"] != filters["category"]:
                continue
        
        # 关键词筛选
        if "keyword" in filters and filters["keyword"]:
            keyword = filters["keyword"].lower()
            if keyword not in etf["name"].lower() and keyword not in etf["code"].lower():
                continue
        
        result.append(etf)
    
    return result
