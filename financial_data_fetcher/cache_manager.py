#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CacheManager - 缓存管理器

管理多地缓存（本地 + GitHub + PythonAnywhere）。
每次数据更新后，同步到三地的缓存。
"""

import json
from pathlib import Path
from datetime import datetime


class CacheManager:
    """缓存管理器"""

    def __init__(self, local_dir="data/cache"):
        self.local_dir = Path(local_dir)
        self.local_dir.mkdir(parents=True, exist_ok=True)

    def save_local(self, key, data):
        """保存到本地缓存"""
        cache_file = self.local_dir / f"{key}.json"
        data["_cached_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def load_local(self, key, max_age_hours=168):
        """从本地缓存加载"""
        cache_file = self.local_dir / f"{key}.json"
        if not cache_file.exists():
            return None
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            cached_at = data.get("_cached_at", "")
            if cached_at:
                dt = datetime.strptime(cached_at, "%Y-%m-%d %H:%M:%S")
                age_hours = (datetime.now() - dt).total_seconds() / 3600
                if age_hours > max_age_hours:
                    return None
            return data
        except Exception:
            return None

    def sync_to_github(self, files):
        """同步文件到GitHub（git add + commit + push）"""
        import subprocess
        repo_dir = str(Path(__file__).parent.parent.parent)
        for f in files:
            subprocess.run(["git", "add", f], cwd=repo_dir, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", f"cache: sync {len(files)} files"],
            cwd=repo_dir, capture_output=True
        )
        subprocess.run(["git", "push", "origin", "main"], cwd=repo_dir, capture_output=True)

    def trigger_pa_sync(self, pa_url="https://froza.pythonanywhere.com"):
        """触发PythonAnywhere同步"""
        try:
            import requests
            resp = requests.post(f"{pa_url}/api/sync", timeout=10)
            return resp.status_code == 200
        except Exception:
            return False
