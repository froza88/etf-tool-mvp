"""
Pipeline v2 - 使用频率文件，增量更新
"""
import json
import os
from datetime import datetime
from pathlib import Path

# 频率文件路径
FREQ_FILES = {
    'static': 'etf_static.json',      # 长期不变
    'annual': 'etf_annual.json',     # 年度变化
    'quarterly': 'etf_quarterly.json', # 季度变化
    'monthly': 'etf_monthly.json',   # 月度变化
    'daily': 'etf_daily.json'        # 日度变化
}

# 字段分类（根据field_frequency_final.md）
STATIC_FIELDS = ['code', 'name', 'issuer', 'issuer_full', 'issuer_short',
                 'issue_date', 'custodian', 'management_fee_rate', 'custody_fee_rate',
                 'benchmark', 'fee_rate', 'category']

ANNUAL_FIELDS = ['year_1_return', 'year_3_return', 'annual_3y']

QUARTERLY_FIELDS = ['top_holdings', 'holdings']

MONTHLY_FIELDS = ['return_1m', 'return_3m', 'return_6m', 'ytd_return',
                   'max_drawdown_1m', 'max_drawdown_3m', 'max_drawdown_6m', 'ytd_max_drawdown']

DAILY_FIELDS = ['scale', 'shares', 'close', 'prev_close', 'change_pct', 'change_rate',
                 'volume', 'max_drawdown', 'sharpe_ratio', 'annual_vol',
                 'calmar_ratio', 'tracking_error', 'premium_discount', 'valuation_percentile',
                 'net_inflow_5d']

def load_frequency_files():
    """加载5个频率文件，合并为统一map"""
    merged = {}
    
    for freq, filename in FREQ_FILES.items():
        filepath = Path(filename)
        if not filepath.exists():
            continue
        
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # data是list，转为code→item的map
        for item in data:
            code = str(item.get('code', ''))
            if not code:
                continue
            
            if code not in merged:
                merged[code] = {}
            
            # 合并字段
            merged[code].update(item)
    
    return merged

def save_frequency_files(data_map):
    """将统一map按频率拆分，保存到5个文件"""
    
    # 初始化频率数据
    freq_data = {freq: [] for freq in FREQ_FILES.keys()}
    
    # 按频率分类
    for code, item in data_map.items():
        for freq in FREQ_FILES.keys():
            freq_item = {'code': code}
            
            if freq == 'static':
                fields = STATIC_FIELDS
            elif freq == 'annual':
                fields = ANNUAL_FIELDS
            elif freq == 'quarterly':
                fields = QUARTERLY_FIELDS
            elif freq == 'monthly':
                fields = MONTHLY_FIELDS
            else:  # daily
                fields = DAILY_FIELDS
            
            # 提取该频率的字段
            for field in fields:
                if field in item and item[field] is not None:
                    freq_item[field] = item[field]
            
            # 只保存有数据的item
            if len(freq_item) > 1:  # 除了code还有其他字段
                freq_data[freq].append(freq_item)
    
    # 保存文件
    for freq, filename in FREQ_FILES.items():
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(freq_data[freq], f, ensure_ascii=False, indent=2)
        
        print(f"  ✅ 保存 {filename}: {len(freq_data[freq])} 只ETF")

def step_build_v2():
    """Pipeline v2 - 增量更新（使用频率文件）"""
    print("=" * 60)
    print("Step 4 (v2): 增量更新标准化数据（使用频率文件）")
    print("=" * 60)
    
    # 1. 加载现有数据（从5个频率文件合并）
    print("\n📂 加载现有数据（频率文件）...")
    existing_map = load_frequency_files()
    print(f"  现有ETF: {len(existing_map)} 只")
    
    # 2. 加载全量数据源（WeStock/非凸/盈米/Wind等）
    # TODO: 这里需要调用各个数据源的抓取/加载逻辑
    # 暂时跳过，先测试框架
    
    # 3. 增量更新
    print("\n🔄 增量更新...")
    updated_count = 0
    new_count = 0
    
    # TODO: 遍历全量数据，更新existing_map
    # 示例逻辑（需要补全）：
    # for etf_code, etf_data in new_data.items():
    #     if etf_code in existing_map:
    #         # 更新（只更新变化的字段）
    #         existing_map[etf_code].update(etf_data)
    #         updated_count += 1
    #     else:
    #         # 新增
    #         existing_map[etf_code] = etf_data
    #         new_count += 1
    
    print(f"  更新: {updated_count} 只 | 新增: {new_count} 只")
    
    # 4. 保存回频率文件
    print("\n💾 保存回频率文件...")
    save_frequency_files(existing_map)
    
    # 5. 生成etf_standard_data.json（合并后的标准文件，供Flask使用）
    print("\n🔗 生成 etf_standard_data.json...")
    standard_data = list(existing_map.values())
    with open('etf_standard_data.json', 'w', encoding='utf-8') as f:
        json.dump(standard_data, f, ensure_ascii=False, indent=2)
    print(f"  ✅ etf_standard_data.json: {len(standard_data)} 只ETF")
    
    print("\n" + "=" * 60)
    print("✅ Step 4 (v2) 完成")
    print("=" * 60)

if __name__ == '__main__':
    step_build_v2()
