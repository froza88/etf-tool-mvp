"""
金融指标计算模块 - 收益率、最大回撤、夏普比率
如果数据源有现成指标则直接返回，否则自行计算
"""
import math


def calc_annual_return(prices):
    """年化收益率（用最近252个交易日）"""
    n = len(prices)
    if n < 20:
        return 0
    if n >= 252:
        return (prices[-1] - prices[-252]) / prices[-252] * 100
    return (prices[-1] - prices[0]) / prices[0] * 100


def calc_multi_year_return(prices):
    """多周期收益率"""
    n = len(prices)
    return {
        'year_1': calc_annual_return(prices),
        'year_3': (prices[-1] - prices[0]) / prices[0] * 100 if n >= 20 else 0,
    }


def calc_max_drawdown(prices):
    """最大回撤（从峰值净值到谷值净值）"""
    peak = prices[0]
    max_dd = 0.0
    for v in prices:
        if v > peak:
            peak = v
        dd = (v - peak) / peak * 100
        if dd < max_dd:
            max_dd = dd
    return round(max_dd, 1)


def calc_sharpe_ratio(prices, risk_free=0.02):
    """夏普比率 = (年化收益-无风险利率) / 年化波动率"""
    n = min(len(prices), 253)  # 最多用1年
    if n < 30:
        return 0
    daily_rets = [(prices[i] - prices[i-1]) / prices[i-1] for i in range(1, n)]
    if not daily_rets:
        return 0
    avg_ret = sum(daily_rets) / len(daily_rets)
    vol = math.sqrt(sum((r - avg_ret)**2 for r in daily_rets) / len(daily_rets))
    if vol == 0:
        return 0
    annual_ret = avg_ret * 252
    annual_vol = vol * math.sqrt(252)
    return round((annual_ret - risk_free) / annual_vol, 2)


def calc_all_metrics(prices):
    """一次性计算所有指标"""
    n = len(prices)
    if n < 20:
        return {'year_1_return': 0, 'year_3_return': 0, 'max_drawdown': 0, 'sharpe_ratio': 0}
    y1 = calc_annual_return(prices)
    y3 = (prices[-1] - prices[0]) / prices[0] * 100
    return {
        'year_1_return': round(y1, 1),
        'year_3_return': round(y3, 1),
        'max_drawdown': calc_max_drawdown(prices),
        'sharpe_ratio': calc_sharpe_ratio(prices),
    }
