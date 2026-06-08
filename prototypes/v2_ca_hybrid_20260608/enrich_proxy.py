#!/usr/bin/env python3
"""
C+A混合方案 · 数据丰富代理
架构：接收ETF代码列表 → 调天天基金+东方财富API → 返回深度数据
部署：可与HTML放同一目录，启动后 http://localhost:8090
用法：python3 enrich_proxy.py [port]
"""
import http.server
import json
import urllib.parse
import urllib.request
import time
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

# ============================================================
# 数据源层
# ============================================================

def fetch_ttjj_estimate(code):
    """天天基金 - 实时估值/净值"""
    try:
        url = f"https://fundgz.1234567.com.cn/js/{code}.js?rt={int(time.time()*1000)}"
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0', 'Referer': 'https://fund.eastmoney.com/'
        })
        with urllib.request.urlopen(req, timeout=5) as resp:
            text = resp.read().decode('utf-8')
            match = __import__('re').search(r'jsonpgz\((.+)\)', text)
            if match:
                d = json.loads(match.group(1))
                return {
                    'nav': d.get('dwjz', ''),
                    'estimate': d.get('gsz', ''),
                    'change_pct': d.get('gszzl', ''),
                    'update_time': d.get('gztime', ''),
                }
    except:
        pass
    return {}

def fetch_eastmoney_klines(code, days=252):
    """东方财富 - K线数据，用于计算收益率和风险指标"""
    try:
        url = (
            f"https://push2his.eastmoney.com/api/qt/stock/kline/get?"
            f"secid=1.{code}&fields1=f1,f2,f3,f4,f5,f6"
            f"&fields2=f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61"
            f"&klt=101&fqt=1&end=20500101&lmt={days+10}"
        )
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            if data.get('data') and data['data'].get('klines'):
                return data['data']['klines']
    except:
        pass
    return []

def fetch_eastmoney_quote_batch(codes):
    """东方财富 - 批量实时行情"""
    try:
        secids = ','.join([f"1.{c}" for c in codes])
        url = (
            f"http://push2.eastmoney.com/api/qt/ulist.np/get?"
            f"fltt=2&fields=f2,f3,f4,f5,f6,f7,f8,f12,f14,f15,f20,f21&secids={secids}"
        )
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            if data.get('data') and data['data'].get('diff'):
                return data['data']['diff']
    except:
        pass
    return []

# ============================================================
# 计算层
# ============================================================

def calc_returns(klines):
    """从K线计算1年收益率"""
    if not klines or len(klines) < 5:
        return None
    try:
        first = float(klines[0].split(',')[2])
        last = float(klines[-1].split(',')[2])
        if first == 0:
            return None
        return round((last / first - 1) * 100, 2)
    except:
        return None

def calc_sharpe(klines, rf=0.015):
    """从K线计算夏普比率（简化版）"""
    if not klines or len(klines) < 20:
        return None
    try:
        closes = [float(k.split(',')[2]) for k in klines[-252:]]
        if len(closes) < 20:
            return None
        daily_returns = [(closes[i]/closes[i-1]-1) for i in range(1, len(closes))]
        mean_ret = sum(daily_returns) / len(daily_returns)
        std_ret = (sum((r-mean_ret)**2 for r in daily_returns) / len(daily_returns)) ** 0.5
        if std_ret == 0:
            return None
        daily_rf = (1 + rf) ** (1/252) - 1
        sharpe = (mean_ret - daily_rf) / std_ret * (252 ** 0.5)
        return round(sharpe, 2)
    except:
        return None

def calc_max_drawdown(klines):
    """计算最大回撤"""
    if not klines or len(klines) < 20:
        return None
    try:
        closes = [float(k.split(',')[2]) for k in klines[-252:]]
        peak = closes[0]
        max_dd = 0
        for c in closes:
            if c > peak:
                peak = c
            dd = (c - peak) / peak
            if dd < max_dd:
                max_dd = dd
        return round(max_dd * 100, 2)
    except:
        return None

# ============================================================
# 聚合层
# ============================================================

def enrich_single(code):
    """对单只ETF聚合所有数据"""
    result = {'code': code}
    
    # 并行获取各数据源
    with ThreadPoolExecutor(max_workers=3) as ex:
        f_ttjj = ex.submit(fetch_ttjj_estimate, code)
        f_kline = ex.submit(fetch_eastmoney_klines, code)
        
        ttjj = f_ttjj.result()
        klines = f_kline.result()
    
    result.update(ttjj)
    result['year_1_return'] = calc_returns(klines)
    result['sharpe_ratio'] = calc_sharpe(klines)
    result['max_drawdown'] = calc_max_drawdown(klines)
    result['_klines_count'] = len(klines)
    
    return result

def enrich_batch(codes):
    """批量丰富ETF数据"""
    results = []
    
    # 每只ETF单独并发（避免单源限流）
    with ThreadPoolExecutor(max_workers=6) as ex:
        futures = {ex.submit(enrich_single, c): c for c in codes}
        for future in as_completed(futures):
            try:
                results.append(future.result())
            except Exception as e:
                code = futures[future]
                results.append({'code': code, 'error': str(e)})
    
    results.sort(key=lambda x: x['code'])
    return results

# ============================================================
# HTTP 服务
# ============================================================

class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        
        # CORS headers
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type',
        }
        
        if parsed.path == '/api/enrich':
            params = urllib.parse.parse_qs(parsed.query)
            codes = params.get('codes', [''])[0].split(',')
            codes = [c.strip() for c in codes if c.strip() and len(c.strip()) == 6]
            
            if not codes:
                self.send_json({"error": "需要ETF代码", "codes": codes}, headers)
                return
            
            start = time.time()
            results = enrich_batch(codes)
            elapsed = round(time.time() - start, 2)
            
            self.send_json({
                "etfs": results,
                "elapsed": elapsed,
                "source": "ttjj+eastmoney",
                "mode": "realtime",
            }, headers)
            return
        
        if parsed.path == '/api/ttjj':
            params = urllib.parse.parse_qs(parsed.query)
            codes = params.get('codes', [''])[0].split(',')
            codes = [c.strip() for c in codes if c.strip()]
            if not codes:
                self.send_json({"error": "需要ETF代码"}, headers)
                return
            results = {}
            with ThreadPoolExecutor(max_workers=5) as ex:
                futures = {ex.submit(fetch_ttjj_estimate, c): c for c in codes}
                for f in as_completed(futures):
                    results[futures[f]] = f.result()
            self.send_json({"etfs": results}, headers)
            return
        
        if parsed.path == '/api/health':
            self.send_json({"status": "ok", "time": time.strftime("%Y-%m-%d %H:%M:%S")}, headers)
            return
        
        self.send_response(404)
        for k, v in headers.items():
            self.send_header(k, v)
        self.end_headers()
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
    
    def send_json(self, data, extra_headers=None):
        self.send_response(200)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        for k, v in (extra_headers or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))
    
    def log_message(self, format, *args):
        msg = format % args
        if '/api/enrich' in msg:
            print(f"  📡 {msg}")

if __name__ == '__main__':
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8090
    print(f"""
╔══════════════════════════════════════════════╗
║  ETF 数据丰富代理 · C+A混合方案后端        ║
║  数据源：天天基金 + 东方财富K线             ║
║  端点：http://localhost:{port}/api/enrich?codes=xxx ║
║  健康检查：http://localhost:{port}/api/health       ║
╚══════════════════════════════════════════════╝
""")
    http.server.HTTPServer(('0.0.0.0', port), Handler).serve_forever()
