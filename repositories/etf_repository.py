"""
ETF Repository 抽象接口
定义数据访问层的标准接口，支持多种数据源实现
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Any


class ETFRepository(ABC):
    """
    ETF 数据访问抽象接口
    
    实现类必须提供以下方法：
    - get_all_etfs: 获取所有 ETF 数据
    - get_etf_by_code: 根据代码获取单个 ETF
    - filter_etfs: 根据条件筛选 ETF
    - get_etf_history: 获取 ETF 历史净值数据
    """
    
    @abstractmethod
    def get_all_etfs(self) -> List[Dict]:
        """
        获取所有 ETF 数据
        
        Returns:
            List[Dict]: ETF 列表，每个 ETF 是一个字典
        """
        pass
    
    @abstractmethod
    def get_etf_by_code(self, code: str) -> Optional[Dict]:
        """
        根据代码获取单个 ETF
        
        Args:
            code: ETF 代码（如 "510300"）
            
        Returns:
            Optional[Dict]: ETF 数据，如果不存在返回 None
        """
        pass
    
    @abstractmethod
    def filter_etfs(self, filters: Dict[str, Any]) -> List[Dict]:
        """
        根据条件筛选 ETF
        
        Args:
            filters: 筛选条件字典，可能包含：
                - type: ETF 类型（如 "股票型"）
                - scale_min/scale_max: 规模范围
                - return_min: 最低收益率
                - category: 分类（如 "宽基"）
                - keyword: 关键词搜索
                
        Returns:
            List[Dict]: 筛选后的 ETF 列表
        """
        pass
    
    @abstractmethod
    def get_etf_history(self, code: str, period: str = '1Y') -> Dict:
        """
        获取 ETF 历史净值数据
        
        Args:
            code: ETF 代码
            period: 时间周期（'1M'/'3M'/'1Y'/'3Y'）
            
        Returns:
            Dict: 历史数据，包含 prices, dates, source 等字段
        """
        pass
    
    def search_etfs(self, keyword: str) -> List[Dict]:
        """
        搜索 ETF（默认实现：在 all_etfs 中过滤）
        
        Args:
            keyword: 搜索关键词
            
        Returns:
            List[Dict]: 匹配的 ETF 列表
        """
        all_etfs = self.get_all_etfs()
        keyword_lower = keyword.lower()
        results = []
        for etf in all_etfs:
            name = etf.get('name', '').lower()
            code = etf.get('code', '').lower()
            if keyword_lower in name or keyword_lower in code:
                results.append(etf)
        return results
