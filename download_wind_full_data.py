#!/usr/bin/env python3
"""
Wind ETF全量数据下载脚本 - 极简版
目标：最快速度下载1470只ETF的Wind数据，保存原始JSON
策略：并发请求 + 断点续传
作者：WorkBuddy AI
日期：2026-05-30
"""

import json
import os
import time
import subprocess
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

# 配置
WIND_CLI_PATH = "/Users/apangduo/.agents/skills/wind-mcp-skill/scripts/cli.mjs"
DATA_DIR = Path("/Users/apangduo/WorkBuddy/Claw/etf-tool-mvp/data/wind_full")
MAX_WORKERS = 10  # 并发数
ETF_LIST_FILE = "/Users/apangduo/WorkBuddy/Claw/etf-tool-mvp/data/etf_standard_data_backup_20260522_235039.json"

# Wind查询：详细查询（复制自test_10_etfs_wind.py）
WIND_QUERY_TEMPLATE = """查询{code}的全部信息，包括：
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

def load_etf_list():
    """加载ETF列表"""
    with open(ETF_LIST_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
        # 假设格式是 [{"code": "510300", "name": "沪深300ETF"}, ...]
        return [item['code'] for item in data if 'code' in item]

def get_completed_etfs():
    """获取已下载完成的ETF代码列表"""
    completed = set()
    if not DATA_DIR.exists():
        return completed
    
    for json_file in DATA_DIR.glob("*.json"):
        # 文件名格式：510300_20260530.json
        etf_code = json_file.stem.split('_')[0]
        completed.add(etf_code)
    
    return completed

def download_etf_data(etf_code):
    """下载单只ETF的Wind数据"""
    try:
        # 构造查询
        query = WIND_QUERY_TEMPLATE.format(code=etf_code)
        
        # 调用Wind CLI
        cmd = [
            'node',
            WIND_CLI_PATH,
            'call',
            'analytics_data',
            'get_financial_data',
            json.dumps({"question": query})
        ]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120
        )
        
        if result.returncode != 0:
            return etf_code, False, f"Node进程返回码{result.returncode}: {result.stderr[:200]}"
        
        # 解析输出
        output = result.stdout.strip()
        if not output:
            return etf_code, False, "Node进程无输出"
        
        # 尝试解析JSON（第1层）
        try:
            data = json.loads(output)
        except json.JSONDecodeError as e:
            return etf_code, False, f"JSON解析失败: {e}"
        
        # 检查是否成功
        if data.get('isError'):
            error_msg = "Unknown error"
            if 'content' in data and data['content']:
                error_msg = data['content'][0].get('text', 'Unknown error')
            return etf_code, False, f"Wind API错误: {error_msg[:200]}"
        
        # 保存原始数据（不解析）
        timestamp = datetime.now().strftime("%Y%m%d")
        output_file = DATA_DIR / f"{etf_code}_{timestamp}.json"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        return etf_code, True, f"成功，文件大小{output_file.stat().st_size}字节"
        
    except subprocess.TimeoutExpired:
        return etf_code, False, "超时（120秒）"
    except Exception as e:
        return etf_code, False, f"异常: {str(e)[:200]}"

def main():
    print("=" * 80)
    print("Wind ETF全量数据下载脚本 - 极简版")
    print("=" * 80)
    print()
    
    # 1. 加载ETF列表
    print("📂 加载ETF列表...")
    etf_codes = load_etf_list()
    print(f"   找到 {len(etf_codes)} 只ETF")
    print()
    
    # 2. 检查已完成的ETF
    print("🔍 检查已下载的ETF...")
    completed = get_completed_etfs()
    print(f"   已完成: {len(completed)} 只")
    print()
    
    # 3. 计算待下载
    pending = [code for code in etf_codes if code not in completed]
    print(f"⏳ 待下载: {len(pending)} 只")
    print()
    
    if not pending:
        print("✅ 所有ETF已下载完成！")
        return
    
    # 4. 确认开始下载
    print(f"🚀 即将开始下载 {len(pending)} 只ETF")
    print(f"   并发数: {MAX_WORKERS}")
    print(f"   预计耗时: {len(pending) * 2 / MAX_WORKERS / 60:.1f} 小时")
    print()
    print("按 Ctrl+C 可随时中断，支持断点续传")
    print()
    
    # 5. 开始下载
    start_time = time.time()
    success_count = 0
    fail_count = 0
    
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(download_etf_data, code): code for code in pending}
        
        for i, future in enumerate(as_completed(futures), 1):
            etf_code, success, message = future.result()
            
            if success:
                success_count += 1
                print(f"✅ [{i}/{len(pending)}] {etf_code}: {message}")
            else:
                fail_count += 1
                print(f"❌ [{i}/{len(pending)}] {etf_code}: {message}")
            
            # 每10只显示一次进度
            if i % 10 == 0:
                elapsed = time.time() - start_time
                if elapsed > 0:
                    speed = i / elapsed * 60  # 只/分钟
                    remaining = (len(pending) - i) / speed if speed > 0 else 0
                    print(f"   📊 进度: {i}/{len(pending)} ({i/len(pending)*100:.1f}%), "
                          f"速度: {speed:.1f}只/分钟, 预计剩余: {remaining:.1f}分钟")
    
    # 6. 总结
    elapsed = time.time() - start_time
    print()
    print("=" * 80)
    print("下载完成！")
    print("=" * 80)
    print(f"✅ 成功: {success_count} 只")
    print(f"❌ 失败: {fail_count} 只")
    print(f"⏱️  总耗时: {elapsed/60:.1f} 分钟")
    print(f"📁 数据目录: {DATA_DIR}")
    print()

if __name__ == "__main__":
    # 创建数据目录
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    main()
