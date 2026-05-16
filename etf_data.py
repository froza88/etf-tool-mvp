#!/usr/bin/env python3
"""
ETF数据模块 - 从标准化数据文件直接加载
数据清洗/合并/格式转换由 build_standard_data.py 负责
"""
import json
import os
import sys
from pathlib import Path
from datetime import datetime, timedelta

# 标准化数据文件
STANDARD_DATA_FILE = Path(__file__).parent / "etf_standard_data.json"
MAX_AGE_HOURS = 168  # 7天

# 回退数据文件
SAMPLE_DATA_FILE = Path(__file__).parent / "etf_complete_130.json"


def _is_file_recent(filepath, max_age_hours):
    if not filepath.exists():
        return False
    mtime = datetime.fromtimestamp(os.path.getmtime(filepath))
    age = datetime.now() - mtime
    return age < timedelta(hours=max_age_hours)


def _load_etfs():
    """从标准化数据文件加载ETF"""
    if _is_file_recent(STANDARD_DATA_FILE, MAX_AGE_HOURS):
        try:
            with open(STANDARD_DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            print(f"✅ 标准化数据：{len(data)} 只ETF", file=sys.stderr)
            return data
        except Exception as e:
            print(f"⚠️  标准化数据加载失败：{e}", file=sys.stderr)

    # 回退：用旧数据
    try:
        with open(SAMPLE_DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        print(f"⚠️  回退数据：{SAMPLE_DATA_FILE.name} ({len(data)} 只)", file=sys.stderr)
        return data
    except Exception as e:
        print(f"❌ 无法加载数据：{e}", file=sys.stderr)
        return []


_ETFs = None


def get_all_etfs():
    global _ETFs
    if _ETFs is None:
        _ETFs = _load_etfs()
    return _ETFs


def get_etf_by_code(code):
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
        if "type" in filters and filters["type"]:
            if etf["type"] != filters["type"]:
                continue
        if "scale_min" in filters and filters["scale_min"]:
            if etf["scale"] < float(filters["scale_min"]):
                continue
        if "scale_max" in filters and filters["scale_max"]:
            if etf["scale"] > float(filters["scale_max"]):
                continue
        if "fee_max" in filters and filters["fee_max"]:
            if etf["fee"] > float(filters["fee_max"]):
                continue
        if "return_min" in filters and filters["return_min"]:
            if etf["year_1_return"] < float(filters["return_min"]):
                continue
        if "category" in filters and filters["category"]:
            if etf["category"] != filters["category"]:
                continue
        if "keyword" in filters and filters["keyword"]:
            keyword = filters["keyword"].lower()
            if keyword not in etf["name"].lower() and keyword not in etf["code"].lower():
                continue

        result.append(etf)

    return result
