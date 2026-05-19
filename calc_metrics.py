#!/usr/bin/env python3
"""
独立计算ETF风控指标：年化收益率/最大回撤/夏普比率/年化波动率
数据源：本地缓存 > 非凸 etf-ohlcs API > AKShare（多源降级）
输出：etf_calculated_metrics.json（自算指标，独立文件，便于复用）

v2: 增强错误处理、日志、断点续跑、数据质量防护
"""
import sys, os, json, time, math, logging, signal
from datetime import datetime

ROOT = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(ROOT, "data")
HISTORY_DIR = os.path.join(DATA_DIR, "history")
OUTPUT_FILE = os.path.join(ROOT, "etf_calculated_metrics.json")
CHECKPOINT_FILE = os.path.join(ROOT, "etf_calculated_metrics_checkpoint.json")
LOG_FILE = os.path.join(ROOT, "calc_metrics.log")

OHLC_LIMIT = 1260  # 约5年交易日
RISK_FREE = 0.02
CHECKPOINT_INTERVAL = 50  # 每50只保存一次checkpoint
REQUIRED_DAYS = 30  # 最少需要30个交易日才能计算

# ── 日志配置 ──────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8'),
        logging.StreamHandler(sys.stdout),
    ]
)
log = logging.getLogger(__name__)


# ── 工具函数 ──────────────────────────────────────────────
def get_exchange(code):
    return 'XSHG' if str(code).startswith('5') else 'XSHE'


def safe_div(numerator, denominator, default=None):
    """安全除法，分母为0时返回default"""
    try:
        if denominator == 0:
            return default
        return numerator / denominator
    except (TypeError, ValueError):
        return default


def calc_max_drawdown(prices):
    """
    计算最大回撤（百分比，负值表示回撤）
    返回：float 或 None（数据不足时）
    """
    if not prices or len(prices) < 2:
        return None
    peak = prices[0]
    max_dd = 0.0
    for v in prices:
        if v is None or not isinstance(v, (int, float)):
            continue
        if v > peak:
            peak = v
        if peak == 0:
            continue
        dd = (v - peak) / peak * 100
        if dd < max_dd:
            max_dd = dd
    return round(max_dd, 2) if max_dd != 0 else None


def calc_sharpe(prices):
    """
    计算夏普比率 (年化)
    返回：float 或 None（数据不足时）
    """
    n = min(len(prices), 253)
    if n < REQUIRED_DAYS:
        return None
    try:
        daily_rets = []
        for i in range(1, n):
            if prices[i] is None or prices[i-1] is None or prices[i-1] == 0:
                continue
            ret = (prices[i] - prices[i-1]) / prices[i-1]
            daily_rets.append(ret)
        if len(daily_rets) < REQUIRED_DAYS:
            return None
        avg = sum(daily_rets) / len(daily_rets)
        # 样本方差（无偏估计）
        var = sum((r - avg) ** 2 for r in daily_rets) / (len(daily_rets) - 1)
        vol = math.sqrt(var) if var > 0 else 0
        if vol == 0:
            return None
        annual_ret = avg * 252
        annual_vol = vol * math.sqrt(252)
        sharpe = (annual_ret - RISK_FREE) / annual_vol
        # 夏普比率异常值过滤（>10 或 <-10 大概率数据异常）
        if sharpe > 20 or sharpe < -20:
            log.warning(f"夏普比率异常值 {sharpe:.2f}，视为无效")
            return None
        return round(sharpe, 2)
    except Exception as e:
        log.debug(f"calc_sharpe 异常: {e}")
        return None


def calc_annual_vol(prices):
    """
    计算年化波动率（百分比）
    返回：float 或 None（数据不足时）
    """
    n = min(len(prices), 253)
    if n < REQUIRED_DAYS:
        return None
    try:
        daily_rets = []
        for i in range(1, n):
            if prices[i] is None or prices[i-1] is None or prices[i-1] == 0:
                continue
            ret = (prices[i] - prices[i-1]) / prices[i-1]
            daily_rets.append(ret)
        if len(daily_rets) < REQUIRED_DAYS:
            return None
        avg = sum(daily_rets) / len(daily_rets)
        var = sum((r - avg) ** 2 for r in daily_rets) / (len(daily_rets) - 1)
        vol = math.sqrt(var) if var > 0 else 0
        return round(vol * math.sqrt(252) * 100, 2)
    except Exception as e:
        log.debug(f"calc_annual_vol 异常: {e}")
        return None


# ── 数据源函数 ──────────────────────────────────────────────
def load_local_cache(code):
    """加载本地缓存的历史K线数据，返回 prices 列表或 None"""
    cache_path = os.path.join(HISTORY_DIR, f"{code}.json")
    if not os.path.exists(cache_path):
        return None
    try:
        with open(cache_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        prices = data.get('prices', [])
        if prices and len(prices) >= REQUIRED_DAYS:
            return prices
        log.debug(f"[{code}] 本地缓存数据不足: {len(prices)}条")
        return None
    except (json.JSONDecodeError, IOError, KeyError) as e:
        log.warning(f"[{code}] 读取本地缓存失败: {e}")
        return None


def get_prices_from_westock(code):
    """
    从 westock-data kline 获取K线数据
    返回：prices 列表或 None
    """
    import subprocess
    # 动态查找 westock-data 脚本路径
    script_paths = [
        os.path.join(os.path.expanduser("~"), ".workbuddy", "plugins", "marketplaces",
                     "cb_teams_marketplace", "plugins", "finance-data", "skills",
                     "westock-data", "scripts", "index.js"),
        # 备用路径
        os.path.join(ROOT, "..", "westock-data", "scripts", "index.js"),
    ]
    script_path = None
    for p in script_paths:
        if os.path.exists(p):
            script_path = p
            break
    if not script_path:
        log.debug(f"[{code}] westock-data 脚本未找到，跳过")
        return None

    try:
        if str(code).startswith(('5', '1')):
            formatted = f'sh{code}'
        elif str(code).startswith(('0', '3')):
            formatted = f'sz{code}'
        else:
            formatted = f'sh{code}'

        cmd = ['node', script_path, 'kline', formatted, '--period', 'day', '--limit', '2000']
        log.debug(f"[{code}] 调用 westock-data: {' '.join(cmd)}")

        result = subprocess.run(
            cmd, capture_output=True, text=True,
            timeout=30, encoding='utf-8', errors='replace'
        )

        if result.returncode != 0:
            log.debug(f"[{code}] westock-data 返回码 {result.returncode}: {result.stderr[:200]}")
            return None

        if not result.stdout:
            return None

        # 解析 markdown 表格输出
        lines = result.stdout.strip().split('\n')
        prices = []
        for line in lines:
            if line.startswith('|') and not line.startswith('|-') and 'date' not in line:
                parts = [p.strip() for p in line.split('|')]
                if len(parts) >= 3:
                    try:
                        price = float(parts[2])  # last price
                        prices.append(price)
                    except (ValueError, IndexError):
                        pass
        if len(prices) >= REQUIRED_DAYS:
            log.debug(f"[{code}] westock-data 返回 {len(prices)} 条数据")
            return prices
        else:
            log.debug(f"[{code}] westock-data 数据不足: {len(prices)}条")
            return None
    except subprocess.TimeoutExpired:
        log.warning(f"[{code}] westock-data 超时（30s）")
        return None
    except (FileNotFoundError, PermissionError) as e:
        log.warning(f"[{code}] westock-data 执行失败: {e}")
        return None
    except Exception as e:
        log.warning(f"[{code}] westock-data 未知错误: {e}")
        return None


def get_prices_from_ft(code, exch):
    """从非凸 API 获取K线数据，返回 prices 列表或 None"""
    try:
        sys.path.insert(0, ROOT)
        from modules.data_source import FTSource
        ft = FTSource()
        ohlc = ft.get_etf_ohlcs(str(code), exch, limit=OHLC_LIMIT)
        prices = ohlc.get("prices", []) if ohlc else []
        if prices and len(prices) >= REQUIRED_DAYS:
            log.debug(f"[{code}] 非凸API返回 {len(prices)} 条数据")
            return prices
        log.debug(f"[{code}] 非凸API数据不足: {len(prices)}条")
        return None
    except Exception as e:
        log.warning(f"[{code}] 非凸API调用失败: {e}")
        return None


def get_prices_from_akshare(code):
    """从 AKShare 获取历史K线，返回 prices 列表或 None"""
    try:
        import akshare as ak
        log.debug(f"[{code}] 调用 AKShare fund_etf_hist_em...")
        # 加 signal 超时保护（AKShare 可能无限等待）
        import threading
        result_container = {"df": None, "error": None}

        def _fetch():
            try:
                result_container["df"] = ak.fund_etf_hist_em(
                    symbol=str(code), period="daily",
                    start_date="20000101", end_date="20261231", adjust=""
                )
            except Exception as e:
                result_container["error"] = e

        t = threading.Thread(target=_fetch)
        t.daemon = True
        t.start()
        t.join(timeout=45)  # 45秒超时

        if t.is_alive():
            log.warning(f"[{code}] AKShare 调用超时（45s），跳过")
            return None

        df = result_container["df"]
        if result_container["error"]:
            log.warning(f"[{code}] AKShare 返回错误: {result_container['error']}")
            return None

        if df is None or df.empty:
            log.debug(f"[{code}] AKShare 返回空数据")
            return None

        prices = df['收盘'].dropna().tolist()
        if len(prices) >= REQUIRED_DAYS:
            log.debug(f"[{code}] AKShare 返回 {len(prices)} 条数据")
            return prices
        log.debug(f"[{code}] AKShare 数据不足: {len(prices)}条")
        return None
    except ImportError:
        log.error(f"[{code}] AKShare 未安装，跳过")
        return None
    except Exception as e:
        log.warning(f"[{code}] AKShare 调用异常: {e}")
        return None


def get_prices_multi_source(code, exch):
    """
    多数据源获取K线数据（降级策略）
    返回：(prices, source_name) 或 (None, None)
    优先级：本地缓存 > westock-data > 非凸API > AKShare
    """
    # 1. 本地缓存
    prices = load_local_cache(code)
    if prices:
        return prices, 'local_cache'

    # 2. westock-data kline
    prices = get_prices_from_westock(code)
    if prices:
        return prices, 'westock_kline'

    # 3. 非凸 API
    prices = get_prices_from_ft(code, exch)
    if prices:
        return prices, 'ft_api'

    # 4. AKShare
    prices = get_prices_from_akshare(code)
    if prices:
        return prices, 'akshare'

    return None, None


# ── 主流程 ──────────────────────────────────────────────
def make_empty_result(source="none", error=None):
    """生成空结果模板（所有指标为 None 表示无数据）"""
    result = {
        "year_1_return": None, "year_2_return": None, "year_3_return": None, "year_5_return": None,
        "max_drawdown": None, "max_drawdown_2y": None, "max_drawdown_3y": None, "max_drawdown_5y": None,
        "sharpe_ratio": None, "sharpe_2y": None, "sharpe_3y": None, "sharpe_5y": None,
        "annual_vol": None, "annual_vol_2y": None, "annual_vol_3y": None, "annual_vol_5y": None,
        "data_source": source,
    }
    if error:
        result["error"] = str(error)[:500]  # 限制错误信息长度
    return result


def compute_metrics_for_code(code, exch):
    """
    为单只ETF计算所有指标
    返回：result dict 或 None（完全无数据时）
    """
    prices, source = get_prices_multi_source(code, exch)
    if not prices or len(prices) < REQUIRED_DAYS:
        log.info(f"[{code}] 所有数据源均无有效数据（最少需要{REQUIRED_DAYS}条，实际{len(prices) if prices else 0}条）")
        return make_empty_result(source="none", error="insufficient_data")

    n = len(prices)
    log.debug(f"[{code}] 数据源={source}, 数据量={n}条")

    result = make_empty_result(source=source)

    # 1年指标（需要252个交易日）
    if n >= 252:
        try:
            p1 = prices[-252:]
            result["year_1_return"] = round(safe_div(prices[-1] - prices[-252], prices[-252], 0) * 100, 2)
            result["max_drawdown"] = calc_max_drawdown(p1)
            result["sharpe_ratio"] = calc_sharpe(p1)
            result["annual_vol"] = calc_annual_vol(p1)
        except Exception as e:
            log.warning(f"[{code}] 计算1年指标失败: {e}")

    # 2年指标
    if n >= 504:
        try:
            p2 = prices[-504:]
            result["year_2_return"] = round(safe_div(prices[-1] - prices[-504], prices[-504], 0) * 100, 2)
            result["max_drawdown_2y"] = calc_max_drawdown(p2)
            result["sharpe_2y"] = calc_sharpe(p2)
            result["annual_vol_2y"] = calc_annual_vol(p2)
        except Exception as e:
            log.warning(f"[{code}] 计算2年指标失败: {e}")

    # 3年指标
    if n >= 756:
        try:
            p3 = prices[-756:]
            result["year_3_return"] = round(safe_div(prices[-1] - prices[-756], prices[-756], 0) * 100, 2)
            result["max_drawdown_3y"] = calc_max_drawdown(p3)
            result["sharpe_3y"] = calc_sharpe(p3)
            result["annual_vol_3y"] = calc_annual_vol(p3)
        except Exception as e:
            log.warning(f"[{code}] 计算3年指标失败: {e}")

    # 5年指标
    if n >= 1260:
        try:
            p5 = prices[-1260:]
            result["year_5_return"] = round(safe_div(prices[-1] - prices[-1260], prices[-1260], 0) * 100, 2)
            result["max_drawdown_5y"] = calc_max_drawdown(p5)
            result["sharpe_5y"] = calc_sharpe(p5)
            result["annual_vol_5y"] = calc_annual_vol(p5)
        except Exception as e:
            log.warning(f"[{code}] 计算5年指标失败: {e}")

    return result


def save_checkpoint(results, done_codes):
    """保存断点（便于中断后恢复）"""
    try:
        with open(CHECKPOINT_FILE, 'w', encoding='utf-8') as f:
            json.dump({"timestamp": datetime.now().isoformat(), "done": done_codes, "results": results},
                      f, ensure_ascii=False)
        log.debug(f"断点已保存（{len(done_codes)}只）")
    except Exception as e:
        log.warning(f"保存断点失败: {e}")


def load_checkpoint():
    """加载断点，返回 (results, done_set)"""
    if not os.path.exists(CHECKPOINT_FILE):
        return {}, set()
    try:
        with open(CHECKPOINT_FILE, 'r', encoding='utf-8') as f:
            cp = json.load(f)
        results = cp.get("results", {})
        done = set(cp.get("done", []))
        log.info(f"加载断点：已处理 {len(done)} 只ETF，时间 {cp.get('timestamp', '未知')}")
        return results, done
    except Exception as e:
        log.warning(f"加载断点失败: {e}，将从头开始")
        return {}, set()


def get_etf_list():
    """读取ETF列表，返回 [{"code":..., "name":...}, ...]"""
    # 优先使用 etf_standard_data.json（数据质量报告确认此文件存在）
    candidates = [
        os.path.join(ROOT, "etf_standard_data.json"),
        os.path.join(ROOT, "etf_complete_all.json"),
    ]
    for path in candidates:
        if os.path.exists(path):
            log.info(f"使用ETF列表: {path}")
            with open(path, encoding='utf-8') as f:
                data = json.load(f)
            return data
    raise FileNotFoundError(f"未找到ETF列表文件，候选路径: {candidates}")


if __name__ == '__main__':
    log.info("=" * 60)
    log.info("ETF风控指标计算 v2 启动")
    log.info("=" * 60)

    # 读取ETF列表
    try:
        etf_list = get_etf_list()
    except FileNotFoundError as e:
        log.error(f"无法读取ETF列表: {e}")
        sys.exit(1)

    codes = [(e["code"], get_exchange(e["code"])) for e in etf_list]
    total = len(codes)
    log.info(f"ETF总数: {total}")

    # 加载断点（支持续跑）
    results, done_codes = load_checkpoint()

    ok = fail = skip = 0
    start_time = time.time()

    for i, (code, exch) in enumerate(codes):
        code_str = str(code)

        # 跳过已处理的
        if code_str in done_codes:
            skip += 1
            continue

        log.debug(f"[{i+1}/{total}] 处理 {code_str} ({exch})...")

        try:
            result = compute_metrics_for_code(code, exch)
            if result:
                results[code_str] = result
                # 判断成功/失败（有至少一个非None指标视为成功）
                has_data = any(v is not None for v in result.values()
                               if isinstance(v, (int, float)) and v != 0)
                if has_data:
                    ok += 1
                else:
                    fail += 1
            else:
                results[code_str] = make_empty_result(source="error", error="compute_returned_none")
                fail += 1
        except Exception as e:
            log.error(f"[{code_str}] 未捕获异常: {e}", exc_info=True)
            results[code_str] = make_empty_result(source="error", error=str(e))
            fail += 1

        done_codes.add(code_str)

        # 进度日志
        if (i + 1) % 50 == 0 or (i + 1) == total:
            elapsed = time.time() - start_time
            speed = (i + 1) / elapsed * 60 if elapsed > 0 else 0  # 只/分钟
            log.info(
                f"进度: {i+1}/{total}  成功={ok} 失败={fail} 跳过={skip}  "
                f"速度≈{speed:.1f}只/分钟"
            )

        # 断点保存
        if (i + 1) % CHECKPOINT_INTERVAL == 0:
            save_checkpoint(results, done_codes)

        # 限速（避免API限流）
        time.sleep(0.2)

    # 最终保存
    save_checkpoint(results, done_codes)

    elapsed_total = time.time() - start_time
    log.info("=" * 60)
    log.info(f"完成! 成功={ok} 失败={fail} 跳过={skip}  耗时={elapsed_total/60:.1f}分钟")
    log.info(f"结果已保存: {OUTPUT_FILE}")
    log.info(f"日志文件: {LOG_FILE}")
    log.info("=" * 60)
