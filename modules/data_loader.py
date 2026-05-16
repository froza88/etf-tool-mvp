"""
数据加载模块 - JSON 文件加载 + 缓存
"""
import json
from pathlib import Path
from datetime import datetime, timedelta
import os


class JsonLoader:
    """JSON 数据加载器（带缓存和时效检查）"""

    def __init__(self):
        self._cache = {}

    def load(self, filepath, max_age_hours=None):
        """
        加载 JSON 文件
        max_age_hours: 文件过期时间，None=不过期
        """
        fp = str(filepath)
        # 检查缓存
        if fp in self._cache:
            return self._cache[fp]

        # 检查时效
        if max_age_hours is not None:
            path = Path(fp)
            if not path.exists():
                return None
            mtime = datetime.fromtimestamp(os.path.getmtime(path))
            age = datetime.now() - mtime
            if age > timedelta(hours=max_age_hours):
                return None

        with open(fp, 'r', encoding='utf-8') as f:
            data = json.load(f)
        self._cache[fp] = data
        return data

    def invalidate(self, filepath):
        """清除缓存"""
        self._cache.pop(str(filepath), None)

    def clear(self):
        """清空所有缓存"""
        self._cache.clear()
