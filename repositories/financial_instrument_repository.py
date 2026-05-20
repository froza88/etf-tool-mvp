"""
金融工具 Repository 抽象接口（通用）
定义所有金融工具数据访问的通用接口，支持多种数据源实现
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Any, TypeVar, Generic
from datetime import datetime

from models.financial_instrument import FinancialInstrument, InstrumentType


T = TypeVar('T', bound=FinancialInstrument)


class FinancialInstrumentRepository(ABC, Generic[T]):
    """
    金融工具数据访问抽象接口（通用）
    
    所有金融工具（ETF、股票、期货等）的 Repository 都应继承此类
    实现类必须提供以下方法：
    - get_all: 获取所有数据
    - get_by_code: 根据代码获取单个对象
    - filter: 根据条件筛选
    - get_history: 获取历史数据
    """
    
    @abstractmethod
    def get_all(self) -> List[T]:
        """
        获取所有金融工具数据
        
        Returns:
            List[T]: 金融工具列表
        """
        pass
    
    @abstractmethod
    def get_by_code(self, code: str) -> Optional[T]:
        """
        根据代码获取单个金融工具
        
        Args:
            code: 金融工具代码（如 "510300"）
            
        Returns:
            Optional[T]: 金融工具对象，如果不存在返回 None
        """
        pass
    
    @abstractmethod
    def filter(self, filters: Dict[str, Any]) -> List[T]:
        """
        根据条件筛选金融工具
        
        Args:
            filters: 筛选条件字典，通用字段包括：
                - instrument_type: 工具类型（InstrumentType）
                - keyword: 关键词搜索（名称/代码）
                - price_min/price_max: 价格范围
                - scale_min/scale_max: 规模范围
                - return_min/return_max: 收益率范围
                - sort_by: 排序字段
                - sort_order: 排序方向（asc/desc）
                - page: 页码
                - page_size: 每页数量
                
        Returns:
            List[T]: 筛选后的金融工具列表
        """
        pass
    
    @abstractmethod
    def get_history(self, code: str, period: str = '1Y') -> Dict[str, Any]:
        """
        获取历史数据
        
        Args:
            code: 金融工具代码
            period: 时间周期（'1M'/'3M'/'1Y'/'3Y'/'5Y'）
            
        Returns:
            Dict: 历史数据，包含 dates, prices, volumes 等字段
        """
        pass
    
    @abstractmethod
    def save(self, instrument: T) -> None:
        """
        保存/更新金融工具数据（写回本地存储）
        
        Args:
            instrument: 金融工具对象
        """
        pass
    
    @abstractmethod
    def save_batch(self, instruments: List[T]) -> None:
        """
        批量保存金融工具数据
        
        Args:
            instruments: 金融工具对象列表
        """
        pass
    
    # ========== 默认实现（子类可选覆盖）==========
    
    def search(self, keyword: str, limit: int = 10) -> List[T]:
        """
        搜索金融工具（默认实现：在 get_all 结果中过滤）
        
        Args:
            keyword: 搜索关键词
            limit: 返回数量限制
            
        Returns:
            List[T]: 匹配的金融工具列表
        """
        all_items = self.get_all()
        keyword_lower = keyword.lower()
        results = []
        for item in all_items:
            name = item.name.lower() if item.name else ''
            code = item.code.lower() if item.code else ''
            if keyword_lower in name or keyword_lower in code:
                results.append(item)
                if len(results) >= limit:
                    break
        return results
    
    def get_by_type(self, instrument_type: InstrumentType) -> List[T]:
        """
        根据类型获取金融工具列表
        
        Args:
            instrument_type: 工具类型
            
        Returns:
            List[T]: 指定类型的金融工具列表
        """
        return self.filter({'instrument_type': instrument_type})
    
    def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """
        统计符合条件的金融工具数量
        
        Args:
            filters: 筛选条件（可选）
            
        Returns:
            int: 数量
        """
        items = self.filter(filters or {})
        return len(items)


class CompositeFinancialInstrumentRepository(FinancialInstrumentRepository[T]):
    """
    组合 Repository（通用）
    
    实现"本地优先 + 在线兜底"策略：
    1. 先查主 Repository（通常是本地存储）
    2. 如果主 Repository 没有，查备用 Repository（在线 API）
    3. 查到后写回主 Repository（缓存）
    """
    
    def __init__(
        self,
        primary: FinancialInstrumentRepository[T],
        fallbacks: List[FinancialInstrumentRepository[T]]
    ):
        """
        初始化组合 Repository
        
        Args:
            primary: 主 Repository（优先查询，通常是本地存储）
            fallbacks: 备用 Repository 列表（兜底查询，通常是在线 API）
        """
        self.primary = primary
        self.fallbacks = fallbacks
        self._stats = {
            'primary_hits': 0,
            'fallback_hits': 0,
            'fallback_errors': 0,
            'cache_writes': 0
        }
    
    def get_all(self) -> List[T]:
        """获取所有：从主 Repository 获取"""
        return self.primary.get_all()
    
    def get_by_code(self, code: str) -> Optional[T]:
        """
        根据代码获取：先查主，再查备用
        
        策略：
        1. 先查 primary
        2. 如果 primary 没有，依次查 fallbacks
        3. 查到后 save 到 primary（缓存）
        """
        # 1. 先查主 Repository
        item = self.primary.get_by_code(code)
        if item is not None:
            self._stats['primary_hits'] += 1
            return item
        
        # 2. 主 Repository 没有，查备用
        for fallback in self.fallbacks:
            try:
                item = fallback.get_by_code(code)
                if item is not None:
                    # 3. 查到后写回主 Repository（缓存）
                    self.primary.save(item)
                    self._stats['fallback_hits'] += 1
                    self._stats['cache_writes'] += 1
                    return item
            except Exception as e:
                print(f"[CompositeRepo] Fallback error: {e}")
                self._stats['fallback_errors'] += 1
        
        # 4. 都找不到
        return None
    
    def filter(self, filters: Dict[str, Any]) -> List[T]:
        """筛选：从主 Repository 筛选（备用太慢，不支持批量）"""
        return self.primary.filter(filters)
    
    def get_history(self, code: str, period: str = '1Y') -> Dict[str, Any]:
        """
        获取历史：先查主，再查备用
        
        策略：
        1. 先查 primary
        2. 如果 primary 没有或数据不足，查 fallbacks
        3. 查到后可选 save 到 primary
        """
        # 1. 先查主 Repository
        try:
            history = self.primary.get_history(code, period)
            if history and history.get('dates'):
                self._stats['primary_hits'] += 1
                return history
        except Exception as e:
            print(f"[CompositeRepo] Primary history error: {e}")
        
        # 2. 主 Repository 没有，查备用
        for fallback in self.fallbacks:
            try:
                history = fallback.get_history(code, period)
                if history and history.get('dates'):
                    self._stats['fallback_hits'] += 1
                    return history
            except Exception as e:
                print(f"[CompositeRepo] Fallback history error: {e}")
                self._stats['fallback_errors'] += 1
        
        # 3. 都找不到，返回空
        return {'dates': [], 'prices': [], 'source': 'none'}
    
    def save(self, instrument: T) -> None:
        """保存：只保存到主 Repository"""
        self.primary.save(instrument)
        self._stats['cache_writes'] += 1
    
    def save_batch(self, instruments: List[T]) -> None:
        """批量保存：只保存到主 Repository"""
        self.primary.save_batch(instruments)
        self._stats['cache_writes'] += len(instruments)
    
    def get_stats(self) -> Dict[str, int]:
        """获取统计信息"""
        return self._stats.copy()
