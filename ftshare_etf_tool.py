#!/usr/bin/env python3
"""
FTShare ETF数据工具 - 基于ftshare-market-data skill
优化版本：利用etf-list-paginated批量获取，避免逐个查询
"""

import subprocess
import json
import sys
from pathlib import Path
from typing import List, Dict, Optional
import time

class FTShareETFTool:
    """基于ftshare-market-data的ETF数据工具"""
    
    def __init__(self, skill_path: str = None):
        """
        初始化
        
        Args:
            skill_path: ftshare-market-data skill的路径
        """
        if skill_path is None:
            # 默认路径
            skill_path = str(Path.home() / ".workbuddy/skills/ftshare-market-data")
        self.skill_path = Path(skill_path)
        self.run_py = self.skill_path / "run.py"
        
        if not self.run_py.exists():
            raise FileNotFoundError(f"找不到run.py: {self.run_py}")
    
    def _run_skill(self, sub_skill: str, *args) -> Dict:
        """
        运行子skill
        
        Args:
            sub_skill: 子skill名称
            *args: 参数列表
            
        Returns:
            JSON响应字典
        """
        cmd = ["/usr/bin/python3", str(self.run_py), sub_skill] + list(args)
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                print(f"⚠️ 命令执行失败: {' '.join(cmd)}", file=sys.stderr)
                print(f"stderr: {result.stderr}", file=sys.stderr)
                return {}
            
            # 解析JSON输出
            output = result.stdout.strip()
            if not output:
                return {}
            
            return json.loads(output)
            
        except subprocess.TimeoutExpired:
            print(f"⚠️ 命令超时: {' '.join(cmd)}", file=sys.stderr)
            return {}
        except json.JSONDecodeError as e:
            print(f"⚠️ JSON解析失败: {e}", file=sys.stderr)
            print(f"stdout: {result.stdout[:500]}", file=sys.stderr)
            return {}
        except Exception as e:
            print(f"⚠️ 执行失败: {e}", file=sys.stderr)
            return {}
    
    def get_all_etfs(self, page_size: int = 200) -> List[Dict]:
        """
        获取所有ETF列表（使用etf-list-paginated）
        
        Args:
            page_size: 每页大小
            
        Returns:
            ETF列表
        """
        print(f"📊 正在获取所有ETF列表（每页{page_size}只）...")
        
        all_etfs = []
        page_no = 1
        
        while True:
            print(f"  查询第{page_no}页...", file=sys.stderr)
            
            result = self._run_skill(
                "etf-list-paginated",
                "--page_no", str(page_no),
                "--page_size", str(page_size)
            )
            
            if not result or "etfs" not in result:
                print(f"⚠️ 第{page_no}页数据获取失败", file=sys.stderr)
                break
            
            etfs = result.get("etfs", [])
            total_pages = result.get("total_pages", 0)
            
            all_etfs.extend(etfs)
            
            print(f"  已获取 {len(all_etfs)}/{result.get('total_size', 0)} 只ETF", file=sys.stderr)
            
            # 检查是否还有下一页
            if page_no >= total_pages:
                break
            
            page_no += 1
            time.sleep(0.5)  # 避免请求过快
        
        print(f"✅ 共获取 {len(all_etfs)} 只ETF")
        return all_etfs
    
    def get_etf_by_codes(self, etf_codes: List[str]) -> List[Dict]:
        """
        根据ETF代码列表获取ETF数据
        
        Args:
            etf_codes: ETF代码列表（如 ["510300", "510050"]）
            
        Returns:
            匹配的ETF数据列表
        """
        print(f"📊 正在查询 {len(etf_codes)} 只ETF数据...")
        
        # 获取所有ETF
        all_etfs = self.get_all_etfs()
        
        # 构建代码集合（支持模糊匹配）
        code_set = set()
        for code in etf_codes:
            # 标准化代码：去除前缀后缀
            normalized = code.strip().upper()
            code_set.add(normalized)
            # 也添加不带扩展名的版本
            if "." in normalized:
                code_set.add(normalized.split(".")[0])
        
        # 筛选匹配的ETF
        matched_etfs = []
        for etf in all_etfs:
            symbol_id = etf.get("symbol_id", "")
            symkey = etf.get("symkey", "")
            
            # 检查是否匹配
            if symbol_id in code_set or symkey in code_set or symbol_id in code_set or symkey.split(".")[0] in code_set:
                matched_etfs.append(etf)
        
        print(f"✅ 找到 {len(matched_etfs)}/{len(etf_codes)} 只匹配的ETF")
        return matched_etfs
    
    def get_etf_detail(self, symbol: str) -> Dict:
        """
        获取单只ETF详情（使用etf-detail）
        
        Args:
            symbol: ETF代码（如 510300.XSHG）
            
        Returns:
            ETF详情
        """
        return self._run_skill("etf-detail", "--etf", symbol)
    
    def get_etf_ohlcs(self, symbol: str, span: str = "DAY1", limit: int = 100) -> Dict:
        """
        获取ETF K线数据（使用etf-ohlcs）
        
        Args:
            symbol: ETF代码（如 510300.XSHG）
            span: K线周期（DAY1/WEEK1/MONTH1/YEAR1）
            limit: 数据条数
            
        Returns:
            K线数据
        """
        return self._run_skill(
            "etf-ohlcs",
            "--etf", symbol,
            "--span", span,
            "--limit", str(limit)
        )
    
    def calculate_max_drawdown(self, symbol: str, days: int = 250) -> float:
        """
        计算最大回撤
        
        Args:
            symbol: ETF代码
            days: 计算天数
            
        Returns:
            最大回撤（负数，如 -0.15 表示 -15%）
        """
        # 获取K线数据
        ohlcs_data = self.get_etf_ohlcs(symbol, span="DAY1", limit=days)
        
        if not ohlcs_data or "ohlcs" not in ohlcs_data:
            print(f"⚠️ 无法获取 {symbol} 的K线数据", file=sys.stderr)
            return 0.0
        
        ohlcs = ohlcs_data["ohlcs"]
        if not ohlcs:
            return 0.0
        
        # 计算最大回撤
        max_drawdown = 0.0
        peak = ohlcs[0]["c"]  # 假设第一个是最高价
        
        for bar in ohlcs:
            close = bar["c"]
            if close > peak:
                peak = close
            
            drawdown = (close - peak) / peak
            if drawdown < max_drawdown:
                max_drawdown = drawdown
        
        return max_drawdown


def main():
    """命令行接口"""
    import argparse
    
    parser = argparse.ArgumentParser(description="FTShare ETF数据工具")
    parser.add_argument("--skill-path", default=None, help="ftshare-market-data skill路径")
    
    subparsers = parser.add_subparsers(dest="command", help="子命令")
    
    # list - 获取所有ETF
    list_parser = subparsers.add_parser("list", help="获取所有ETF列表")
    list_parser.add_argument("--page-size", type=int, default=200, help="每页大小")
    list_parser.add_argument("--output", "-o", help="输出文件路径（JSON格式）")
    
    # batch - 批量查询ETF
    batch_parser = subparsers.add_parser("batch", help="批量查询ETF")
    batch_parser.add_argument("--codes", nargs="+", required=True, help="ETF代码列表")
    batch_parser.add_argument("--output", "-o", help="输出文件路径（JSON格式）")
    
    # detail - 查询单只ETF详情
    detail_parser = subparsers.add_parser("detail", help="查询单只ETF详情")
    detail_parser.add_argument("--symbol", required=True, help="ETF代码（如 510300.XSHG）")
    
    # ohlcs - 查询K线数据
    ohlcs_parser = subparsers.add_parser("ohlcs", help="查询K线数据")
    ohlcs_parser.add_argument("--symbol", required=True, help="ETF代码")
    ohlcs_parser.add_argument("--span", default="DAY1", help="K线周期（DAY1/WEEK1/MONTH1/YEAR1）")
    ohlcs_parser.add_argument("--limit", type=int, default=100, help="数据条数")
    
    # drawdown - 计算最大回撤
    drawdown_parser = subparsers.add_parser("drawdown", help="计算最大回撤")
    drawdown_parser.add_argument("--symbol", required=True, help="ETF代码")
    drawdown_parser.add_argument("--days", type=int, default=250, help="计算天数")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # 创建工具实例
    tool = FTShareETFTool(args.skill_path)
    
    # 执行命令
    if args.command == "list":
        etfs = tool.get_all_etfs(args.page_size)
        
        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                json.dump(etfs, f, ensure_ascii=False, indent=2)
            print(f"✅ 数据已保存到: {args.output}")
        else:
            print(json.dumps(etfs[:10], ensure_ascii=False, indent=2))
            print(f"... 共 {len(etfs)} 只ETF")
    
    elif args.command == "batch":
        etfs = tool.get_etf_by_codes(args.codes)
        
        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                json.dump(etfs, f, ensure_ascii=False, indent=2)
            print(f"✅ 数据已保存到: {args.output}")
        else:
            print(json.dumps(etfs, ensure_ascii=False, indent=2))
    
    elif args.command == "detail":
        detail = tool.get_etf_detail(args.symbol)
        print(json.dumps(detail, ensure_ascii=False, indent=2))
    
    elif args.command == "ohlcs":
        ohlcs = tool.get_etf_ohlcs(args.symbol, args.span, args.limit)
        print(json.dumps(ohlcs, ensure_ascii=False, indent=2))
    
    elif args.command == "drawdown":
        drawdown = tool.calculate_max_drawdown(args.symbol, args.days)
        print(f"最大回撤: {drawdown:.2%}")


if __name__ == "__main__":
    main()
