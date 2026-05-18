#!/usr/bin/env python3
"""
多源数据获取器 - 用N个数据源填满所有字段
策略：数据源1（优先） → 数据源2（备份） → 数据源3（兜底）
"""

import json
import time
from datetime import datetime, timedelta
from pathlib import Path

# 数据源优先级（从高到低）
DATA_SOURCES = {
    'price': ['非凸', 'AKShare', '本地缓存'],
    'history': ['非凸', 'AKShare', '本地缓存'],
    'risk': ['盈米', '自算(AKShare)', '本地缓存'],
    'holdings': ['AKShare', '非凸', '兜底列表'],
    'scale': ['AKShare', '东方财富', '本地缓存'],
    'issuer': ['AKShare', '非凸', '本地缓存']
}

def fetch_from_ft(code, data_type):
    """从非凸科技获取数据"""
    try:
        # TODO: 实际调用非凸API
        # 示例：ft_api.get_etf_price(code)
        return None  # 暂时返回None，等API接入
    except:
        return None

def fetch_from_ak_share(code, data_type):
    """从AKShare获取数据"""
    try:
        import akshare as ak
        
        if data_type == 'price':
            df = ak.fund_etf_spot_em()
            row = df[df['代码'] == code]
            if not row.empty:
                return {
                    'close': float(row['最新价'].iloc[0]),
                    'change_pct': float(row['涨跌幅'].iloc[0]),
                    'prev_close': float(row['昨收'].iloc[0])
                }
        
        elif data_type == 'history':
            df = ak.fund_etf_hist_em(
                symbol=str(code),
                period='daily',
                start_date=(datetime.now() - timedelta(days=1100)).strftime('%Y%m%d'),
                end_date=datetime.now().strftime('%Y%m%d'),
                adjust='qfq'
            )
            if not df.empty:
                return {
                    'prices': [float(v) for v in df['收盘']],
                    'dates': [str(d) for d in df['日期']]
                }
        
        elif data_type == 'holdings':
            # TODO: AKShare持仓数据
            pass
        
    except Exception as e:
        return None
    
    return None

def fetch_from_yingmi(code, data_type):
    """从盈米获取数据"""
    try:
        # TODO: 实际调用盈米API（已注册13601229012）
        # 示例：yingmi_api.get_risk_metrics(code)
        return None  # 暂时返回None，等API接入
    except:
        return None

def get_data_with_fallback(code, data_type, local_cache):
    """多源数据获取（带fallback）"""
    
    # 1. 尝试所有数据源
    sources = DATA_SOURCES.get(data_type, [])
    
    for source in sources:
        if source == '非凸':
            data = fetch_from_ft(code, data_type)
        elif source == 'AKShare':
            data = fetch_from_ak_share(code, data_type)
        elif source == '盈米':
            data = fetch_from_yingmi(code, data_type)
        elif source == '本地缓存':
            if code in local_cache:
                data = local_cache[code]
            else:
                data = None
        else:
            data = None
        
        # 如果获取到有效数据，返回
        if data is not None:
            return data, source
    
    # 2. 所有数据源都失败
    return None, None

def verify_data_quality(code, data, data_type):
    """数据质量验证"""
    
    if data_type == 'price':
        # 价格应>0
        if data.get('close', 0) <= 0:
            return False, '价格<=0'
        
        # 涨跌幅应在合理范围内（-10% to 10%）
        if abs(data.get('change_pct', 0)) > 10:
            return False, '涨跌幅超出合理范围'
    
    elif data_type == 'history':
        # 历史数据应>20条
        if len(data.get('prices', [])) < 20:
            return False, '历史数据不足20条'
    
    elif data_type == 'risk':
        # 夏普比率应在合理范围内（-5 to 5）
        if abs(data.get('sharpe_ratio', 0)) > 5:
            return False, '夏普比率超出合理范围'
    
    return True, 'ok'

def fetch_all_data_for_etf(code, local_cache):
    """为单只ETF获取所有需要的数据"""
    
    result = {'code': code}
    data_sources = {}  # 记录每个字段的数据来源
    
    # 1. 实时价格
    price_data, source = get_data_with_fallback(code, 'price', local_cache)
    if price_data:
        is_valid, reason = verify_data_quality(code, price_data, 'price')
        if is_valid:
            result.update(price_data)
            data_sources['price'] = source
    
    # 2. 历史K线
    history_data, source = get_data_with_fallback(code, 'history', local_cache)
    if history_data:
        is_valid, reason = verify_data_quality(code, history_data, 'history')
        if is_valid:
            result['prices'] = history_data['prices']
            result['dates'] = history_data['dates']
            result['count'] = len(history_data['prices'])
            data_sources['history'] = source
    
    # 3. 风险指标（从历史数据计算）
    if 'prices' in result and len(result['prices']) >= 20:
        metrics = calc_metrics_from_prices(result['prices'])
        if metrics:
            result.update(metrics)
    
    # 4. 持仓数据
    holdings_data, source = get_data_with_fallback(code, 'holdings', local_cache)
    if holdings_data:
        result['holdings'] = holdings_data
        data_sources['holdings'] = source
    
    # 5. 基金规模
    scale_data, source = get_data_with_fallback(code, 'scale', local_cache)
    if scale_data:
        result['scale'] = scale_data
        data_sources['scale'] = source
    
    # 6. 记录数据来源
    result['data_source'] = data_sources
    result['updated'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    return result

def calc_metrics_from_prices(prices):
    """从价格序列计算风险指标"""
    n = len(prices)
    if n < 20:
        return None
    
    # 近1年/3年收益
    y1 = None
    y3 = None
    if n >= 252:
        y1 = (prices[-1] - prices[-252]) / prices[-252] * 100
    if n >= 756:
        y3 = (prices[-1] - prices[-756]) / prices[-756] * 100
    
    # 最大回撤
    peak = prices[0]
    max_dd = 0.0
    for p in prices:
        if p > peak:
            peak = p
        dd = (p - peak) / peak * 100
        if dd < max_dd:
            max_dd = dd
    
    # 年化波动率 & 夏普比率
    annual_vol = 0
    sharpe = 0
    if n >= 30:
        daily_returns = [(prices[i] - prices[i-1]) / prices[i-1] 
                        for i in range(1, min(n, 253))]
        if daily_returns:
            avg_ret = sum(daily_returns) / len(daily_returns)
            vol = (sum((r - avg_ret)**2 for r in daily_returns) / len(daily_returns)) ** 0.5
            annual_vol = vol * (252 ** 0.5) * 100
            annual_ret = avg_ret * 252 * 100
            sharpe = (annual_ret - 2) / annual_vol if annual_vol > 0 else 0
    
    return {
        "year_1_return": round(y1, 2) if y1 is not None else 0,
        "year_3_return": round(y3, 2) if y3 is not None else 0,
        "max_drawdown": round(max_dd, 2),
        "sharpe_ratio": round(sharpe, 2),
        "annual_vol": round(annual_vol, 2),
    }

# 测试函数
def test_multi_source():
    """测试多源数据获取"""
    print("测试多源数据获取...")
    
    # 加载本地缓存
    cache_file = Path(__file__).parent / "etf_history_cache.json"
    local_cache = {}
    if cache_file.exists():
        with open(cache_file, encoding="utf-8") as f:
            local_cache = json.load(f)
    
    # 测试几只ETF
    test_codes = ['510300', '510050', '510500']
    
    for code in test_codes:
        print(f"\n获取 {code} 的数据...")
        result = fetch_all_data_for_etf(code, local_cache)
        
        print(f"  价格: {result.get('close', '❌')} (来源: {result.get('data_source', {}).get('price', '无')})")
        print(f"  历史数据: {result.get('count', '❌')}条 (来源: {result.get('data_source', {}).get('history', '无')})")
        print(f"  夏普比率: {result.get('sharpe_ratio', '❌')} (来源: {result.get('data_source', {}).get('risk', '自算')})")

if __name__ == "__main__":
    test_multi_source()
