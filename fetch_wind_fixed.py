#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Wind风险指标批量抓取 - 修复版

正确的Wind API响应格式：
{
  "content": [{"type": "text", "text": "{\"data\": {...}}"}],
  "isError": false
}

使用方法：
    python3 fetch_wind_fixed.py [etf_list.json]
"""

import json
import os
import subprocess
import time
import sys
from datetime import datetime

# 配置
DEFAULT_INPUT = 'etfs_missing_wind.json'
CACHE_DIR = 'data/cache/wind'
WIND_CLI = '/Users/apangduo/.agents/skills/wind-mcp-skill/scripts/cli.mjs'

def fetch_wind_risk(code, name=''):
    """抓取单只ETF的Wind风险指标 - 修复版"""
    try:
        # 调用Wind API
        question = f"查询{code}的夏普比率近1年、年化波动率近1年、最大回撤近1年"
        cmd = [
            'node',
            WIND_CLI,
            'call',
            'analytics_data',
            'get_financial_data',
            json.dumps({"question": question})
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode != 0:
            return None, f"命令执行失败: {result.stderr[:100]}"
        
        # 解析响应（格式: {"content": [{"type": "text", "text": "..."}], "isError": false}）
        stdout = result.stdout.strip()
        
        # 找到JSON开始的位置（跳过可能的日志信息）
        json_start = stdout.find('{')
        if json_start == -1:
            return None, f"找不到JSON: {stdout[:200]}"
        
        json_str = stdout[json_start:]
        response = json.loads(json_str)
        
        # 检查是否错误
        if response.get('isError'):
            error_msg = response.get('content', [{}])[0].get('text', '未知错误')
            return None, f"API返回错误: {error_msg[:100]}"
        
        # 提取text字段（它是JSON字符串）
        content_list = response.get('content', [])
        if not content_list or len(content_list) == 0:
            return None, "content为空"
        
        text_str = content_list[0].get('text', '')
        if not text_str:
            return None, "text为空"
        
        # 解析text（它是JSON字符串）
        data_obj = json.loads(text_str)
        
        # 提取数据
        data_list = data_obj.get('data', {}).get('data', [])
        if not data_list or len(data_list) == 0:
            return None, "data.data为空"
        
        columns = data_list[0].get('columns', [])
        rows = data_list[0].get('rows', [])
        if not rows:
            return None, "rows为空"
        
        # 根据columns映射字段位置
        col_map = {}
        for idx, col in enumerate(columns):
            col_name = col.get('name', '')
            col_map[col_name] = idx
        
        # 提取指标（取第一个row）
        row = rows[0] if rows else []
        
        risk_data = {
            'windcode': f"{code}.OF",
            'name': name or '',
            'fetched_at': datetime.now().isoformat()
        }
        
        # 根据列名提取（兼容中英文）
        for col_name, idx in col_map.items():
            if '夏普' in col_name or 'SHARPE' in col_name.upper():
                risk_data['sharpe_1y'] = float(row[idx]) if idx < len(row) and row[idx] else None
            elif '波动率' in col_name or 'VOLATILITY' in col_name.upper():
                risk_data['volatility_1y'] = float(row[idx]) if idx < len(row) and row[idx] else None
            elif '回撤' in col_name or 'DRAWDOWN' in col_name.upper():
                risk_data['max_drawdown_1y'] = float(row[idx]) if idx < len(row) and row[idx] else None
        
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
    print("🔧 Wind风险指标批量抓取 - 修复版")
    print("=" * 60)
    
    # 确定输入文件
    input_file = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_INPUT
    
    if not os.path.exists(input_file):
        print(f"❌ 输入文件不存在: {input_file}")
        return
    
    # 加载ETF列表
    with open(input_file, 'r', encoding='utf-8') as f:
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
        
        # 限流
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
