"""
fetchers 包 - 统一封装所有外部数据源调用
核心原则：查询即存储 - 每次外部API调用都立即持久化到本地
"""

from pathlib import Path

# 项目根目录
ROOT = Path(__file__).parent.parent

# 缓存目录
CACHE_DIR = ROOT / "data" / "cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# 缓存有效期（天）
DEFAULT_CACHE_DAYS = 7
