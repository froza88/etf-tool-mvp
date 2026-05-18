#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DataAbsorber - 数据吸收器
实现"填表格"思路：能获取的数据都保存，不断丰富本地数据库

核心原则：
1. 不遗漏任何可见数据
2. 多源融合：从所有可用数据源获取同一字段
3. 优先级策略：权威数据源优先，兜底数据源补充
4. 持续改进：每次运行都尝试补充缺失字段
"""

import json
import sys
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).parent
OUTPUT = ROOT / "etf_standard_data.json"

# 定义所有可获取的字段及其数据源优先级
FIELD_SOURCES = {
    # 基础信息
    "code": ["akshare", "ft", "local"],
    "name": ["akshare", "ft", "local"],
    "issuer": ["ft", "akshare", "local"],
    "issue_date": ["ft", "akshare"],
    "custodian": ["ft"],
    
    # 规模与份额
    "scale": ["ft", "akshare"],  # ft: market_cap, akshare: 基金份额×净值
    "shares": ["akshare"],  # 基金份额
    
    # 价格数据
    "close": ["ft", "akshare"],
    "prev_close": ["ft", "akshare"],
    "change_pct": ["akshare", "ft"],
    "change_rate": ["ft"],
    "volume": ["akshare", "ft"],
    
    # 历史K线（用于计算风险指标）
    "history_prices": ["akshare"],  # fund_etf_hist_em
    
    # 风险收益指标
    "year_1_return": ["calc", "yingmi", "akshare"],  # calc: 自算, yingmi: 盈米
    "year_3_return": ["calc", "yingmi"],
    "max_drawdown": ["calc", "yingmi"],
    "sharpe_ratio": ["calc", "yingmi"],
    "annual_vol": ["calc"],
    
    # 持仓信息
    "top_holdings": ["ft", "akshare"],  # ft: 非凸, akshare: fund_portfolio_hold_em
    
    # 分类信息
    "category": ["local", "akshare"],  # 宽基/行业
}

class DataAbsorber:
    """数据吸收器 - 填表格思路"""
    
    def __init__(self):
        self.stats = {
            "total_etfs": 0,
            "fields_filled": defaultdict(int),
            "fields_missing": defaultdict(int),
            "sources_used": defaultdict(int),
        }
    
    def absorb(self, etf_code, field_name, value, source):
        """
        吸收一个数据字段
        
        Args:
            etf_code: ETF代码
            field_name: 字段名
            value: 字段值（如果为None/空/0，则不吸收）
            source: 数据源名称
        """
        # 有效性检查：只吸收非空数据
        if value is None:
            return False
        if isinstance(value, str) and value.strip() == "":
            return False
        if isinstance(value, (int, float)) and value == 0:
            return False
        if isinstance(value, list) and len(value) == 0:
            return False
        
        # 吸收数据
        self.stats["fields_filled"][field_name] += 1
        self.stats["sources_used"][source] += 1
        return True
    
    def report(self):
        """生成吸收报告"""
        print("\n=== 数据吸收报告 ===")
        print(f"\n总ETF数: {self.stats['total_etfs']}")
        
        print(f"\n✅ 字段填充统计:")
        for field, count in sorted(self.stats["fields_filled"].items(), key=lambda x: -x[1]):
            pct = count / self.stats["total_etfs"] * 100
            print(f"   {field}: {count} 只 ({pct:.1f}%)")
        
        print(f"\n📊 数据源使用统计:")
        for source, count in sorted(self.stats["sources_used"].items(), key=lambda x: -x[1]):
            print(f"   {source}: {count} 次")
        
        print(f"\n⚠️  缺失字段统计:")
        for field, count in sorted(self.stats["fields_missing"].items(), key=lambda x: -x[1]):
            pct = count / self.stats["total_etfs"] * 100
            print(f"   {field}: {count} 只 ({pct:.1f}%)")

def enrich_etf_with_all_sources(etf_code, existing_data=None):
    """
    从所有数据源吸收数据，填充到ETF记录中
    
    填表格思路：
    1. 先填充权威数据源（如AKShare的列表数据）
    2. 再补充辅助数据源（如非凸的持仓数据）
    3. 最后计算衍生指标（如收益率/夏普比率）
    3. 每次运行都尝试补充之前缺失的字段
    """
    if existing_data is None:
        existing_data = {}
    
    absorber = DataAbsorber()
    enriched = existing_data.copy()
    
    # 第1步：从AKShare获取基础数据（最全）
    try:
        import akshare as ak
        df = ak.fund_etf_spot_em()
        row = df[df['代码'] == etf_code]
        if not row.empty:
            enriched["code"] = etf_code
            enriched["name"] = row.iloc[0]['名称']
            enriched["close"] = float(row.iloc[0]['最新价'])
            enriched["change_pct"] = float(row.iloc[0]['涨跌幅'])
            enriched["volume"] = float(row.iloc[0]['成交量'])
            enriched["scale"] = float(row.iloc[0]['总市值']) / 1e8 if '总市值' in row.columns else 0
            
            # 标记数据来源
            enriched["_sources"] = enriched.get("_sources", {})
            enriched["_sources"].update({
                "code": "akshare",
                "name": "akshare",
                "close": "akshare",
                "change_pct": "akshare",
            })
    except:
        pass
    
    # 第2步：从非凸获取实时数据（优先级更高）
    # TODO: 调用非凸API
    
    # 第3步：补充持仓数据（AKShare）
    if not enriched.get("top_holdings"):
        try:
            df = ak.fund_portfolio_hold_em(symbol=etf_code, date="2026")
            if df is not None and len(df) > 0:
                holdings = []
                for _, r in df.iterrows():
                    holdings.append({
                        "name": str(r.iloc[2]).strip(),
                        "weight": f"{float(r.iloc[3]):.2f}%"
                    })
                    if len(holdings) >= 5:
                        break
                enriched["top_holdings"] = holdings
                enriched["_sources"]["top_holdings"] = "akshare"
        except:
            pass
    
    # 第4步：计算风险指标（如果缺失）
    if enriched.get("year_1_return", 0) == 0:
        try:
            df = ak.fund_etf_hist_em(
                symbol=etf_code, period='daily',
                start_date='20230516', end_date='20260516',
                adjust='qfq'
            )
            if df is not None and len(df) >= 252:
                prices = [float(v) for v in list(df['收盘'])]
                year_1_return = (prices[-1] - prices[-252]) / prices[-252] * 100
                enriched["year_1_return"] = round(year_1_return, 1)
                enriched["_sources"]["year_1_return"] = "calc"
        except:
            pass
    
    # 第5步：记录数据完整性
    for field in ["code", "name", "issuer", "scale", "close", "top_holdings", "year_1_return"]:
        if enriched.get(field):
            absorber.stats["fields_filled"][field] += 1
        else:
            absorber.stats["fields_missing"][field] += 1
    
    return enriched, absorber

if __name__ == "__main__":
    print("=== DataAbsorber 测试 ===\n")
    
    # 测试：吸收单只ETF的数据
    test_code = "510300"
    print(f"测试ETF: {test_code}\n")
    
    enriched, absorber = enrich_etf_with_all_sources(test_code)
    
    print(f"吸收结果:")
    for key, value in enriched.items():
        if key.startswith("_"):
            continue
        print(f"   {key}: {value if not isinstance(value, list) else f'{len(value)} 只持仓'}")
    
    if "_sources" in enriched:
        print(f"\n数据来源:")
        for field, source in enriched["_sources"].items():
            print(f"   {field} ← {source}")
    
    absorber.stats["total_etfs"] = 1
    absorber.report()
