"""
ETF 对比工具 — 腾讯云云函数（SCF）入口
单文件，零依赖（仅标准库），内存缓存本地数据。

部署方式：
1. 上传到腾讯云 SCF，入口设为 main_handler
2. 将 etf_standard_data.json 打包进代码包
3. 绑定 API 网关触发器
"""

import json
import os
import time
from pathlib import Path

# ─── 本地数据加载（全局缓存） ───
_DATA = None
_DATA_MTIME = 0


def load_data():
    """加载本地 ETF 数据，只在文件变化时重新加载"""
    global _DATA, _DATA_MTIME
    data_file = Path(__file__).parent / "etf_standard_data.json"
    if not data_file.exists():
        return {}
    mtime = data_file.stat().st_mtime
    if _DATA is None or mtime > _DATA_MTIME:
        with open(data_file, "r", encoding="utf-8") as f:
            raw = json.load(f)
        # 建立 code -> info 索引
        _DATA = {}
        if isinstance(raw, list):
            for item in raw:
                code = item.get("code")
                if code:
                    _DATA[str(code)] = item
        elif isinstance(raw, dict):
            _DATA = raw
        _DATA_MTIME = mtime
    return _DATA


# ─── 字段映射（本地字段 → 对比输出字段） ───
FIELD_MAP = {
    "name": "名称",
    "code": "代码",
    "issuer_short": "发行人",
    "issuer_full": "发行人全称",
    "category": "品类",
    "benchmark": "跟踪标的",
    "issue_date": "成立日期",
    "custodian": "托管人",
    "management_fee_rate": "管理费率(%)",
    "custody_fee_rate": "托管费率(%)",
    "fee_rate": "综合费率(%)",
    "close": "最新价",
    "prev_close": "昨收",
    "change_rate": "涨跌幅(%)",
    "scale": "规模(百万)",
    "shares": "份额(百万份)",
    "volume": "成交额(万元)",
    "year_1_return": "近1年回报(%)",
    "year_3_return": "近3年回报(%)",
    "annual_vol": "年化波动率(%)",
    "max_drawdown": "最大回撤(%)",
    "sharpe_ratio": "夏普比率",
    "calmar_ratio": "卡玛比率",
    "annual_3y": "年化回报(%)",
}

# 对比页核心字段（优先展示）
COMPARE_FIELDS = [
    "代码", "名称", "发行人", "品类",
    "跟踪标的", "成立日期", "综合费率(%)",
    "最新价", "涨跌幅(%)", "规模(百万)", "成交额(万元)",
    "近1年回报(%)", "近3年回报(%)",
    "年化波动率(%)", "最大回撤(%)", "夏普比率",
]

# 数值格式化
def fmt_val(v, key=""):
    """格式化数值"""
    if v is None or v == "":
        return "—"
    if isinstance(v, float):
        if "费率" in key:
            return f"{v:.2f}"
        if "回报" in key or "涨跌" in key or "波动" in key or "回撤" in key:
            return f"{v:+.2f}"
        if "夏普" in key or "卡玛" in key:
            return f"{v:.2f}"
        if "规模" in key:
            return f"{v:.0f}"
        return f"{v:.2f}"
    return str(v)


def main_handler(event, context):
    """
    API 网关触发。

    请求格式：
    GET /?codes=518880,517520
    GET /?search=黄金

    返回格式：
    {
      "ok": true,
      "data": {
        "etfs": [...],
        "fields": [...],
        "updated": "2026-06-04"
      }
    }
    """
    # 1. 解析请求参数
    params = event.get("queryStringParameters") or event.get("queryString") or event.get("path") or ""
    if isinstance(params, dict):
        codes_str = params.get("codes", "")
        search = params.get("search", "")
    else:
        codes_str = ""
        search = ""
        # 尝试从 path 解析
        path = event.get("path", "")
        if "codes=" in path:
            import urllib.parse
            qs = urllib.parse.parse_qs(path.split("?")[1] if "?" in path else "")
            codes_str = ",".join(qs.get("codes", [""]))
            search = ",".join(qs.get("search", [""]))

    # 2. 加载数据
    db = load_data()

    # 3. 搜索模式
    if search and not codes_str:
        results = []
        keyword = search.lower()
        for code, info in db.items():
            name = str(info.get("name", "")).lower()
            issuer = str(info.get("issuer_short", "")).lower()
            if keyword in name or keyword in issuer or keyword in code:
                item = {}
                for local_key, cn_key in FIELD_MAP.items():
                    item[cn_key] = fmt_val(info.get(local_key), cn_key)
                results.append(item)
        return make_response({"ok": True, "data": {"etfs": results[:20], "count": len(results)}})

    # 4. 对比模式
    if codes_str:
        codes = [c.strip() for c in codes_str.split(",") if c.strip()]
        etfs = []
        for code in codes:
            info = db.get(code)
            if info:
                item = {}
                for local_key, cn_key in FIELD_MAP.items():
                    item[cn_key] = fmt_val(info.get(local_key), cn_key)
                etfs.append(item)

        return make_response({
            "ok": True,
            "data": {
                "etfs": etfs,
                "fields": COMPARE_FIELDS,
                "count": len(etfs),
                "updated": "2026-06-04",
            }
        })

    # 5. 默认返回首页数据
    return make_response({
        "ok": True,
        "data": {
            "total": len(db),
            "updated": "2026-06-04",
        }
    })


def make_response(body):
    """构造 API 网关响应"""
    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/json; charset=utf-8",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, OPTIONS",
            "Cache-Control": "public, max-age=300",
        },
        "body": json.dumps(body, ensure_ascii=False),
    }


# ─── 本地调试入口 ───
if __name__ == "__main__":
    # 模拟 API 网关事件
    import sys
    codes = sys.argv[1] if len(sys.argv) > 1 else "518880,517520"
    event = {"queryStringParameters": {"codes": codes}}
    result = main_handler(event, None)
    print(result["body"])
