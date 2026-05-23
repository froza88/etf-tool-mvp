"""
WeStock 数据源 Fetcher - 封装 WeStock CLI 调用，内置查询即存储逻辑

核心原则：
1. 查询前先查本地缓存
2. 缓存命中且有效 → 直接返回
3. 缓存未命中 → 调用 WeStock CLI → 立即存储到本地缓存
4. 外部 API 失效时，本地缓存仍可提供服务
"""

import json
import os
import subprocess
from datetime import datetime, timedelta
from pathlib import Path

# 项目根目录
ROOT = Path(__file__).parent.parent

# WeStock CLI 路径
WESTOCK_CLI = Path.home() / ".workbuddy" / "plugins" / "marketplaces" / "cb_teams_marketplace" / "plugins" / "finance-data" / "skills" / "westock-data" / "scripts" / "index.js"

# 缓存目录
CACHE_DIR = ROOT / "data" / "cache" / "westock"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# 缓存有效期（天）
CACHE_VALID_DAYS = 1


class WeStockFetcher:
    """
    WeStock CLI 数据获取器（查询即存储）
    
    用法：
        fetcher = WeStockFetcher()
        data = fetcher.fetch_etf_info("510300")
    """
    
    def __init__(self, cache_dir=None, cache_days=CACHE_VALID_DAYS):
        self.cache_dir = Path(cache_dir) if cache_dir else CACHE_DIR
        self.cache_days = cache_days
    
    def fetch_etf_info(self, code: str, force_refresh=False) -> dict:
        """
        获取 ETF 基础信息（费率/规模/净申购等）
        
        查询即存储流程：
        1. 检查本地缓存
        2. 缓存有效且非强制刷新 → 返回缓存
        3. 缓存无效或强制刷新 → 调用 WeStock CLI
        4. 调用成功 → 立即存储到本地缓存
        5. 返回数据
        
        Args:
            code: ETF 代码（如 "510300"）
            force_refresh: 是否强制重新调用 API（忽略缓存）
        
        Returns:
            dict: 获取到的数据，或 None（如果失败）
        """
        cache_file = self.cache_dir / f"{code}.json"
        
        # 1. 检查本地缓存
        if not force_refresh and cache_file.exists():
            cache = self._load_cache(cache_file)
            if cache and self._is_cache_valid(cache):
                print(f"  ✓ 缓存有效，使用缓存数据: {cache_file.name}")
                return cache['data']
        
        # 2. 缓存无效或强制刷新，调用 WeStock CLI
        print(f"  → 调用 WeStock CLI (etf {code})...")
        
        markdown_output = self._call_westock_cli(code)
        
        if not markdown_output:
            # API 调用失败，尝试返回过期缓存（如果有）
            if cache_file.exists():
                cache = self._load_cache(cache_file)
                if cache:
                    print(f"  ⚠️  WeStock CLI 失败，使用过期缓存: {cache_file.name}")
                    return cache['data']
            return None
        
        # 3. 解析 Markdown 数据
        parsed_data = self._parse_etf_markdown(markdown_output)
        
        if not parsed_data:
            print(f"  ✗ 解析 WeStock 数据失败")
            # 尝试返回过期缓存
            if cache_file.exists():
                cache = self._load_cache(cache_file)
                if cache:
                    print(f"  ⚠️  解析失败，使用过期缓存: {cache_file.name}")
                    return cache['data']
            return None
        
        # 4. 立即存储到本地缓存（查询即存储）
        self._save_cache(cache_file, parsed_data)
        
        print(f"  ✓ WeStock CLI 成功，获取到 {len(parsed_data)} 个字段，已缓存")
        return parsed_data
    
    def _call_westock_cli(self, code: str) -> str:
        """
        调用 WeStock CLI
        
        Args:
            code: ETF 代码（如 "510300" 或 "sh510300"）
        
        Returns:
            str: WeStock CLI 返回的 Markdown 输出，或 None（如果失败）
        """
        # 确保代码有市场前缀（默认 sh）
        if not code.startswith(('sh', 'sz', 'bj', 'hk', 'us')):
            code = f"sh{code}"
        
        cmd = [
            "node",
            str(WESTOCK_CLI),
            "etf",
            code
        ]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                print(f"  ✗ WeStock CLI 调用失败 (exit code {result.returncode})")
                print(f"  stderr: {result.stderr[:200]}")
                return None
            
            return result.stdout
            
        except subprocess.TimeoutExpired:
            print(f"  ✗ WeStock CLI 调用超时")
            return None
        except Exception as e:
            print(f"  ✗ WeStock CLI 调用异常: {e}")
            return None
    
    def _parse_etf_markdown(self, markdown: str) -> dict:
        """
        解析 WeStock etf 命令返回的 Markdown 表格
        
        WeStock 输出格式示例：
        | code | name | ... | managementFee | custodyFee | serviceFee | disc | size | shares | sharesChg | sharesChgRatio | ...
        | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | ...
        | sh510300 | 华泰300ETF | ... | 0.5 | 0.1 | 0.25 | -0.02 | 1000000000 | 500000000 | 1000000 | 0.2 | ...
        
        Args:
            markdown: WeStock CLI 返回的 Markdown 文本
        
        Returns:
            dict: 解析后的数据，映射到我们的字段
        """
        # 查找 Markdown 表格
        lines = markdown.split('\n')
        
        # 找到表头行（第一个以 | 开头的行）
        header_line_idx = -1
        for i, line in enumerate(lines):
            if line.strip().startswith('|'):
                header_line_idx = i
                break
        
        if header_line_idx == -1:
            print(f"  ✗ 未找到 Markdown 表格")
            return None
        
        # 找到分隔行（下一个以 | 开头且包含 --- 的行）
        separator_line_idx = -1
        for i in range(header_line_idx + 1, min(header_line_idx + 5, len(lines))):
            if lines[i].strip().startswith('|') and '---' in lines[i]:
                separator_line_idx = i
                break
        
        if separator_line_idx == -1:
            print(f"  ✗ 未找到表格分隔行")
            return None
        
        # 找到第一个数据行（分隔行后的第一个以 | 开头的行）
        data_line_idx = -1
        for i in range(separator_line_idx + 1, len(lines)):
            if lines[i].strip().startswith('|'):
                data_line_idx = i
                break
        
        if data_line_idx == -1:
            print(f"  ✗ 未找到数据行")
            return None
        
        # 解析表头
        header = [col.strip() for col in lines[header_line_idx].split('|')[1:-1]]
        
        # 解析数据
        values = [val.strip() for val in lines[data_line_idx].split('|')[1:-1]]
        
        if len(values) != len(header):
            print(f"  ✗ 数据列数与表头列数不匹配: {len(values)} vs {len(header)}")
            return None
        
        # 构建数据字典
        data = {}
        for i, col in enumerate(header):
            if i >= len(values):
                continue
            value_str = values[i]
            # 尝试转换为数字
            try:
                if '.' in value_str:
                    parsed_value = float(value_str)
                else:
                    parsed_value = int(value_str)
            except (ValueError, TypeError):
                parsed_value = value_str if value_str else None
            data[col] = parsed_value
        
        # 字段映射：WeStock 字段 -> 我们的字段
        field_mapping = {
            'managementFee': 'fee_rate_management',
            'custodyFee': 'fee_rate_custody',
            'serviceFee': 'fee_rate_service',
            'disc': 'premium_discount',
            'size': 'scale',
            'shares': 'shares',
            'sharesChg': 'net_inflow_shares',
            'sharesChgRatio': 'net_inflow_ratio'
        }
        
        result = {}
        for ws_field, our_field in field_mapping.items():
            if ws_field in data:
                result[our_field] = data[ws_field]
        
        # 计算总费率（管理费率 + 托管费率 + 销售服务费率）
        fee_rate_management = result.get('fee_rate_management', 0) or 0
        fee_rate_custody = result.get('fee_rate_custody', 0) or 0
        fee_rate_service = result.get('fee_rate_service', 0) or 0
        result['fee_rate'] = fee_rate_management + fee_rate_custody + fee_rate_service
        
        # 计算净申购金额（份额 × 净值，需要估算净值，这里先用份额代替）
        # 注意：实际应该用 ETF 的净值来计算，这里暂时用份额
        result['net_inflow_5d'] = result.get('net_inflow_shares', 0) or 0
        
        return result
    
    def _load_cache(self, cache_file: Path) -> dict:
        """加载缓存文件"""
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return None
    
    def _save_cache(self, cache_file: Path, data: dict):
        """保存缓存文件（查询即存储）"""
        cache_item = {
            'code': cache_file.stem,
            'source': 'westock',
            'endpoint': 'etf',
            'fetched_at': datetime.now().isoformat(),
            'data': data,
            'ttl_days': self.cache_days
        }
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(cache_item, f, ensure_ascii=False, indent=2)
    
    def _is_cache_valid(self, cache_item: dict) -> bool:
        """检查缓存是否有效（未过期）"""
        fetched_at_str = cache_item.get('fetched_at')
        if not fetched_at_str:
            return False
        
        try:
            fetched_at = datetime.fromisoformat(fetched_at_str)
            return datetime.now() - fetched_at < timedelta(days=self.cache_days)
        except:
            return False


def update_etf_with_westock(etf_list: list, dry_run=False) -> tuple:
    """
    用 WeStock 数据更新 ETF 列表
    
    Args:
        etf_list: ETF 列表（每个元素是 dict，包含 code, name 等字段）
        dry_run: 是否只模拟，不实际修改
    
    Returns:
        tuple: (updated_count, api_call_count)
    """
    fetcher = WeStockFetcher()
    updated_count = 0
    api_call_count = 0
    
    for i, etf in enumerate(etf_list):
        code = str(etf['code'])
        
        print(f"\n[{i+1}/{len(etf_list)}] {code} | {etf.get('name', '')}")
        
        # 从 WeStock 获取数据（或缓存）
        westock_data = fetcher.fetch_etf_info(code, force_refresh=False)
        
        if not westock_data:
            print(f"  ✗ 获取失败，跳过")
            continue
        
        # 检查是 API 调用还是缓存命中
        cache_file = CACHE_DIR / f"{code}.json"
        if cache_file.exists():
            mtime = datetime.fromtimestamp(cache_file.stat().st_mtime)
            if datetime.now() - mtime < timedelta(seconds=10):  # 刚创建的缓存 = API 调用
                api_call_count += 1
        
        # 更新 ETF 数据（只填充缺失字段）
        updated_fields = []
        for field, value in westock_data.items():
            if field.startswith('_'):
                continue  # 跳过内部字段
            
            if field not in etf or etf[field] is None or etf[field] == '':
                if not dry_run:
                    etf[field] = value
                updated_fields.append(field)
        
        if updated_fields:
            print(f"  ✓ 更新字段: {', '.join(updated_fields)}")
            updated_count += 1
        else:
            print(f"  - 无需更新（字段已存在）")
    
    print(f"\n=== 更新完成 ===")
    print(f"处理 ETF 数量: {len(etf_list)}")
    print(f"更新 ETF 数量: {updated_count}")
    print(f"API 调用次数: {api_call_count}")
    
    return updated_count, api_call_count


if __name__ == '__main__':
    # 命令行测试入口
    import sys
    sys.path.insert(0, str(ROOT))
    
    import argparse
    parser = argparse.ArgumentParser(description='WeStock Fetcher 测试')
    parser.add_argument('--code', type=str, help='ETF 代码')
    parser.add_argument('--force', action='store_true', help='强制刷新（忽略缓存）')
    args = parser.parse_args()
    
    if not args.code:
        print("请指定 --code")
        sys.exit(1)
    
    fetcher = WeStockFetcher()
    data = fetcher.fetch_etf_info(args.code, force_refresh=args.force)
    
    if data:
        print("\n获取到的数据:")
        for k, v in data.items():
            print(f"  {k}: {v}")
    else:
        print("\n获取失败")
