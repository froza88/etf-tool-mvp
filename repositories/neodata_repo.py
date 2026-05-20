"""
NeoDataRepo v1.1 — NeoData API 在线兜底数据源
======================================

v1.1 升级：从 apiRecall Markdown 表格解析 price/volume/收益率/持仓等字段

交付状态：✅ 代码可运行，CLI 调用通，解析为最简实现（后续优化）

验收标准：
  ✅ NeoDataRepo 可实例化
  ✅ get_etf_by_code('510300') 返回 Dict（非 None）
  ✅ get_all_etfs() 返回 []（符合预期）
  ✅ filter_etfs({}) 返回 []（符合预期）

测试方法：
  cd /Users/apangduo/WorkBuddy/Claw/etf-tool-mvp
  python3 -c "from repositories.neodata_repo import NeoDataRepo; r=NeoDataRepo(); print(r.get_etf_by_code('510300'))"
"""

import json
import subprocess
import sys
from pathlib import Path
from typing import List, Dict, Optional, Any

from .etf_repository import ETFRepository


# ── NeoDataRepo ──────────────────────────────

class NeoDataRepo(ETFRepository):
    """
    NeoData 在线兜底数据源

    调用：CLI 脚本 query.py
    解析：v1.0 最简实现（仅提取 code/name/source，价格等后续版本优化）
    """

    def __init__(self, script_path: Optional[str] = None):
        default = (
            Path.home()
            / ".workbuddy/plugins/marketplaces/cb_teams_marketplace"
            / "plugins/finance-data/skills/neodata-financial-search/scripts/query.py"
        )
        self.script_path = script_path or str(default)
        self._cache: Dict[str, Dict] = {}

    # ── 私有：CLI 调用 ──────────────────────

    def _call(self, query: str) -> Optional[Dict]:
        """调用 NeoData CLI，返回解析后的 JSON dict，失败返回 None"""
        try:
            r = subprocess.run(
                [sys.executable, self.script_path, "--query", query],
                capture_output=True, text=True,
                timeout=30, encoding="utf-8",
            )
            if r.returncode != 0:
                return None
            data = json.loads(r.stdout)
            if data.get("code") != "200" or not data.get("suc"):
                return None
            return data
        except Exception:
            return None

    # ── 私有：Markdown 表格解析 ──────────

    @staticmethod
    def _parse_md_table(content: str) -> Optional[List[Dict[str, str]]]:
        """解析 Markdown 管道表格（返回 header→value 的 dict 列表）

        处理格式：
        | 列1 | 列2 |    ← header
        | --- | --- |    ← separator（跳过）
        | v1  | v2  |    ← data rows
        """
        lines = [l.strip() for l in content.split("\n") if l.strip()]
        # 找第一个含 | 且不含 :--- 的行为表头
        header_idx = -1
        headers = None
        for i, line in enumerate(lines):
            if "|" not in line:
                continue
            if ":---" in line:
                continue  # 分隔行
            parts = [h.strip() for h in line.split("|") if h.strip()]
            if len(parts) >= 2:
                headers = parts
                header_idx = i
                break
        if headers is None:
            return None

        rows: List[Dict[str, str]] = []
        for line in lines[header_idx + 1:]:
            if "|" not in line or ":---" in line:
                continue
            cells = [c.strip() for c in line.split("|") if c.strip()]
            if not cells:
                continue
            # 补齐/截断到 header 长度
            while len(cells) < len(headers):
                cells.append("")
            cells = cells[:len(headers)]
            rows.append(dict(zip(headers, cells)))
        return rows if rows else None

    @staticmethod
    def _safe_float(v: Any, default: float = 0.0) -> float:
        """安全转 float，-- 或空返回 default"""
        if v is None or v == "" or v == "--" or v == "-":
            return default
        try:
            return float(str(v).replace(",", "").replace("亿", "").strip())
        except (ValueError, TypeError):
            return default

    @staticmethod
    def _safe_int(v: Any, default: int = 0) -> int:
        """安全转 int"""
        if v is None or v == "" or v == "--":
            return default
        try:
            return int(float(str(v).replace(",", "").strip()))
        except (ValueError, TypeError):
            return default

    # ── 私有：解析响应（v1.1 Markdown 表格）──

    def _parse_etf(self, data: Dict, code: str) -> Optional[Dict]:
        """从 NeoData 响应解析 ETF dict（v1.1：从 apiRecall Markdown 表格提取字段）"""
        if not data:
            return None

        recalls = data.get("data", {}).get("apiData", {}).get("apiRecall", [])
        entity_list = data.get("data", {}).get("apiData", {}).get("entity", [])

        # 从 entity 取 name（注意：name 字段是代码如 510300.JJ，code 字段才是中文名）
        name = entity_list[0].get("code", code) if entity_list else code

        result: Dict[str, Any] = {
            "code": code,
            "name": name,
            "source": "neodata",
            "price": 0.0,
            "change_pct": 0.0,
            "volume": 0,
            "amount": 0.0,
            "pre_close": 0.0,
            "open": 0.0,
            "high": 0.0,
            "low": 0.0,
            "nav": 0.0,
            "scale": 0.0,           # 规模（亿）
            "share_count": 0,
            "year_1_return": 0.0,
            "year_3_return": 0.0,
        }

        for recall in recalls:
            content: str = recall.get("content", "")
            rtype: str = recall.get("type", "")
            if not content:
                continue

            # ── apiRecall[0]：实时行情 ──
            if "实时行情" in rtype:
                rows = self._parse_md_table(content)
                if rows:
                    row = rows[0]
                    result["price"] = self._safe_float(row.get("最新价格"))
                    result["pre_close"] = self._safe_float(row.get("昨收盘"))
                    result["open"] = self._safe_float(row.get("今开盘"))
                    result["high"] = self._safe_float(row.get("当天最高价格"))
                    result["low"] = self._safe_float(row.get("当天最低价格"))
                    result["volume"] = self._safe_int(row.get("总成交"))
                    result["nav"] = self._safe_float(row.get("基金净值"))

            # ── apiRecall[1]：份额/规模 ──
            elif "最新份额" in rtype:
                rows = self._parse_md_table(content)
                if rows:
                    row = rows[0]
                    scale_raw = self._safe_float(row.get("规模"))
                    if scale_raw > 0:
                        result["scale"] = round(scale_raw / 100_000_000, 2)
                    result["share_count"] = self._safe_int(row.get("份额"))
                    # 如果实时行情没拿到 price，从收盘价补
                    if result["price"] == 0.0:
                        result["price"] = self._safe_float(row.get("收盘价（不复权）"))

            # ── apiRecall[2]：净值/收益率 ──
            elif "净值" in rtype and "回报" in rtype:
                rows = self._parse_md_table(content)
                if rows:
                    row = rows[0]  # 取最新（第一行）
                    result["nav"] = self._safe_float(row.get("单位净值(元)")) or result["nav"]
                    result["change_pct"] = self._safe_float(row.get("复权单位净值日增长率"))
                    result["year_1_return"] = round(self._safe_float(row.get("近1年回报率(%)")), 2)
                    result["year_3_return"] = round(self._safe_float(row.get("近3年回报率(%)")), 2)
                    result["return_1w"] = round(self._safe_float(row.get("近一周回报率(%)")), 2)
                    result["return_1m"] = round(self._safe_float(row.get("近1个月回报率(%)")), 2)
                    result["return_3m"] = round(self._safe_float(row.get("近3个月回报率(%)")), 2)
                    result["return_6m"] = round(self._safe_float(row.get("近6个月回报率(%)")), 2)
                    result["return_ytd"] = round(self._safe_float(row.get("今年以来回报率(%)")), 2)
                    result["return_since_inception"] = round(self._safe_float(row.get("成立以来回报率(%)")), 2)

            # ── apiRecall[3]：资产配置/持仓 ──
            elif "资产配置" in rtype:
                rows = self._parse_md_table(content)
                if rows:
                    holdings = []
                    for hrow in rows:
                        asset_name = hrow.get("资产类型名", "")
                        ratio = self._safe_float(hrow.get("比例"))
                        if asset_name and ratio > 0:
                            holdings.append({
                                "name": asset_name,
                                "ratio": ratio,
                            })
                    if holdings:
                        result["holdings_overview"] = holdings

        return result

    # ── ETFRepository 接口实现 ───────────────────

    def get_all_etfs(self) -> List[Dict]:
        """NeoData 不支持批量，返回 []"""
        return []

    def get_etf_by_code(self, code: str) -> Optional[Dict]:
        """根据代码查询（CLI 调用 + 最简解析）"""
        if code in self._cache:
            return self._cache[code]
        data = self._call(f"{code} ETF 最新数据")
        etf = self._parse_etf(data, code) if data else None
        if etf:
            self._cache[code] = etf
        return etf

    def filter_etfs(self, filters: Dict[str, Any]) -> List[Dict]:
        """NeoData 不支持筛选，返回 []"""
        return []

    def get_etf_history(self, code: str, period: str = "1Y") -> Dict:
        """历史数据（v1.0 空实现）"""
        return {"prices": [], "dates": [], "source": "neodata"}

    def get_etf_holdings(self, code: str) -> List[Dict]:
        """持仓（v1.0 空实现）"""
        return []

    def get_etf_by_tracking_index(self, index_code: str) -> List[Dict]:
        return []

    def get_etf_by_category(self, category: str) -> List[Dict]:
        return []

    # ── FinancialInstrumentRepository 接口 ─────────────

    def get_all(self):
        return self.get_all_etfs()

    def get_by_code(self, code: str):
        return self.get_etf_by_code(code)

    def filter(self, filters: Dict[str, Any]):
        return self.filter_etfs(filters)

    def get_history(self, code: str, period: str = "1Y"):
        return self.get_etf_history(code, period)

    def save(self, instrument):
        pass  # 只读

    def save_batch(self, instruments):
        pass  # 只读
