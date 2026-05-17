"""
数据源模块 - 统一的金融数据获取接口
对接 AKShare(东方财富)、非凸科技(market.ft.tech) 等免费数据源
其他工具可直接 import 复用
"""
import json
import time
import math
import warnings
warnings.filterwarnings('ignore')


class AKShareSource:
    """AKShare 东方财富数据源"""

    def __init__(self):
        self._ak = None

    @property
    def ak(self):
        if self._ak is None:
            import akshare as ak
            self._ak = ak
        return self._ak

    def get_etf_spot_all(self):
        """获取全市场ETF实时行情列表 (含规模、管理人)"""
        import pandas as pd
        df = self.ak.fund_etf_spot_em()
        results = []
        for _, row in df.iterrows():
            try:
                mcap = float(row.iloc[32]) if pd.notna(row.iloc[32]) else None  # 总市值=基金规模
                if mcap and mcap > 1e12:
                    mcap = None
            except:
                mcap = None
            results.append({
                'code': str(row.iloc[0]).strip(),
                'name': str(row.iloc[1]).strip(),
                'change_pct': float(row.iloc[6]) if pd.notna(row.iloc[6]) else None,
                'volume': float(row.iloc[7]) if pd.notna(row.iloc[7]) else None,
                'amount': float(row.iloc[8]) if pd.notna(row.iloc[8]) else None,
                'market_cap': mcap,
                'manager': str(row.iloc[6]).strip() if pd.notna(row.iloc[6]) else '',
            })
        return results

    def get_portfolio_hold(self, code, date="2025"):
        """获取ETF持仓权重（含股票名称+权重%）"""
        df = self.ak.fund_portfolio_hold_em(symbol=code, date=date)
        if df is None or len(df) == 0:
            return []
        results = []
        for _, row in df.head(10).iterrows():
            try:
                results.append({
                    'stock_code': str(row.iloc[1]).strip().zfill(6),
                    'name': str(row.iloc[2]).strip(),
                    'weight_pct': float(row.iloc[3]),
                })
            except:
                pass
        return results

    def get_hist_ohlc(self, code, start_date='20240101', end_date='20260516'):
        """获取ETF历史日线数据"""
        df = self.ak.fund_etf_hist_em(
            symbol=code, period='daily',
            start_date=start_date, end_date=end_date,
            adjust='qfq'
        )
        if df is None or len(df) < 20:
            return None
        prices = [float(v) for v in list(df['收盘'])]
        dates = [str(d) for d in list(df['日期'])]
        return {'prices': prices, 'dates': dates}


class FTSource:
    """非凸科技 market.ft.tech 数据源"""

    def __init__(self):
        self._root = None

    @property
    def root(self):
        if self._root is None:
            import os
            self._root = os.path.expanduser("~/.workbuddy/skills/ftshare-market-data")
        return self._root

    def _run_subskill(self, skill_name, **kwargs):
        import subprocess
        import os
        args = ['python3', os.path.join(self.root, 'run.py'), skill_name]
        for k, v in kwargs.items():
            args.extend([f'--{k.replace("_", "-")}', str(v)])
        result = subprocess.run(args, capture_output=True, text=True, timeout=20, cwd=self.root)
        if result.returncode == 0:
            import json
            return json.loads(result.stdout)
        return None

    def get_etf_detail(self, code, exchange='XSHG'):
        """获取单只ETF详情（含收益率）"""
        data = self._run_subskill('etf-detail', etf=f'{code}.{exchange}')
        if not data:
            return None
        return {
            'code': code,
            'name': data.get('name', ''),
            'manager': data.get('manager', ''),
            'issue_date': data.get('issue_date', ''),
            'return_1y': data.get('change_rate_1y'),
            'return_3y': data.get('change_rate_3y'),
            'return_6m': data.get('change_rate_6m'),
            'close': data.get('close'),
            'market_cap': data.get('market_cap_total'),
        }

    def get_etf_components(self, code, exchange='XSHG'):
        """获取ETF成份股"""
        data = self._run_subskill('etf-component', symbol=f'{code}.{exchange}')
        if not data:
            return []
        names = data.get('components_name', [])
        codes = data.get('components', [])
        return [{'code': c, 'name': n} for c, n in zip(codes, names)]

    def get_etf_ohlcs(self, code, exchange='XSHG', limit=150):
        """获取ETF K线数据（用于计算回撤/夏普）"""
        data = self._run_subskill('etf-ohlcs', etf=f'{code}.{exchange}', span='DAY1', limit=limit)
        if not data or 'ohlcs' not in data:
            return None
        ohlcs = data['ohlcs']
        if not ohlcs or len(ohlcs) < 20:
            return None
        prices = [float(o['c']) for o in ohlcs]
        dates = [str(o.get('otm', '')) for o in ohlcs]
        return {'prices': prices, 'dates': dates}
