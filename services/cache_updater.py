"""
后台缓存更新服务 - 实现"查询即存储"原则
当用户查询 ETF 时，后台自动触发缓存更新，将外部数据源的最新数据保存到本地。
"""

import threading
import sys
import time
from pathlib import Path
from datetime import datetime

# 项目根目录
ROOT = Path(__file__).parent.parent


def update_etf_cache_background(codes, source="unknown"):
    """
    后台线程更新 ETF 缓存
    
    Args:
        codes: ETF 代码列表
        source: 触发来源（如 "compare_page", "detail_page"）
    """
    def _update():
        try:
            # 延迟导入，避免循环依赖
            sys.path.insert(0, str(ROOT))
            
            from fetchers.wind_fetcher import WindFetcher
            from pipeline import load_json, save_json, WIND_DATA_FILE
            
            fetcher = WindFetcher()
            wind_data = load_json(WIND_DATA_FILE) or {}
            
            updated = 0
            for i, code in enumerate(codes):
                try:
                    # 调用 Wind Fetcher 获取最新数据（会自动缓存到 data/cache/wind/{code}.json）
                    result = fetcher.fetch_etf_info(code, "")
                    if result:
                        # 合并到汇总文件
                        if code not in wind_data:
                            wind_data[code] = {}
                        wind_data[code].update(result)
                        wind_data[code]["_last_update"] = datetime.now().isoformat()
                        updated += 1
                    
                    # 避免 QPS 限制
                    if i < len(codes) - 1:
                        time.sleep(0.3)
                        
                except Exception as e:
                    print(f"[CacheUpdater] 更新 {code} 失败: {e}")
            
            # 保存汇总文件
            save_json(WIND_DATA_FILE, wind_data)
            
            print(f"[CacheUpdater] 完成: 更新 {updated}/{len(codes)} 只 ETF 缓存 (来源: {source})")
            
        except Exception as e:
            print(f"[CacheUpdater] 后台更新失败: {e}")
    
    # 启动守护线程（不阻塞请求）
    thread = threading.Thread(target=_update, daemon=True, name=f"CacheUpdate-{source}")
    thread.start()
    print(f"[CacheUpdater] 已启动后台缓存更新: {len(codes)} 只 ETF (来源: {source})")


def update_etf_history_background(codes):
    """
    后台更新 ETF 历史 K 线（用于 year_3_return 等长期指标）
    注意：此操作较慢，仅在前端明确请求时调用
    """
    def _update():
        try:
            sys.path.insert(0, str(ROOT))
            # TODO: 调用 batch_fill_history.py 逻辑
            print(f"[CacheUpdater] 历史 K 线更新暂未实现")
        except Exception as e:
            print(f"[CacheUpdater] 历史更新失败: {e}")
    
    thread = threading.Thread(target=_update, daemon=True)
    thread.start()
