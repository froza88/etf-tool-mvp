#!/usr/bin/env python3
"""
独立计算ETF风控指标：年化收益率/最大回撤/夏普比率/年化波动率
数据源：本地缓存 > 非凸 etf-ohlcs API > AKShare（多源降级）
输出：etf_calculated_metrics.json（自算指标，独立文件，便于复用）
"""
import sys, os, json, time, math
import akshare as ak
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from modules.data_source import FTSource

ROOT = os.path.dirname(os.path.abspath(__file__))
OHLC_LIMIT = 1260  # 约5年交易日，用于计算1/2/3/5年指标
RISK_FREE = 0.02

def get_exchange(code):
    return 'XSHG' if str(code).startswith('5') else 'XSHE'

def calc_max_drawdown(prices):
    peak = prices[0]
    max_dd = 0.0
    for v in prices:
        if v > peak:
            peak = v
        dd = (v - peak) / peak * 100
        if dd < max_dd:
            max_dd = dd
    return round(max_dd, 2)

def calc_sharpe(prices):
    n = min(len(prices), 253)
    if n < 30:
        return 0
    daily_rets = [(prices[i] - prices[i-1]) / prices[i-1] for i in range(1, n)]
    if not daily_rets:
        return 0
    avg = sum(daily_rets) / len(daily_rets)
    vol = math.sqrt(sum((r - avg)**2 for r in daily_rets) / len(daily_rets))
    if vol == 0:
        return 0
    annual_ret = avg * 252
    annual_vol = vol * math.sqrt(252)
    return round((annual_ret - RISK_FREE) / annual_vol, 2)

def calc_annual_vol(prices):
    n = min(len(prices), 253)
    if n < 30:
        return 0
    daily_rets = [(prices[i] - prices[i-1]) / prices[i-1] for i in range(1, n)]
    if not daily_rets:
        return 0
    avg = sum(daily_rets) / len(daily_rets)
    vol = math.sqrt(sum((r - avg)**2 for r in daily_rets) / len(daily_rets))
    return round(vol * math.sqrt(252) * 100, 2)

def load_local_cache(code):
    """加载本地缓存的历史K线数据"""
    cache_path = os.path.join(ROOT, "data", "history", f"{code}.json")
    if os.path.exists(cache_path):
        try:
            with open(cache_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if 'prices' in data and len(data['prices']) > 0:
                    return data['prices']
        except:
            pass
    return None

def get_prices_from_westock(code):
    """从westock-data kline获取K线数据"""
    import subprocess
    try:
        # 转换代码格式：510300 -> sh510300
        if str(code).startswith('5') or str(code).startswith('1'):
            formatted = f'sh{code}'
        elif str(code).startswith('0') or str(code).startswith('3'):
            formatted = f'sz{code}'
        else:
            formatted = f'sh{code}'
        
        cmd = ['node', 
                '/Users/apangduo/.workbuddy/plugins/marketplaces/cb_teams_marketplace/plugins/finance-data/skills/westock-data/scripts/index.js',
                'kline', formatted, '--period', 'day', '--limit', '2000']
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30, encoding='utf-8')
        
        if result.returncode == 0 and result.stdout:
            # 解析markdown表格输出
            lines = result.stdout.strip().split('\n')
            prices = []
            for line in lines:
                if line.startswith('|') and not line.startswith('|-') and 'date' not in line:
                    parts = [p.strip() for p in line.split('|')]
                    if len(parts) >= 3:
                        try:
                            price = float(parts[2])  # last price
                            prices.append(price)
                        except:
                            pass
            if len(prices) >= 30:
                return prices
    except:
        pass
    return None

def get_prices_multi_source(code, exch):
    """多数据源获取K线数据：本地缓存 > westock-data > 非凸 > AKShare"""
    # 1. 优先使用本地缓存
    prices = load_local_cache(code)
    if prices and len(prices) >= 30:
        return prices, 'local_cache'
    
    # 2. 使用westock-data kline（新增加）
    prices = get_prices_from_westock(code)
    if prices and len(prices) >= 30:
        return prices, 'westock_kline'
    
    # 3. 使用非凸API
    ft = FTSource()
    try:
        ohlc = ft.get_etf_ohlcs(str(code), exch, limit=OHLC_LIMIT)
        if ohlc and len(ohlc.get("prices", [])) >= 30:
            return ohlc["prices"], 'ft_api'
    except:
        pass
    
    # 4. 使用AKShare
    try:
        import akshare as ak
        df = ak.fund_etf_hist_em(symbol=str(code), period="daily", start_date="20000101", end_date="20261231", adjust="")
        if not df.empty:
            prices = df['收盘'].tolist()
            return prices, 'akshare'
    except:
        pass
    
    return None, None

if __name__ == '__main__':
    # 读取ETF列表
    with open(os.path.join(ROOT, "etf_complete_all.json"), encoding="utf-8") as f:
        full = json.load(f)
    codes = [(e["code"], get_exchange(e["code"])) for e in full]
    print(f"ETF总数: {len(codes)}")
    
    results = {}
    ok = fail = 0
    
    for i, (code, exch) in enumerate(codes):
        try:
            prices, source = get_prices_multi_source(code, exch)
            if prices and len(prices) >= 30:
                n = len(prices)
                
                # 动态计算各周期指标
                result = {"year_1_return": 0, "year_2_return": 0, "year_3_return": 0, "year_5_return": 0,
                         "max_drawdown": 0, "max_drawdown_2y": 0, "max_drawdown_3y": 0, "max_drawdown_5y": 0,
                         "sharpe_ratio": 0, "sharpe_2y": 0, "sharpe_3y": 0, "sharpe_5y": 0,
                         "annual_vol": 0, "annual_vol_2y": 0, "annual_vol_3y": 0, "annual_vol_5y": 0,
                         "data_source": source}
                
                # 1年指标
                if n >= 252:
                    p1 = prices[-252:]
                    result["year_1_return"] = round((prices[-1] - prices[-252]) / prices[-252] * 100, 2)
                    result["max_drawdown"] = calc_max_drawdown(p1)
                    result["sharpe_ratio"] = calc_sharpe(p1)
                    result["annual_vol"] = calc_annual_vol(p1)
                
                # 2年指标
                if n >= 504:
                    p2 = prices[-504:]
                    result["year_2_return"] = round((prices[-1] - prices[-504]) / prices[-504] * 100, 2)
                    result["max_drawdown_2y"] = calc_max_drawdown(p2)
                    result["sharpe_2y"] = calc_sharpe(p2)
                    result["annual_vol_2y"] = calc_annual_vol(p2)
                
                # 3年指标
                if n >= 756:
                    p3 = prices[-756:]
                    result["year_3_return"] = round((prices[-1] - prices[-756]) / prices[-756] * 100, 2)
                    result["max_drawdown_3y"] = calc_max_drawdown(p3)
                    result["sharpe_3y"] = calc_sharpe(p3)
                    result["annual_vol_3y"] = calc_annual_vol(p3)
                
                # 5年指标
                if n >= 1260:
                    p5 = prices[-1260:]
                    result["year_5_return"] = round((prices[-1] - prices[-1260]) / prices[-1260] * 100, 2)
                    result["max_drawdown_5y"] = calc_max_drawdown(p5)
                    result["sharpe_5y"] = calc_sharpe(p5)
                    result["annual_vol_5y"] = calc_annual_vol(p5)
                
                results[str(code)] = result
                ok += 1
            else:
                results[str(code)] = {"year_1_return": 0, "year_2_return": 0, "year_3_return": 0, "year_5_return": 0,
                                        "max_drawdown": 0, "max_drawdown_2y": 0, "max_drawdown_3y": 0, "max_drawdown_5y": 0,
                                        "sharpe_ratio": 0, "sharpe_2y": 0, "sharpe_3y": 0, "sharpe_5y": 0,
                                        "annual_vol": 0, "annual_vol_2y": 0, "annual_vol_3y": 0, "annual_vol_5y": 0,
                                        "data_source": "none"}
                fail += 1
        except Exception as e:
            results[str(code)] = {"year_1_return": 0, "year_2_return": 0, "year_3_return": 0, "year_5_return": 0,
                                    "max_drawdown": 0, "max_drawdown_2y": 0, "max_drawdown_3y": 0, "max_drawdown_5y": 0,
                                    "sharpe_ratio": 0, "sharpe_2y": 0, "sharpe_3y": 0, "sharpe_5y": 0,
                                    "annual_vol": 0, "annual_vol_2y": 0, "annual_vol_3y": 0, "annual_vol_5y": 0,
                                    "data_source": "error", "error": str(e)}
            fail += 1
        
        if (i + 1) % 100 == 0:
            print(f"  进度: {i+1}/{len(codes)} 成功={ok} 失败={fail}")
        
        time.sleep(0.15)
    
    output = os.path.join(ROOT, "etf_calculated_metrics.json")
    with open(output, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False)
    print(f"\n完成! 成功={ok} 失败={fail} 保存到 {output}")
