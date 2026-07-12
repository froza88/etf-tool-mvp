#!/usr/bin/env python3
"""FMP 免费层分析报告生成器 — 演示可用能力"""
import json
import sys
from datetime import datetime, timedelta

sys.path.insert(0, '/Users/apangduo/.workbuddy/binaries/python/envs/default/lib/python3.13/site-packages')

from openbb import obb

# FMP API Key
obb.user.credentials.fmp_api_key = 'dvB90egYLCMZXZA808JzxKLQPIql9BG8'


def main():
    print(f"=== FMP 免费层能力报告 ===\n生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")

    # 1. ETF 历史行情 (仅 SPY 确认可行)
    print("--- 1. ETF 历史行情 ---")
    try:
        r = obb.etf.historical('SPY', provider='fmp', start_date='2026-01-01')
        if r.results:
            closes = [row.close for row in r.results]
            start = r.results[0].date
            end = r.results[-1].date
            ret = (closes[-1] / closes[0] - 1) * 100
            max_dd = max([1 - closes[i] / max(closes[:i+1]) for i in range(1, len(closes))], default=0) * 100
            print(f"  SPY [{start} ~ {end}]: {len(r.results)} 个交易日")
            print(f"  年初至今收益: {ret:+.2f}%")
            print(f"  最大回撤: -{max_dd:.2f}%")
        else:
            print("  SPY: 无数据")
    except Exception as e:
        print(f"  SPY: Error - {e}")

    # 2. ETF 业绩指标
    print("\n--- 2. ETF 价格表现 ---")
    try:
        r = obb.etf.price_performance('SPY', provider='fmp')
        if r.results:
            perf = r.results[0]
            print(f"  SPY 1日: {perf.one_day*100 if perf.one_day else 0:+.2f}%")
            print(f"  SPY 1周: {perf.one_week*100 if perf.one_week else 0:+.2f}%")
            print(f"  SPY 1月: {perf.one_month*100 if perf.one_month else 0:+.2f}%")
            print(f"  SPY 3月: {perf.three_month*100 if perf.three_month else 0:+.2f}%")
            print(f"  SPY YTD: {perf.ytd*100 if perf.ytd else 0:+.2f}%")
            print(f"  SPY 1年: {perf.one_year*100 if perf.one_year else 0:+.2f}%")
    except Exception as e:
        print(f"  Error: {e}")

    # 3. 个股基础信息
    print("\n--- 3. 个股概览 ---")
    symbols = ['AAPL', 'MSFT', 'NVDA', 'TSLA']
    profiles = {}
    for sym in symbols:
        try:
            p = obb.equity.profile(sym, provider='fmp')
            if p.results:
                profiles[sym] = p.results[0]
                pf = profiles[sym]
                sector = getattr(pf, 'sector', '') or getattr(pf, 'industry_category', 'N/A')
                beta = getattr(pf, 'beta', None)
                ceo = getattr(pf, 'ceo', 'N/A')
                print(f"  {sym}: {pf.name} | 市值 ${pf.market_cap:,.0f} | 行业 {sector} | Beta {beta:.2f}" if beta else f"  {sym}: {pf.name} | 市值 ${pf.market_cap:,.0f} | 行业 {sector}")
        except Exception as e:
            print(f"  {sym}: Error - {e}")

    # 4. 同行对比
    print("\n--- 4. AAPL 同行对比 ---")
    try:
        peers = obb.equity.compare.peers('AAPL', provider='fmp')
        if peers.results:
            for p in peers.results:
                print(f"  {p.symbol}: {p.name} | 股价 ${p.price:.2f} | 市值 ${p.market_cap:,.0f}")
    except Exception as e:
        print(f"  Error: {e}")

    # 5. 财务报表
    print("\n--- 5. AAPL 财务摘要 ---")
    try:
        inc = obb.equity.fundamental.income('AAPL', provider='fmp', period='annual', limit=3)
        if inc.results:
            print(f"  {'年份':<8} {'营收 (B)':>10} {'净利 (B)':>10} {'毛利率':>8} {'EPS':>8}")
            for row in reversed(inc.results):
                rev = (row.revenue or 0) / 1e9
                ni = (row.bottom_line_net_income or 0) / 1e9
                gp = (row.gross_profit or 0)
                margin = (gp / row.revenue * 100) if row.revenue > 0 else 0
                eps = getattr(row, 'basic_earnings_per_share', None) or 0
                fy = row.fiscal_year or str(row.period_ending)[:4] if row.period_ending else 'N/A'
                if rev > 0:
                    print(f"  {str(fy):<8} {rev:>10.2f} {ni:>10.2f} {margin:>7.1f}% {eps:>7.2f}")
    except Exception as e:
        print(f"  Error: {e}")

    # 6. 实时报价
    print("\n--- 6. 实时报价 ---")
    for sym in symbols:
        try:
            q = obb.equity.price.quote(sym, provider='fmp')
            if q.results:
                qd = q.results[0]
                price = qd.last_price or qd.close or 0
                chg_pct = (qd.change_percent or 0) * 100
                vol = qd.volume or 0
                ma50 = qd.ma50 or 0
                print(f"  {sym}: ${price:.2f} ({chg_pct:+.2f}%) Vol:{vol:,} MA50:${ma50:.2f}" if ma50 else f"  {sym}: ${price:.2f} ({chg_pct:+.2f}%) Vol:{vol:,}")
        except Exception as e:
            print(f"  {sym}: Error - {e}")

    print(f"\n=== 报告结束 ===\nAPI 余额: FMP 免费层 250次/天，以上共消耗约 12 次请求")


if __name__ == '__main__':
    main()
