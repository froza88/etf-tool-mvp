#!/usr/bin/env python3
"""
原型B：Python 代理爬虫模式
架构：用户输入代码 → Python后端并发调FTShare+WeStock API → 聚合JSON → 前端渲染
特点：有后端代理，能获取深度数据（规模/费率/持仓/风险指标）
依赖：requests
运行：python proto_b_proxy.py
然后浏览器打开 http://localhost:8080
"""
import http.server
import json
import urllib.parse
import urllib.request
import time
import sys
import os
from concurrent.futures import ThreadPoolExecutor, as_completed

# ============================================================
# 数据源层：各数据源的HTTP API封装
# ============================================================

def fetch_ttjj_fund(code):
    """来源1：天天基金 - 实时估值/净值"""
    try:
        url = f"https://fundgz.1234567.com.cn/js/{code}.js?rt={int(time.time()*1000)}"
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0',
            'Referer': 'https://fund.eastmoney.com/'
        })
        with urllib.request.urlopen(req, timeout=5) as resp:
            text = resp.read().decode('utf-8')
            match = __import__('re').search(r'jsonpgz\((.+)\)', text)
            if match:
                return json.loads(match.group(1))
    except Exception as e:
        return {"error": str(e), "source": "ttjj"}
    return {"error": "parse_failed", "source": "ttjj"}

def fetch_eastmoney_fund_detail(code):
    """来源2：东方财富 - ETF基本信息（规模/类型/管理人）"""
    try:
        url = f"https://fundmobapi.eastmoney.com/FundMNewApi/FundMNFBasicInfo?FCODE={code}&deviceid=web&plat=web&product=EFund&version=2.0.0"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            if data.get('Datas') and data['Datas'][0]:
                return data['Datas'][0]
    except Exception as e:
        return {"error": str(e), "source": "eastmoney"}
    return {"error": "no_data", "source": "eastmoney"}

def fetch_eastmoney_quote(code):
    """来源3：东方财富行情 - K线数据（用于计算收益率）"""
    try:
        # 获取最近1年K线
        url = f"https://push2his.eastmoney.com/api/qt/stock/kline/get?secid=1.{code}&fields1=f1,f2,f3,f4,f5,f6&fields2=f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61&klt=101&fqt=1&end=20500101&lmt=260"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            if data.get('data') and data['data'].get('klines'):
                return data['data']['klines']
    except:
        pass
    return []

def calc_return_from_klines(klines):
    """从K线数据计算1年收益率"""
    if not klines or len(klines) < 2:
        return None
    try:
        first_close = float(klines[0].split(',')[2])
        last_close = float(klines[-1].split(',')[2])
        if first_close == 0:
            return None
        return round((last_close / first_close - 1) * 100, 2)
    except:
        return None

# ============================================================
# 聚合层：多源数据合并
# ============================================================

def aggregate(code):
    """对单只ETF聚合所有数据源"""
    result = {"code": code}
    
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {
            executor.submit(fetch_ttjj_fund, code): 'ttjj',
            executor.submit(fetch_eastmoney_fund_detail, code): 'detail',
            executor.submit(fetch_eastmoney_quote, code): 'klines',
        }
        for future in as_completed(futures):
            key = futures[future]
            try:
                data = future.result()
                result[key] = data
            except Exception as e:
                result[key] = {"error": str(e)}

    # 提取关键字段
    ttjj = result.get('ttjj', {})
    detail = result.get('detail', {})
    klines = result.get('klines', [])

    row = {
        'code': code,
        'name': ttjj.get('name', detail.get('SHORTNAME', code)),
        'nav': ttjj.get('dwjz', ''),
        'estimate': ttjj.get('gsz', ''),
        'change_pct': ttjj.get('gszzl', ''),
        'update_time': ttjj.get('gztime', ''),
        'scale': detail.get('FScale', ''),
        'manager': detail.get('JJGS', ''),
        'type': detail.get('FTYPE', ''),
        'year_1_return': calc_return_from_klines(klines),
        'data_sources': [k for k,v in result.items() if 'error' not in str(v)],
        'errors': [f"{k}:{v['error']}" for k,v in result.items() if isinstance(v, dict) and 'error' in v],
    }
    return row

# ============================================================
# HTTP服务
# ============================================================

HTML = '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>ETF爬虫对比 · 代理模式</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;background:#f5f5f5;color:#333;padding:20px}
.container{max-width:900px;margin:0 auto}
h1{font-size:20px;margin-bottom:4px}
.arch{color:#888;font-size:12px;margin-bottom:16px}
.arch span{background:#e8f5e9;color:#2e7d32;padding:2px 8px;border-radius:10px;font-size:11px;margin-right:4px}
.input-row{display:flex;gap:10px;margin-bottom:16px;flex-wrap:wrap}
input{flex:1;min-width:200px;padding:10px 14px;border:1px solid #ddd;border-radius:6px;font-size:14px}
button{padding:10px 24px;background:#d32f2f;color:#fff;border:none;border-radius:6px;cursor:pointer;font-size:14px;font-weight:600}
button:hover{background:#b71c1c}
button:disabled{background:#ccc}
.error{background:#ffebee;color:#c62828;padding:12px;border-radius:6px;margin-bottom:16px;display:none}
.loading{text-align:center;padding:40px;color:#999}
table{width:100%;border-collapse:collapse;background:#fff;border-radius:8px;overflow:hidden;box-shadow:0 1px 4px rgba(0,0,0,.08);margin-bottom:16px}
th,td{padding:12px 14px;text-align:left;font-size:13px;border-bottom:1px solid #f0f0f0}
th{background:#fafafa;font-weight:600;color:#555;font-size:12px}
td:first-child{font-weight:600;color:#555}
.red{color:#d32f2f;font-weight:600}
.green{color:#2e7d32;font-weight:600}
.blue{color:#1565c0;font-weight:600}
.sources{font-size:11px;color:#888;margin-top:8px}
.pick-row{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:12px}
.pick-btn{padding:6px 14px;border:1px solid #ddd;border-radius:16px;background:#fff;cursor:pointer;font-size:12px}
.pick-btn:hover{background:#f5f5f5}
</style>
</head>
<body>
<div class="container">
<h1>🔍 ETF爬虫对比 <span class="arch">代理模式</span></h1>
<div class="arch">
  <span>天天基金</span> <span>东方财富</span> <span>并发请求</span>
  架构：用户输入 → Python代理并发爬3个数据源 → 聚合JSON → 前端渲染 | 代码量：~200行
</div>

<div class="pick-row" id="quickPicks">
  <span style="font-size:12px;color:#888;line-height:28px;margin-right:4px">快速选择：</span>
</div>

<div class="input-row">
  <input id="codeInput" placeholder="输入ETF代码，逗号分隔。例：159928,159732,562950" value="159928,159732,562950">
  <button id="compareBtn">开始对比</button>
</div>
<div id="error" class="error"></div>
<div id="result"></div>
</div>

<script>
async function compare() {
  const input = document.getElementById('codeInput').value.trim();
  if (!input) return;
  const codes = input.split(',').map(c => c.trim()).filter(Boolean);
  
  document.getElementById('result').innerHTML = '<div class="loading">⏳ 后端并发爬取中（天天基金+东方财富+K线）…</div>';
  document.getElementById('error').style.display = 'none';
  document.getElementById('compareBtn').disabled = true;
  
  try {
    const resp = await fetch(`/api/compare?codes=${codes.join(',')}`);
    const data = await resp.json();
    if (data.error) throw new Error(data.error);
    render(data.etfs);
  } catch(e) {
    document.getElementById('error').textContent = e.message;
    document.getElementById('error').style.display = 'block';
    document.getElementById('result').innerHTML = '';
  } finally {
    document.getElementById('compareBtn').disabled = false;
  }
}

function render(etfs) {
  if (!etfs.length) return;
  
  const hasKline = etfs.some(e => e.year_1_return !== null);
  
  let html = '<table><thead><tr><th>代码</th><th>名称</th><th>净值</th><th>估算</th><th>涨跌</th>';
  if (hasKline) html += '<th>近1年收益</th>';
  html += '<th>数据源</th></tr></thead><tbody>';
  
  for (const e of etfs) {
    const chg = parseFloat(e.change_pct);
    const cls = chg > 0 ? 'red' : chg < 0 ? 'green' : '';
    const ret = e.year_1_return;
    const retCls = ret !== null ? (ret > 0 ? 'red' : ret < 0 ? 'green' : '') : '';
    
    html += `<tr>
      <td>${e.code}</td><td>${e.name}</td>
      <td>${e.nav}</td><td>${e.estimate}</td>
      <td class="${cls}">${chg>0?'+':''}${e.change_pct}%</td>`;
    if (hasKline) html += `<td class="${retCls}">${ret !== null ? (ret>0?'+':'')+ret+'%' : '-'}</td>`;
    html += `<td>${(e.errors||[]).length ? '⚠️' : '✅'} ${e.data_sources?.join('+')||''}`;
    if (e.errors?.length) html += `<br><span style="font-size:10px;color:#c62828">${e.errors.join(', ')}</span>`;
    html += `</td></tr>`;
  }
  html += '</tbody></table>';
  
  const totalSources = [...new Set(etfs.flatMap(e=>e.data_sources||[]))];
  html += `<div class="sources">数据源：${totalSources.join(' · ')} | 并发请求，总耗时约3-5秒</div>`;
  
  document.getElementById('result').innerHTML = html;
}

document.getElementById('compareBtn').onclick = compare;
document.getElementById('codeInput').onkeydown = e => { if(e.key==='Enter') compare(); };

const picks = [['159928','消费'],['159732','消费电子'],['562950','消费电子(低费)'],['510300','沪深300'],['510050','上证50'],['518880','黄金'],['159915','创业板']];
picks.forEach(([c,n])=>{
  const b=document.createElement('span');
  b.className='pick-btn';b.textContent=c;b.title=n;
  b.onclick=()=>{document.getElementById('codeInput').value=c;compare();};
  document.getElementById('quickPicks').appendChild(b);
});
</script>
</body>
</html>'''

class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        
        if parsed.path == '/':
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(HTML.encode('utf-8'))
            return
        
        if parsed.path == '/api/compare':
            params = urllib.parse.parse_qs(parsed.query)
            codes = params.get('codes', [''])[0].split(',')
            codes = [c.strip() for c in codes if c.strip()]
            
            if not codes:
                self.send_json({"error": "请提供ETF代码"})
                return
            
            start = time.time()
            results = []
            with ThreadPoolExecutor(max_workers=5) as executor:
                futures = {executor.submit(aggregate, c): c for c in codes}
                for future in as_completed(futures):
                    results.append(future.result())
            
            # 按代码排序
            results.sort(key=lambda x: x['code'])
            elapsed = round(time.time() - start, 2)
            
            self.send_json({"etfs": results, "elapsed": elapsed})
            return
        
        self.send_response(404)
        self.end_headers()
    
    def send_json(self, data):
        self.send_response(200)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))
    
    def log_message(self, format, *args):
        pass  # 静默日志

if __name__ == '__main__':
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
    print(f"\n✅ 原型B启动: http://localhost:{port}")
    print(f"   架构：Python代理 → 并发爬虫（天天基金+东方财富+K线）→ JSON → 前端\n")
    http.server.HTTPServer(('0.0.0.0', port), Handler).serve_forever()
