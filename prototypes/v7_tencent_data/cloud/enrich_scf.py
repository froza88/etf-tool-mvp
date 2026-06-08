#!/usr/bin/env python3
"""
SCF 云函数 — ETF 实时价格查询
部署：API网关 触发器，/api/ttjj 路由到此函数
数据源：天天基金（主力）→ 腾讯行情（兜底）
"""

import json
import urllib.request
import time
import re
from concurrent.futures import ThreadPoolExecutor, as_completed


def fetch_ttjj_estimate(code):
    """天天基金 - 实时估值/净值"""
    try:
        url = f"https://fundgz.1234567.com.cn/js/{code}.js?rt={int(time.time()*1000)}"
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0',
            'Referer': 'https://fund.eastmoney.com/'
        })
        with urllib.request.urlopen(req, timeout=5) as resp:
            text = resp.read().decode('utf-8')
            match = re.search(r'jsonpgz\((.+)\)', text)
            if match:
                d = json.loads(match.group(1))
                return {
                    'nav': d.get('dwjz', ''),
                    'estimate': d.get('gsz', ''),
                    'change_pct': d.get('gszzl', ''),
                    'update_time': d.get('gztime', ''),
                }
    except Exception:
        pass
    return {}


def fetch_tencent_quote(code):
    """腾讯行情 - 兜底"""
    try:
        prefix = 'sh' if code.startswith(('5', '6')) else 'sz'
        url = f'http://qt.gtimg.cn/q={prefix}{code}'
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=5) as resp:
            raw = resp.read().decode('gbk', errors='ignore')
        if '=' not in raw or '~' not in raw:
            return {}
        parts = raw.split('"')[1].split('~')
        if len(parts) < 33:
            return {}
        latest = parts[3]
        prev_close = parts[4]
        change_pct = parts[32]
        ts = parts[30]
        update_time = f"{ts[:4]}-{ts[4:6]}-{ts[6:8]} {ts[8:10]}:{ts[10:12]}:{ts[12:14]}"
        return {
            'nav': prev_close,
            'estimate': latest,
            'change_pct': change_pct,
            'update_time': update_time,
        }
    except Exception:
        return {}


def make_response(status_code, body):
    """SCF API 网关格式响应"""
    return {
        'isBase64Encoded': False,
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json; charset=utf-8',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type',
        },
        'body': json.dumps(body, ensure_ascii=False),
    }


def main_handler(event, context):
    """SCF 入口函数"""
    # API 网关触发
    path = event.get('path', '') or event.get('rawPath', '')
    method = event.get('httpMethod', '') or event.get('requestContext', {}).get('http', {}).get('method', 'GET')
    
    # CORS 预检
    if method == 'OPTIONS':
        return make_response(200, {'status': 'ok'})
    
    # 健康检查
    if path in ('/api/health', '/health'):
        return make_response(200, {
            'status': 'ok',
            'time': time.strftime('%Y-%m-%d %H:%M:%S'),
            'source': 'scf',
        })
    
    # 实时价格查询
    if path in ('/api/ttjj', '/ttjj'):
        query = event.get('queryString', event.get('queryStringParameters', {}))
        codes_str = query.get('codes', '')
        codes = [c.strip() for c in codes_str.split(',') if c.strip()]
        
        if not codes:
            return make_response(400, {'error': '需要 codes 参数'})
        
        results = {}
        # 并行抓取
        with ThreadPoolExecutor(max_workers=10) as ex:
            ttjj_futures = {ex.submit(fetch_ttjj_estimate, c): c for c in codes}
            tencent_futures = {ex.submit(fetch_tencent_quote, c): c for c in codes}
            
            for f in as_completed(ttjj_futures):
                code = ttjj_futures[f]
                results[code] = f.result() or {}
            
            # 腾讯数据优先：覆盖涨跌%和收盘价（实际收盘数据，比天天基金估算更准）
            for f in as_completed(tencent_futures):
                code = tencent_futures[f]
                tc = f.result()
                if tc:
                    results[code]['prev_close'] = tc.get('nav', '')
                    results[code]['change_pct'] = tc.get('change_pct', '')
                    results[code]['update_time'] = tc.get('update_time', '')
        
        # 腾讯没返回的，天天基金兜底
        for code, r in results.items():
            if not r.get('prev_close') and not r.get('change_pct'):
                tc = fetch_tencent_quote(code)
                if tc:
                    results[code] = {**results[code], **tc, 'prev_close': tc.get('nav',''), 'update_time': tc.get('update_time','')}
        
        return make_response(200, {'etfs': results})
    
    # 404
    return make_response(404, {'error': 'not found', 'path': path})


# 本地测试入口
if __name__ == '__main__':
    # 模拟 API 网关事件
    test_event = {
        'path': '/api/ttjj',
        'httpMethod': 'GET',
        'queryString': {'codes': '518880,510300'},
    }
    resp = main_handler(test_event, None)
    print(json.dumps(json.loads(resp['body']), ensure_ascii=False, indent=2))
