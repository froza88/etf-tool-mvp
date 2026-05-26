#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
手动更新 ETF 规模数据脚本
从 AKShare 获取最新规模数据，更新 etf_standard_data.json
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).parent
STANDARD_FILE = ROOT / "etf_standard_data.json"

def log(msg):
    print(f"[{__import__('datetime').datetime.now().strftime('%H:%M:%S')}] {msg}")

def load_standard():
    """加载标准化数据"""
    with open(STANDARD_FILE, encoding="utf-8") as f:
        data = json.load(f)
    # 处理两种格式：list 或 {"etfs": []}
    if isinstance(data, list):
        return data
    elif isinstance(data, dict) and "etfs" in data:
        return data["etfs"]
    else:
        return []

def save_standard(etfs):
    """保存标准化数据"""
    # 保持原格式
    with open(STANDARD_FILE, encoding="utf-8") as f:
        original = json.load(f)
    
    if isinstance(original, list):
        with open(STANDARD_FILE, "w", encoding="utf-8") as f:
            json.dump(etfs, f, ensure_ascii=False, indent=2)
    else:
        original["etfs"] = etfs
        with open(STANDARD_FILE, "w", encoding="utf-8") as f:
            json.dump(original, f, ensure_ascii=False, indent=2)
    
    log(f"保存完成: {len(etfs)} 只 ETF")

def fetch_scale_from_akshare():
    """从 AKShare 获取规模数据"""
    try:
        import warnings
        warnings.filterwarnings("ignore")
        import akshare as ak
        
        log("正在从 AKShare 获取 ETF 实时行情...")
        df = ak.fund_etf_spot_em()
        log(f"AKShare 返回 {len(df)} 只 ETF 行情")
        
        # 检查是否有 '总市值' 或 '流通市值' 字段
        log(f"可用字段: {list(df.columns)}")
        
        # 构建 code → 规模映射
        scale_map = {}
        for _, row in df.iterrows():
            try:
                code = str(row['代码']).strip()
                # 尝试获取规模相关字段
                scale = None
                if '总市值' in df.columns:
                    scale = float(row['总市值']) if row['总市值'] else None
                elif '流通市值' in df.columns:
                    scale = float(row['流通市值']) if row['流通市值'] else None
                elif '规模' in df.columns:
                    scale = float(row['规模']) if row['规模'] else None
                
                if scale is not None:
                    # 转换为亿元
                    scale_map[code] = round(scale / 1e8, 2)
            except Exception as e:
                pass
        
        log(f"成功获取 {len(scale_map)} 只 ETF 的规模数据")
        return scale_map
        
    except Exception as e:
        log(f"AKShare 获取失败: {e}")
        return {}

def main():
    log("=" * 50)
    log("开始手动更新 ETF 规模数据")
    log("=" * 50)
    
    # 1. 加载现有数据
    etfs = load_standard()
    log(f"加载现有数据: {len(etfs)} 只 ETF")
    
    # 2. 从 AKShare 获取最新规模
    scale_map = fetch_scale_from_akshare()
    
    if not scale_map:
        log("⚠️ 未获取到规模数据，尝试从 Wind 获取...")
        # TODO: 这里可以添加 Wind API 调用
        log("⚠️ Wind API 调用未实现，跳过")
        return
    
    # 3. 更新规模数据
    updated = 0
    for etf in etfs:
        code = etf.get('code', '')
        if code in scale_map:
            old_scale = etf.get('scale', 0)
            new_scale = scale_map[code]
            etf['scale'] = new_scale
            updated += 1
            if updated <= 5:  # 只打印前5个
                log(f"  {code}: {old_scale} → {new_scale} 亿")
    
    log(f"更新完成: {updated}/{len(etfs)} 只 ETF")
    
    # 4. 保存
    save_standard(etfs)
    
    log("=" * 50)
    log("更新完成")
    log("=" * 50)

if __name__ == "__main__":
    main()
