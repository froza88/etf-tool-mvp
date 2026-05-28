#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Wind数据批量抓取 - 简化循环版
每次抓取1只ETF，保存缓存，继续下一只，直到积分用完或列表完成
"""
import json
import subprocess
import time
import os
from datetime import datetime

# 配置
ETF_LIST_FILE = 'etfs_missing_wind.json'  # 1457只缺失Wind数据的ETF
CACHE_DIR = 'data/cache/wind'
WIND_CLI = '/Users/apangduo/.agents/skills/wind-mcp-skill/scripts/cli.mjs'
POINTS_PER_CALL = 1  # Wind每次调用消耗1分（根据实测）

def fetch_wind_risk(code, name):
    """调用Wind API获取风险指标"""
    question = f"查询{code}{name}的夏普比率近1年、年化波动率近1年、最大回撤近1年"
    
    cmd = [
        'node',
        WIND_CLI,
        'call',
        'analytics_data',
        'get_financial_data',
        json.dumps({"question": question})
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        output = result.stdout
        
        # 解析响应
        if 'content' not in output:
            return None, f"响应无content: {output[:200]}"
        
        # 提取content[0].text (JSON字符串)
        import re
        content_match = re.search(r'"text":\s*"([^"]*)"', output)
        if not content_match:
            return None, f"无法提取text: {output[:200]}"
        
        text_str = content_match.group(1).replace('\\n', '\n').replace('\\"', '"')
        
        try:
            # 正确解析：先解析整个响应，再提取text字段
            response_obj = json.loads(output)
            text_str = response_obj['content'][0]['text']  # text是JSON字符串
            data_obj = json.loads(text_str)  # 解析text为JSON对象
        except Exception as parse_err:
            return None, f"JSON解析失败: {str(parse_err)[:100]}"
        
        # 提取数据
        data_list = data_obj.get('data', {}).get('data', [])
        if not data_list:
            return None, "data.data为空"
        
        columns = data_list[0].get('columns', [])
        rows = data_list[0].get('rows', [])
        
        if not rows:
            return None, "rows为空"
        
        # 映射列名
        col_map = {}
        for idx, col in enumerate(columns):
            col_name = col.get('name', '')
            col_map[col_name] = idx
        
        # 提取第一个row的数据
        row = rows[0] if rows else []
        
        risk_data = {
            'windcode': f"{code}.OF",
            'name': name,
            'fetched_at': datetime.now().isoformat()
        }
        
        for col_name, idx in col_map.items():
            if idx >= len(row):
                continue
            val = row[idx]
            if '夏普' in col_name or 'SHARPE' in col_name.upper():
                risk_data['sharpe_1y'] = float(val) if val else None
            elif '波动率' in col_name or 'VOLATILITY' in col_name.upper():
                risk_data['volatility_1y'] = float(val) if val else None
            elif '回撤' in col_name or 'DRAWDOWN' in col_name.upper():
                risk_data['max_drawdown_1y'] = float(val) if val else None
        
        return risk_data, None
        
    except Exception as e:
        return None, f"异常: {str(e)[:100]}"

def main():
    """主循环：遍历ETF列表，逐个抓取"""
    
    # 加载ETF列表
    with open(ETF_LIST_FILE, 'r', encoding='utf-8') as f:
        etf_list = json.load(f)
    
    print(f"📋 ETF列表: {len(etf_list)} 只")
    
    # 创建缓存目录
    os.makedirs(CACHE_DIR, exist_ok=True)
    
    # 统计
    success_count = 0
    error_count = 0
    skip_count = 0
    
    # 主循环
    for i, etf in enumerate(etf_list):
        code = etf['code']
        name = etf.get('name', '')
        
        # 检查是否已抓取
        cache_file = os.path.join(CACHE_DIR, f"{code}_risk.json")
        if os.path.exists(cache_file):
            skip_count += 1
            if i % 50 == 0:
                print(f"⏭️  [{i+1}/{len(etf_list)}] 跳过 {code} (已存在)")
            continue
        
        print(f"🔄 [{i+1}/{len(etf_list)}] 抓取 {code} {name}...", end='', flush=True)
        
        # 调用Wind API
        risk_data, error = fetch_wind_risk(code, name)
        
        if risk_data:
            # 保存缓存
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(risk_data, f, ensure_ascii=False, indent=2)
            success_count += 1
            print(f" ✅ sharpe={risk_data.get('sharpe_1y')}, vol={risk_data.get('volatility_1y')}, dd={risk_data.get('max_drawdown_1y')}")
        else:
            error_count += 1
            print(f" ❌ {error[:80]}")
        
        # 限速：每次调用后休眠1秒（避免限流）
        time.sleep(1)
        
        # 每10只显示一次统计
        if (i + 1) % 10 == 0:
            print(f"📊 进度: {i+1}/{len(etf_list)} | 成功:{success_count} 失败:{error_count} 跳过:{skip_count}")
    
    # 最终统计
    print(f"\n{'='*60}")
    print(f"✅ Wind抓取完成")
    print(f"📊 总计: {len(etf_list)} 只ETF")
    print(f"   成功: {success_count}")
    print(f"   失败: {error_count}")
    print(f"   跳过: {skip_count}")
    print(f"{'='*60}")

if __name__ == '__main__':
    main()
