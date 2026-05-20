"""
金融工具基础模型
定义所有金融工具的基类和通用类型
"""

from enum import Enum
from typing import Dict, Any, Optional, List
from datetime import datetime


class InstrumentType(Enum):
    """金融工具类型"""
    ETF = "etf"
    STOCK = "stock"
    FUTURE = "future"
    BOND = "bond"
    FUND = "fund"
    INDEX = "index"


class FinancialInstrument:
    """
    金融工具基类
    
    所有金融工具（ETF、股票、期货等）的通用属性
    子类可以扩展特定字段
    """
    
    def __init__(
        self,
        code: str,
        name: str,
        instrument_type: InstrumentType,
        **kwargs
    ):
        """
        初始化金融工具
        
        Args:
            code: 代码（如 "510300"）
            name: 名称（如 "沪深300ETF"）
            instrument_type: 工具类型
            **kwargs: 其他属性
        """
        self.code = code
        self.name = name
        self.instrument_type = instrument_type
        
        # 通用字段
        self.issuer = kwargs.get('issuer')  # 发行人/上市公司
        self.price = kwargs.get('price')  # 最新价格
        self.scale = kwargs.get('scale')  # 规模（亿元）
        self.return_1y = kwargs.get('return_1y')  # 年化收益率
        self.sharpe_ratio = kwargs.get('sharpe_ratio')  # 夏普比率
        self.max_drawdown = kwargs.get('max_drawdown')  # 最大回撤
        self.volatility = kwargs.get('volatility')  # 波动率
        
        # 时间字段
        self.created_at = kwargs.get('created_at', datetime.now())
        self.updated_at = kwargs.get('updated_at', datetime.now())
        
        # 扩展字段（存储原始数据）
        self.extra = kwargs.get('extra', {})
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'code': self.code,
            'name': self.name,
            'instrument_type': self.instrument_type.value,
            'issuer': self.issuer,
            'price': self.price,
            'scale': self.scale,
            'return_1y': self.return_1y,
            'sharpe_ratio': self.sharpe_ratio,
            'max_drawdown': self.max_drawdown,
            'volatility': self.volatility,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'extra': self.extra
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'FinancialInstrument':
        """从字典创建"""
        instrument_type = InstrumentType(data.get('instrument_type', 'etf'))
        return cls(
            code=data['code'],
            name=data['name'],
            instrument_type=instrument_type,
            **{k: v for k, v in data.items() if k not in ['code', 'name', 'instrument_type']}
        )
    
    def __repr__(self):
        return f"<{self.instrument_type.value.upper()} {self.code} {self.name}>"


class ETF(FinancialInstrument):
    """ETF 基金"""
    
    def __init__(self, code: str, name: str, **kwargs):
        super().__init__(code, name, InstrumentType.ETF, **kwargs)
        
        # ETF 特有字段
        self.expense_ratio = kwargs.get('expense_ratio')  # 管理费率
        self.tracking_index = kwargs.get('tracking_index')  # 跟踪指数
        self.holdings = kwargs.get('holdings', [])  # 持仓明细
        self.category = kwargs.get('category')  # 分类（宽基/行业/主题）


class Stock(FinancialInstrument):
    """股票"""
    
    def __init__(self, code: str, name: str, **kwargs):
        super().__init__(code, name, InstrumentType.STOCK, **kwargs)
        
        # 股票特有字段
        self.market = kwargs.get('market')  # 市场（沪市/深市/港股/美股）
        self.industry = kwargs.get('industry')  # 行业
        self.pe_ratio = kwargs.get('pe_ratio')  # 市盈率
        self.pb_ratio = kwargs.get('pb_ratio')  # 市净率
        self.market_cap = kwargs.get('market_cap')  # 市值（亿元）
        self.float_cap = kwargs.get('float_cap')  # 流通市值


class Future(FinancialInstrument):
    """期货"""
    
    def __init__(self, code: str, name: str, **kwargs):
        super().__init__(code, name, InstrumentType.FUTURE, **kwargs)
        
        # 期货特有字段
        self.underlying = kwargs.get('underlying')  # 标的
        self.contract_multiplier = kwargs.get('contract_multiplier')  # 合约乘数
        self.margin_ratio = kwargs.get('margin_ratio')  # 保证金比例
        self.expire_date = kwargs.get('expire_date')  # 到期日
        self.open_interest = kwargs.get('open_interest')  # 持仓量


class Bond(FinancialInstrument):
    """债券"""
    
    def __init__(self, code: str, name: str, **kwargs):
        super().__init__(code, name, InstrumentType.BOND, **kwargs)
        
        # 债券特有字段
        self.coupon_rate = kwargs.get('coupon_rate')  # 票面利率
        self.maturity_date = kwargs.get('maturity_date')  # 到期日
        self.issuer_rating = kwargs.get('issuer_rating')  # 发行人评级
        self.bond_type = kwargs.get('bond_type')  # 债券类型（国债/企业债/转债）


class Fund(FinancialInstrument):
    """公募基金（非ETF）"""
    
    def __init__(self, code: str, name: str, **kwargs):
        super().__init__(code, name, InstrumentType.FUND, **kwargs)
        
        # 基金特有字段
        self.fund_type = kwargs.get('fund_type')  # 基金类型（股票型/债券型/混合型）
        self.manager = kwargs.get('manager')  # 基金经理
        self.fund_company = kwargs.get('fund_company')  # 基金公司
        self.nav = kwargs.get('nav')  # 最新净值


class Index(FinancialInstrument):
    """指数"""
    
    def __init__(self, code: str, name: str, **kwargs):
        super().__init__(code, name, InstrumentType.INDEX, **kwargs)
        
        # 指数特有字段
        self.publisher = kwargs.get('publisher')  # 发布机构（中证/上交所/深交所）
        self.base_date = kwargs.get('base_date')  # 基准日期
        self.base_point = kwargs.get('base_point')  # 基准点数
        self.components = kwargs.get('components', [])  # 成份股列表
