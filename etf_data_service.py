"""
ETF 数据服务层 - 可插拔数据源架构
本地数据库是 SSOT (Single Source of Truth)
外部数据源只是"补充者"，查询即存储
"""

import json
import os
import sys
from pathlib import Path
from datetime import datetime, timedelta

ROOT = Path(__file__).parent
DATA_FILE = ROOT / "etf_standard_data.json"


class ETFDataSource:
    """
    ETF 数据源抽象基类
    所有数据源必须实现 get_etfs_by_codes(codes) 方法
    """
    
    def get_etfs_by_codes(self, codes: list) -> list:
        """
        根据 ETF 代码列表获取数据
        :param codes: ETF 代码列表，如 ['510300', '510500']
        :return: ETF 数据列表
        """
        raise NotImplementedError("子类必须实现 get_etfs_by_codes 方法")
    
    def get_etf_by_code(self, code: str):
        """获取单个 ETF 数据（便捷方法）"""
        results = self.get_etfs_by_codes([code])
        return results[0] if results else None


class LocalJSONSource(ETFDataSource):
    """
    数据源 A：本地 etf_standard_data.json
    当前主力数据源，查询速度快
    """
    
    def __init__(self, data_file=None):
        self.data_file = Path(data_file) if data_file else DATA_FILE
        self._cache = None
        self._cache_mtime = None
    
    def _load_data(self):
        """加载本地数据（带缓存），统一返回 {'etfs': [...]} 格式"""
        if not self.data_file.exists():
            return {"etfs": []}
        
        mtime = os.path.getmtime(self.data_file)
        if self._cache is not None and self._cache_mtime == mtime:
            return self._cache
        
        with open(self.data_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        # 统一格式：如果是数组，包装成 {'etfs': data}
        if isinstance(data, list):
            data = {"etfs": data}
        
        self._cache = data
        self._cache_mtime = mtime
        return data
    
    def get_etfs_by_codes(self, codes: list) -> list:
        data = self._load_data()
        etfs_dict = {e["code"]: e for e in data.get("etfs", [])}
        
        result = []
        for code in codes:
            if code in etfs_dict:
                result.append(etfs_dict[code])
        return result


class ETFDataService:
    """
    ETF 数据服务层 - 统一入口
    
    设计原则：
    1. 本地数据库永远是 SSOT
    2. 外部数据源只是"补充者"
    3. 查询即存储：每次查询外部 API 都写入本地
    
    数据流：
    用户请求 → 先查本地 DB → 缺失/过期 → 调外部 API → 写入本地 DB → 返回
    """
    
    def __init__(self, local_source=None, external_source=None, max_age_hours=24):
        """
        :param local_source: 本地数据源（默认 LocalJSONSource）
        :param external_source: 外部数据源（可选，为 None 时不调用外部 API）
        :param max_age_hours: 数据最大年龄（小时），超过则视为过期
        """
        self.local_source = local_source or LocalJSONSource()
        self.external_source = external_source  # 可以是 WindSource, YFDZTCSource 等
        self.max_age_hours = max_age_hours
    
    def get_etfs_by_codes(self, codes: list, force_refresh=False) -> list:
        """
        根据 codes 获取 ETF 数据（查询即存储）
        
        :param codes: ETF 代码列表
        :param force_refresh: 是否强制刷新（忽略本地缓存）
        :return: ETF 数据列表
        """
        # 1. 先查本地 DB
        local_etfs = {e["code"]: e for e in self.local_source.get_etfs_by_codes(codes)}
        
        result = []
        missing_codes = []
        
        for code in codes:
            if code in local_etfs and not force_refresh:
                etf = local_etfs[code]
                # 检查数据是否过期
                if not self._is_data_expired(etf):
                    result.append(etf)
                    continue
            missing_codes.append(code)
        
        # 2. 缺失/过期 → 调外部 API
        if missing_codes and self.external_source:
            try:
                external_etfs = self.external_source.get_etfs_by_codes(missing_codes)
                # 3. 写入本地 DB（查询即存储）
                self._save_to_local(external_etfs)
                result.extend(external_etfs)
            except Exception as e:
                print(f"[ETFDataService] 外部数据源调用失败: {e}", file=sys.stderr)
                # 降级：使用本地数据（即使过期）
                for code in missing_codes:
                    if code in local_etfs:
                        result.append(local_etfs[code])
        elif missing_codes:
            # 没有外部数据源，使用本地数据（即使可能过期）
            for code in missing_codes:
                if code in local_etfs:
                    result.append(local_etfs[code])
        
        return result
    
    def _is_data_expired(self, etf: dict) -> bool:
        """检查 ETF 数据是否过期"""
        updated = etf.get("updated", "")
        if not updated:
            return True
        
        try:
            updated_time = datetime.fromisoformat(updated)
            return datetime.now() - updated_time > timedelta(hours=self.max_age_hours)
        except:
            return True
    
    def _save_to_local(self, etfs: list):
        """写入本地数据库（查询即存储）"""
        if not etfs:
            return
        
        # 读取本地数据
        local_data = self.local_source._load_data()
        local_etfs_dict = {e["code"]: e for e in local_data.get("etfs", [])}
        
        # 更新/插入
        for etf in etfs:
            code = etf["code"]
            if code in local_etfs_dict:
                # 更新现有记录（只更新非空字段）
                local_etfs_dict[code].update({k: v for k, v in etf.items() if v is not None})
            else:
                # 插入新记录
                local_etfs_dict[code] = etf
        
        # 写回文件
        local_data["etfs"] = list(local_etfs_dict.values())
        local_data["updated"] = datetime.now().isoformat()
        
        with open(self.local_source.data_file, "w", encoding="utf-8") as f:
            json.dump(local_data, f, ensure_ascii=False, indent=2)
        
        # 清除缓存
        self.local_source._cache = None
        self.local_source._cache_mtime = None
        
        print(f"[ETFDataService] 已写入本地数据库: {[e['code'] for e in etfs]}", file=sys.stderr)


# ========== 工厂函数 ==========

def create_default_service(max_age_hours=24):
    """
    创建默认数据服务（本地 JSON + 无外部源）
    后续可以改成：create_service_with_wind() 或 create_service_with_yfdztc()
    """
    return ETFDataService(
        local_source=LocalJSONSource(),
        external_source=None,  # 暂时不配置外部源
        max_age_hours=max_age_hours
    )
