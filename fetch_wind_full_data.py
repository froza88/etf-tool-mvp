#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Wind ETF 全量数据批量抓取脚本

从Wind API获取每只ETF的全部可用信息，保存完整JSON响应。
不选择性提取字段，保留Wind返回的所有数据。

使用方法：
    python3 fetch_wind_full_data.py
"""

import json
import os
import subprocess
import time
from datetime import datetime
from pathlib import Path

# 配置
ETF_LIST_FILE = 'data/etfs.json'  # 所有ETF列表
OUTPUT_DIR = 'data/wind_full'  # 输出目录
WIND_SCRIPT = '/Users/apangduo/.agents/skills/wind-mcp-skill/scripts/cli.mjs'
BATCH_SIZE = 10  # 每批处理数量
SLEEP_BETWEEN_CALLS = 1.0  # 每次调用间隔（秒）

def load_etf_list():
    """加载ETF列表"""
    if not os.path.exists(ETF_LIST_FILE):
        print(f"❌ ETF列表文件不存在: {ETF_LIST_FILE}")
        return []
    
    with open(ETF_LIST_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # 处理不同格式
    if isinstance(data, list):
        etf_list = data
    elif isinstance(data, dict) and 'etfs' in data:
        etf_list = data['etfs']
    else:
        print(f"❌ 无法识别ETF列表格式")
        return []
    
    print(f"📋 加载ETF列表: {len(etf_list)} 只")
    return etf_list

def fetch_wind_full_data(code, name=''):
    """
    抓取单只ETF的Wind全量数据
    
    调用Wind API查询该ETF的全部可用信息
    """
    try:
        # 构造查询：要求Wind返回该ETF的全部信息
        # 使用多个维度的查询，确保覆盖所有数据
        queries = [
            f"查询{code}的基本信息，包括名称、管理人、托管人、成立日期、上市日期、投资范围、业绩比较基准",
            f"查询{code}的净值数据，包括最新净值、累计净值、净值日期",
            f"查询{code}的规模数据，包括最新规模、份额",
            f"查询{code}的费率信息，包括管理费、托管费、销售服务费",
            f"查询{code}的风险指标，包括夏普比率、年化波动率、最大回撤、贝塔、阿尔法、跟踪误差、信息比率",
            f"查询{code}的收益率，包括近1周、近1月、近3月、近6月、近1年、近2年、近3年收益率",
            f"查询{code}的持仓信息，包括前十大重仓股、行业配置",
            f"查询{code}的交易数据，包括成交额、换手率、跟踪偏离度"
        ]
        
        all_data = {
            'code': code,
            'name': name,
            'fetched_at': datetime.now().isoformat(),
            'queries': {}
        }
        
        for i, query in enumerate(queries):
            try:
                # 调用Wind MCP技能
                cmd = [
                    'node',
                    WIND_SCRIPT,
                    'call',
                    'analytics_data',
                    'get_financial_data',
                    json.dumps({"question": query})
                ]
                
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=60
                )
                
                if result.returncode != 0:
                    all_data['queries'][f'q{i}'] = {
                        'query': query,
                        'success': False,
                        'error': result.stderr[:200]
                    }
                    continue
                
                # 解析结果
                output = result.stdout.strip()
                try:
                    parsed = json.loads(output)
                    all_data['queries'][f'q{i}'] = {
                        'query': query,
                        'success': parsed.get('ok', False),
                        'data': parsed.get('data', {}),
                        'error': parsed.get('error', None) if not parsed.get('ok') else None
                    }
                except json.JSONDecodeError:
                    all_data['queries'][f'q{i}'] = {
                        'query': query,
                        'success': False,
                        'error': f'JSON解析失败: {output[:200]}'
                    }
                
                # 限流
                time.sleep(SLEEP_BETWEEN_CALLS)
                
            except subprocess.TimeoutExpired:
                all_data['queries'][f'q{i}'] = {
                    'query': query,
                    'success': False,
                    'error': '超时'
                }
            except Exception as e:
                all_data['queries'][f'q{i}'] = {
                    'query': query,
                    'success': False,
                    'error': str(e)[:200]
                }
        
        return all_data, None
        
    except Exception as e:
        return None, f"异常: {str(e)[:200]}"

def main():
    """主函数"""
    print("=" * 80)
    print("🌐 Wind ETF 全量数据批量抓取")
    print("=" * 80)
    print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # 加载ETF列表
    etf_list = load_etf_list()
    if not etf_list:
        return
    
    # 创建输出目录
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # 统计
    success_count = 0
    fail_count = 0
    skip_count = 0
    error_types = {}
    
    # 遍历ETF
    total = len(etf_list)
    print(f"开始抓取 {total} 只ETF的Wind全量数据...")
    print(f"输出目录: {OUTPUT_DIR}")
    print(f"预计时间: {total * 8 * SLEEP_BETWEEN_CALLS / 60:.1f} 分钟")
    print("-" * 80)
    
    start_time = time.time()
    
    for i, etf in enumerate(etf_list):
        code = etf.get('code', etf.get('symbol', ''))
        name = etf.get('name', '')
        
        if not code:
            print(f"[{i+1}/{total}] ⚠️  跳过（无代码）")
            skip_count += 1
            continue
        
        # 检查是否已抓取
        output_file = os.path.join(OUTPUT_DIR, f"{code}.json")
        if os.path.exists(output_file):
            skip_count += 1
            if (i + 1) % 50 == 0:
                print(f"[{i+1}/{total}] ⏭ {code} - 已存在，跳过")
            continue
        
        # 抓取
        if (i + 1) % 5 == 0 or i == 0:
            elapsed = time.time() - start_time
            avg_time = elapsed / max(i, 1)
            eta = (total - i) * avg_time / 60
            print(f"[{i+1}/{total}] 🔍 {code} {name[:10]} - 抓取中... (ETA: {eta:.1f}分钟)")
        
        all_data, error = fetch_wind_full_data(code, name)
        
        if all_data:
            # 保存
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(all_data, f, ensure_ascii=False, indent=2)
            success_count += 1
            
            # 统计成功查询数
            success_queries = sum(1 for q in all_data['queries'].values() if q.get('success'))
            if (i + 1) % 5 == 0:
                print(f"  ✅ 成功: {success_queries}/8 查询成功")
        else:
            fail_count += 1
            error_key = error[:50] if error else '未知'
            error_types[error_key] = error_types.get(error_key, 0) + 1
            if (i + 1) % 5 == 0:
                print(f"  ❌ 失败: {error}")
        
        # 每批保存进度
        if (i + 1) % BATCH_SIZE == 0:
            elapsed = time.time() - start_time
            speed = (i + 1) / elapsed * 60  # 只/分钟
            print(f"  📊 进度: {i+1}/{total} ({((i+1)/total*100):.1f}%), 速度: {speed:.1f}只/分钟")
            print(f"  成功: {success_count}, 失败: {fail_count}, 跳过: {skip_count}")
            print("-" * 80)
    
    # 完成统计
    elapsed_total = time.time() - start_time
    print("-" * 80)
    print("✅ 抓取完成！")
    print(f"  成功: {success_count}")
    print(f"  失败: {fail_count}")
    print(f"  跳过: {skip_count}")
    print(f"  总计: {total}")
    print(f"  用时: {elapsed_total/60:.1f} 分钟")
    print(f"  平均速度: {total/elapsed_total*60:.1f} 只/分钟")
    
    if error_types:
        print()
        print("失败原因统计:")
        for error, count in sorted(error_types.items(), key=lambda x: -x[1])[:5]:
            print(f"  {error}: {count} 次")
    
    print()
    print(f"结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)

if __name__ == '__main__':
    main()
