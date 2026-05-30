#!/usr/bin/env python3
"""
合并Wind数据到我们的ETF数据库
策略：用Wind数据补全我们的数据库（不覆盖已有有效数据）
作者：WorkBuddy AI
日期：2026-05-31
"""

import json
import os
from pathlib import Path
from datetime import datetime

# 配置
OUR_DB_FILE = "data/etf_standard_data_backup_20260522_235039.json"
WIND_DATA_DIR = Path("data/wind_full")
OUTPUT_FILE = f"data/etf_db_with_wind_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

# 字段映射：Wind字段名 → 我们的字段名
FIELD_MAPPING = {
    # 基本信息
    "Wind代码": "wind_code",
    "证券简称": "name",
    "基金全称": "full_name",
    "基金管理人": "issuer",
    "基金托管人": "custodian",
    "基金成立日": "establish_date",
    "上市日期": "list_date",
    "投资类型_二级分类": "invest_type",
    "投资范围": "invest_scope",
    "业绩比较基准": "benchmark",
    
    # 规模份额
    "基金规模合计": "scale",
    "最新份额": "shares",
    "最新规模": "latest_scale",
    "最新份额规模": "latest_shares_scale",
    "场内流通份额": "exchange_shares",
    
    # 费率信息
    "管理费率_支持历史": "management_fee_history",
    "托管费率_支持历史": "custodian_fee_history",
    "销售服务费率_支持历史": "service_fee_history",
    "最高申购费率": "max_subscribe_fee",
    "最高赎回费率": "max_redeem_fee",
    "管理费率": "management_fee",
    "托管费率": "custodian_fee",
    
    # 净值数据
    "最新单位净值": "nav",
    "最新累计单位净值": "accum_nav",
    "最新复权单位净值": "adj_nav",
    "最新净值日期": "nav_date",
    "日回报": "daily_return",
    "最新日回报": "latest_daily_return",
    
    # 风险指标（近1年）
    "近1年夏普比率": "sharpe_ratio_1y",
    "近1年年化波动率": "annual_vol_1y",
    "近1年最大回撤": "max_drawdown_1y",
    "近1年跟踪误差": "tracking_error_1y",
    "近1年贝塔": "beta_1y",
    "近1年阿尔法": "alpha_1y",
    "近1年信息比率": "info_ratio_1y",
    
    # 风险指标（近2年）
    "近2年夏普比率": "sharpe_ratio_2y",
    "近2年年化波动率": "annual_vol_2y",
    "近2年最大回撤": "max_drawdown_2y",
    "近2年跟踪误差": "tracking_error_2y",
    "近2年贝塔": "beta_2y",
    "近2年阿尔法": "alpha_2y",
    "近2年信息比率": "info_ratio_2y",
    
    # 风险指标（近3年）
    "近3年夏普比率": "sharpe_ratio_3y",
    "近3年年化波动率": "annual_vol_3y",
    "近3年最大回撤": "max_drawdown_3y",
    "近3年跟踪误差": "tracking_error_3y",
    "近3年贝塔": "beta_3y",
    "近3年阿尔法": "alpha_3y",
    "近3年信息比率": "info_ratio_3y",
    
    # 收益率
    "近1周回报": "return_1w",
    "近1月回报": "return_1m",
    "近3月回报": "return_3m",
    "近6月回报": "return_6m",
    "近1年回报": "return_1y",
    "近2年回报": "return_2y",
    "近3年回报": "return_3y",
}

def parse_wind_file(file_path):
    """解析单个Wind数据文件"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 解析Wind数据格式
        if 'content' not in data or not data['content']:
            return None
        
        content = data['content'][0]
        if 'text' not in content:
            return None
        
        text = content['text']
        inner = json.loads(text)
        
        if 'data' not in inner or 'data' not in inner['data']:
            return None
        
        wind_data = inner['data']['data']
        if not wind_data:
            return None
        
        # 提取所有数据集的字段
        result = {}
        for ds in wind_data:
            if 'columns' not in ds or 'rows' not in ds:
                continue
            
            columns = [col['name'] for col in ds['columns']]
            if not ds['rows']:
                continue
                
            row = ds['rows'][0]
            for col_name, val in zip(columns, row):
                if val is not None and val != '' and val != 0:
                    result[col_name] = val
        
        return result
        
    except Exception as e:
        return None

def merge_etf(our_etf, wind_etf):
    """合并单只ETF的数据"""
    if not wind_etf:
        return our_etf
    
    # 遍历字段映射
    for wind_field, our_field in FIELD_MAPPING.items():
        if wind_field in wind_etf and wind_etf[wind_field] is not None:
            # Wind有这个字段的值
            wind_value = wind_etf[wind_field]
            
            # 检查值是否有效（不是None/空/0）
            if wind_value is None or wind_value == '' or wind_value == 0:
                continue
                
            # 我们的数据库是否缺少这个字段，或者字段值为空/0
            if our_field not in our_etf or our_etf[our_field] is None or our_etf[our_field] == '' or our_etf[our_field] == 0:
                our_etf[our_field] = wind_value
                
    return our_etf

def main():
    print("=" * 80)
    print("合并Wind数据到ETF数据库")
    print("=" * 80)
    print()
    
    # 1. 加载我们的数据库
    with open(OUR_DB_FILE, 'r', encoding='utf-8') as f:
        our_db = json.load(f)
    print(f"✅ 我们的数据库: {len(our_db)} 只ETF")
    
    # 2. 加载Wind数据（从原始JSON文件）
    wind_files = list(WIND_DATA_DIR.glob("*.json"))
    print(f"✅ Wind数据文件: {len(wind_files)} 个")
    
    # 创建code → Wind数据的映射
    wind_dict = {}
    for wind_file in wind_files:
        wind_data = parse_wind_file(wind_file)
        if wind_data and 'Wind代码' in wind_data:
            wind_code = wind_data['Wind代码']
            wind_dict[wind_code] = wind_data
    
    print(f"✅ Wind数据映射: {len(wind_dict)} 只ETF\n")
    
    # 3. 合并数据
    merged_count = 0
    for our_etf in our_db:
        # 找到对应的Wind数据（通过code匹配）
        code = our_etf.get('code', '')
        if not code:
            continue
            
        # Wind代码格式：510300.OF → 我们需要找到Wind代码
        # 尝试不同后缀
        matched = False
        for suffix in ['', '.OF', '.SH', '.SZ', '.HK']:
            test_code = f"{code}{suffix}"
            if test_code in wind_dict:
                our_etf = merge_etf(our_etf, wind_dict[test_code])
                merged_count += 1
                matched = True
                break
        
        if not matched:
            # 尝试反向：从Wind代码中提取数字部分
            for wind_code in wind_dict.keys():
                if code in wind_code:
                    our_etf = merge_etf(our_etf, wind_dict[wind_code])
                    merged_count += 1
                    break
    
    print(f"✅ 合并完成: {merged_count} 只ETF匹配到Wind数据\n")
    
    # 4. 保存合并后的数据库
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(our_db, f, ensure_ascii=False, indent=2)
    
    print(f"✅ 合并后数据库已保存: {OUTPUT_FILE}")
    print(f"   文件大小: {os.path.getsize(OUTPUT_FILE) / 1024 / 1024:.2f} MB")
    print()
    
    # 5. 统计合并效果
    print("=" * 80)
    print("合并效果统计")
    print("=" * 80)
    print()
    
    # 检查关键字段的完整度
    key_fields = ['tracking_error_1y', 'management_fee', 'custodian_fee', 'sharpe_ratio_1y', 'annual_vol_1y']
    
    for field in key_fields:
        count = sum(1 for etf in our_db if etf.get(field) is not None and etf.get(field) != 0)
        print(f"{field}: {count}/{len(our_db)} ({count/len(our_db)*100:.1f}%)")
    
    print()

if __name__ == "__main__":
    main()
