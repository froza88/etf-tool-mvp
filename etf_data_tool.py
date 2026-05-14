#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ETF数据批量获取工具
结合AkShare的ETF专用函数和缓存、重试机制
"""

import argparse
import sys
import json
import time
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, List
import hashlib

try:
    import akshare as ak
    import pandas as pd
except ImportError as e:
    print(f"错误: 缺少必要的依赖库")
    print(f"请运行: pip install akshare pandas")
    sys.exit(1)


class CacheManager:
    """数据缓存管理器"""
    
    def __init__(self, cache_dir: str = None, cache_expiry_hours: int = 24):
        """
        初始化缓存管理器
        
        Args:
            cache_dir: 缓存目录路径
            cache_expiry_hours: 缓存过期时间（小时）
        """
        if cache_dir is None:
            cache_dir = os.path.join(os.path.expanduser("~"), ".etf_data_cache")
        
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_expiry_hours = cache_expiry_hours
    
    def _get_cache_key(self, func_name: str, **kwargs) -> str:
        """生成缓存键"""
        params_str = json.dumps(kwargs, sort_keys=True, ensure_ascii=False)
        key_str = f"{func_name}:{params_str}"
        return hashlib.md5(key_str.encode('utf-8')).hexdigest()
    
    def get(self, func_name: str, **kwargs) -> Optional[pd.DataFrame]:
        """
        从缓存获取数据
        
        Args:
            func_name: 函数名
            **kwargs: 函数参数
            
        Returns:
            缓存的DataFrame，如果不存在或已过期则返回None
        """
        cache_key = self._get_cache_key(func_name, **kwargs)
        cache_file = self.cache_dir / f"{cache_key}.parquet"
        
        if not cache_file.exists():
            return None
        
        # 检查缓存是否过期
        file_time = datetime.fromtimestamp(cache_file.stat().st_mtime)
        expiry_time = datetime.now() - timedelta(hours=self.cache_expiry_hours)
        
        if file_time < expiry_time:
            cache_file.unlink()  # 删除过期缓存
            return None
        
        try:
            df = pd.read_parquet(cache_file)
            return df
        except Exception:
            return None
    
    def set(self, func_name: str, data: pd.DataFrame, **kwargs) -> bool:
        """
        保存数据到缓存
        
        Args:
            func_name: 函数名
            data: 要缓存的数据
            **kwargs: 函数参数
            
        Returns:
            是否成功保存
        """
        cache_key = self._get_cache_key(func_name, **kwargs)
        cache_file = self.cache_dir / f"{cache_key}.parquet"
        
        try:
            data.to_parquet(cache_file)
            return True
        except Exception as e:
            print(f"缓存保存失败: {e}")
            return False
    
    def clear(self) -> int:
        """
        清除所有缓存
        
        Returns:
            删除的缓存文件数量
        """
        count = 0
        for file in self.cache_dir.glob("*.parquet"):
            file.unlink()
            count += 1
        return count


def retry_on_failure(max_retries: int = 3, delay: float = 1.0):
    """
    失败重试装饰器
    
    Args:
        max_retries: 最大重试次数
        delay: 重试延迟（秒）
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            last_error = None
            current_delay = delay
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_error = e
                    if attempt < max_retries - 1:
                        print(f"请求失败，{current_delay}秒后重试... (尝试 {attempt + 1}/{max_retries})")
                        time.sleep(current_delay)
                        current_delay *= 2  # 指数退避
            raise last_error
        return wrapper
    return decorator


class ETFDataTool:
    """ETF数据获取工具"""
    
    def __init__(self, use_cache: bool = True, cache_expiry_hours: int = 24):
        """
        初始化工具
        
        Args:
            use_cache: 是否使用缓存
            cache_expiry_hours: 缓存过期时间（小时）
        """
        self.use_cache = use_cache
        self.cache = CacheManager(cache_expiry_hours=cache_expiry_hours) if use_cache else None
    
    def _fetch_with_cache(self, func_name: str, fetch_func, use_cache: bool = None, **kwargs) -> pd.DataFrame:
        """
        带缓存的数据获取
        
        Args:
            func_name: 函数名（用于缓存键）
            fetch_func: 实际获取数据的函数（无参数）
            use_cache: 是否使用缓存（覆盖默认设置）
            **kwargs: 函数参数（仅用于缓存键）
            
        Returns:
            DataFrame数据
        """
        should_cache = use_cache if use_cache is not None else self.use_cache
        
        # 尝试从缓存获取
        if should_cache and self.cache:
            cached_data = self.cache.get(func_name, **kwargs)
            if cached_data is not None:
                print("✓ 使用缓存数据")
                return cached_data
        
        # 从网络获取
        print("正在获取数据...")
        data = fetch_func()
        
        # 保存到缓存
        if should_cache and self.cache and data is not None and not data.empty:
            self.cache.set(func_name, data, **kwargs)
            print("✓ 数据已缓存")
        
        return data
    
    @retry_on_failure(max_retries=3, delay=1.0)
    def get_etf_realtime(self, symbol: str = None, use_cache: bool = False) -> pd.DataFrame:
        """
        获取ETF实时行情
        
        Args:
            symbol: ETF代码（可选，为空则获取全部）
            use_cache: 是否使用缓存
            
        Returns:
            ETF实时行情数据
        """
        def fetch():
            df = ak.fund_etf_spot_em()
            if symbol:
                return df[df['代码'] == symbol]
            return df
        
        return self._fetch_with_cache("etf_realtime", fetch, use_cache=use_cache, symbol=symbol)
    
    @retry_on_failure(max_retries=3, delay=1.0)
    def get_etf_history(self, symbol: str, period: str = "daily",
                       start_date: str = None, end_date: str = None,
                       adjust: str = "qfq", use_cache: bool = True) -> pd.DataFrame:
        """
        获取ETF历史数据
        
        Args:
            symbol: ETF代码（如 "510300"）
            period: 周期（daily/weekly/monthly）
            start_date: 开始日期（格式：YYYYMMDD）
            end_date: 结束日期（格式：YYYYMMDD）
            adjust: 复权类型（qfq-前复权, hfq-后复权, ""-不复权）
            use_cache: 是否使用缓存
            
        Returns:
            历史数据
        """
        # 默认日期范围：最近一年
        if not end_date:
            end_date = datetime.now().strftime("%Y%m%d")
        if not start_date:
            start_date = (datetime.now() - timedelta(days=365)).strftime("%Y%m%d")
        
        def fetch():
            df = ak.fund_etf_hist_em(
                symbol=symbol,
                period=period,
                start_date=start_date,
                end_date=end_date,
                adjust=adjust
            )
            return df
        
        return self._fetch_with_cache("etf_history", fetch, use_cache=use_cache,
                                     symbol=symbol, period=period, start_date=start_date,
                                     end_date=end_date, adjust=adjust)
    
    def calculate_return(self, symbol: str, periods: List[str] = None) -> Dict[str, float]:
        """
        计算ETF收益率
        
        Args:
            symbol: ETF代码
            periods: 计算周期列表（如 ["1w", "1m", "3m", "6m", "1y", "3y", "5y"]）
            
        Returns:
            各周期收益率字典
        """
        if periods is None:
            periods = ["1w", "1m", "3m", "6m", "1y"]
        
        # 获取足够长的历史数据
        end_date = datetime.now().strftime("%Y%m%d")
        start_date = (datetime.now() - timedelta(days=365*5)).strftime("%Y%m%d")  # 5年
        
        try:
            df = self.get_etf_history(symbol, start_date=start_date, end_date=end_date, use_cache=True)
            
            if df.empty or '收盘' not in df.columns:
                return {}
            
            # 确保日期列是datetime类型
            df['日期'] = pd.to_datetime(df['日期'])
            df = df.sort_values('日期')
            
            returns = {}
            latest_price = df['收盘'].iloc[-1]
            
            period_days = {
                "1w": 7,
                "1m": 30,
                "3m": 90,
                "6m": 180,
                "1y": 365,
                "3y": 365*3,
                "5y": 365*5
            }
            
            for period in periods:
                if period in period_days:
                    days = period_days[period]
                    start_price = df[df['日期'] <= df['日期'].iloc[-1] - timedelta(days=days)]['收盘']
                    
                    if not start_price.empty:
                        start_price = start_price.iloc[-1]
                        return_pct = (latest_price - start_price) / start_price * 100
                        returns[period] = round(return_pct, 2)
            
            return returns
        
        except Exception as e:
            print(f"计算收益率失败: {e}")
            return {}
    
    def calculate_drawdown(self, symbol: str) -> Dict[str, float]:
        """
        计算ETF最大回撤
        
        Args:
            symbol: ETF代码
            
        Returns:
            回撤相关指标
        """
        try:
            # 获取历史数据（最近1年）
            end_date = datetime.now().strftime("%Y%m%d")
            start_date = (datetime.now() - timedelta(days=365)).strftime("%Y%m%d")
            
            df = self.get_etf_history(symbol, start_date=start_date, end_date=end_date, use_cache=True)
            
            if df.empty or '收盘' not in df.columns:
                return {}
            
            df = df.sort_values('日期')
            
            # 计算累计最大值
            df['cummax'] = df['收盘'].cummax()
            
            # 计算回撤
            df['drawdown'] = (df['收盘'] - df['cummax']) / df['cummax'] * 100
            
            max_drawdown = df['drawdown'].min()
            
            # 当前回撤
            current_drawdown = df['drawdown'].iloc[-1]
            
            return {
                'max_drawdown': round(max_drawdown, 2),
                'current_drawdown': round(current_drawdown, 2)
            }
        
        except Exception as e:
            print(f"计算回撤失败: {e}")
            return {}
    
    def get_etf_complete_data(self, symbol: str) -> Dict[str, Any]:
        """
        获取ETF完整数据（实时+历史指标）
        
        Args:
            symbol: ETF代码
            
        Returns:
            完整数据字典
        """
        result = {'代码': symbol}
        
        try:
            # 1. 获取实时数据
            rt_df = self.get_etf_realtime(symbol=symbol, use_cache=False)
            
            if not rt_df.empty:
                rt_data = rt_df.iloc[0].to_dict()
                result.update(rt_data)
            
            # 2. 计算收益率
            returns = self.calculate_return(symbol)
            result['returns'] = returns
            
            # 3. 计算回撤
            drawdown = self.calculate_drawdown(symbol)
            result.update(drawdown)
            
            return result
        
        except Exception as e:
            print(f"获取ETF完整数据失败: {e}")
            return result
    
    def batch_get_etf_data(self, symbols: List[str], output_file: str = None) -> pd.DataFrame:
        """
        批量获取ETF数据
        
        Args:
            symbols: ETF代码列表
            output_file: 输出文件路径（CSV格式）
            
        Returns:
            包含所有ETF数据的DataFrame
        """
        all_data = []
        
        for i, symbol in enumerate(symbols, 1):
            print(f"\n进度: {i}/{len(symbols)} - 正在获取 {symbol}...")
            
            try:
                data = self.get_etf_complete_data(symbol)
                all_data.append(data)
                
                # 避免请求过快
                if i < len(symbols):
                    time.sleep(1)
            
            except Exception as e:
                print(f"获取 {symbol} 失败: {e}")
                all_data.append({'代码': symbol, '错误': str(e)})
        
        # 转换为DataFrame
        df = pd.DataFrame(all_data)
        
        # 保存到文件
        if output_file:
            df.to_csv(output_file, index=False, encoding='utf-8-sig')
            print(f"\n✓ 数据已保存到: {output_file}")
        
        return df
    
    def clear_cache(self) -> int:
        """清除缓存"""
        if self.cache:
            return self.cache.clear()
        return 0


def print_dataframe(df: pd.DataFrame, max_rows: int = 20, title: str = "数据结果"):
    """美化打印DataFrame"""
    if df is None or df.empty:
        print("没有数据")
        return
    
    print(f"\n{'='*80}")
    print(f"  {title}")
    print(f"  共 {len(df)} 条记录")
    print(f"{'='*80}\n")
    
    # 设置显示选项
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', None)
    pd.set_option('display.max_colwidth', 20)
    
    # 分页显示
    if len(df) > max_rows:
        print(df.head(max_rows))
        print(f"\n... (还有 {len(df) - max_rows} 条记录)")
    else:
        print(df)
    
    print("\n" + "="*80)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="ETF数据获取工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 获取所有ETF实时行情
  %(prog)s realtime
  
  # 获取单只ETF实时行情
  %(prog)s realtime --symbol 510300
  
  # 获取ETF历史数据
  %(prog)s history --symbol 510300 --period daily
  
  # 计算ETF收益率
  %(prog)s return --symbol 510300
  
  # 计算ETF最大回撤
  %(prog)s drawdown --symbol 510300
  
  # 批量获取ETF数据
  %(prog)s batch --symbols 510300,510880,510500 --output etf_data.csv
  
  # 清除缓存
  %(prog)s clear-cache
        """
    )
    
    # 全局参数
    parser.add_argument("--no-cache", action="store_true", help="不使用缓存")
    parser.add_argument("--cache-expiry", type=int, default=24, 
                       help="缓存过期时间（小时）")
    parser.add_argument("--output", "-o", type=str, help="输出文件路径（CSV/JSON格式）")
    parser.add_argument("--format", type=str, choices=["table", "json", "csv"], 
                       default="table", help="输出格式")
    
    # 子命令
    subparsers = parser.add_subparsers(dest="command", help="数据类型")
    
    # 实时行情
    realtime_parser = subparsers.add_parser("realtime", help="ETF实时行情")
    realtime_parser.add_argument("--symbol", "-s", type=str, help="ETF代码")
    
    # 历史数据
    history_parser = subparsers.add_parser("history", help="ETF历史数据")
    history_parser.add_argument("--symbol", "-s", type=str, required=True, help="ETF代码")
    history_parser.add_argument("--period", "-p", type=str, default="daily",
                                     choices=["daily", "weekly", "monthly"], help="周期")
    history_parser.add_argument("--start-date", type=str, help="开始日期（YYYYMMDD）")
    history_parser.add_argument("--end-date", type=str, help="结束日期（YYYYMMDD）")
    history_parser.add_argument("--adjust", type=str, default="qfq",
                                     choices=["qfq", "hfq", ""], help="复权类型")
    
    # 收益率
    return_parser = subparsers.add_parser("return", help="计算ETF收益率")
    return_parser.add_argument("--symbol", "-s", type=str, required=True, help="ETF代码")
    return_parser.add_argument("--periods", "-p", type=str, 
                                    help="计算周期（逗号分隔，如 1w,1m,3m,6m,1y）")
    
    # 回撤
    drawdown_parser = subparsers.add_parser("drawdown", help="计算ETF最大回撤")
    drawdown_parser.add_argument("--symbol", "-s", type=str, required=True, help="ETF代码")
    
    # 批量获取
    batch_parser = subparsers.add_parser("batch", help="批量获取ETF数据")
    batch_parser.add_argument("--symbols", "-s", type=str, required=True,
                                    help="ETF代码列表（逗号分隔）")
    batch_parser.add_argument("--output", "-o", type=str, required=True,
                                   help="输出文件路径（CSV格式）")
    
    # 清除缓存
    subparsers.add_parser("clear-cache", help="清除缓存")
    
    args = parser.parse_args()
    
    # 如果没有命令，显示帮助
    if not args.command:
        parser.print_help()
        return
    
    # 初始化工具
    tool = ETFDataTool(use_cache=not args.no_cache, cache_expiry_hours=args.cache_expiry)
    
    # 执行命令
    df = None
    result = None
    title = "数据结果"
    
    try:
        if args.command == "realtime":
            df = tool.get_etf_realtime(symbol=args.symbol, use_cache=not args.no_cache)
            title = f"ETF实时行情 - {args.symbol if args.symbol else '全部'}"
        
        elif args.command == "history":
            df = tool.get_etf_history(
                symbol=args.symbol,
                period=args.period,
                start_date=args.start_date,
                end_date=args.end_date,
                adjust=args.adjust,
                use_cache=not args.no_cache
            )
            title = f"ETF历史数据 - {args.symbol} ({args.period})"
        
        elif args.command == "return":
            periods = None
            if args.periods:
                periods = args.periods.split(',')
            
            result = tool.calculate_return(symbol=args.symbol, periods=periods)
            title = f"ETF收益率 - {args.symbol}"
        
        elif args.command == "drawdown":
            result = tool.calculate_drawdown(symbol=args.symbol)
            title = f"ETF最大回撤 - {args.symbol}"
        
        elif args.command == "batch":
            symbols = args.symbols.split(',')
            df = tool.batch_get_etf_data(symbols=symbols, output_file=args.output)
            title = f"批量ETF数据 - {len(symbols)}只"
        
        elif args.command == "clear-cache":
            count = tool.clear_cache()
            print(f"✓ 已清除 {count} 个缓存文件")
            return
        
        # 输出结果
        if result is not None:
            # 打印结果字典
            print(f"\n{'='*80}")
            print(f"  {title}")
            print(f"{'='*80}\n")
            for key, value in result.items():
                print(f"  {key}: {value}")
            print("\n" + "="*80)
        
        elif df is not None:
            if args.output:
                # 保存到文件
                if args.output.endswith('.json'):
                    df.to_json(args.output, orient='records', force_ascii=False, indent=2)
                else:
                    df.to_csv(args.output, index=False, encoding='utf-8-sig')
                print(f"✓ 数据已保存到: {args.output}")
            elif args.format == "json":
                print(df.to_json(orient='records', force_ascii=False, indent=2))
            elif args.format == "csv":
                print(df.to_csv(index=False))
            else:
                print_dataframe(df, title=title)
    
    except KeyboardInterrupt:
        print("\n\n操作已取消")
        sys.exit(0)
    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
