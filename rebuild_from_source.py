#!/usr/bin/env python3
"""
从源头一键重建 ETF 数据库
1. 用 AKShare(东方财富) 重新获取全量 ETF 行情数据
2. 用 ftshare API 重新获取 top_holdings
3. 重新运行 build_standard_data.py 生成标准化数据
"""
import json
import os
import sys
import subprocess
import time
import warnings
warnings.filterwarnings('ignore')

ROOT = os.path.dirname(os.path.abspath(__file__))

print("=" * 60)
print("  ETF 数据库源头重建")
print("=" * 60)

# ==================== Step 1: AKShare 获取全量数据 ====================
print("\n[1/3] 从东方财富(AKShare)重新获取全量ETF数据...")
try:
    import akshare as ak
    import pandas as pd
    
    df = ak.fund_etf_spot_em()
    print(f"  获取到 {len(df)} 只ETF")
    
    # 逐行构建标准数据
    etf_list = []
    for i, (idx, row) in enumerate(df.iterrows()):
        try:
            etf = {
                'code': str(row['代码']).strip(),
                'name': str(row['名称']).strip(),
            }
            for field, src_field, default in [
                ('latest_price', '最新价', None),
                ('change_pct', '涨跌幅', None),
                ('volume', '成交量', None),
                ('amount', '成交额', None),
                ('market_cap', '基金规模', None),
                ('manager', '基金管理人', ''),
            ]:
                try:
                    val = row[src_field]
                    etf[field] = float(val) if pd.notna(val) else default
                except:
                    etf[field] = default
            etf_list.append(etf)
        except Exception as e:
            print(f"  处理第{i}行异常: {e}")
            continue
    
    # 去重（按代码去重，保留第一条）
    seen = set()
    unique = []
    for e in etf_list:
        c = e['code']
        if c not in seen:
            seen.add(c)
            unique.append(e)
    dup = len(etf_list) - len(unique)
    if dup:
        print(f"  去重: 去除 {dup} 条重复记录")
    
    # 按规模降序排序
    unique.sort(key=lambda x: x.get('market_cap') or 0, reverse=True)
    
    # 保存
    output_file = os.path.join(ROOT, 'etf_complete_all.json')
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(unique, f, ensure_ascii=False, indent=2)
    print(f"  已保存: {output_file} ({len(unique)} 只, {os.path.getsize(output_file)/1024:.0f}KB)")
    
except ImportError:
    print("  ❌ akshare 未安装，跳过。如有需要请运行: pip install akshare")
    print("  使用仓库中已有的 etf_complete_all.json")
except Exception as e:
    print(f"  ❌ AKShare 获取失败: {e}")
    print("  使用仓库中已有的 etf_complete_all.json")

# ==================== Step 2: 重新获取 top_holdings ====================
print("\n[2/3] 重新获取 top_holdings（调用 etf-component API）...")
refetch_script = os.path.join(ROOT, 'refetch_holdings_v2.py')
if os.path.exists(refetch_script):
    try:
        result = subprocess.run(
            [sys.executable, refetch_script],
            capture_output=True, text=True, timeout=300
        )
        print(result.stdout)
        if result.returncode != 0:
            print(f"  ⚠️  top_holdings 获取部分失败，但数据已保存")
    except subprocess.TimeoutExpired:
        print(f"  ⚠️  获取超时（5分钟），部分数据已保存")
    except Exception as e:
        print(f"  ❌ 获取 top_holdings 失败: {e}")
else:
    print(f"  ⚠️  refetch_holdings_v2.py 不存在，跳过")

# ==================== Step 3: 运行 build_standard_data.py ====================
print("\n[3/3] 运行数据标准化...")
build_script = os.path.join(ROOT, 'build_standard_data.py')
if os.path.exists(build_script):
    try:
        result = subprocess.run(
            [sys.executable, build_script],
            capture_output=True, text=True, timeout=60
        )
        print(result.stdout)
        if result.returncode == 0:
            print("✅ 标准化数据生成成功")
        else:
            print("  ❌ 标准化失败")
    except Exception as e:
        print(f"  ❌ 标准化异常: {e}")
else:
    print(f"  ⚠️  build_standard_data.py 不存在，跳过")

print("\n" + "=" * 60)
print("  重建完成！请提交到远程并 pull 部署")
print("=" * 60)
