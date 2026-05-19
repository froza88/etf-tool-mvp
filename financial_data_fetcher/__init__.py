#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
financial_data_fetcher - 金融数据通用获取框架（四层架构第1层：数据采集层）

提供统一的多源数据获取、缓存管理、限流控制、数据验证能力。
可被ETF/股票/基金/期货/外汇等所有金融工具复用。

目录结构：
  __init__.py
  base_fetcher.py        # 基础获取器（重试、缓存、验证）
  multi_source_fetcher.py  # 多源数据获取器
  cache_manager.py       # 缓存管理器
  rate_limiter.py        # 限流管理器
  data_validator.py      # 数据验证器
"""

from .base_fetcher import BaseFetcher
from .multi_source_fetcher import MultiSourceFetcher
from .cache_manager import CacheManager
from .rate_limiter import RateLimiter
from .data_validator import DataValidator

__all__ = [
    'BaseFetcher',
    'MultiSourceFetcher',
    'CacheManager',
    'RateLimiter',
    'DataValidator',
]
