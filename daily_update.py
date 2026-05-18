#!/usr/bin/env python3
"""
每日数据更新脚本 - 统一拉取价格+计算指标+生成静态文件
用法：python3 daily_update.py [--push]
流程：AKShare实时 → 计算风险指标 → 合并标准化数据 → git push（可选）
"""
import json, os, sys, time, subprocess, math
from datetime import datetime, timedelta
from pathlib import Path

warnings_filtered = False

def _filter_warnings():
    global warnings_filtered
    if not warnings_filtered:
        import warnings
        warnings.filterwarnings('ignore')
        warnings_filtered = True

ROOT = Path(__file__).parent

# 输出文件
STANDARD_FILE = ROOT / "etf_standard_data.json"
HISTORY_FILE = ROOT / "etf_history_cache.json"
RISK_FILE = ROOT / "etf_risk_metrics.json"

# 临时缓存
CACHE = {}

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

def load_standard():
    with open(STANDARD_FILE, encoding="utf-8") as f:
        return json.load(f)

def save_standard(data):
    with open(STANDARD_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    log(f"保存标准化数据: {len(data)} 只")

def calc_metrics_from_prices(prices):
    """从价格序列计算风险指标"""
    n = len(prices)
    if n < 20:
        return None
    
    # 近1年/3年收益
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
        daily_returns = [(prices[i] - prices[i-1]) / prices[i-1] 
                        for i in range(1, min(n, 253))]
        if daily_returns:
            avg_ret = sum(daily_returns) / len(daily_returns)
            vol = math.sqrt(sum((r - avg_ret)**2 for r in daily_returns) / len(daily_returns))
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

def update_prices(etfs):
    """Step 1: 用AKShare获取最新实时价格"""
    _filter_warnings()
    try:
        import akshare as ak
        log("Step 1: 获取实时行情...")
        df = ak.fund_etf_spot_em()
        log(f"  AKShare返回 {len(df)} 只ETF行情")
        
        # 构建 code→行情 映射
        price_map = {}
        for _, row in df.iterrows():
            try:
                code = str(row['代码']).strip()
                close = float(row['最新价'])  # 最新价
                change_pct = float(row['涨跌幅'])  # 涨跌幅
                prev_close = float(row['昨收'])  # 昨收
                volume = float(row['成交额'])  # 成交额
                
                price_map[code] = {
                    'close': close,
                    'change_pct': change_pct,
                    'prev_close': prev_close,
                    'volume': round(volume / 1e8, 2) if volume else 0,  # 亿元
                }
            except:
                pass
        
        # 更新ETF数据
        updated = 0
        for etf in etfs:
            code = etf['code']
            if code in price_map:
                pm = price_map[code]
                etf['close'] = pm['close']
                etf['change_pct'] = pm['change_pct']
                etf['prev_close'] = pm['prev_close']
                etf['volume'] = pm['volume']
                updated += 1
        
        log(f"  价格更新: {updated}/{len(etfs)} 只")
        return True
    except Exception as e:
        log(f"  ⚠️ AKShare价格获取失败: {e}")
        return False

def update_history(etfs):
    """Step 2: 拉取历史K线并计算风险指标"""
    _filter_warnings()
    try:
        import akshare as ak
    except:
        log("  ⚠️ akshare未安装，跳过历史数据")
        return {}
    
    log("Step 2: 拉取历史K线并计算风险指标...")
    
    # 只处理规模前500的ETF（覆盖95%+的访问量）
    sorted_etfs = sorted(etfs, key=lambda x: x.get('scale', 0) or 0, reverse=True)
    target_etfs = sorted_etfs[:500]
    
    history_cache = {}
    risk_metrics = {}
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=1100)  # 3年+
    
    ok = fail = 0
    for i, etf in enumerate(target_etfs):
        code = etf['code']
        try:
            df = ak.fund_etf_hist_em(
                symbol=str(code),
                period='daily',
                start_date=start_date.strftime('%Y%m%d'),
                end_date=end_date.strftime('%Y%m%d'),
                adjust='qfq'
            )
            if df is not None and len(df) > 0:
                prices = [float(v) for v in list(df['收盘'])]
                dates = [str(d) for d in list(df['日期'])]
                
                # 保存历史数据
                history_cache[code] = {
                    'prices': prices,
                    'dates': dates,
                    'count': len(prices),
                    'updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
                
                # 计算风险指标
                metrics = calc_metrics_from_prices(prices)
                if metrics:
                    risk_metrics[code] = metrics
                    # 更新ETF对象
                    etf.update(metrics)
                    ok += 1
        except Exception as e:
            fail += 1
        
        if (i + 1) % 50 == 0:
            log(f"  进度: {i+1}/{len(target_etfs)} 成功={ok} 失败={fail}")
        
        time.sleep(0.15)
    
    log(f"  历史数据完成: 成功={ok} 失败={fail}")
    return history_cache, risk_metrics

def save_history_cache(history):
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False)
    log(f"保存历史缓存: {len(history)} 只 -> {HISTORY_FILE.name}")

def save_risk_metrics(risk):
    with open(RISK_FILE, "w", encoding="utf-8") as f:
        json.dump(risk, f, ensure_ascii=False)
    log(f"保存风险指标: {len(risk)} 只 -> {RISK_FILE.name}")

def git_commit_push():
    """Step 3: git commit & push"""
    log("Step 3: Git提交...")
    try:
        subprocess.run(["git", "add", "-A"], cwd=ROOT, check=True, capture_output=True)
        result = subprocess.run(
            ["git", "commit", "-m", f"daily: {datetime.now().strftime('%Y-%m-%d')}数据更新"],
            cwd=ROOT, capture_output=True, text=True
        )
        if result.returncode == 0 or "nothing to commit" in result.stdout.lower():
            push = subprocess.run(["git", "push", "origin", "main"], 
                                  cwd=ROOT, capture_output=True, text=True)
            if push.returncode == 0:
                log("  ✅ Git push 成功")
                return True
        log(f"  Git状态: {result.stdout[:200]}")
    except Exception as e:
        log(f"  ⚠️ Git操作失败: {e}")
    return False

def main():
    parser = argparse.ArgumentParser(description="每日ETF数据更新")
    parser.add_argument("--push", action="store_true", help="更新后自动git push")
    parser.add_argument("--history-only", action="store_true", help="只更新历史K线缓存")
    args = parser.parse_args()
    
    log("=" * 50)
    log("ETF每日数据更新开始")
    log("=" * 50)
    
    # 加载现有数据
    etfs = load_standard()
    log(f"加载标准化数据: {len(etfs)} 只")
    
    # Step 1: 更新价格
    price_ok = update_prices(etfs)
    
    # Step 2: 更新历史K线+风险指标
    history, risk = update_history(etfs)
    if history:
        save_history_cache(history)
        save_risk_metrics(risk)
    
    # 保存标准化数据
    save_standard(etfs)
    
    # Step 3: Git push（可选）
    if args.push:
        git_commit_push()
    
    log("=" * 50)
    log("更新完成")
    log("=" * 50)
    
    # 统计
    has_sharpe = sum(1 for e in etfs if e.get('sharpe_ratio', 0) != 0)
    has_price = sum(1 for e in etfs if e.get('close', 0) > 0)
    log(f"价格覆盖: {has_price}/{len(etfs)}")
    log(f"夏普覆盖: {has_sharpe}/{len(etfs)}")

if __name__ == "__main__":
    import argparse
    main()
