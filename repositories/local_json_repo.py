"""
LocalJSONRepo - 本地JSON数据源实现
从 etf_standard_data.json / data/snapshots/ 读取ETF数据

数据加载优先级：快照 → 标准数据文件 → 过期标准数据 → 回退数据
历史数据降级策略：本地history文件 → 全局缓存 → AKShare实时 → 模拟数据

基于 etf_data.py 和 app.py 中现有逻辑的封装移植
"""

import json
import math
import os
import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any

from .etf_repository import ETFRepository


class LocalJSONRepo(ETFRepository):
    """本地JSON数据源实现

    继承 ETFRepository 抽象接口，从本地JSON文件读取ETF数据。
    保持与现有 etf_data.py 完全一致的数据加载行为和筛选逻辑。
    """

    MAX_AGE_HOURS: int = 168  # 7天

    def __init__(self, root_path: Optional[Path] = None):
        """初始化本地JSON数据源

        Args:
            root_path: 项目根目录，默认为 repositories/ 的上级目录（即 etf-tool-mvp/）
        """
        self.root: Path = root_path or Path(__file__).parent.parent
        self.data_dir: Path = self.root / "data"
        self.snapshot_dir: Path = self.data_dir / "snapshots"
        self.standard_data_file: Path = self.root / "etf_standard_data.json"

        self._etf_list: Optional[List[Dict]] = None
        self._etf_map: Optional[Dict[str, Dict]] = None

    # ========== 私有方法：数据加载 ==========

    @staticmethod
    def _is_file_recent(filepath: Path, max_age_hours: int) -> bool:
        """检查文件是否在指定时间内被修改过

        Args:
            filepath: 文件路径
            max_age_hours: 最大允许的小时数

        Returns:
            文件存在且在有效期内返回 True
        """
        if not filepath.exists():
            return False
        mtime = datetime.fromtimestamp(os.path.getmtime(filepath))
        age = datetime.now() - mtime
        return age < timedelta(hours=max_age_hours)

    def _load_from_snapshot(self) -> Optional[List[Dict]]:
        """从最新版本快照加载数据（最高优先级）

        扫描 data/snapshots/v_*.json，取最新文件中的 standard_data 字段。

        Returns:
            ETF 数据列表，如果快照为空或加载失败返回 None
        """
        if not self.snapshot_dir.exists():
            return None

        snapshots = sorted(self.snapshot_dir.glob("v_*.json"), reverse=True)
        if not snapshots:
            return None

        latest = snapshots[0]
        try:
            with open(latest, "r", encoding="utf-8") as f:
                data = json.load(f)
            standard_data = data.get("standard_data")
            if standard_data and len(standard_data) > 0:
                snapshot_date = data.get("date", "unknown")
                print(
                    f"✅ 快照数据（{snapshot_date}）：{len(standard_data)} 只ETF",
                    file=sys.stderr,
                )
                return standard_data
        except Exception as e:
            print(f"⚠️ 快照加载失败：{e}", file=sys.stderr)

        return None

    def _load_etfs(self) -> List[Dict]:
        """加载ETF数据：快照 → 标准数据 → 过期数据 → 回退

        4层降级策略：
        1. 本地快照（最新版本）
        2. 标准数据文件（较新）
        3. 标准数据文件（即使过期）
        4. 回退文件（etf_complete_all.json / etf_data_generated.json）

        Returns:
            ETF 数据列表，无法加载时返回空列表 []
        """
        # 优先级1：本地快照（最新版本）
        snapshot_data = self._load_from_snapshot()
        if snapshot_data:
            return snapshot_data

        # 优先级2：标准数据文件（较新）
        if self._is_file_recent(self.standard_data_file, self.MAX_AGE_HOURS):
            try:
                with open(self.standard_data_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                print(f"✅ 标准化数据：{len(data)} 只ETF", file=sys.stderr)
                return data
            except Exception as e:
                print(f"⚠️ 标准化数据加载失败：{e}", file=sys.stderr)

        # 优先级3：标准数据文件（即使过期也用）
        if self.standard_data_file.exists():
            try:
                with open(self.standard_data_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                print(f"⚠️ 过期数据：{len(data)} 只ETF", file=sys.stderr)
                return data
            except Exception:
                pass

        # 优先级4：从旧缓存恢复
        for backup_name in ["etf_complete_all.json", "etf_data_generated.json"]:
            backup_file = self.root / backup_name
            if backup_file.exists():
                try:
                    with open(backup_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    print(
                        f"⚠️ 回退数据：{backup_name} ({len(data)} 只)",
                        file=sys.stderr,
                    )
                    return data
                except Exception:
                    pass

        print("❌ 无法加载任何数据", file=sys.stderr)
        return []

    def _ensure_loaded(self) -> None:
        """确保数据已加载，同时构建 code→ETF 的 O(1) 索引"""
        if self._etf_list is None:
            self._etf_list = self._load_etfs()
            self._etf_map = {
                etf["code"]: etf for etf in self._etf_list if "code" in etf
            }

    # ========== ETFRepository 接口实现 ==========

    def get_all_etfs(self) -> List[Dict]:
        """获取所有ETF数据

        首次调用时触发数据加载，后续调用直接返回缓存。

        Returns:
            ETF 数据列表，每个元素为包含 code/name/type/category 等字段的字典。
            数据无法加载时返回空列表 []。
        """
        self._ensure_loaded()
        return self._etf_list

    def get_etf_by_code(self, code: str) -> Optional[Dict]:
        """根据代码获取单个ETF（O(1) 查找）

        Args:
            code: ETF 代码，如 "510300"

        Returns:
            匹配的 ETF 字典，如果不存在返回 None
        """
        self._ensure_loaded()
        return self._etf_map.get(code)

    def filter_etfs(self, filters: Dict[str, Any]) -> List[Dict]:
        """根据条件筛选ETF

        支持的筛选条件：
        - type: ETF类型（如 "股票型"）
        - scale_min / scale_max: 规模范围（亿元）
        - return_min: 最低年化收益率
        - category: 分类（如 "宽基"、"行业"）
        - keyword: 关键词搜索（匹配名称或代码）

        Args:
            filters: 筛选条件字典

        Returns:
            筛选后的 ETF 列表，无匹配时返回空列表 []
        """
        etfs = self.get_all_etfs()
        result: List[Dict] = []

        for etf in etfs:
            if "type" in filters and filters["type"]:
                if etf.get("type") != filters["type"]:
                    continue
            if "scale_min" in filters and filters["scale_min"]:
                if (etf.get("scale") or 0) < float(filters["scale_min"]):
                    continue
            if "scale_max" in filters and filters["scale_max"]:
                if (etf.get("scale") or 0) > float(filters["scale_max"]):
                    continue
            if "return_min" in filters and filters["return_min"]:
                if (etf.get("year_1_return") or 0) < float(filters["return_min"]):
                    continue
            if "category" in filters and filters["category"]:
                if etf.get("category") != filters["category"]:
                    continue
            if "keyword" in filters and filters["keyword"]:
                keyword = str(filters["keyword"]).lower()
                name = etf.get("name", "").lower()
                code = etf.get("code", "").lower()
                if keyword not in name and keyword not in code:
                    continue

            result.append(etf)

        return result

    def get_etf_history(self, code: str, period: str = "1Y") -> Dict:
        """获取ETF历史净值数据

        4层降级策略：
        1. data/history/ 独立文件（最稳定，永久保存）
        2. etf_history_cache.json 全局缓存
        3. AKShare 实时获取（仅非生产环境）
        4. 模拟数据（兜底）

        Args:
            code: ETF 代码
            period: 时间周期，可选 '1M' / '3M' / '1Y' / '3Y'

        Returns:
            包含以下字段的字典：
            - code: ETF代码
            - period: 时间周期
            - prices: 归一化净值列表（以首日为基准 1.0）
            - dates: 日期列表
            - base_value: 基准净值
            - source: 数据来源标识
            - count: 数据点数
        """
        periods_map = {"1M": 22, "3M": 66, "1Y": 252, "3Y": 756}
        limit: int = periods_map.get(period, 252)

        # ===== 策略1：从 data/history/ 独立文件读取 =====
        try:
            sys.path.insert(0, str(self.root))
            from modules.local_store import load_etf_history as _load_history

            hist = _load_history(code)
            if hist and len(hist.get("prices", [])) >= limit:
                prices = hist["prices"][-limit:]
                dates = (
                    hist.get("dates", [])[-limit:] if hist.get("dates") else []
                )
                base: float = prices[0]
                normalized = [round(p / base, 4) for p in prices]
                return {
                    "code": code,
                    "period": period,
                    "prices": normalized,
                    "dates": dates,
                    "base_value": base,
                    "source": "local_history",
                    "count": len(prices),
                    "updated": hist.get("updated", ""),
                }
        except Exception as e:
            print(f"本地历史文件读取失败 [{code}]: {e}", file=sys.stderr)

        # ===== 策略2：从旧的全局缓存文件读取 =====
        try:
            cache_file = self.root / "etf_history_cache.json"
            if cache_file.exists():
                with open(cache_file, encoding="utf-8") as f:
                    cache = json.load(f)
                if code in cache:
                    entry = cache[code]
                    prices = entry.get("prices", [])
                    dates = entry.get("dates", [])
                    if len(prices) >= limit:
                        prices = prices[-limit:]
                        dates = dates[-limit:] if dates else []
                        base = prices[0]
                        normalized = [round(p / base, 4) for p in prices]
                        return {
                            "code": code,
                            "period": period,
                            "prices": normalized,
                            "dates": dates,
                            "base_value": base,
                            "source": "local_cache",
                            "count": len(prices),
                            "updated": entry.get("updated", ""),
                        }
        except Exception as e:
            print(f"本地缓存读取失败 [{code}]: {e}", file=sys.stderr)

        # ===== 策略3：AKShare实时 =====
        if os.environ.get("FLASK_ENV") != "production":
            try:
                import akshare as ak

                end_date = datetime.now()
                if period == "1M":
                    start_date = end_date - timedelta(days=35)
                elif period == "3M":
                    start_date = end_date - timedelta(days=100)
                elif period == "1Y":
                    start_date = end_date - timedelta(days=400)
                else:  # 3Y
                    start_date = end_date - timedelta(days=1100)

                df = ak.fund_etf_hist_em(
                    symbol=str(code),
                    period="daily",
                    start_date=start_date.strftime("%Y%m%d"),
                    end_date=end_date.strftime("%Y%m%d"),
                    adjust="qfq",
                )
                if df is not None and len(df) > 0:
                    prices = [float(v) for v in list(df["收盘"])]
                    dates = [str(d) for d in list(df["日期"])]
                    if len(prices) >= 5:
                        base = prices[0]
                        normalized = [round(p / base, 4) for p in prices]
                        # 同时保存到本地
                        try:
                            from modules.local_store import save_etf_history

                            save_etf_history(code, prices, dates, source="akshare")
                        except Exception:
                            pass
                        return {
                            "code": code,
                            "period": period,
                            "prices": normalized,
                            "dates": dates,
                            "base_value": base,
                            "source": "akshare_realtime",
                            "count": len(prices),
                        }
            except Exception as e:
                print(f"AKShare 历史数据失败 [{code}]: {e}", file=sys.stderr)

        # ===== 策略4：模拟数据（最终兜底） =====
        etf = self.get_etf_by_code(code)
        annual_return: float = etf.get("year_1_return", 0) if etf else 0

        data: List[float] = []
        value = 1.0
        daily_return = (annual_return / 100) / 252

        for i in range(limit):
            volatility = 0.02
            random_return = (
                (math.sin(i * 0.1) * 0.01)
                + daily_return
                + (math.cos(i * 0.3) * 0.005)
            )
            value = value * (1 + random_return)
            data.append(round(value, 4))

        return {
            "code": code,
            "period": period,
            "prices": data,
            "dates": [],
            "base_value": 1.0,
            "source": "simulated",
            "count": len(data),
            "note": "数据暂不可用，显示模拟数据",
        }

    def reload_data(self) -> None:
        """强制重新加载数据（pipeline 更新后调用）

        清除内部缓存，下次访问时自动重新从数据源加载。
        """
        self._etf_list = None
        self._etf_map = None
        self._ensure_loaded()

    # =========================================================
    # FinancialInstrumentRepository 抽象方法实现（适配器）
    # =========================================================

    def get_all(self):
        """获取所有ETF（实现 FinancialInstrumentRepository.get_all）"""
        etfs = self.get_all_etfs()
        # 将 Dict 转换为 ETF 对象（简单适配）
        from models.financial_instrument import ETF
        result = []
        for d in etfs:
            try:
                etf = ETF(
                    code=d.get('code', ''),
                    name=d.get('name', ''),
                    instrument_type=InstrumentType.ETF,
                    price=d.get('price'),
                    change_pct=d.get('change_pct'),
                    volume=d.get('volume'),
                    amount=d.get('amount'),
                    turnover=d.get('turnover'),
                    pre_close=d.get('pre_close'),
                    high=d.get('high'),
                    low=d.get('low'),
                    open=d.get('open'),
                    close=d.get('close'),
                )
                # 复制额外字段
                for k, v in d.items():
                    if not hasattr(etf, k):
                        setattr(etf, k, v)
                result.append(etf)
            except Exception:
                result.append(d)  # 兜底：返回原字典
        return result

    def get_by_code(self, code: str):
        """根据代码获取ETF（实现 FinancialInstrumentRepository.get_by_code）"""
        d = self.get_etf_by_code(code)
        if not d:
            return None
        from models.financial_instrument import ETF
        try:
            etf = ETF(
                code=d.get('code', ''),
                name=d.get('name', ''),
                instrument_type=InstrumentType.ETF,
                price=d.get('price'),
                change_pct=d.get('change_pct'),
                volume=d.get('volume'),
                amount=d.get('amount'),
                turnover=d.get('turnover'),
                pre_close=d.get('pre_close'),
                high=d.get('high'),
                low=d.get('low'),
                open=d.get('open'),
                close=d.get('close'),
            )
            for k, v in d.items():
                if not hasattr(etf, k):
                    setattr(etf, k, v)
            return etf
        except Exception:
            return d

    def filter(self, filters: Dict[str, Any]) -> List:
        """筛选ETF（实现 FinancialInstrumentRepository.filter）"""
        return self.filter_etfs(filters)

    def get_history(self, code: str, period: str = '1Y') -> Dict[str, Any]:
        """获取ETF历史（实现 FinancialInstrumentRepository.get_history）"""
        return self.get_etf_history(code, period)

    def save(self, instrument: Any) -> None:
        """保存ETF（LocalJSONRepo 只读，不实现）"""
        pass  # 本地JSON是只读数据源，不支持保存

    def save_batch(self, instruments: List[Any]) -> None:
        """批量保存ETF（LocalJSONRepo 只读，不实现）"""
        pass  # 本地JSON是只读数据源，不支持保存

    # =========================================================
    # ETFRepository 其余抽象方法实现（暂返回空/空列表）
    # =========================================================

    def get_etf_by_category(self, category: str) -> List[Dict]:
        """根据分类查询ETF（暂返回空列表）"""
        return []  # TODO: 从本地数据实现按分类筛选

    def get_etf_by_tracking_index(self, index_code: str) -> List[Dict]:
        """根据跟踪指数查询ETF（暂返回空列表）"""
        return []  # TODO: 从本地数据实现按跟踪指数筛选

    def get_etf_holdings(self, code: str) -> List[Dict]:
        """获取ETF持仓明细（暂返回空列表）"""
        return []  # TODO: 从本地数据实现持仓明细查询