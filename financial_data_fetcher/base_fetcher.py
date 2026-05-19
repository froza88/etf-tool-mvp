#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BaseFetcher - 基础数据获取器（抽象类）

所有金融工具的数据获取器都继承此类。
提供：重试机制、缓存管理、数据验证、多源降级。
"""

import time
import json
from abc import ABC, abstractmethod
from pathlib import Path
from datetime import datetime


class BaseFetcher(ABC):
    """基础数据获取器抽象类"""

    def __init__(self, data_type, cache_dir=None):
        """
        Args:
            data_type: 数据类型（'etf', 'stock', 'fund', 'future', 'forex'）
            cache_dir: 缓存目录（默认 data/<data_type>/）
        """
        self.data_type = data_type
        self.cache_dir = Path(cache_dir) if cache_dir else Path(f"data/{data_type}")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.sources = self._load_sources()
        self.rate_limiter = None  # 由子类设置

    @abstractmethod
    def _load_sources(self):
        """加载数据源配置（子类实现）"""
        pass

    @abstractmethod
    def fetch_realtime(self, code, fields=None):
        """实时获取数据（子类实现，调用具体API）"""
        pass

    @abstractmethod
    def fetch_history(self, code, start_date=None, end_date=None):
        """获取历史数据（子类实现）"""
        pass

    # ============ 通用方法（子类可直接用） ===========

    def get_from_cache(self, code):
        """从本地缓存读取数据"""
        cache_file = self.cache_dir / f"{code}.json"
        if not cache_file.exists():
            return None
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None

    def save_to_cache(self, code, data):
        """保存到本地缓存（永久存储）"""
        cache_file = self.cache_dir / f"{code}.json"
        data["_cached_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def fetch_with_cache(self, code, fields=None, max_age_hours=168):
        """
        获取数据的统一入口：缓存优先 → 实时获取 → 降级
        Args:
            code: 产品代码
            fields: 需要的字段列表（None=全部）
            max_age_hours: 缓存最大年龄（小时），默认7天
        Returns:
            dict: 数据字典
        """
        # 1. 尝试从缓存读取
        cached = self.get_from_cache(code)
        if cached and self._is_cache_valid(cached, max_age_hours):
            return cached

        # 2. 缓存无效/不存在，实时获取
        try:
            data = self.fetch_realtime(code, fields)
            if data:
                self.save_to_cache(code, data)
                return data
        except Exception as e:
            print(f"  实时获取失败 [{code}]: {e}")

        # 3. 实时获取失败，降级用缓存（即使过期）
        if cached:
            print(f"  降级使用过期缓存 [{code}]")
            return cached

        return None

    def _is_cache_valid(self, cached_data, max_age_hours):
        """检查缓存是否有效（未过期）"""
        cached_at = cached_data.get("_cached_at", "")
        if not cached_at:
            return False
        try:
            dt = datetime.strptime(cached_at, "%Y-%m-%d %H:%M:%S")
            age_hours = (datetime.now() - dt).total_seconds() / 3600
            return age_hours <= max_age_hours
        except Exception:
            return False

    def fetch_multi_source(self, code, fields=None):
        """
        多源获取：按优先级尝试多个数据源
        子类可重写此方法来定义具体的数据源优先级
        """
        # 默认实现：先缓存，再实时
        return self.fetch_with_cache(code, fields)

    def validate(self, data, fields=None):
        """验证数据有效性（子类可重写）"""
        if not data:
            return False
        if fields:
            return all(data.get(f) is not None for f in fields)
        return True

    def retry_with_backoff(self, func, *args, max_retries=3, **kwargs):
        """带指数退避的重试"""
        for attempt in range(max_retries):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if attempt == max_retries - 1:
                    raise
                wait = 2 ** attempt  # 1, 2, 4 秒
                print(f"  重试 {attempt+1}/{max_retries}，等待 {wait}s: {e}")
                time.sleep(wait)
