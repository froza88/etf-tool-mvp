#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MultiSourceFetcher - 多源数据获取器

按优先级从多个数据源获取数据，自动降级。
ETF工具具体实现：AKShare（主） + 非凸（辅） + 盈米（风险指标）
"""

import json
from pathlib import Path
from .base_fetcher import BaseFetcher


class ETFFetcher(MultiSourceFetcher):
    """ETF数据获取器 - 具体实现"""

    def __init__(self):
        super().__init__('etf')

    def _load_sources(self):
        """加载数据源配置"""
        return {
            'akshare': {'priority': 1, 'enabled': True},
            'ft': {'priority': 2, 'enabled': True},  # 非凸
            'yingmi': {'priority': 3, 'enabled': True},
        }

    def fetch_realtime(self, code, fields=None):
        """实时获取ETF数据（调用AKShare）"""
        import akshare as ak
        try:
            df = ak.fund_etf_spot_em()
            row = df[df['代码'] == code]
            if row.empty:
                return None
            return {
                'code': code,
                'name': row.iloc[0]['名称'],
                'close': float(row.iloc[0]['最新价']),
                'change_pct': float(row.iloc[0]['涨跌幅']),
                'volume': float(row.iloc[0]['成交量']),
                '_source': 'akshare',
                '_fetch_time': str(self._now()),
            }
        except Exception as e:
            print(f"AKShare获取失败 [{code}]: {e}")
            return None

    def fetch_history(self, code, start_date=None, end_date=None):
        """获取ETF历史K线"""
        import akshare as ak
        from datetime import datetime, timedelta
        if not end_date:
            end_date = datetime.now()
        if not start_date:
            start_date = end_date - timedelta(days=1100)
        try:
            df = ak.fund_etf_hist_em(
                symbol=str(code),
                period='daily',
                start_date=start_date.strftime('%Y%m%d'),
                end_date=end_date.strftime('%Y%m%d'),
                adjust='qfq',
            )
            if df is None or len(df) == 0:
                return None
            return {
                'code': code,
                'prices': [float(v) for v in df['收盘']],
                'dates': [str(d) for d in df['日期']],
                'count': len(df),
                '_source': 'akshare',
            }
        except Exception as e:
            print(f"AKShare历史数据失败 [{code}]: {e}")
            return None

    def _now(self):
        from datetime import datetime
        return datetime.now()


class MultiSourceFetcher(BaseFetcher):
    """多源数据获取器基类"""

    def fetch_multi_source(self, code, fields=None):
        """
        按优先级多源获取
        子类实现具体的数据源调用逻辑
        """
        sources = sorted(self.sources.items(), key=lambda x: x[1]['priority'])
        for source_name, config in sources:
            if not config.get('enabled'):
                continue
            try:
                data = self._fetch_from_source(source_name, code, fields)
                if data and self.validate(data, fields):
                    data['_source'] = source_name
                    return data
            except Exception as e:
                print(f"  数据源 {source_name} 失败 [{code}]: {e}")
                continue
        return None

    def _fetch_from_source(self, source_name, code, fields):
        """从指定数据源获取（子类重写）"""
        if source_name == 'akshare':
            return self.fetch_realtime(code, fields)
        raise NotImplementedError(f"数据源 {source_name} 未实现")
