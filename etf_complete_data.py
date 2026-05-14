#!/usr/bin/env python3
"""
ETF完整数据获取工具 - 基于ftshare-market-data
一次性获取：实时数据 + 多周期收益率 + 最大回撤
"""

import subprocess
import json
import sys
import time
from pathlib import Path
from typing import List, Dict, Optional
import argparse

class ETFCompleteDataTool:
    """ETF完整数据工具"""
    
    def __init__(self, skill_path: str = None):
        if skill_path is None:
            skill_path = str(Path.home() / ".workbuddy/skills/ftshare-market-data")
        self.skill_path = Path(skill_path)
        self.run_py = self.skill_path / "run.py"
        
        if not self.run_py.exists():
            raise FileNotFoundError(f"找不到run.py: {self.run_py}")
    
    def _run_skill(self, sub_skill: str, *args) -> Dict:
        """运行子skill"""
        cmd = ["/usr/bin/python3", str(self.run_py), sub_skill] + list(args)
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode != 0:
                return {}
            
            output = result.stdout.strip()
            if not output:
                return {}
            
            return json.loads(output)
            
        except:
            return {}
    
    def get_all_etfs(self, page_size: int = 200) -> List[Dict]:
        """获取所有ETF列表"""
        print(f"📊 正在获取所有ETF列表（每页{page_size}只）...", file=sys.stderr)
        
        all_etfs = []
        page_no = 1
        
        while True:
            result = self._run_skill(
                "etf-list-paginated",
                "--page_no", str(page_no),
                "--page_size", str(page_size)
            )
            
            if not result or "etfs" not in result:
                break
            
            etfs = result.get("etfs", [])
            total_pages = result.get("total_pages", 0)
            
            all_etfs.extend(etfs)
            
            print(f"  已获取 {len(all_etfs)}/{result.get('total_size', 0)} 只ETF", file=sys.stderr)
            
            if page_no >= total_pages:
                break
            
            page_no += 1
            time.sleep(0.3)
        
        print(f"✅ 共获取 {len(all_etfs)} 只ETF", file=sys.stderr)
        return all_etfs
    
    def filter_etfs_by_codes(self, all_etfs: List[Dict], etf_codes: List[str]) -> List[Dict]:
        """根据代码列表筛选ETF"""
        code_set = set()
        for code in etf_codes:
            normalized = code.strip().upper()
            code_set.add(normalized)
            if "." in normalized:
                code_set.add(normalized.split(".")[0])
        
        matched_etfs = []
        for etf in all_etfs:
            symbol_id = etf.get("symbol_id", "")
            symkey = etf.get("symkey", "")
            
            if symbol_id in code_set or symkey in code_set:
                matched_etfs.append(etf)
        
        return matched_etfs
    
    def get_etf_ohlcs(self, symbol: str, span: str = "DAY1", limit: int = 250) -> List[Dict]:
        """获取ETF K线数据"""
        result = self._run_skill(
            "etf-ohlcs",
            "--etf", symbol,
            "--span", span,
            "--limit", str(limit)
        )
        
        if not result or "ohlcs" not in result:
            return []
        
        return result["ohlcs"]
    
    def calculate_max_drawdown(self, ohlcs: List[Dict]) -> float:
        """计算最大回撤"""
        if not ohlcs:
            return 0.0
        
        max_drawdown = 0.0
        peak = ohlcs[0]["c"]
        
        for bar in ohlcs:
            close = bar["c"]
            if close > peak:
                peak = close
            
            drawdown = (close - peak) / peak
            if drawdown < max_drawdown:
                max_drawdown = drawdown
        
        return max_drawdown
    
    def enrich_with_drawdown(self, etfs: List[Dict], limit: int = 250) -> List[Dict]:
        """为ETF列表添加最大回撤数据"""
        print(f"📉 正在计算 {len(etfs)} 只ETF的最大回撤...", file=sys.stderr)
        
        for i, etf in enumerate(etfs, 1):
            symkey = etf.get("symkey", "")
            
            if not symkey:
                continue
            
            print(f"  [{i}/{len(etfs)}] {symkey}...", file=sys.stderr)
            
            # 获取K线数据
            ohlcs = self.get_etf_ohlcs(symkey, span="DAY1", limit=limit)
            
            # 计算最大回撤
            max_drawdown = self.calculate_max_drawdown(ohlcs)
            etf["max_drawdown"] = max_drawdown
            
            time.sleep(0.2)  # 避免请求过快
        
        print(f"✅ 最大回撤计算完成", file=sys.stderr)
        return etfs


def main():
    parser = argparse.ArgumentParser(description="ETF完整数据获取工具")
    parser.add_argument("--codes-file", required=True, help="ETF代码文件路径（JSON格式，数组）")
    parser.add_argument("--output", "-o", required=True, help="输出文件路径（JSON格式）")
    parser.add_argument("--page-size", type=int, default=200, help="每页大小")
    parser.add_argument("--limit", type=int, default=250, help="K线数据条数（用于计算最大回撤）")
    
    args = parser.parse_args()
    
    # 读取ETF代码
    with open(args.codes_file, "r", encoding="utf-8") as f:
        etf_codes = json.load(f)
    
    print(f"📋 共 {len(etf_codes)} 只ETF待查询", file=sys.stderr)
    
    # 创建工具实例
    tool = ETFCompleteDataTool()
    
    # 步骤1：获取所有ETF（实时数据 + 多周期收益率）
    start_time = time.time()
    all_etfs = tool.get_all_etfs(args.page_size)
    
    # 步骤2：筛选目标ETF
    matched_etfs = tool.filter_etfs_by_codes(all_etfs, etf_codes)
    print(f"✅ 找到 {len(matched_etfs)}/{len(etf_codes)} 只匹配的ETF", file=sys.stderr)
    
    step1_time = time.time() - start_time
    print(f"⏱️ 步骤1耗时: {step1_time:.1f}秒", file=sys.stderr)
    
    # 步骤3：计算最大回撤
    start_time = time.time()
    enriched_etfs = tool.enrich_with_drawdown(matched_etfs, args.limit)
    
    step2_time = time.time() - start_time
    print(f"⏱️ 步骤2耗时: {step2_time:.1f}秒", file=sys.stderr)
    
    # 保存结果
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(enriched_etfs, f, ensure_ascii=False, indent=2)
    
    total_time = step1_time + step2_time
    print(f"✅ 数据已保存到: {args.output}", file=sys.stderr)
    print(f"⏱️ 总耗时: {total_time:.1f}秒 ({total_time/60:.1f}分钟)", file=sys.stderr)
    
    # 打印统计信息
    print(f"\n📊 数据字段说明:")
    print(f"  实时数据: close, open, high, low, volume, turnover...")
    print(f"  多周期收益率: change_rate_5d/10d/20d/60d/6m/1y/2y/3y/ytd")
    print(f"  最大回撤: max_drawdown")
    print(f"  市值数据: market_cap_total, market_cap_circulating")
    print(f"  交易数据: turnover_rate, amplitude, order_ratio...")


if __name__ == "__main__":
    main()
