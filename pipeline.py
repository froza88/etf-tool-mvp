#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ETF 数据 Pipeline - 统一入口（v2：集成本地存储+版本管理）

用法：python pipeline.py [step]
  python pipeline.py          # 执行全部步骤
  python pipeline.py sync     # 只同步 ETF 列表
  python pipeline.py enrich   # 只补充价格+持仓
  python pipeline.py calc     # 只计算风险指标
  python pipeline.py build    # 只生成标准化数据
  python pipeline.py deploy   # 只部署（git push）
  python pipeline.py snapshot # 手动创建版本快照
  python pipeline.py verify   # 校验数据完整性
  python pipeline.py migrate  # 迁移旧数据到本地存储

v2 改进：
- 每步执行后自动创建版本快照（data/snapshots/）
- 历史K线按ETF拆分为独立文件（data/history/），永久保存
- 自动冗余备份（data/backup/）
- 数据完整性校验
- 版本元数据自动记录（data/meta.json）
"""

import argparse
import json
import math
import os
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).parent

# Wind 数据文件（查询即存储缓存）
WIND_DATA_FILE = ROOT / "etf_wind_data.json"

# 本地存储模块
sys.path.insert(0, str(ROOT))
from modules.local_store import (
    create_snapshot,
    create_backup,
    save_etf_history,
    load_etf_history,
    migrate_history_cache,
    verify_data_integrity,
    init_store,
    load_json,
    save_json,
    LEGACY_FILES,
    HISTORY_DIR,
)


# ============ 工具函数 ============

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")


def _trigger_pa_sync():
    """推送成功后触发 PythonAnywhere 同步（调用 /api/sync）"""
    import os
    pa_url = os.environ.get('PA_URL', 'https://froza.pythonanywhere.com')
    if not pa_url:
        return
    try:
        import requests
        resp = requests.post(f'{pa_url}/api/sync', timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            log(f"  PA 同步成功: {data.get('status', '')} | {data.get('git_output', '')[:80]}")
        else:
            log(f"  PA 同步 HTTP 失败: {resp.status_code} | {resp.text[:80]}")
    except Exception as e:
        log(f"  PA 同步请求失败: {e}")


def get_akshare():
    """懒加载 AKShare，过滤警告"""
    import warnings
    warnings.filterwarnings("ignore")
    import akshare as ak
    return ak


# ============ Step 1: 同步 ETF 列表 ============

def step_sync_list():
    """从 AKShare + 本地 取并集，同步 ETF 列表"""
    log("Step 1: 同步 ETF 列表")
    ak = get_akshare()

    # 从 AKShare 获取最新列表
    try:
        df = ak.fund_etf_spot_em()
        akshare_etfs = []
        for _, row in df.iterrows():
            try:
                etf = {
                    "code": str(row["代码"]).zfill(6),
                    "name": str(row["名称"]).strip(),
                    "market_cap": float(row["总市值"]) if "总市值" in row else 0,
                    "volume": float(row["成交量"]) if "成交量" in row else 0,
                    "change_pct": float(row["涨跌幅"]) if "涨跌幅" in row else 0,
                }
                akshare_etfs.append(etf)
            except Exception:
                continue
        log(f"  AKShare 返回 {len(akshare_etfs)} 只")
        akshare_codes = {e["code"] for e in akshare_etfs}
    except Exception as e:
        log(f"  AKShare 获取失败: {e}")
        akshare_etfs = []
        akshare_codes = set()

    # 加载本地数据
    local_file = LEGACY_FILES["complete"]
    if local_file.exists():
        local_etfs = load_json(local_file)
        local_codes = {e.get("code", "") for e in local_etfs if e.get("code")}
        log(f"  本地数据: {len(local_etfs)} 只")
    else:
        local_etfs = []
        local_codes = set()

    # 取并集
    merged = {}
    for etf in akshare_etfs:
        merged[etf["code"]] = etf
    for etf in local_etfs:
        code = etf.get("code", "")
        if code and code not in merged:
            merged[code] = etf

    new_count = len(akshare_codes - local_codes)
    log(f"  并集: {len(merged)} 只（新增 {new_count}）")

    save_json(local_file, list(merged.values()))

    # 自动快照
    create_snapshot("sync")
    return len(merged)


# ============ Step 2: 补充数据（价格 + 持仓） ============

def step_enrich():
    """从各数据源补充价格、持仓等字段"""
    log("Step 2: 补充数据（价格 + 持仓）")

    gen_file = LEGACY_FILES["generated"]
    if not gen_file.exists():
        log(f"  非凸数据文件不存在: {gen_file.name}，跳过")
        return

    # 加载非凸数据（已有价格和持仓）
    gen_data = load_json(gen_file)
    gen_map = {}
    for item in gen_data:
        code = str(item.get("code", ""))
        if code:
            gen_map[code] = item
    log(f"  非凸数据: {len(gen_map)} 只")

    # 用 AKShare 补充持仓（仅缺失持仓的 ETF）
    ak = get_akshare()
    holdings_added = 0
    codes_need_holdings = [c for c, v in gen_map.items() if not v.get("top_holdings")]

    if codes_need_holdings:
        log(f"  需补充持仓: {len(codes_need_holdings)} 只")
        for i, code in enumerate(codes_need_holdings):
            try:
                df = ak.fund_portfolio_hold_em(symbol=code, date="2026")
                if df is not None and len(df) > 0:
                    holdings = []
                    for _, r in df.iterrows():
                        try:
                            name = str(r.iloc[2]).strip()
                            weight = float(r.iloc[3])
                            holdings.append({"name": name, "weight": f"{weight:.2f}%"})
                        except Exception:
                            pass
                        if len(holdings) >= 5:
                            break
                    gen_map[code]["top_holdings"] = holdings
                    holdings_added += 1
            except Exception:
                pass
            time.sleep(0.2)
            if (i + 1) % 20 == 0:
                log(f"  持仓进度: {i+1}/{len(codes_need_holdings)}")

    log(f"  持仓补充: +{holdings_added} 只")
    save_json(gen_file, list(gen_map.values()))

    # 自动快照
    create_snapshot("enrich")


# ============ Step 2.5: 从 Wind 补充基础信息 ============

def step_enrich_wind():
    """从 Wind API 补充 ETF 基础信息（托管人/基准/费率）- 查询即存储
    每次调用自动缓存到 data/cache/wind/{code}.json，优先读缓存
    """
    log("Step 2.5: 从 Wind 补充基础信息")

    from fetchers.wind_fetcher import WindFetcher

    standard_file = LEGACY_FILES["standard"]
    if not standard_file.exists():
        log("  无标准化数据，请先运行 build 步骤")
        return

    # 加载现有数据
    standard_data = load_json(standard_file)

    # 加载已有 Wind 缓存（etf_wind_data.json 汇总，增量补充）
    wind_data = {}
    if WIND_DATA_FILE.exists():
        wind_data = load_json(WIND_DATA_FILE) or {}

    # 找出需要 Wind 数据的 ETF（缺失 custodian / benchmark / management_fee_rate）
    need_wind = []
    for e in standard_data:
        code = e.get("code", "")
        if not code:
            continue
        existing = wind_data.get(code, {})
        missing = []
        if not e.get("custodian") and not existing.get("custodian"):
            missing.append("custodian")
        if not e.get("benchmark") and not existing.get("benchmark"):
            missing.append("benchmark")
        if not e.get("management_fee_rate") and not existing.get("management_fee_rate"):
            missing.append("management_fee_rate")
        if missing:
            need_wind.append((code, e.get("name", ""), missing))

    if not need_wind:
        log("  所有 ETF 已有 Wind 基础信息，跳过")
        return

    log(f"  需补充 Wind 数据: {len(need_wind)} 只（已缓存: {len(wind_data)}）")

    # 每日限制：每次调用 ~6.67 积分，保留余量不耗尽
    # 剩余 ~934 积分 → 上限 100 次（约 667 积分）
    daily_limit = min(len(need_wind), 100)
    batch = need_wind[:daily_limit]
    if len(need_wind) > daily_limit:
        log(f"  今日处理前 {daily_limit} 只，剩余 {len(need_wind) - daily_limit} 只（后续可继续）")

    fetcher = WindFetcher()
    api_calls = 0
    updated = 0

    for i, (code, name, missing_fields) in enumerate(batch):
        short_name = name[:25] if name else ""

        try:
            wind_result = fetcher.fetch_etf_info(code, name)
            if wind_result:
                # 存储到汇总文件
                wind_data[code] = wind_data.get(code, {})
                for field in missing_fields:
                    if field in wind_result and wind_result[field]:
                        wind_data[code][field] = wind_result[field]
                updated += 1
                api_calls += 1
            else:
                log(f"  [{i+1}/{len(batch)}] {code} {short_name} ✗ 获取失败")
        except Exception as e:
            log(f"  [{i+1}/{len(batch)}] {code} {short_name} ✗ 异常: {e}")

        if (i + 1) % 20 == 0:
            log(f"  进度: {i+1}/{len(batch)} 成功={updated}")

        # 避免 QPS 限制
        time.sleep(0.5)

    # 保存 Wind 汇总数据
    save_json(WIND_DATA_FILE, wind_data)

    log(f"  Wind 补充: 更新 {updated}/{len(batch)} 只，API 调用 ~{api_calls} 次")
    log(f"  Wind 汇总缓存: {len(wind_data)} 只")

    create_snapshot("enrich_wind")


# ============ Step 3: 计算风险指标（唯一实现） ============

def calc_metrics_from_prices(prices):
    """
    从价格序列计算风险指标（唯一实现，全项目共用）
    返回: dict with year_1_return, year_3_return, max_drawdown, sharpe_ratio, annual_vol
    """
    n = len(prices)
    if n < 20:
        return None

    # 近 1 年 / 3 年收益
    y1 = None
    y3 = None
    if n >= 252:
        y1 = (prices[-1] - prices[-252]) / prices[-252] * 100
    if n >= 756:
        y3 = (prices[-1] - prices[-756]) / prices[-756] * 100

    # 最大回撤
    peak = prices[0]
    max_dd = 0.0
    for p in prices:
        if p > peak:
            peak = p
        dd = (p - peak) / peak * 100
        if dd < max_dd:
            max_dd = dd

    # 年化波动率 & 夏普比率
    annual_vol = 0
    sharpe = 0
    if n >= 30:
        daily_returns = [
            (prices[i] - prices[i - 1]) / prices[i - 1]
            for i in range(1, min(n, 253))
        ]
        if daily_returns:
            avg_ret = sum(daily_returns) / len(daily_returns)
            vol = math.sqrt(sum((r - avg_ret) ** 2 for r in daily_returns) / len(daily_returns))
            annual_vol = vol * math.sqrt(252) * 100
            annual_ret = avg_ret * 252 * 100
            sharpe = (annual_ret - 2) / annual_vol if annual_vol > 0 else 0

    return {
        "year_1_return": round(y1, 2) if y1 is not None else 0,
        "year_3_return": round(y3, 2) if y3 is not None else 0,
        "max_drawdown": round(max_dd, 2),
        "sharpe_ratio": round(sharpe, 2),
        "annual_vol": round(annual_vol, 2),
    }


def step_calc_metrics():
    """从历史 K 线计算风险指标，写入 etf_calculated_metrics.json
    v2改进：历史K线同时保存到 data/history/{code}.json（永久存储）
    """
    log("Step 3: 计算风险指标")

    calc_file = LEGACY_FILES["metrics"]
    standard_file = LEGACY_FILES["standard"]

    # 加载现有计算结果
    calc_data = {}
    if calc_file.exists():
        calc_data = load_json(calc_file)
        log(f"  已有指标: {len(calc_data)} 只")

    # 加载 ETF 列表
    if standard_file.exists():
        etfs = load_json(standard_file)
    elif LEGACY_FILES["complete"].exists():
        etfs = load_json(LEGACY_FILES["complete"])
    else:
        log("  无 ETF 数据，跳过")
        return

    # 找出需要计算的 ETF（没有指标或指标为 0）
    need_calc = [e for e in etfs if e.get("code") and not calc_data.get(e["code"], {}).get("year_1_return")]
    log(f"  需计算: {len(need_calc)} 只")

    if not need_calc:
        log("  所有 ETF 已有指标，跳过")
        return

    # 优先从 data/history/ 加载（新存储方式），回退到旧缓存
    ak = get_akshare()
    ok = fail = 0

    # 按规模排序，优先处理大基金
    need_calc.sort(key=lambda x: x.get("scale", 0) or 0, reverse=True)

    # 限制每天最多处理 200 只（避免 API 限流）
    batch = need_calc[:200]
    if len(need_calc) > 200:
        log(f"  今天处理前 200 只，剩余 {len(need_calc) - 200} 只")

    for i, etf in enumerate(batch):
        code = etf["code"]

        # 优先从本地历史文件读取（永久存储）
        local_history = load_etf_history(code)
        if local_history and len(local_history.get("prices", [])) >= 252:
            prices = local_history["prices"]
            metrics = calc_metrics_from_prices(prices)
            if metrics:
                calc_data[code] = metrics
                ok += 1
                continue

        # 本地没有，从 AKShare 拉取
        try:
            df = ak.fund_etf_hist_em(
                symbol=str(code),
                period="daily",
                start_date=(datetime.now() - timedelta(days=1100)).strftime("%Y%m%d"),
                end_date=datetime.now().strftime("%Y%m%d"),
                adjust="qfq",
            )
            if df is not None and len(df) >= 20:
                prices = [float(v) for v in list(df["收盘"])]
                dates = [str(d) for d in list(df["日期"])]
                metrics = calc_metrics_from_prices(prices)
                if metrics:
                    calc_data[code] = metrics
                    # v2: 保存到独立历史文件（永久存储）
                    save_etf_history(code, prices, dates, source="akshare")
                    ok += 1
                else:
                    fail += 1
            else:
                fail += 1
        except Exception:
            fail += 1

        time.sleep(0.3)
        if (i + 1) % 50 == 0:
            log(f"  进度: {i+1}/{len(batch)} 成功={ok} 失败={fail}")

    log(f"  计算: 成功={ok} 失败={fail}")

    # 保存指标数据
    save_json(calc_file, calc_data)

    # 同步更新旧的 history_cache.json（兼容）
    _sync_legacy_history_cache()

    # 自动快照
    create_snapshot("calc")


def _sync_legacy_history_cache():
    """将 data/history/ 中的数据同步回旧格式 etf_history_cache.json（兼容）"""
    from modules.local_store import HISTORY_DIR
    cache = {}
    for f in HISTORY_DIR.glob("*.json"):
        data = load_json(f)
        if data and "code" in data:
            code = data["code"]
            cache[code] = {
                "prices": data.get("prices", []),
                "dates": data.get("dates", []),
                "count": data.get("count", 0),
                "updated": data.get("updated", ""),
            }
    if cache:
        save_json(LEGACY_FILES["history_cache"], cache)


# ============ Step 4: 生成标准化数据 ============

def step_build():
    """合并所有数据源，生成 etf_standard_data.json"""
    log("Step 4: 生成标准化数据")

    from modules.issuer_extract import get_full_name as issuer_full_name
    from modules.issuer_extract import get_short_name as issuer_short_name

    full_file = LEGACY_FILES["complete"]
    gen_file = LEGACY_FILES["generated"]
    calc_file = LEGACY_FILES["metrics"]
    output_file = LEGACY_FILES["standard"]

    if not full_file.exists():
        log(f"  缺少 {full_file.name}，请先运行 sync 步骤")
        return

    full_data = load_json(full_file)
    log(f"  全量数据: {len(full_data)} 只")

    # 加载生成数据
    gen_data = []
    if gen_file.exists():
        gen_data = load_json(gen_file)
    gen_map = {}
    for item in gen_data:
        code = str(item.get("code", ""))
        if code:
            gen_map[code] = item

    # 加载计算指标
    calc_data = {}
    if calc_file.exists():
        calc_data = load_json(calc_file)

    # 加载盈米指标（补充）
    yingmi_data = {}
    if LEGACY_FILES["yingmi"].exists():
        yingmi_data = load_json(LEGACY_FILES["yingmi"]) or {}

    # 加载 Wind 补充数据
    wind_data = {}
    if WIND_DATA_FILE.exists():
        wind_data = load_json(WIND_DATA_FILE) or {}
        log(f"  Wind 数据: {len(wind_data)} 只")

    # 建立 name→issuer 映射
    known_names = {}
    for item in gen_data:
        n = item.get("name", "").strip()
        i = item.get("issuer", "").strip()
        if n and i and n not in known_names:
            known_names[n] = i
    known_names = dict(sorted(known_names.items(), key=lambda x: -len(x[0])))

    _COMMON_ISSUERS = sorted([
        "基金管理有限公司", "基金", "证券", "资产管理有限公司", "资产管理",
        "华泰柏瑞基金", "华泰柏瑞", "易方达", "华夏基金", "华夏", "华宝基金", "华宝",
        "天弘基金", "天弘", "国泰基金", "国泰", "南方基金", "南方", "博时基金", "博时",
        "银华基金", "银华", "广发基金", "广发", "嘉实基金", "嘉实",
        "招商基金", "招商", "富国基金", "富国",
        "汇添富", "汇添富基金", "景顺长城", "景顺长城基金", "景顺",
        "中欧基金", "鹏华基金", "鹏华", "万家基金", "万家", "建信基金", "建信",
        "工银瑞信", "工银",
        "交银施罗德", "交银", "兴证全球", "兴全", "前海开源", "中银基金", "中银", "上投摩根",
        "国投瑞银", "长信基金", "长城基金", "长城", "财通基金", "创金合信",
        "金鹰基金", "大成基金", "大成", "融通基金", "融通", "西部利得", "新华基金", "新华",
        "华商基金", "诺安基金", "方正富邦", "东吴基金", "浙商基金",
        "中信保诚", "光大保德", "摩根士丹利", "摩根", "农银汇理", "中海基金",
        "中加基金", "中信建投", "鑫元基金", "鑫元", "国联基金", "国联", "信达澳亚",
        "宏利基金", "太平基金", "永赢基金", "永赢", "恒生前海", "汇安基金", "汇安",
        "山西证券", "格林基金", "贝莱德", "路博迈", "国金基金",
        "英大基金", "兴银基金", "兴银", "中泰资管", "申万菱信", "银河基金", "银河",
        "长盛基金", "红塔红土", "大摩基金", "德邦基金", "南华基金", "南华",
        "尚正基金", "瑞达基金", "富敦基金", "中科沃土", "华宸未来",
        "明亚基金", "华融基金", "红土创新", "华泰资管", "太平洋证券",
        "中原证券", "国海证券", "第一创业", "东方证券", "长江资管",
        "浙商资管", "财通资管",
        "华安", "平安", "东财", "兴业", "泰康", "浦银",
        "华富", "国寿", "中金", "鹏扬", "海富通", "民生加银",
        "国联安", "弘毅远方",
    ], key=lambda x: -len(x))

    def extract_name_issuer(raw_name):
        for issuer in _COMMON_ISSUERS:
            if raw_name.endswith(issuer):
                name = raw_name[:-len(issuer)].strip().rstrip("-")
                if name:
                    return name, issuer
        for known_name, known_issuer in known_names.items():
            if known_name in raw_name:
                rest = raw_name.replace(known_name, "", 1).strip()
                if rest and len(rest) <= 12:
                    return known_name, known_issuer
        for issuer in _COMMON_ISSUERS:
            if raw_name.startswith(issuer):
                name = raw_name[len(issuer):].strip()
                if name:
                    return name, issuer
        return raw_name, ""

    # 分类关键词
    CATEGORY_KEYWORDS = {
        "宽基": ["沪深300", "中证500", "上证50", "科创50", "中证1000", "中证800",
                  "中证2000", "创业板指", "深证100", "上证指数", "中证全指", "国证2000"],
        "红利": ["红利", "股息", "高股息"],
        "债券": ["国债", "政金债", "地方债", "信用债", "可转债", "债券", "利率债"],
        "商品": ["黄金", "原油", "豆粕", "有色", "化工", "钢铁", "煤炭", "农产品"],
        "跨境": ["纳斯达克", "标普", "日经", "恒生", "德国DAX", "法国CAC", "英国富时",
                  "港股通", "恒生科技", "中概", "QDII", "美元", "全球"],
        "货币": ["货币", "理财", "短债", "逆回购"],
    }

    def classify_category(raw_name):
        for cat, keywords in CATEGORY_KEYWORDS.items():
            if any(k in raw_name for k in keywords):
                return cat
        return "行业"

    # 标准化
    standard_etfs = []
    no_issuer_count = 0

    for etf in full_data:
        code = str(etf.get("code", ""))
        raw_name = etf.get("name", "")
        gen = gen_map.get(code, {})

        name, issuer = extract_name_issuer(raw_name)
        issuer = issuer_full_name(issuer)
        issuer_short = issuer_short_name(issuer)
        if gen and not issuer and gen.get("issuer"):
            issuer = gen["issuer"]
        if not issuer:
            no_issuer_count += 1

        # 持仓
        raw_holdings = gen.get("top_holdings", [])
        top_holdings = []
        for h in raw_holdings[:5]:
            if isinstance(h, dict) and "name" in h:
                top_holdings.append({"name": h["name"], "weight": h.get("weight", "")})
            elif isinstance(h, str):
                parts = h.split(" ", 1)
                top_holdings.append({"name": parts[0], "weight": parts[1] if len(parts) > 1 else ""})

        # 规模
        mcap_ft = gen.get("market_cap", 0) or 0
        mcap_ak = etf.get("market_cap", 0) or 0
        close_price = gen.get("close", 0) or 0
        if mcap_ft:
            scale_raw = mcap_ft / 1e8
        elif mcap_ak and close_price:
            scale_raw = (mcap_ak * close_price) / 1e8
        elif mcap_ak:
            scale_raw = mcap_ak / 1e8
        else:
            scale_raw = 0
        shares_raw = mcap_ak / 1e8 if mcap_ak else 0
        if not shares_raw and scale_raw and close_price:
            shares_raw = scale_raw / close_price
        vol_raw = etf.get("volume", 0) or 0
        volume_val = vol_raw / 1e8 if vol_raw else 0

        # 风险指标：自算优先，盈米补充
        calc = calc_data.get(code, {})
        ym = yingmi_data.get(code, {})

        # 收益率：自算 > 盈米 > 非凸
        year_1_return = calc.get("year_1_return", 0) or ym.get("year_1_return", 0) or gen.get("year_1_return", 0)
        year_3_return = calc.get("year_3_return", 0) or ym.get("year_3_return", 0) or 0
        max_drawdown = calc.get("max_drawdown", 0) or ym.get("max_drawdown", 0) or gen.get("max_drawdown", 0)
        sharpe_ratio = calc.get("sharpe_ratio", 0) or ym.get("sharpe_ratio", 0) or gen.get("sharpe_ratio", 0.0)
        annual_vol = calc.get("annual_vol", 0) or ym.get("annual_vol_1y", 0) or 0

        # Wind 补充数据
        wd = wind_data.get(code, {})

        # custodian: Wind > gen
        custodian = wd.get("custodian", "") or gen.get("custodian", "")
        # benchmark: Wind（之前 gen 没有此字段）
        benchmark = wd.get("benchmark", "") or gen.get("benchmark", "")
        # 费率: Wind > gen
        mgmt_fee = wd.get("management_fee_rate", 0) or gen.get("management_fee_rate", 0)
        custody_fee = wd.get("custody_fee_rate", 0) or gen.get("custody_fee_rate", 0)

        standard_etf = {
            "code": code,
            "name": name,
            "issuer": issuer,
            "issuer_full": issuer,
            "issuer_short": issuer_short,
            "scale": round(scale_raw, 1) if scale_raw else 0,
            "shares": round(shares_raw, 1) if shares_raw else 0,
            "issue_date": gen.get("issue_date", ""),
            "custodian": custodian,
            "top_holdings": top_holdings,
            "change_pct": etf.get("change_pct"),
            "close": gen.get("close", 0),
            "prev_close": gen.get("prev_close", 0),
            "change_rate": gen.get("change_rate", 0),
            "volume": round(volume_val, 1) if volume_val else 0,
            "year_1_return": year_1_return,
            "year_3_return": year_3_return,
            "max_drawdown": max_drawdown,
            "sharpe_ratio": sharpe_ratio,
            "annual_vol": annual_vol,
            "category": classify_category(raw_name),
            "benchmark": benchmark,
            "management_fee_rate": mgmt_fee,
            "custody_fee_rate": custody_fee,
        }
        standard_etfs.append(standard_etf)

    # 统计
    has_return = sum(1 for e in standard_etfs if e["year_1_return"] != 0)
    has_sharpe = sum(1 for e in standard_etfs if e["sharpe_ratio"] != 0)
    has_holdings = sum(1 for e in standard_etfs if e["top_holdings"])

    log(f"  标准化完成: {len(standard_etfs)} 只")
    log(f"  有收益率: {has_return} 只 | 有夏普: {has_sharpe} 只 | 有持仓: {has_holdings} 只")
    log(f"  无发行人: {no_issuer_count} 只")

    save_json(output_file, standard_etfs)

    # 自动快照 + 备份
    create_snapshot("build")
    create_backup()


# ============ Step 5: 部署 ============

def step_deploy():
    """部署：版本追踪 + git add + commit + push"""
    log("Step 5: 部署（git push）")

    # 部署前创建最终快照
    create_snapshot("pre_deploy")

    # 自动运行版本追踪器
    try:
        log("  生成版本清单...")
        from version_tracker import VersionTracker
        tracker = VersionTracker(str(ROOT))
        commits = tracker.get_git_log()
        if commits:
            md_content = tracker.generate_markdown(commits)
            tracker.save_markdown(md_content)
            log(f"  版本清单: {len(commits)} 个版本")
    except Exception as e:
        log(f"  版本追踪跳过: {e}")

    try:
        subprocess.run(["git", "add", "-A"], cwd=ROOT, check=True, capture_output=True)
        date_str = datetime.now().strftime("%Y-%m-%d")
        result = subprocess.run(
            ["git", "commit", "-m", f"pipeline: {date_str} 数据更新"],
            cwd=ROOT, capture_output=True, text=True,
        )
        if result.returncode == 0 or "nothing to commit" in result.stdout.lower():
            push = subprocess.run(
                ["git", "push", "origin", "main"],
                cwd=ROOT, capture_output=True, text=True,
            )
            if push.returncode == 0:
                log("  git push 成功")
                # 触发 PythonAnywhere 同步
                _trigger_pa_sync()
                # 部署后快照
                create_snapshot("deploy")
                return True
        log(f"  git 状态: {result.stdout[:200]}")
    except Exception as e:
        log(f"  git 操作失败: {e}")
    return False


# ============ 辅助步骤 ============

def step_snapshot():
    """手动创建版本快照"""
    log("手动创建版本快照")
    create_snapshot("manual")


def step_verify():
    """校验数据完整性"""
    log("校验数据完整性")
    report = verify_data_integrity()
    print(json.dumps(report, indent=2, ensure_ascii=False))
    if report["issues"]:
        log(f"发现问题: {len(report['issues'])} 个")
        for issue in report["issues"]:
            log(f"  ⚠️ {issue}")
    else:
        log("数据完整性校验通过")


def step_migrate():
    """迁移旧数据到本地存储"""
    log("迁移旧数据到本地存储")
    report = init_store()
    print(json.dumps(report, indent=2, ensure_ascii=False))


# ============ 主入口 ============

STEPS = {
    "sync": ("同步 ETF 列表", step_sync_list),
    "enrich": ("补充数据（价格+持仓）", step_enrich),
    "enrich_wind": ("从 Wind 补充基础信息", step_enrich_wind),
    "calc": ("计算风险指标", step_calc_metrics),
    "build": ("生成标准化数据", step_build),
    "deploy": ("部署（git push）", step_deploy),
    "snapshot": ("手动创建版本快照", step_snapshot),
    "verify": ("校验数据完整性", step_verify),
    "migrate": ("迁移旧数据到本地存储", step_migrate),
}

STEP_ORDER = ["sync", "enrich", "enrich_wind", "calc", "build", "deploy"]


def main():
    parser = argparse.ArgumentParser(description="ETF 数据 Pipeline v2")
    parser.add_argument("step", nargs="?", default=None,
                        choices=list(STEPS.keys()) + ["all"],
                        help="要执行的步骤（默认 all）")
    parser.add_argument("--push", action="store_true", help="执行完后自动 git push")
    parser.add_argument("--no-wind", action="store_true", help="跳过 Wind 数据补充步骤")
    args = parser.parse_args()

    log("=" * 50)
    log("ETF 数据 Pipeline v2（本地存储 + 版本管理）")
    log("=" * 50)

    if args.step is None or args.step == "all":
        # 执行全部步骤
        steps_to_run = [s for s in STEP_ORDER if not (args.no_wind and s == "enrich_wind")]
        if args.no_wind:
            log("(已跳过 Wind 数据补充)")
        for step_name in steps_to_run:
            desc, func = STEPS[step_name]
            log(f"\n{'='*30}")
            log(f"执行: {desc}")
            log(f"{'='*30}")
            try:
                func()
            except Exception as e:
                log(f"步骤 {step_name} 失败: {e}")
                if step_name in ("sync", "build"):
                    log("关键步骤失败，终止流程")
                    break
    else:
        desc, func = STEPS[args.step]
        log(f"\n执行: {desc}")
        try:
            func()
        except Exception as e:
            log(f"步骤 {args.step} 失败: {e}")

    if args.push and (args.step is None or args.step == "all" or args.step != "deploy"):
        step_deploy()

    log("\n" + "=" * 50)
    log("Pipeline 完成")
    log("=" * 50)


if __name__ == "__main__":
    main()
