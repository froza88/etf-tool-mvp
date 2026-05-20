"""
ETF Service 接口定义 - 继承通用接口
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Any
from models.financial_instrument import ETF, InstrumentType
from .financial_instrument_service import (
    FinancialInstrumentQueryService,
    FinancialInstrumentCompareService,
    FinancialInstrumentHistoryService,
    FinancialInstrumentScreeningService
)


class ETFQueryService(FinancialInstrumentQueryService[ETF]):
    """
    ETF 查询服务
    
    继承通用 FinancialInstrumentQueryService[ETF]
    添加 ETF 特有的查询方法
    """
    
    @abstractmethod
    def get_etf_list_by_category(self, category: str) -> List[Dict[str, Any]]:
        """
        根据分类获取 ETF 列表（ETF 特有）
        
        Args:
            category: 分类（如 "宽基"/"行业"/"主题"）
            
        Returns:
            List[Dict]: ETF 列表
        """
        pass
    
    @abstractmethod
    def get_etf_list_by_tracking_index(self, index_code: str) -> List[Dict[str, Any]]:
        """
        根据跟踪指数获取 ETF 列表（ETF 特有）
        
        Args:
            index_code: 指数代码（如 "000300.SH"）
            
        Returns:
            List[Dict]: ETF 列表
        """
        pass


class ETFCompareService(FinancialInstrumentCompareService[ETF]):
    """
    ETF 对比服务
    
    继承通用 FinancialInstrumentCompareService[ETF]
    """
    pass  # ETF 对比逻辑与通用接口一致，无需扩展


class ETFHistoryService(FinancialInstrumentHistoryService[ETF]):
    """
    ETF 历史数据服务
    
    继承通用 FinancialInstrumentHistoryService[ETF]
    添加 ETF 特有的历史数据方法
    """
    
    @abstractmethod
    def get_etf_nav_history(self, code: str, period: str = '1Y') -> Dict[str, Any]:
        """
        获取 ETF 净值历史（ETF 特有，区别于价格历史）
        
        Args:
            code: ETF 代码
            period: 时间周期
            
        Returns:
            Dict: 净值历史数据
        """
        pass


class ETFScreeningService(FinancialInstrumentScreeningService[ETF]):
    """
    ETF 筛选服务
    
    继承通用 FinancialInstrumentScreeningService[ETF]
    添加 ETF 特有的筛选方法
    """
    
    @abstractmethod
    def screen_by_category(self, category: str, criteria: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        按分类筛选 ETF（ETF 特有）
        
        Args:
            category: 分类（如 "宽基"）
            criteria: 筛选条件
            
        Returns:
            Dict: 筛选结果
        """
        pass
    
    @abstractmethod
    def get_etf_screening_templates(self) -> List[Dict[str, Any]]:
        """
        获取 ETF 筛选模板（ETF 特有）
        
        Returns:
            List[Dict]: 筛选模板列表
        """
        pass
