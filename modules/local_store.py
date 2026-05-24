#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LocalStore - 本地数据存储层
实现数据本地化、版本快照、冗余备份、历史数据永久保存

核心设计：
1. data/ 目录统一管理所有数据文件
2. 每次pipeline运行后自动生成版本快照（snapshots/）
3. 历史K线按ETF拆分为独立文件（history/），永久保存
4. 实时数据缓存（realtime/），每日刷新
5. 自动冗余备份（backup/），保留7天日备+4周周备
6. 版本元数据自动记录（meta.json）

目录结构：
  data/
  ├── snapshots/          # 版本快照（每次pipeline自动保存）
  │   ├── v_2026-05-19.json
  │   └── ...
  ├── history/            # 历史K线（按ETF独立存储，永久保存）
  │   ├── 510300.json
  │   └── ...
  ├── realtime/           # 实时数据缓存
  │   ├── prices.json
  │   ├── metrics.json
  │   └── generated.json
  ├── backup/             # 冗余备份
  │   ├── daily/          # 最近7天日备
  │   └── weekly/         # 最近4周周备
  └── meta.json           # 版本元数据
"""

import json
import os
import shutil
import gzip
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).parent.parent
DATA_DIR = ROOT / "data"
SNAPSHOTS_DIR = DATA_DIR / "snapshots"
HISTORY_DIR = DATA_DIR / "history"
REALTIME_DIR = DATA_DIR / "realtime"
BACKUP_DAILY_DIR = DATA_DIR / "backup" / "daily"
BACKUP_WEEKLY_DIR = DATA_DIR / "backup" / "weekly"
META_FILE = DATA_DIR / "meta.json"

# 兼容：项目根目录下的旧数据文件
LEGACY_FILES = {
    "standard": ROOT / "etf_standard_data.json",
    "generated": ROOT / "etf_data_generated.json",
    "metrics": ROOT / "etf_calculated_metrics.json",
    "yingmi": ROOT / "etf_yingmi_metrics.json",
    "complete": ROOT / "etf_complete_all.json",
    "prices": ROOT / "etf_prices.json",
    "prev_close": ROOT / "etf_prev_close.json",
    "history_cache": ROOT / "etf_history_cache.json",
}


def _ensure_dirs():
    """确保所有数据目录存在"""
    for d in [DATA_DIR, SNAPSHOTS_DIR, HISTORY_DIR, REALTIME_DIR,
              BACKUP_DAILY_DIR, BACKUP_WEEKLY_DIR]:
        d.mkdir(parents=True, exist_ok=True)


def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")


# ============ JSON 读写 ============

def load_json(path):
    """读取JSON文件，支持 .gz 压缩"""
    if not path.exists():
        # 尝试 gzip 版本
        gz_path = Path(str(path) + ".gz")
        if gz_path.exists():
            with gzip.open(gz_path, "rt", encoding="utf-8") as f:
                return json.load(f)
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path, data, compress=False):
    """保存JSON文件，可选 gzip 压缩"""
    if compress:
        gz_path = Path(str(path) + ".gz")
        with gzip.open(gz_path, "wt", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
        # 如果有未压缩版本，删除
        if path.exists():
            path.unlink()
    else:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)


# ============ 版本快照 ============

def create_snapshot(step_name="all"):
    """
    创建版本快照：将所有核心数据文件打包到一个日期命名的快照中
    每次pipeline步骤执行后自动调用
    """
    _ensure_dirs()
    date_str = datetime.now().strftime("%Y-%m-%d")
    snapshot_file = SNAPSHOTS_DIR / f"v_{date_str}.json"

    # 加载现有快照（同一天多次运行会追加步骤记录）
    snapshot = {}
    if snapshot_file.exists():
        snapshot = load_json(snapshot_file) or {}

    # 收集当前所有核心数据
    standard_raw = load_json(LEGACY_FILES["standard"]) or []
    # 兼容 dict 格式 {"etfs": [...], "updated": "..."}
    if isinstance(standard_raw, dict) and "etfs" in standard_raw:
        standard = standard_raw["etfs"]
    else:
        standard = standard_raw
    metrics = load_json(LEGACY_FILES["metrics"]) or {}
    yingmi = load_json(LEGACY_FILES["yingmi"]) or {}
    history_cache = load_json(LEGACY_FILES["history_cache"]) or {}

    snapshot.update({
        "date": date_str,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "step": step_name,
        "stats": {
            "total_etfs": len(standard),
            "has_price": sum(1 for e in standard if isinstance(e, dict) and e.get("close", 0) > 0),
            "has_return": sum(1 for e in standard if isinstance(e, dict) and e.get("year_1_return", 0) != 0),
            "has_sharpe": sum(1 for e in standard if isinstance(e, dict) and e.get("sharpe_ratio", 0) != 0),
            "has_holdings": sum(1 for e in standard if isinstance(e, dict) and e.get("top_holdings")),
            "has_issuer": sum(1 for e in standard if isinstance(e, dict) and e.get("issuer")),
            "metrics_count": len(metrics),
            "yingmi_count": len(yingmi),
            "history_count": len(history_cache),
        },
        # 核心数据内嵌（标准数据+指标，不含历史K线——太大了）
        "standard_data": standard,
        "calculated_metrics": metrics,
        "yingmi_metrics": yingmi,
    })

    # 追加步骤执行记录
    if "steps_run" not in snapshot:
        snapshot["steps_run"] = []
    snapshot["steps_run"].append({
        "step": step_name,
        "time": datetime.now().strftime("%H:%M:%S"),
    })

    save_json(snapshot_file, snapshot)
    log(f"版本快照: v_{date_str}.json (步骤: {step_name})")

    # 同时更新 meta.json
    _update_meta(step_name, snapshot["stats"])

    return snapshot_file


def _update_meta(step_name, stats):
    """更新元数据文件"""
    meta = {}
    if META_FILE.exists():
        meta = load_json(META_FILE) or {}

    meta["last_update"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    meta["last_step"] = step_name
    meta["current_stats"] = stats

    # 版本历史（保留最近30条）
    if "version_history" not in meta:
        meta["version_history"] = []
    meta["version_history"].append({
        "date": datetime.now().strftime("%Y-%m-%d"),
        "step": step_name,
        "stats": stats,
    })
    meta["version_history"] = meta["version_history"][-30:]

    save_json(META_FILE, meta)


# ============ 冗余备份 ============

def create_backup():
    """
    创建冗余备份
    策略：日备保留7天 + 周备保留4周
    """
    _ensure_dirs()
    date_str = datetime.now().strftime("%Y-%m-%d")
    weekday = datetime.now().weekday()

    # 日备：复制标准数据文件
    daily_backup = BACKUP_DAILY_DIR / f"etf_standard_{date_str}.json"
    standard = load_json(LEGACY_FILES["standard"])
    if standard:
        save_json(daily_backup, standard)
        log(f"日备: {daily_backup.name}")

    # 周备：每周一执行，打包所有数据
    if weekday == 0:  # 周一
        weekly_backup = BACKUP_WEEKLY_DIR / f"full_backup_{date_str}.json"
        full_data = {}
        for key, path in LEGACY_FILES.items():
            data = load_json(path)
            if data is not None:
                full_data[key] = data
        if full_data:
            save_json(weekly_backup, full_data, compress=True)
            log(f"周备: {weekly_backup.name} (gzip)")

    # 清理过期备份
    _cleanup_backups()


def _cleanup_backups():
    """清理过期备份文件"""
    now = datetime.now()

    # 日备：保留7天
    for f in BACKUP_DAILY_DIR.glob("*.json"):
        try:
            # 从文件名提取日期 etf_standard_2026-05-12.json
            date_part = f.stem.split("_")[-1]
            file_date = datetime.strptime(date_part, "%Y-%m-%d")
            if (now - file_date).days > 7:
                f.unlink()
        except (ValueError, IndexError):
            pass

    # 周备：保留4周
    for f in BACKUP_WEEKLY_DIR.glob("*.json.gz"):
        try:
            date_part = f.stem.replace("full_backup_", "")
            file_date = datetime.strptime(date_part, "%Y-%m-%d")
            if (now - file_date).days > 28:
                f.unlink()
        except (ValueError, IndexError):
            pass


# ============ 历史K线永久存储 ============

def save_etf_history(code, prices, dates, source="akshare"):
    """
    保存单只ETF的历史K线到独立文件
    采用增量追加策略：只添加新数据，不覆盖已有数据
    """
    _ensure_dirs()
    history_file = HISTORY_DIR / f"{code}.json"

    # 加载已有历史
    existing = load_json(history_file) or {"prices": [], "dates": []}
    existing_prices = existing.get("prices", [])
    existing_dates = existing.get("dates", [])

    # 构建日期索引，只追加新数据
    existing_date_set = set(existing_dates)
    new_count = 0
    for i, date in enumerate(dates):
        if date not in existing_date_set:
            existing_prices.append(prices[i])
            existing_dates.append(date)
            existing_date_set.add(date)
            new_count += 1

    # 按日期排序
    if existing_dates and new_count > 0:
        paired = sorted(zip(existing_dates, existing_prices), key=lambda x: x[0])
        existing_dates = [p[0] for p in paired]
        existing_prices = [p[1] for p in paired]

    history_data = {
        "code": code,
        "prices": existing_prices,
        "dates": existing_dates,
        "count": len(existing_prices),
        "source": source,
        "updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }

    save_json(history_file, history_data)
    return new_count


def load_etf_history(code):
    """加载单只ETF历史K线"""
    # 优先从独立文件读取
    history_file = HISTORY_DIR / f"{code}.json"
    data = load_json(history_file)
    if data:
        return data

    # 回退：从旧的全局缓存文件读取
    cache = load_json(LEGACY_FILES["history_cache"]) or {}
    return cache.get(code)


def migrate_history_cache():
    """将旧的 etf_history_cache.json 迁移到独立文件"""
    cache = load_json(LEGACY_FILES["history_cache"])
    if not cache:
        log("无需迁移：历史缓存为空或不存在")
        return 0

    _ensure_dirs()
    migrated = 0
    for code, entry in cache.items():
        if isinstance(entry, dict) and "prices" in entry:
            prices = entry["prices"]
            dates = entry.get("dates", [])
            if prices:
                history_file = HISTORY_DIR / f"{code}.json"
                if not history_file.exists():
                    history_data = {
                        "code": code,
                        "prices": prices,
                        "dates": dates,
                        "count": len(prices),
                        "source": entry.get("source", "akshare"),
                        "updated": entry.get("updated", ""),
                    }
                    save_json(history_file, history_data)
                    migrated += 1

    log(f"历史数据迁移: {migrated} 只ETF → data/history/")
    return migrated


# ============ 实时数据缓存 ============

def save_realtime(category, data):
    """保存实时数据到缓存"""
    _ensure_dirs()
    cache_file = REALTIME_DIR / f"{category}.json"
    save_json(cache_file, data)

    # 同时更新根目录的兼容文件（确保旧代码仍可运行）
    compat_map = {
        "prices": LEGACY_FILES["prices"],
        "metrics": LEGACY_FILES["metrics"],
        "generated": LEGACY_FILES["generated"],
        "yingmi": LEGACY_FILES["yingmi"],
    }
    if category in compat_map:
        save_json(compat_map[category], data)


def load_realtime(category, max_age_hours=168):
    """加载实时数据缓存（带过期检查）"""
    cache_file = REALTIME_DIR / f"{category}.json"

    # 优先从 realtime/ 读取
    if cache_file.exists():
        mtime = datetime.fromtimestamp(cache_file.stat().st_mtime)
        if datetime.now() - mtime < timedelta(hours=max_age_hours):
            return load_json(cache_file)

    # 回退：从根目录旧文件读取
    compat_map = {
        "prices": LEGACY_FILES["prices"],
        "metrics": LEGACY_FILES["metrics"],
        "generated": LEGACY_FILES["generated"],
        "yingmi": LEGACY_FILES["yingmi"],
        "standard": LEGACY_FILES["standard"],
    }
    if category in compat_map:
        return load_json(compat_map[category])

    return None


# ============ 数据完整性校验 ============

def verify_data_integrity():
    """校验数据完整性，返回诊断报告"""
    report = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "files": {},
        "issues": [],
        "summary": {},
    }

    # 检查所有核心数据文件
    for key, path in LEGACY_FILES.items():
        exists = path.exists()
        size = path.stat().st_size if exists else 0
        data = load_json(path) if exists else None

        file_info = {
            "exists": exists,
            "size_kb": round(size / 1024) if size else 0,
            "count": len(data) if data else 0,
        }

        if key == "standard" and data:
            file_info["has_price"] = sum(1 for e in data if e.get("close", 0) > 0)
            file_info["has_return"] = sum(1 for e in data if e.get("year_1_return", 0) != 0)
            file_info["has_sharpe"] = sum(1 for e in data if e.get("sharpe_ratio", 0) != 0)
            file_info["has_holdings"] = sum(1 for e in data if e.get("top_holdings"))
            file_info["has_issuer"] = sum(1 for e in data if e.get("issuer"))

        report["files"][key] = file_info

    # 检查快照
    snapshots = list(SNAPSHOTS_DIR.glob("v_*.json"))
    report["summary"]["snapshot_count"] = len(snapshots)
    report["summary"]["latest_snapshot"] = max(
        (s.stem for s in snapshots), default="none"
    )

    # 检查历史数据
    history_files = list(HISTORY_DIR.glob("*.json"))
    report["summary"]["history_etf_count"] = len(history_files)

    # 检查备份
    daily_backups = list(BACKUP_DAILY_DIR.glob("*.json"))
    weekly_backups = list(BACKUP_WEEKLY_DIR.glob("*.json.gz"))
    report["summary"]["daily_backup_count"] = len(daily_backups)
    report["summary"]["weekly_backup_count"] = len(weekly_backups)

    # 问题检测
    std = report["files"].get("standard", {})
    if not std.get("exists"):
        report["issues"].append("核心数据文件 etf_standard_data.json 不存在")
    elif std.get("count", 0) == 0:
        report["issues"].append("核心数据文件为空")
    if std.get("has_price", 0) < std.get("count", 1) * 0.9:
        report["issues"].append(f"价格覆盖率低: {std.get('has_price', 0)}/{std.get('count', 0)}")

    return report


# ============ 初始化 ============

def init_store():
    """初始化本地存储：迁移旧数据 + 创建首次快照"""
    _ensure_dirs()
    log("初始化本地数据存储...")

    # 1. 迁移历史缓存到独立文件
    migrated = migrate_history_cache()
    log(f"历史数据迁移: {migrated} 只")

    # 2. 创建首次快照
    standard = load_json(LEGACY_FILES["standard"]) or []
    if standard:
        create_snapshot("init")
        log("首次版本快照已创建")
    else:
        log("无标准数据，跳过快照")

    # 3. 创建首次备份
    create_backup()

    # 4. 校验数据完整性
    report = verify_data_integrity()
    if report["issues"]:
        log(f"数据问题: {len(report['issues'])} 个")
        for issue in report["issues"]:
            log(f"  - {issue}")
    else:
        log("数据完整性校验通过")

    return report


# ============ CLI ============

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("用法: python local_store.py [init|snapshot|backup|verify|migrate|report]")
        sys.exit(0)

    cmd = sys.argv[1]

    if cmd == "init":
        init_store()
    elif cmd == "snapshot":
        step = sys.argv[2] if len(sys.argv) > 2 else "manual"
        create_snapshot(step)
    elif cmd == "backup":
        create_backup()
    elif cmd == "verify":
        report = verify_data_integrity()
        print(json.dumps(report, indent=2, ensure_ascii=False))
    elif cmd == "migrate":
        migrate_history_cache()
    elif cmd == "report":
        report = verify_data_integrity()
        print(f"\n=== 数据存储报告 ===")
        print(f"时间: {report['timestamp']}")
        print(f"\n核心文件:")
        for key, info in report["files"].items():
            status = "✅" if info["exists"] else "❌"
            print(f"  {status} {key}: {info.get('count', 0)} 条, {info.get('size_kb', 0)} KB")
        print(f"\n快照: {report['summary'].get('snapshot_count', 0)} 个")
        print(f"历史: {report['summary'].get('history_etf_count', 0)} 只ETF")
        print(f"日备: {report['summary'].get('daily_backup_count', 0)} 个")
        print(f"周备: {report['summary'].get('weekly_backup_count', 0)} 个")
        if report["issues"]:
            print(f"\n问题:")
            for issue in report["issues"]:
                print(f"  ⚠️ {issue}")
