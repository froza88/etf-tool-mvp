#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据迁移脚本：从 etf_standard_data.backup.json 按频率拆分到5个新文件

新文件结构：
- etf_static.json - 长期不变数据（code, name, issuer, issue_date, custodian, category, management_fee_rate, custody_fee_rate, fee_rate, track_index_code, track_index_name）
- etf_annual.json - 年度变化数据（year_1_return, year_3_return, ytd_return, ytd_max_drawdown, annual_3y, index_1y_return）
- etf_quarterly.json - 季度变化数据（top_holdings）
- etf_monthly.json - 月度变化数据（return_1m, return_3m, return_6m）
- etf_daily.json - 日度变化数据（scale, shares, close, prev_close, change_rate, change_pct, max_drawdown, sharpe_ratio, annual_vol, calmar_ratio, max_drawdown_1m, max_drawdown_3m, max_drawdown_6m, max_drawdown_1y, max_drawdown_3y, turnover_rate, turnover_value, discount_ratio, stock_ratio）

使用方法：
    python3 migrate_to_frequency_files.py [backup_file_path]

示例：
    python3 migrate_to_frequency_files.py etf_standard_data.backup.json
"""

import json
import sys
import os
from datetime import datetime

# 默认备份文件路径
DEFAULT_BACKUP_FILE = 'etf_standard_data.backup.json'

# 新文件结构定义
FREQUENCY_FILES = {
    'etf_static.json': {
        'fields': ['code', 'name', 'issuer', 'issue_date', 'custodian', 'category', 'management_fee_rate', 'custody_fee_rate', 'fee_rate', 'track_index_code', 'track_index_name'],
        'description': '长期不变数据'
    },
    'etf_annual.json': {
        'fields': ['code', 'year_1_return', 'year_3_return', 'ytd_return', 'ytd_max_drawdown', 'annual_3y', 'index_1y_return'],
        'description': '年度变化数据'
    },
    'etf_quarterly.json': {
        'fields': ['code', 'top_holdings'],
        'description': '季度变化数据'
    },
    'etf_monthly.json': {
        'fields': ['code', 'return_1m', 'return_3m', 'return_6m'],
        'description': '月度变化数据'
    },
    'etf_daily.json': {
        'fields': ['code', 'scale', 'shares', 'close', 'prev_close', 'change_rate', 'change_pct', 'max_drawdown', 'sharpe_ratio', 'annual_vol', 'calmar_ratio', 'max_drawdown_1m', 'max_drawdown_3m', 'max_drawdown_6m', 'max_drawdown_1y', 'max_drawdown_3y', 'turnover_rate', 'turnover_value', 'discount_ratio', 'stock_ratio'],
        'description': '日度变化数据'
    }
}

def load_backup_data(backup_file):
    """加载备份数据"""
    print(f"📂 加载备份文件: {backup_file}")
    
    if not os.path.exists(backup_file):
        print(f"❌ 备份文件不存在: {backup_file}")
        return None
    
    try:
        with open(backup_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 检查数据格式
        if isinstance(data, list):
            print(f"✅ 备份数据加载成功: {len(data)} 只ETF (列表格式)")
            return data
        elif isinstance(data, dict):
            # 可能是 {code: {...}} 格式
            print(f"✅ 备份数据加载成功: {len(data)} 只ETF (字典格式)")
            # 转换为列表格式
            etf_list = list(data.values())
            return etf_list
        else:
            print(f"❌ 备份数据格式未知: {type(data)}")
            return None
    except Exception as e:
        print(f"❌ 加载备份数据失败: {e}")
        return None

def extract_fields(etf_data, fields):
    """从ETF数据中提取指定字段"""
    result = {}
    for field in fields:
        if field in etf_data and etf_data[field] is not None and etf_data[field] != '':
            result[field] = etf_data[field]
    return result

def migrate_data(backup_data):
    """迁移数据：从备份数据按频率拆分到5个新文件"""
    print(f"\n🔄 开始数据迁移...")
    
    # 初始化新文件数据结构
    new_data = {
        'etf_static.json': [],
        'etf_annual.json': [],
        'etf_quarterly.json': [],
        'etf_monthly.json': [],
        'etf_daily.json': []
    }
    
    # 统计信息
    stats = {
        'total_etfs': len(backup_data),
        'etf_static': 0,
        'etf_annual': 0,
        'etf_quarterly': 0,
        'etf_monthly': 0,
        'etf_daily': 0
    }
    
    # 遍历每只ETF
    for i, etf in enumerate(backup_data):
        code = etf.get('code', f'UNKNOWN_{i}')
        name = etf.get('name', '未知')
        
        # 1. etf_static.json - 长期不变数据
        static_data = extract_fields(etf, FREQUENCY_FILES['etf_static.json']['fields'])
        if len(static_data) > 1:  # 至少有code字段
            new_data['etf_static.json'].append(static_data)
            stats['etf_static'] += 1
        
        # 2. etf_annual.json - 年度变化数据
        annual_data = extract_fields(etf, FREQUENCY_FILES['etf_annual.json']['fields'])
        if len(annual_data) > 1:  # 至少有code字段
            new_data['etf_annual.json'].append(annual_data)
            stats['etf_annual'] += 1
        
        # 3. etf_quarterly.json - 季度变化数据
        quarterly_data = extract_fields(etf, FREQUENCY_FILES['etf_quarterly.json']['fields'])
        if len(quarterly_data) > 1:  # 至少有code字段
            new_data['etf_quarterly.json'].append(quarterly_data)
            stats['etf_quarterly'] += 1
        
        # 4. etf_monthly.json - 月度变化数据
        monthly_data = extract_fields(etf, FREQUENCY_FILES['etf_monthly.json']['fields'])
        if len(monthly_data) > 1:  # 至少有code字段
            new_data['etf_monthly.json'].append(monthly_data)
            stats['etf_monthly'] += 1
        
        # 5. etf_daily.json - 日度变化数据
        daily_data = extract_fields(etf, FREQUENCY_FILES['etf_daily.json']['fields'])
        if len(daily_data) > 1:  # 至少有code字段
            new_data['etf_daily.json'].append(daily_data)
            stats['etf_daily'] += 1
        
        # 进度显示
        if (i + 1) % 100 == 0:
            print(f"  进度: {i + 1}/{len(backup_data)}")
    
    print(f"✅ 数据迁移完成")
    return new_data, stats

def save_new_data(new_data, output_dir='.'):
    """保存新文件结构"""
    print(f"\n💾 保存新文件结构...")
    
    for filename, data in new_data.items():
        filepath = os.path.join(output_dir, filename)
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            file_size = os.path.getsize(filepath) / 1024 / 1024  # MB
            print(f"  ✅ {filename}: {len(data)} 只ETF, {file_size:.2f} MB")
        except Exception as e:
            print(f"  ❌ 保存 {filename} 失败: {e}")
    
    print(f"✅ 所有文件保存完成")

def generate_report(stats, new_data):
    """生成迁移报告"""
    print(f"\n📊 数据迁移报告")
    print(f"=" * 60)
    print(f"总ETF数量: {stats['total_etfs']}")
    print(f"-" * 60)
    
    for filename, file_info in FREQUENCY_FILES.items():
        count = stats[filename.replace('.json', '')]
        data = new_data[filename]
        
        print(f"\n{filename} - {file_info['description']}")
        print(f"  包含字段: {', '.join(file_info['fields'])}")
        print(f"  ETF数量: {count}/{stats['total_etfs']} ({count/stats['total_etfs']*100:.1f}%)")
        
        # 计算字段填充率
        if len(data) > 0:
            sample = data[0]
            filled_fields = [f for f in file_info['fields'] if f in sample and sample[f] is not None and sample[f] != '']
            print(f"  字段填充率(样本): {len(filled_fields)}/{len(file_info['fields'])} ({len(filled_fields)/len(file_info['fields'])*100:.1f}%)")
    
    print(f"\n" + "=" * 60)

def main():
    """主函数"""
    print("🚀 ETF数据迁移工具")
    print("=" * 60)
    
    # 1. 确定备份文件路径
    if len(sys.argv) > 1:
        backup_file = sys.argv[1]
    else:
        backup_file = DEFAULT_BACKUP_FILE
    
    print(f"备份文件: {backup_file}")
    
    # 2. 加载备份数据
    backup_data = load_backup_data(backup_file)
    if backup_data is None:
        return
    
    # 3. 迁移数据
    new_data, stats = migrate_data(backup_data)
    
    # 4. 保存新文件
    save_new_data(new_data)
    
    # 5. 生成报告
    generate_report(stats, new_data)
    
    print(f"\n🎉 数据迁移完成！")
    print(f"下一步: 检查新文件结构，确认数据正确后，可以删除旧文件")

if __name__ == '__main__':
    main()
