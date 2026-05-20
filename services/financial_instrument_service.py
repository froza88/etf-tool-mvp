"""
金融工具 Service 抽象接口（通用）
定义所有金融工具业务逻辑的通用接口，支持多类型扩展
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Any, TypeVar, Generic
from datetime import datetime

from models.financial_instrument import FinancialInstrument, InstrumentType


T = TypeVar('T', bound=FinancialInstrument)


class FinancialInstrumentQueryService(ABC, Generic[T]):
    """
    金融工具查询服务（通用）
    
    职责：
    - 获取金融工具列表（支持筛选、排序、分页）
    - 获取单个金融工具详情
    - 搜索金融工具（关键词）
    """
    
    @abstractmethod
    def get_list(
        self,
        filters: Optional[Dict[str, Any]] = None,
        sort_by: str = 'code',
        sort_order: str = 'asc',
        page: int = 1,
        page_size: int = 50
    ) -> Dict[str, Any]:
        """
        获取金融工具列表（支持筛选、排序、分页）
        
        返回格式：
        {
            "total": 100,
            "page": 1,
            "page_size": 50,
            "total_pages": 2,
            "items": [...]  # 精简字段列表
        }
        """
        pass
    
    @abstractmethod
    def get_detail(self, code: str) -> Optional[Dict[str, Any]]:
        """
        获取单个金融工具详情（完整字段）
        
        返回格式：
        {
            "code": "510300",
            "name": "沪深300ETF",
            "instrument_type": "etf",
            ... # 所有字段
        }
        """
        pass
    
    @abstractmethod
    def search(self, keyword: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        搜索金融工具（关键词匹配名称和代码）
        
        返回格式：
        [{"code": "510300", "name": "沪深300ETF", "instrument_type": "etf"}, ...]
        """
        pass
    
    @abstractmethod
    def get_by_type(self, instrument_type: InstrumentType, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        根据类型获取金融工具列表
        
        Args:
            instrument_type: 工具类型
            filters: 额外筛选条件
            
        返回格式：
        [{"code": "...", "name": "...", ...}, ...]
        """
        pass


class FinancialInstrumentCompareService(ABC, Generic[T]):
    """
    金融工具对比服务（通用）
    
    职责：
    - 对比多只金融工具的关键指标
    - 生成对比表格数据
    - 计算评分/排名
    """
    
    @abstractmethod
    def compare(self, codes: List[str], metrics: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        对比多只金融工具
        
        Args:
            codes: 金融工具代码列表
            metrics: 对比指标列表（可选，默认使用常用指标）
            
        返回格式：
        {
            "items": [...],  # 金融工具列表
            "metrics": [...],  # 对比指标列表
            "table": [[...], ...]  # 对比表格（二维数组）
        }
        """
        pass
    
    @abstractmethod
    def get_compare_metrics(self, instrument_type: InstrumentType) -> List[str]:
        """
        获取可对比的指标列表（按类型）
        
        Args:
            instrument_type: 工具类型
            
        返回格式：
        ["return_1y", "sharpe_ratio", "max_drawdown", ...]
        """
        pass
    
    @abstractmethod
    def rank(self, codes: List[str], metric: str, ascending: bool = False) -> List[Dict[str, Any]]:
        """
        对金融工具按指标排名
        
        Args:
            codes: 金融工具代码列表
            metric: 排名指标
            ascending: 是否升序（默认降序，越大越好）
            
        返回格式：
        [{"code": "510300", "name": "沪深300ETF", "value": 0.15, "rank": 1}, ...]
        """
        pass


class FinancialInstrumentHistoryService(ABC, Generic[T]):
    """
    金融工具历史数据服务（通用）
    
    职责：
    - 获取历史价格/净值数据
    - 计算收益率曲线
    - 生成图表数据
    """
    
    @abstractmethod
    def get_history(
        self,
        code: str,
        period: str = '1Y',
        normalized: bool = True
    ) -> Dict[str, Any]:
        """
        获取历史数据
        
        Args:
            code: 金融工具代码
            period: 时间周期（'1M'/'3M'/'1Y'/'3Y'/'5Y'）
            normalized: 是否归一化（便于对比）
            
        返回格式：
        {
            "code": "510300",
            "period": "1Y",
            "dates": ["2025-01-01", ...],
            "prices": [1.0, 1.02, ...],  # 归一化或原始价格
            "volumes": [1000000, ...],  # 成交量（可选）
            "source": "local_cache" | "online_api" | "simulated"
        }
        """
        pass
    
    @abstractmethod
    def get_multiple_history(
        self,
        codes: List[str],
        period: str = '1Y',
        normalized: bool = True
    ) -> Dict[str, Any]:
        """
        获取多只金融工具的历史数据（用于对比走势图）
        
        Args:
            codes: 金融工具代码列表
            period: 时间周期
            normalized: 是否归一化
            
        返回格式：
        {
            "codes": ["510300", "510500"],
            "period": "1Y",
            "data": {
                "510300": {"dates": [...], "prices": [...]},
                "510500": {"dates": [...], "prices": [...]}
            }
        }
        """
        pass
    
    @abstractmethod
    def calculate_return(self, code: str, period: str = '1Y') -> float:
        """
        计算收益率
        
        Args:
            code: 金融工具代码
            period: 时间周期
            
        Returns:
            float: 收益率（如 0.15 表示 15%）
        """
        pass


class FinancialInstrumentScreeningService(ABC, Generic[T]):
    """
    金融工具筛选服务（通用）
    
    职责：
    - 执行多步筛选流程
    - 生成筛选报告
    - 推荐最优金融工具
    """
    
    @abstractmethod
    def screen(
        self,
        criteria: List[Dict[str, Any]],
        instrument_type: Optional[InstrumentType] = None
    ) -> Dict[str, Any]:
        """
        执行筛选流程
        
        Args:
            criteria: 筛选条件列表，每个条件是一个字典：
                {
                    "step": 1,
                    "name": "规模过滤",
                    "criteria": "规模 >= 10亿",
                    "filter": {"scale_min": 10}
                }
            instrument_type: 工具类型（可选，用于限定筛选范围）
        
        返回格式：
        {
            "total_count": 100,
            "instrument_type": "etf",
            "steps": [
                {
                    "step": 1,
                    "name": "规模过滤",
                    "criteria": "规模 >= 10亿",
                    "passed": [...],  # 通过的金融工具
                    "eliminated_count": 50
                },
                ...
            ],
            "winner": {...}  # 最终推荐
        }
        """
        pass
    
    @abstractmethod
    def get_default_criteria(self, instrument_type: InstrumentType) -> List[Dict[str, Any]]:
        """
        获取默认筛选条件
        
        Args:
            instrument_type: 工具类型
            
        返回格式：
        [
            {"step": 1, "name": "规模过滤", "criteria": "规模 >= 10亿", "filter": {...}},
            ...
        ]
        """
        pass
    
    @abstractmethod
    def get_available_filters(self, instrument_type: InstrumentType) -> List[Dict[str, Any]]:
        """
        获取可用的筛选条件（按类型）
        
        Args:
            instrument_type: 工具类型
            
        返回格式：
        [
            {"field": "scale", "label": "规模（亿元）", "type": "range"},
            {"field": "return_1y", "label": "年化收益率", "type": "range"},
            ...
        ]
        """
        pass


class FinancialInstrumentAnalyticsService(ABC, Generic[T]):
    """
    金融工具分析服务（通用）
    
    职责：
    - 计算风险指标（夏普、最大回撤、波动率）
    - 生成分析报告
    - 相关性分析
    """
    
    @abstractmethod
    def calculate_sharpe_ratio(self, code: str, period: str = '1Y', risk_free_rate: float = 0.02) -> float:
        """
        计算夏普比率
        
        Args:
            code: 金融工具代码
            period: 时间周期
            risk_free_rate: 无风险利率（默认 2%）
            
        Returns:
            float: 夏普比率
        """
        pass
    
    @abstractmethod
    def calculate_max_drawdown(self, code: str, period: str = '1Y') -> float:
        """
        计算最大回撤
        
        Args:
            code: 金融工具代码
            period: 时间周期
            
        Returns:
            float: 最大回撤（如 -0.15 表示 -15%）
        """
        pass
    
    @abstractmethod
    def calculate_volatility(self, code: str, period: str = '1Y') -> float:
        """
        计算波动率（标准差）
        
        Args:
            code: 金融工具代码
            period: 时间周期
            
        Returns:
            float: 波动率（年化）
        """
        pass
    
    @abstractmethod
    def correlation_analysis(self, codes: List[str], period: str = '1Y') -> Dict[str, Any]:
        """
        相关性分析
        
        Args:
            codes: 金融工具代码列表
            period: 时间周期
            
        返回格式：
        {
            "codes": ["510300", "510500"],
            "correlation_matrix": [[1.0, 0.8], [0.8, 1.0]],
            "period": "1Y"
        }
        """
        pass
