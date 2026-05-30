#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Wind ETF 全量数据批量抓取脚本（优化版）

修正：1只ETF只调用1次API，查询全部可能字段
"""

import json
import os
import subprocess
import time
from datetime import datetime
from pathlib import Path

# 配置
ETF_LIST_FILE = 'data/etfs.json'
OUTPUT_DIR = 'data/wind_full'
WIND_SCRIPT = '/Users/apangduo/.agents/skills/wind-mcp-skill/scripts/cli.mjs'
SLEEP_BETWEEN_CALLS = 2.0  # 每次调用间隔（秒）

def load_etf_list():
    """加载ETF列表"""
    if not os.path.exists(ETF_LIST_FILE):
        print(f"❌ ETF列表文件不存在: {ETF_LIST_FILE}")
        return []
    
    with open(ETF_LIST_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    if isinstance(data, list):
        etf_list = data
    elif isinstance(data, dict) and 'etfs' in data:
        etf_list = data['etfs']
    else:
        print(f"❌ 无法识别ETF列表格式")
        return []
    
    print(f"📋 加载ETF列表: {len(etf_list)} 只")
    return etf_list

def fetch_wind_all_data(code, name=''):
    """
    抓取单只ETF的Wind全量数据（1次API调用）
    
    构造超级查询，要求Wind返回该ETF的所有可能信息
    """
    try:
        # 超级查询：要求Wind返回该ETF的全部信息
        super_query = f"""查询{code}的全部信息，包括：
1. 基本资料：Wind代码、证券简称、基金全称、基金管理人、基金托管人、基金成立日、上市日期、投资类型、投资范围、业绩比较基准
2. 规模份额：最新规模、最新份额、基金规模合计、份额规模
3. 费率信息：管理费率、托管费率、销售服务费率、最高申购费率、最高赎回费率
4. 净值数据：最新净值、累计净值、净值日期、日回报、复权单位净值
5. 风险指标：夏普比率（近1年、近2年、近3年）、年化波动率（近1年、近2年、近3年）、最大回撤（近1年、近2年、近3年）、跟踪误差（近1年、近2年、近3年）、贝塔（近1年、近2年、近3年）、阿尔法（近1年、近2年、近3年）、信息比率
6. 收益率：近1周回报、近1月回报、近3月回报、近6月回报、近1年回报、近2年回报、近3年回报、近5年回报、成立以来回报
7. 持仓信息：前十大重仓股（证券代码、证券简称、持股数量、持股市值）、行业配置（行业名称、投资市值、占净值比）
8. 交易数据：成交额、换手率、跟踪偏离度、融资余额、融券余额
9. 分红信息：成立以来分红次数、成立以来分红总额、单位分红
10. 评级信息：最新评级、评级机构、评级日期"""

        print(f"  📊 超级查询（{len(super_query)}字符）...")
        
        # 调用Wind MCP技能
        cmd = [
            'node',
            WIND_SCRIPT,
            'call',
            'analytics_data',
            'get_financial_data',
            json.dumps({"question": super_query})
        ]
        
        start_time = time.time()
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120  # 超级查询可能耗时更长
        )
        elapsed = time.time() - start_time
        
        print(f"  ⏱️  耗时: {elapsed:.2f}秒")
        
        if result.returncode != 0:
            return None, f"命令执行失败（返回码{result.returncode}）: {result.stderr[:200]}"
        
        # 解析结果（注意：Wind返回的是嵌套JSON）
        output = result.stdout.strip()
        
        try:
            # 第1层解析：外层格式
            outer = json.loads(output)
            
            if outer.get('isError'):
                return None, f"Wind API返回错误: {outer}"
            
            # 第2层解析：content[0].text 是JSON字符串
            if 'content' not in outer or not outer['content']:
                return None, f"Wind API返回格式异常（无content）: {output[:200]}"
            
            text_content = outer['content'][0]['text']
            inner = json.loads(text_content)
            
            # 第3层：inner.data.data 是实际数据
            if 'data' not in inner or 'data' not in inner['data']:
                return None, f"Wind API返回格式异常（无data.data）: {text_content[:200]}"
            
            wind_data = inner['data']['data']  # 这可能是列表
            
            # 构造返回结构
            result_data = {
                'code': code,
                'name': name,
                'fetched_at': datetime.now().isoformat(),
                'query': super_query,
                'wind_response': inner,  # 保存完整Wind响应
                'data_sets': []
            }
            
            # 解析数据集（可能有多个，如持仓+行业配置）
            if isinstance(wind_data, list):
                for data_set in wind_data:
                    if isinstance(data_set, dict):
                        columns = [col['name'] for col in data_set.get('columns', [])]
                        row_count = len(data_set.get('rows', []))
                        result_data['data_sets'].append({
                            'columns': columns,
                            'row_count': row_count
                        })
            
            return result_data, None
            
        except json.JSONDecodeError as e:
            return None, f"JSON解析失败: {e}\n原始输出: {output[:500]}"
        except Exception as e:
            return None, f"解析异常: {e}"
        
    except subprocess.TimeoutExpired:
        return None, "超时（120秒）"
    except Exception as e:
        return None, f"异常: {str(e)[:200]}"

def test_10_etfs():
    """测试10只ETF，测量积分消耗"""
    print("=" * 80)
    print("🧪 测试10只ETF - 测量Wind API积分消耗")
    print("=" * 80)
    print()
    
    etf_list = load_etf_list()
    if not etf_list:
        return
    
    # 取前10只
    test_etfs = etf_list[:10]
    
    print(f"📋 测试ETF: {[etf['code'] for etf in test_etfs]}")
    print(f"⏳ 预计耗时: {len(test_etfs) * 10 / 60:.1f} 分钟")
    print()
    print("-" * 80)
    
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    success_count = 0
    fail_count = 0
    total_api_calls = 0
    
    start_time = time.time()
    
    for i, etf in enumerate(test_etfs):
        code = etf.get('code', etf.get('symbol', ''))
        name = etf.get('name', '')
        
        print(f"[{i+1}/10] 🔍 {code} {name[:10]}...")
        
        data, error = fetch_wind_all_data(code, name)
        total_api_calls += 1
        
        if data:
            # 保存
            output_file = os.path.join(OUTPUT_DIR, f"{code}_test.json")
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            success_count += 1
            
            # 显示数据集信息
            data_sets = data.get('data_sets', [])
            print(f"  ✅ 成功: {len(data_sets)}个数据集")
            for ds in data_sets:
                print(f"     - {ds['row_count']}行 x {len(ds['columns'])}列: {ds['columns'][:3]}...")
        else:
            fail_count += 1
            print(f"  ❌ 失败: {error}")
        
        print()
        
        # 限流
        if i < len(test_etfs) - 1:
            time.sleep(SLEEP_BETWEEN_CALLS)
    
    elapsed = time.time() - start_time
    
    print("-" * 80)
    print("✅ 测试完成！")
    print(f"  成功: {success_count}/10")
    print(f"  失败: {fail_count}/10")
    print(f"  API调用: {total_api_calls}次")
    print(f"  用时: {elapsed/60:.1f}分钟")
    print()
    print("⚠️  请检查Wind API积分消耗！")
    print(f"  如果消耗了 {total_api_calls} 积分 → 每只ETF消耗1积分")
    print(f"  如果消耗了 >{total_api_calls} 积分 → Wind按数据量计分")
    print()
    print("=" * 80)

if __name__ == '__main__':
    test_10_etfs()
