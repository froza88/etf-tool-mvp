#!/usr/bin/env python3
"""
ETF数据模块 v2 - 本地存储优先
优先级：data/snapshots/最新快照 → etf_standard_data.json → 回退数据

数据清洗/合并/格式转换由 pipeline.py 负责
"""
import json
import os
import sys
from pathlib import Path
from datetime import datetime, timedelta

ROOT = Path(__file__).parent
DATA_DIR = ROOT / "data"

# 数据源优先级
SNAPSHOT_DIR = DATA_DIR / "snapshots"
STANDARD_DATA_FILE = ROOT / "etf_standard_data.json"
MAX_AGE_HOURS = 168  # 7天


def _is_file_recent(filepath, max_age_hours):
    if not filepath.exists():
        return False
    mtime = datetime.fromtimestamp(os.path.getmtime(filepath))
    age = datetime.now() - mtime
    return age < timedelta(hours=max_age_hours)


def _load_from_snapshot():
    """从最新版本快照加载数据（最高优先级）"""
    if not SNAPSHOT_DIR.exists():
        return None

    # 找到最新的快照文件
    snapshots = sorted(SNAPSHOT_DIR.glob("v_*.json"), reverse=True)
    if not snapshots:
        return None

    latest = snapshots[0]
    try:
        with open(latest, "r", encoding="utf-8") as f:
            data = json.load(f)
        # 快照中的 standard_data 字段包含完整数据
        standard_data = data.get("standard_data")
        if standard_data and len(standard_data) > 0:
            snapshot_date = data.get("date", "unknown")
            print(f"✅ 快照数据（{snapshot_date}）：{len(standard_data)} 只ETF", file=sys.stderr)
            return standard_data
    except Exception as e:
        print(f"⚠️ 快照加载失败：{e}", file=sys.stderr)

    return None


def _load_etfs():
    """加载ETF数据：快照 → 标准数据 → 回退"""
    # 优先级1：本地快照（最新版本）
    snapshot_data = _load_from_snapshot()
    if snapshot_data:
        return snapshot_data

    # 优先级2：标准数据文件
    if _is_file_recent(STANDARD_DATA_FILE, MAX_AGE_HOURS):
        try:
            with open(STANDARD_DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            # 兼容两种格式：list 或 {"etfs": [...]}
            if isinstance(data, dict):
                data = data.get("etfs", data)
            print(f"✅ 标准化数据：{len(data)} 只ETF", file=sys.stderr)
            return data
        except Exception as e:
            print(f"⚠️  标准化数据加载失败：{e}", file=sys.stderr)

    # 优先级3：标准数据文件（即使过期也用）
    if STANDARD_DATA_FILE.exists():
        try:
            with open(STANDARD_DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                data = data.get("etfs", data)
            print(f"⚠️  过期数据：{len(data)} 只ETF", file=sys.stderr)
            return data
        except Exception:
            pass

    # 优先级4：从旧缓存恢复
    for backup_name in ["etf_complete_all.json", "etf_data_generated.json"]:
        backup_file = ROOT / backup_name
        if backup_file.exists():
            try:
                with open(backup_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, dict):
                    data = data.get("etfs", data)
                print(f"⚠️  回退数据：{backup_name} ({len(data)} 只)", file=sys.stderr)
                return data
            except Exception:
                pass

    print(f"❌ 无法加载任何数据", file=sys.stderr)
    return []


_ETFLIST = None
_ETFMAP = None


def _normalize_units(data):
    """统一数据单位：部分数据源返回 scale/amount 为'亿'单位，需转为'元'"""
    for etf in data:
        # scale: ETF规模不可能小于1万元，若 < 10000 则视为亿单位
        scale = etf.get("scale")
        if scale is not None and isinstance(scale, (int, float)) and 0 < scale < 10000:
            etf["scale"] = scale * 100000000
        # amount: 成交额同理
        amount = etf.get("amount")
        if amount is not None and isinstance(amount, (int, float)) and 0 < amount < 10000:
            etf["amount"] = amount * 100000000
    return data


def _ensure_loaded():
    """确保数据已加载，同时构建 code→ETF 索引"""
    global _ETFLIST, _ETFMAP
    if _ETFLIST is None:
        _ETFLIST = _load_etfs()
        _normalize_units(_ETFLIST)
        _ETFMAP = {etf["code"]: etf for etf in _ETFLIST if "code" in etf}


def get_all_etfs():
    _ensure_loaded()
    return _ETFLIST


def get_etf_by_code(code):
    """O(1) 查找 ETF（使用 dict 索引）"""
    _ensure_loaded()
    return _ETFMAP.get(code)


def filter_etfs(filters):
    """筛选ETF"""
    etfs = get_all_etfs()
    result = []

    for etf in etfs:
        if "type" in filters and filters["type"]:
            if etf.get("type") != filters["type"]:
                continue
        if "scale_min" in filters and filters["scale_min"]:
            if (etf.get("scale") or 0) < float(filters["scale_min"]):
                continue
        if "scale_max" in filters and filters["scale_max"]:
            if (etf.get("scale") or 0) > float(filters["scale_max"]):
                continue
        if "return_min" in filters and filters["return_min"]:
            if (etf.get("year_1_return") or 0) < float(filters["return_min"]):
                continue
        if "category" in filters and filters["category"]:
            if etf.get("category") != filters["category"]:
                continue
        if "keyword" in filters and filters["keyword"]:
            keyword = filters["keyword"].lower()
            name = etf.get("name", "").lower()
            code = etf.get("code", "").lower()
            if keyword not in name and keyword not in code:
                continue

        result.append(etf)

    return result


def reload_data():
    """强制重新加载数据（pipeline 更新后调用）"""
    global _ETFLIST, _ETFMAP
    _ETFLIST = None
    _ETFMAP = None
    _ensure_loaded()
