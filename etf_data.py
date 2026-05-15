#!/usr/bin/env python3
"""
ETF数据模块 - 支持双数据源（130只 + 全量1645只）
优先使用全量数据（如果可用且最近更新）
"""
import json
import os
import sys
from pathlib import Path
from datetime import datetime, timedelta

# 数据文件配置
FULL_DATA_FILE = Path(__file__).parent / "etf_complete_all.json"
SAMPLE_DATA_FILE = Path(__file__).parent / "etf_complete_130.json"
MAX_AGE_HOURS = 24  # 全量数据最大有效期（小时）

def _is_file_recent(filepath, max_age_hours):
    """检查文件是否存在且最近更新"""
    if not filepath.exists():
        return False
    
    # 检查文件修改时间
    mtime = datetime.fromtimestamp(os.path.getmtime(filepath))
    age = datetime.now() - mtime
    
    return age < timedelta(hours=max_age_hours)

def _load_etfs():
    """加载ETF数据并转换为标准格式（优先使用全量数据）"""
    
    # 优先尝试加载全量数据（如果可用且最近更新）
    if _is_file_recent(FULL_DATA_FILE, MAX_AGE_HOURS):
        try:
            with open(FULL_DATA_FILE, "r", encoding="utf-8") as f:
                raw_etfs = json.load(f)
            print(f"✅ 使用全量数据：{FULL_DATA_FILE.name} ({len(raw_etfs)} 只ETF)", file=sys.stderr)
        except:
            raw_etfs = None
    
    # 回退到样本数据
    if raw_etfs is None:
        try:
            with open(SAMPLE_DATA_FILE, "r", encoding="utf-8") as f:
                raw_etfs = json.load(f)
            print(f"⚠️  使用样本数据：{SAMPLE_DATA_FILE.name} ({len(raw_etfs)} 只ETF)", file=sys.stderr)
        except Exception as e:
            print(f"❌ 无法加载数据文件：{e}", file=sys.stderr)
            return []
    
    etfs = []
    for etf in raw_etfs:
        # 获取名称和管理人
        raw_name = etf.get("name", "")
        manager = etf.get("manager", "")
        
        # 清理名称：去除末尾重复的管理人名称
        name = raw_name
        if manager and raw_name.endswith(manager):
            name = raw_name[:-len(manager)].rstrip("-")
        
        # 转换字段映射（适配 etf_complete_all.json 实际字段）
        transformed = {
            "code": etf.get("code", ""),
            "name": name,
            "type": "股票型",  # 默认值
            "scale": etf.get("market_cap", 0) / 1e8 if etf.get("market_cap") else 0,  # 规模（亿元）
            "fee": 0.6,  # 默认值
            "management_fee": 0.5,
            "custody_fee": 0.1,
            "tracking_error": 0.02,
            "year_1_return": etf.get("change_pct", 0) / 100 if etf.get("change_pct") else 0,
            "year_3_return": 0,  # etf_complete_all.json 无此字段
            "max_drawdown": 0,  # etf_complete_all.json 无此字段
            "sharpe_ratio": 0.0,
            "launch_date": "",  # etf_complete_all.json 无此字段
            "issuer": etf.get("name", "").replace(name, "").strip("-") if name else "",
            "underlying": "",  # etf_complete_all.json 无此字段
            "top_holdings": [],
            "volume": etf.get("volume", 0) / 1e8 if etf.get("volume") else 0,
            "category": "宽基" if any(k in etf.get("name", "") for k in ["沪深300", "中证500", "上证50", "科创50"]) else "行业",
        }
        etfs.append(transformed)
    
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
