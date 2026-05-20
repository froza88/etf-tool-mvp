#!/usr/bin/env python3
"""
分析盈米API返回的字段名，找出正确的sharpe_ratio映射
用法：python3 analyze_yingmi_fields.py
"""
import os, json

ROOT = os.path.dirname(os.path.abspath(__file__))
CACHE_DIR = os.path.join(ROOT, ".yingmi_cache")

def main():
    if not os.path.exists(CACHE_DIR):
        print("缓存目录不存在，请先运行 enrich_yingmi.py")
        return
    
    cache_files = [f for f in os.listdir(CACHE_DIR) if f.endswith(".json")]
    print(f"缓存文件数: {len(cache_files)}\n")
    
    # 收集所有字段名
    all_fields_1y = set()
    all_fields_3y = set()
    
    sample = None
    
    for cf in cache_files[:50]:  # 分析前50个样本
        with open(os.path.join(CACHE_DIR, cf), encoding="utf-8") as f:
            fund = json.load(f)
        
        da = fund.get("data", {})
        metrics = da.get("metricsAnalyzes", [])
        
        for pm in metrics:
            period = pm.get("stageType", "")
            if not pm.get("isValid", False):
                continue
            
            fields = [mm.get("title", "") for mm in pm.get("metrics", []) if mm.get("title")]
            
            if period == "oneYear":
                all_fields_1y.update(fields)
            elif period == "threeYear":
                all_fields_3y.update(fields)
        
        if sample is None:
            sample = fund
    
    print("=" * 60)
    print("【1年期可用字段】")
    print("=" * 60)
    for f in sorted(all_fields_1y):
        print(f"  - {f}")
    
    print("\n" + "=" * 60)
    print("【3年期可用字段】")
    print("=" * 60)
    for f in sorted(all_fields_3y):
        print(f"  - {f}")
    
    # 打印一个完整样本
    if sample:
        print("\n" + "=" * 60)
        print("【完整样本】")
        print("=" * 60)
        code = sample.get("fundCode", "UNKNOWN")
        print(f"ETF代码: {code}")
        da = sample.get("data", {})
        metrics = da.get("metricsAnalyzes", [])
        for pm in metrics:
            period = pm.get("stageType", "")
            print(f"\n  [{period}] isValid={pm.get('isValid', False)}")
            for mm in pm.get("metrics", []):
                title = mm.get("title", "")
                vt = mm.get("metricsValueText", "")
                desc = mm.get("metricsDesc", "")
                print(f"    {title}: {vt} ({desc})")

if __name__ == "__main__":
    main()
