#!/usr/bin/env python3
"""
批量抓取Wind风险指标（夏普比率/年化波动率/最大回撤）
目标：Top 200 ETF（按规模排序）
假设：每条调用消耗5积分，今天能抓200只（1000积分）
"""

import json
import subprocess
import time
import os
from datetime import datetime

# 配置
TOP_ETF_FILE = 'top200_etf_no_wind.json'  # 修改为：无Wind数据的58只ETF
CACHE_DIR = 'data/cache/wind'
LOG_FILE = f'wind_fetch_log_{datetime.now().strftime("%Y%m%d_%H%M%S")}.txt'

# 确保缓存目录存在
os.makedirs(CACHE_DIR, exist_ok=True)

# 读取Top 200 ETF列表
with open(TOP_ETF_FILE, 'r', encoding='utf-8') as f:
    top_etfs = json.load(f)

print(f"开始批量抓取Wind风险指标...")
print(f"目标ETF数量: {len(top_etfs)}")
print(f"预计消耗积分: {len(top_etfs) * 5} (假设5分/只)")
print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("-" * 80)

success_count = 0
fail_count = 0
skip_count = 0

for i, etf in enumerate(top_etfs, 1):
    code = etf['code']
    name = etf['name']
    
    # 检查是否已抓取过（避免重复消耗积分）
    cache_file = os.path.join(CACHE_DIR, f"{code}_risk.json")
    if os.path.exists(cache_file):
        print(f"[{i:3d}/{len(top_etfs)}] ⏭ {code} {name} - 已存在，跳过")
        skip_count += 1
        continue
    
    print(f"[{i:3d}/{len(top_etfs)}] 🔍 {code} {name} - 抓取中...", end=' ', flush=True)
    
    # 构造Wind API调用命令
    question = f"查询{code}{name}的夏普比率近1年、年化波动率近1年、最大回撤近1年"
    cmd = [
        'node',
        '/Users/apangduo/.agents/skills/wind-mcp-skill/scripts/cli.mjs',  # 修复：cli.mjs 不是 cli.js
        'call',
        'analytics_data',
        'get_financial_data',
        json.dumps({"question": question})
    ]
    
    try:
        # 调用Wind API
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            # 解析返回结果
            output = result.stdout
            try:
                data = json.loads(output)
                if 'content' in data and len(data['content']) > 0:
                    text_content = data['content'][0]['text']
                    parsed = json.loads(text_content)
                    
                    if 'data' in parsed and 'data' in parsed['data']:
                        # parsed['data']['data'] 是 LIST: [{"columns":..., "rows":[[...]]}]
                        result_list = parsed['data']['data']
                        if result_list and len(result_list) > 0:
                            first_result = result_list[0]  # DICT: {"columns":..., "rows":...}
                            rows = first_result.get('rows', [])  # LIST: [[code, name, sharpe, vol, max_dd]]
                            if rows and len(rows) > 0:
                                # 保存数据
                                cache_data = {
                                    'windcode': rows[0][0] if len(rows[0]) > 0 else code,
                                    'name': rows[0][1] if len(rows[0]) > 1 else name,
                                    'sharpe_1y': rows[0][2] if len(rows[0]) > 2 else None,
                                    'volatility_1y': rows[0][3] if len(rows[0]) > 3 else None,
                                    'max_drawdown_1y': rows[0][4] if len(rows[0]) > 4 else None,
                                    'fetched_at': datetime.now().isoformat()
                                }
                            
                            with open(cache_file, 'w', encoding='utf-8') as f:
                                json.dump(cache_data, f, ensure_ascii=False, indent=2)
                            
                            print(f"✅ 成功 (夏普:{cache_data['sharpe_1y']}, 波动率:{cache_data['volatility_1y']}%, 回撤:{cache_data['max_drawdown_1y']}%)")
                            success_count += 1
                        else:
                            print(f"❌ 无数据")
                            fail_count += 1
                    else:
                        print(f"❌ 返回格式错误")
                        fail_count += 1
                else:
                    print(f"❌ 返回为空")
                    fail_count += 1
            except json.JSONDecodeError:
                print(f"❌ JSON解析失败")
                fail_count += 1
        else:
            print(f"❌ API调用失败 (code={result.returncode})")
            fail_count += 1
    except subprocess.TimeoutExpired:
        print(f"❌ 超时")
        fail_count += 1
    except Exception as e:
        print(f"❌ 异常: {str(e)}")
        fail_count += 1
    
    # 限速：每次调用后休眠2秒（避免触发限流）
    if i < len(top_etfs):
        time.sleep(2)

# 统计结果
print("-" * 80)
print(f"批量抓取完成!")
print(f"成功: {success_count}")
print(f"失败: {fail_count}")
print(f"跳过: {skip_count}")
print(f"结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# 保存日志
log_content = f"""
Wind风险指标批量抓取日志
开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
目标ETF数: {len(top_etfs)}
成功: {success_count}
失败: {fail_count}
跳过: {skip_count}
"""
with open(LOG_FILE, 'w', encoding='utf-8') as f:
    f.write(log_content)

print(f"日志已保存到: {LOG_FILE}")
