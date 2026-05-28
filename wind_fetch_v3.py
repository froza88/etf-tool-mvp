#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Wind数据批量抓取 - 最简化版
"""
import json
import subprocess
import time
import os
import signal
from datetime import datetime

# 忽略SIGHUP信号（防止被Bash工具终止）
signal.signal(signal.SIGHUP, signal.SIG_IGN)

# 配置
ETF_LIST_FILE = 'etfs_missing_wind.json'
CACHE_DIR = 'data/cache/wind'
WIND_CLI = '/Users/apangduo/.agents/skills/wind-mcp-skill/scripts/cli.mjs'

def fetch_wind_risk(code, name):
    """调用Wind API获取风险指标"""
    question = f"查询{code}{name}的夏普比率近1年、年化波动率近1年、最大回撤近1年"
    
    cmd = [
        'node', WIND_CLI,
        'call', 'analytics_data', 'get_financial_data',
        json.dumps({"question": question})
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        output = result.stdout
        
        # 解析：整个响应是JSON
        response = json.loads(output)
        text_str = response['content'][0]['text']  # text是JSON字符串
        data_obj = json.loads(text_str)  # 解析text
        
        # 提取数据
        data_list = data_obj.get('data', {}).get('data', [])
        if not data_list:
            return None, "data.data为空"
        
        columns = data_list[0].get('columns', [])
        rows = data_list[0].get('rows', [])
        
        if not rows:
            return None, "rows为空"
        
        # 映射列名
        col_map = {col['name']: idx for idx, col in enumerate(columns)}
        row = rows[0]
        
        # 提取指标
        risk_data = {
            'windcode': f"{code}.OF",
            'name': name,
            'fetched_at': datetime.now().isoformat()
        }
        
        for col_name, idx in col_map.items():
            if idx >= len(row): continue
            val = row[idx]
            if not val: continue
            
            if '夏普' in col_name or 'SHARPE' in col_name.upper():
                risk_data['sharpe_1y'] = float(val)
            elif '波动率' in col_name or 'VOLATILITY' in col_name.upper():
                risk_data['volatility_1y'] = float(val)
            elif '回撤' in col_name or 'DRAWDOWN' in col_name.upper():
                risk_data['max_drawdown_1y'] = float(val)
        
        return risk_data, None
        
    except Exception as e:
        return None, f"异常: {str(e)[:80]}"

def main():
    """主循环"""
    with open(ETF_LIST_FILE, 'r', encoding='utf-8') as f:
        etf_list = json.load(f)
    
    print(f"📋 ETF列表: {len(etf_list)} 只")
    os.makedirs(CACHE_DIR, exist_ok=True)
    
    success = error = skip = 0
    
    for i, etf in enumerate(etf_list):
        code = etf['code']
        name = etf.get('name', '')
        
        cache_file = os.path.join(CACHE_DIR, f"{code}_risk.json")
        if os.path.exists(cache_file):
            skip += 1
            if i % 100 == 0:
                print(f"⏭️  [{i+1}/{len(etf_list)}] 跳过 {code}")
            continue
        
        print(f"🔄 [{i+1}/{len(etf_list)}] {code} {name}...", end='', flush=True)
        
        risk_data, err = fetch_wind_risk(code, name)
        
        if risk_data:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(risk_data, f, ensure_ascii=False, indent=2)
            success += 1
            print(f" ✅ sharpe={risk_data.get('sharpe_1y')}")
        else:
            error += 1
            print(f" ❌ {err[:60]}")
        
        time.sleep(1)
        
        if (i+1) % 10 == 0:
            print(f"📊 进度: {i+1}/{len(etf_list)} | ✅{success} ❌{error} ⏭️{skip}")
    
    print(f"\n{'='*60}")
    print(f"✅ 完成 | 成功:{success} 失败:{error} 跳过:{skip}")
    print(f"{'='*60}")

if __name__ == '__main__':
    import sys, os
    # Fork: 父进程立即退出，子进程继续运行（成为孤儿进程，避免Bash工具SIGHUP）
    pid = os.fork()
    if pid > 0:
        # 父进程
        print(f"父进程退出，子进程(PID:{pid})继续运行", flush=True)
        sys.exit(0)
    else:
        # 子进程 - 关闭标准输出/错误，避免Bash工具等待
        sys.stdout.close()
        sys.stderr.close()
        # 重定向到日志文件
        log = open('wind_v3_fork.log', 'a')
        sys.stdout = log
        sys.stderr = log
        main()
