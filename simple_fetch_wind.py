#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简化版Wind风险指标批量抓取脚本

从 etfs_missing_wind.json 读取ETF列表，逐个抓取Wind风险指标
保存到 data/cache/wind/{code}_risk.json

使用方法：
    python3 simple_fetch_wind.py
"""

import json
import os
import subprocess
import time
from datetime import datetime

# 配置
INPUT_FILE = 'etfs_missing_wind.json'
CACHE_DIR = 'data/cache/wind'
WIND_SCRIPT = '/Users/apangduo/.agents/skills/wind-mcp-skill/scripts/cli.mjs'

def fetch_wind_risk(code, name=''):
    """抓取单只ETF的Wind风险指标"""
    try:
        # 调用Wind API
        question = f"查询{code}的夏普比率近1年、年化波动率近1年、最大回撤近1年"
        cmd = [
            'node',
            WIND_SCRIPT,
            'call',
            'analytics_data',
            'get_financial_data',
            json.dumps({"question": question})
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode != 0:
            return None, f"命令执行失败: {result.stderr[:100]}"
        
        # 解析结果
        output = result.stdout.strip()
        parsed = json.loads(output)
        
        if not parsed.get('ok'):
            return None, f"API返回失败: {parsed.get('error', {}).get('message', '未知错误')}"
        
        data_list = parsed.get('data', {}).get('data', [])
        if not data_list or len(data_list) == 0:
            return None, "API返回数据为空"
        
        rows = data_list[0].get('rows', [])
        if not rows:
            return None, "API返回rows为空"
        
        # 提取指标
        risk_data = {
            'windcode': f"{code}.OF",
            'name': name or '',
            'fetched_at': datetime.now().isoformat()
        }
        
        for row in rows:
            indicator = row.get('indicator', '')
            value = row.get('value', None)
            
            if 'SHARPE' in indicator.upper() or '夏普' in indicator:
                risk_data['sharpe_1y'] = float(value) if value else None
            elif 'VOLATILITY' in indicator.upper() or '波动率' in indicator:
                risk_data['volatility_1y'] = float(value) if value else None
            elif 'DRAWDOWN' in indicator.upper() or '回撤' in indicator:
                risk_data['max_drawdown_1y'] = float(value) if value else None
        
        return risk_data, None
        
    except subprocess.TimeoutExpired:
        return None, "超时"
    except json.JSONDecodeError as e:
        return None, f"JSON解析失败: {e}"
    except Exception as e:
        return None, f"异常: {e}"

def main():
    """主函数"""
    print("=" * 60)
    print("🌬️ 简化版Wind风险指标批量抓取")
    print("=" * 60)
    
    # 加载ETF列表
    if not os.path.exists(INPUT_FILE):
        print(f"❌ 输入文件不存在: {INPUT_FILE}")
        return
    
    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        etf_list = json.load(f)
    
    print(f"📋 ETF列表: {len(etf_list)} 只")
    print(f"开始时间: {datetime.now().strftime('%H:%M:%S')}")
    print("-" * 60)
    
    # 创建缓存目录
    os.makedirs(CACHE_DIR, exist_ok=True)
    
    # 统计
    success_count = 0
    fail_count = 0
    skip_count = 0
    
    # 遍历ETF
    for i, etf in enumerate(etf_list):
        code = etf['code']
        name = etf.get('name', '')
        
        # 检查是否已抓取
        cache_file = os.path.join(CACHE_DIR, f"{code}_risk.json")
        if os.path.exists(cache_file):
            skip_count += 1
            if (i + 1) % 100 == 0:
                print(f"[{i+1}/{len(etf_list)}] ⏭ {code} - 已存在，跳过")
            continue
        
        # 抓取
        if (i + 1) % 10 == 0:
            print(f"[{i+1}/{len(etf_list)}] 🔍 {code} {name} - 抓取中...")
        
        risk_data, error = fetch_wind_risk(code, name)
        
        if risk_data:
            # 保存
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(risk_data, f, ensure_ascii=False, indent=2)
            success_count += 1
            
            if (i + 1) % 10 == 0:
                print(f"  ✅ 成功: sharpe={risk_data.get('sharpe_1y')}, vol={risk_data.get('volatility_1y')}, dd={risk_data.get('max_drawdown_1y')}")
        else:
            fail_count += 1
            if (i + 1) % 10 == 0:
                print(f"  ❌ 失败: {error}")
        
        # 限流（避免过快调用Wind API）
        time.sleep(0.5)
    
    # 完成统计
    print("-" * 60)
    print(f"✅ 完成！")
    print(f"  成功: {success_count}")
    print(f"  失败: {fail_count}")
    print(f"  跳过: {skip_count}")
    print(f"  总计: {len(etf_list)}")
    print(f"结束时间: {datetime.now().strftime('%H:%M:%S')}")

if __name__ == '__main__':
    main()
