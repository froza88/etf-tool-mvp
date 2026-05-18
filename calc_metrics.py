#!/usr/bin/env python3
"""
独立计算ETF风控指标：年化收益率/最大回撤/夏普比率/年化波动率
数据源：非凸 etf-ohlcs API（日K线）
输出：etf_calculated_metrics.json（自算指标，独立文件，便于复用）
"""
import sys, os, json, time, math
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

# 读取ETF列表
with open(os.path.join(ROOT, "etf_complete_all.json"), encoding="utf-8") as f:
    full = json.load(f)
codes = [(e["code"], get_exchange(e["code"])) for e in full]
print(f"ETF总数: {len(codes)}")

ft = FTSource()
results = {}
ok = fail = 0

for i, (code, exch) in enumerate(codes):
    try:
        ohlc = ft.get_etf_ohlcs(str(code), exch, limit=OHLC_LIMIT)
        if ohlc and len(ohlc.get("prices", [])) >= 30:
            prices = ohlc["prices"]
            n = len(prices)
            
            # 动态计算各周期指标
            result = {"year_1_return": 0, "year_2_return": 0, "year_3_return": 0, "year_5_return": 0,
                     "max_drawdown": 0, "max_drawdown_2y": 0, "max_drawdown_3y": 0, "max_drawdown_5y": 0,
                     "sharpe_ratio": 0, "sharpe_2y": 0, "sharpe_3y": 0, "sharpe_5y": 0,
                     "annual_vol": 0, "annual_vol_2y": 0, "annual_vol_3y": 0, "annual_vol_5y": 0}
            
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
                                    "annual_vol": 0, "annual_vol_2y": 0, "annual_vol_3y": 0, "annual_vol_5y": 0}
            fail += 1
    except:
        results[str(code)] = {"year_1_return": 0, "year_2_return": 0, "year_3_return": 0, "year_5_return": 0,
                                "max_drawdown": 0, "max_drawdown_2y": 0, "max_drawdown_3y": 0, "max_drawdown_5y": 0,
                                "sharpe_ratio": 0, "sharpe_2y": 0, "sharpe_3y": 0, "sharpe_5y": 0,
                                "annual_vol": 0, "annual_vol_2y": 0, "annual_vol_3y": 0, "annual_vol_5y": 0}
        fail += 1
    
    if (i + 1) % 100 == 0:
        print(f"  进度: {i+1}/{len(codes)} 成功={ok} 失败={fail}")
    
    time.sleep(0.15)

output = os.path.join(ROOT, "etf_calculated_metrics.json")
with open(output, "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False)
print(f"\n完成! 成功={ok} 失败={fail} 保存到 {output}")
