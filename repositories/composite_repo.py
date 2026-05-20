"""
CompositeRepo - 组合 Repository 实现

实现"本地优先、在线兜底"策略：
1. 先查本地 Repository（快、稳）
2. 本地没有则查在线 Repository（鲜、全）
3. 在线也失败则查备用 Repository（容错）

所有 Repository 都必须实现 ETFRepository 接口。
"""

import json
import sys
import time
from pathlib import Path
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta

from .etf_repository import ETFRepository
from .financial_instrument_repository import CompositeFinancialInstrumentRepository, FinancialInstrumentRepository


class CompositeRepo(CompositeFinancialInstrumentRepository[Any], ETFRepository):
    """
    组合 Repository - 实现多数据源 fallback 策略
    
    继承 CompositeFinancialInstrumentRepository（已实现通用方法）
    同时继承 ETFRepository（需要实现的 ETF 特有方法）
    
    使用方式：
    ```python
    local_repo = LocalJSONRepo()
    neodata_repo = NeoDataRepo()
    westock_repo = WestockRepo()
    
    repo = CompositeRepo(
        primary=local_repo,
        fallbacks=[neodata_repo, westock_repo],
        cache_write=True  # 在线数据写入本地缓存
    )
    ```
    
    查询策略：
    - get_etf_by_code: 先查 primary，没有则依次查 fallbacks，查到后写入 primary 缓存
    - get_all_etfs: 直接查 primary（全量数据本地应该有）
    - filter_etfs: 直接查 primary（筛选条件本地可满足）
    - get_etf_history: 先查 primary，没有则查 fallbacks，查到后写入缓存
    """
    
    def __init__(
        self,
        primary: FinancialInstrumentRepository[Any],
        fallbacks: List[FinancialInstrumentRepository[Any]] = None,
        cache_write: bool = True,
        cache_ttl: int = 86400  # 缓存有效期（秒），默认 1 天
    ):
        """
        初始化 CompositeRepo
        
        Args:
            primary: 主数据源（通常是本地 JSON）
            fallbacks: 备用数据源列表（按顺序尝试）
            cache_write: 是否将在线数据写入本地缓存
            cache_ttl: 缓存有效期（秒），超过则重新从在线获取
        """
        CompositeFinancialInstrumentRepository.__init__(
            self, primary, fallbacks or []
        )
        self.cache_write = cache_write
        self.cache_ttl = cache_ttl
        
        # 统计信息（覆盖父类的 stats）
        self.stats = {
            'primary_hits': 0,
            'fallback_hits': 0,
            'fallback_errors': 0,
            'cache_writes': 0
        }
    
    # ========= ETFRepository 抽象方法实现 =========
    
    def get_all_etfs(self) -> List[Dict]:
        """
        获取所有 ETF（直接查 primary）
        
        全量数据应该从本地获取，不需要 fallback
        """
        # 直接调用 ETFRepository 接口方法
        return self.primary.get_all_etfs()
    
    def get_etf_by_code(self, code: str) -> Optional[Dict]:
        """
        根据代码获取 ETF（先查 primary，没有则 fallback）
        
        策略：
        1. 查 primary
        2. 如果 primary 有且未过期，直接返回
        3. 如果 primary 没有或已过期，依次查 fallbacks
        4. 查到后，写入 primary 缓存
        """
        # 1. 查 primary
        item = self.primary.get_etf_by_code(code)
        
        # 2. 检查是否过期（如果有 timestamp 字段）
        if item is not None:
            if not self._is_cache_expired(item):
                self.stats['primary_hits'] += 1
                return item
            # 过期了，继续查 fallbacks
        
        # 3. 依次查 fallbacks
        for i, repo in enumerate(self.fallbacks):
            try:
                item = repo.get_etf_by_code(code)
                if item is not None:
                    self.stats['fallback_hits'] += 1
                    
                    # 4. 写入 primary 缓存
                    if self.cache_write:
                        self._write_to_cache(code, item)
                        self.stats['cache_writes'] += 1
                    
                    return item
            except Exception as e:
                print(f"[CompositeRepo] Fallback repo {i} error: {e}", file=sys.stderr)
                self.stats['fallback_errors'] += 1
                continue
        
        # 所有数据源都失败了
        return None
    
    def filter_etfs(self, filters: Dict[str, Any]) -> List[Dict]:
        """
        筛选 ETF（直接查 primary）
        
        筛选条件通常基于本地数据就能满足
        """
        return self.primary.filter_etfs(filters)
    
    def get_etf_history(self, code: str, period: str = "1y") -> Dict:
        """
        获取历史数据（先查 primary，没有则 fallback）
        """
        # 1. 查 primary
        history = self.primary.get_etf_history(code, period)
        
        # 2. 检查是否有有效数据
        if history and history.get('prices') and len(history['prices']) > 0:
            self.stats['primary_hits'] += 1
            return history
        
        # 3. 依次查 fallbacks
        for i, repo in enumerate(self.fallbacks):
            try:
                history = repo.get_etf_history(code, period)
                if history and history.get('prices') and len(history['prices']) > 0:
                    self.stats['fallback_hits'] += 1
                    return history
            except Exception as e:
                print(f"[CompositeRepo] Fallback repo {i} error: {e}", file=sys.stderr)
                self.stats['fallback_errors'] += 1
                continue
        
        # 所有数据源都失败了，返回空数据
        return {'prices': [], 'dates': [], 'source': 'error'}
    
    def _is_cache_expired(self, etf: Dict) -> bool:
        """
        检查缓存是否过期
        
        判断逻辑：
        1. 有 timestamp 字段且超过 cache_ttl 秒 → 过期
        2. 有 data_date 字段且不是今天 → 过期（可选）
        3. 其他情况 → 未过期
        """
        # 检查 timestamp
        timestamp = etf.get('_timestamp')
        if timestamp is not None:
            try:
                age = time.time() - timestamp
                if age > self.cache_ttl:
                    return True
            except (TypeError, ValueError):
                pass
        
        # 检查 data_date（可选）
        data_date = etf.get('_data_date')
        if data_date is not None:
            today = datetime.now().strftime('%Y-%m-%d')
            if data_date != today:
                return True
        
        return False
    
    def _write_to_cache(self, code: str, etf: Dict):
        """
        将在线数据写入本地缓存
        
        写入 data/neodata_cache/{code}.json，pipeline 后期整合时读取这些文件
        填充到主数据集的缺失字段中。
        """
        etf['_timestamp'] = int(time.time())
        etf['_data_date'] = datetime.now().strftime('%Y-%m-%d')
        etf['_source'] = 'fallback_cache'
        
        try:
            cache_dir = Path(self.primary.root) / "data" / "neodata_cache" \
                if hasattr(self.primary, 'root') else Path("data/neodata_cache")
            cache_dir.mkdir(parents=True, exist_ok=True)
            cache_file = cache_dir / f"{code}.json"
            
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(etf, f, ensure_ascii=False, indent=2, default=str)
            print(f"[CompositeRepo] Wrote {code} to cache ({cache_file})", file=sys.stderr)
        except Exception as e:
            print(f"[CompositeRepo] Failed to write {code} to cache: {e}", file=sys.stderr)
    
    # ========= ETFRepository 其余抽象方法（暂返回空）=========
    
    def get_etf_by_category(self, category: str) -> List[Dict]:
        """根据分类查询ETF（暂返回空列表）"""
        return []
    
    def get_etf_by_tracking_index(self, index_code: str) -> List[Dict]:
        """根据跟踪指数查询ETF（暂返回空列表）"""
        return []
    
    def get_etf_holdings(self, code: str) -> List[Dict]:
        """获取ETF持仓明细（暂返回空列表）"""
        return []
    
    def get_stats(self) -> Dict:
        """获取统计信息"""
        return self.stats.copy()
    
    def reset_stats(self):
        """重置统计信息"""
        self.stats = {
            'primary_hits': 0,
            'fallback_hits': 0,
            'fallback_errors': 0,
            'cache_writes': 0
        }
