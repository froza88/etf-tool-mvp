"""
Wind 数据源 Fetcher - 封装 Wind API 调用，内置查询即存储逻辑

核心原则：
1. 查询前先查本地缓存
2. 缓存命中且有效 → 直接返回
3. 缓存未命中 → 调用 Wind API（获取完整数据） → 立即存储到本地缓存
4. 外部 API 失效时，本地缓存仍可提供服务
5. 每次调用都获取并存储完整的 Wind 原始数据（所有可用字段）
"""

import json
import os
import shutil
import subprocess
import time
from datetime import datetime, timedelta
from pathlib import Path

# 检测 node 可执行文件路径（解决 Mac 上 subprocess 找不到 node 的问题）
# 按优先级检测：1) PATH 中的 node  2) 常见安装路径  3) WorkBuddy 管理的 node
_CANDIDATE_NODE_PATHS = [
    shutil.which('node'),
    '/usr/local/bin/node',
    '/opt/homebrew/bin/node',
    str(Path.home() / '.nvm/versions/node'),  # nvm 默认路径（需追加版本）
    '/Users/apangduo/.workbuddy/binaries/node/versions/22.12.0/bin/node',
    '/Users/apangduo/.workbuddy/binaries/node/versions/22.22.2/bin/node',
]
NODE_PATH = next((p for p in _CANDIDATE_NODE_PATHS if p and Path(p).exists()), 'node')

# 项目根目录
ROOT = Path(__file__).parent.parent

# Wind CLI 路径
WIND_CLI = Path.home() / ".agents" / "skills" / "wind-mcp-skill" / "scripts" / "cli.mjs"

# 缓存目录
CACHE_DIR = ROOT / "data" / "cache" / "wind"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# 缓存有效期（天）
CACHE_VALID_DAYS = 7

# Wind API 单次调用成本（积分）
WIND_COST_PER_CALL = 6.67  # 40积分 / 6次 = 6.67积分/次


class WindFetcher:
    """
    Wind API 数据获取器（查询即存储）
    
    用法：
        fetcher = WindFetcher()
        data = fetcher.fetch_etf_info("511670", "华宝港股通恒生中国香港上市企业100ETF")
    """
    
    def __init__(self, cache_dir=None, cache_days=CACHE_VALID_DAYS):
        self.cache_dir = Path(cache_dir) if cache_dir else CACHE_DIR
        self.cache_days = cache_days
    
    def fetch_etf_info(self, code: str, name: str, force_refresh=False) -> dict:
        """
        获取 ETF 基础信息（基金管理人/成立日/费率/基准等）
        
        查询即存储流程：
        1. 检查本地缓存
        2. 缓存有效且非强制刷新 → 返回缓存
        3. 缓存无效或强制刷新 → 调用 Wind API（获取完整数据）
        4. 调用成功 → 立即存储到本地缓存（原始数据+解析数据）
        5. 返回解析后的数据
        
        Args:
            code: ETF 代码（如 "511670"）
            name: ETF 名称
            force_refresh: 是否强制重新调用 API（忽略缓存）
        
        Returns:
            dict: 获取到的数据（解析后的），或 None（如果失败）
        """
        cache_file = self.cache_dir / f"{code}.json"
        
        # 1. 检查本地缓存
        if not force_refresh and cache_file.exists():
            cache = self._load_cache(cache_file)
            if cache and self._is_cache_valid(cache):
                print(f"  ✓ 缓存有效，使用缓存数据: {cache_file.name}")
                return cache['data']
        
        # 2. 缓存无效或强制刷新，调用 Wind API（获取完整原始数据）
        print(f"  → 调用 Wind API (get_fund_info)...")
        
        wind_response = self._call_wind_api(code, name)  # 返回完整原始数据
        
        if not wind_response:
            # API 调用失败，尝试返回过期缓存（如果有）
            if cache_file.exists():
                cache = self._load_cache(cache_file)
                if cache:
                    print(f"  ⚠️ Wind API 失败，使用过期缓存: {cache_file.name}")
                    return cache['data']
            return None
        
        # 3. 解析 Wind 数据（从完整原始数据中提取所有字段）
        parsed_data = self._parse_wind_fund_info(wind_response)
        
        # 4. 立即存储到本地缓存（查询即存储）—— 同时保存原始数据和解析数据
        self._save_cache(cache_file, wind_response, parsed_data)
        
        print(f"  ✓ Wind API 成功，获取到 {len(parsed_data)} 个字段，已缓存（含原始数据）")
        return parsed_data
    
    def _call_wind_api(self, code: str, name: str) -> dict:
        """
        调用 Wind API，返回完整原始数据
        
        Args:
            code: ETF 代码
            name: ETF 名称
        
        Returns:
            dict: Wind API 返回的完整原始数据（含 data/columns/rows），或 None（如果失败）
        """
        # 改进问题：要求返回所有可获取的字段
        question = f"{code}{name}基金，请提供完整档案信息，包括：基本信息（基金管理人、基金托管人、基金成立日、上市日期、投资类型）、费率信息（管理费率、托管费率、申购费率、赎回费率）、业绩信息（业绩比较基准、基金经理、基金规模、单位净值）、风险指标（波动率、夏普比率、最大回撤、跟踪误差）等所有可获取的字段"
        
        cmd = [
            NODE_PATH,
            str(WIND_CLI),
            "call",
            "fund_data",
            "get_fund_info",
            json.dumps({"question": question, "lang": "中文"})
        ]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
                cwd=str(WIND_CLI.parent)
            )
            
            if result.returncode != 0:
                print(f"  ✗ Wind API 调用失败 (exit code {result.returncode})")
                print(f"  stderr: {result.stderr[:200]}")
                return None
            
            # 解析返回数据，返回完整原始数据（不只提取rows）
            output = json.loads(result.stdout)
            text = output['content'][0]['text']
            inner_data = json.loads(text)
            
            # 验证数据结构
            if 'data' not in inner_data or 'data' not in inner_data['data']:
                print(f"  ✗ Wind API 返回数据结构异常")
                return None
            
            columns = inner_data['data']['data'][0]['columns']
            rows = inner_data['data']['data'][0]['rows']
            
            if not rows:
                print(f"  ✗ Wind API 返回空数据")
                return None
            
            print(f"  ✓ Wind API 返回 {len(columns)} 个字段（原始数据已获取）")
            return inner_data  # 返回完整原始数据
            
        except subprocess.TimeoutExpired:
            print(f"  ✗ Wind API 调用超时")
            return None
        except Exception as e:
            print(f"  ✗ Wind API 调用异常: {e}")
            return None
    
    def _parse_wind_fund_info(self, wind_response: dict) -> dict:
        """
        解析 Wind get_fund_info 返回的原始数据，提取所有字段
        
        从 wind_response['data']['data'][0] 中提取 columns 和 rows，
        动态解析所有字段（不硬编码映射关系）
        
        Wind 字段名保持原样，同时添加映射到我们的标准字段名
        
        Args:
            wind_response: Wind API 返回的原始数据（inner_data）
        
        Returns:
            dict: 解析后的数据（包含所有 Wind 字段 + 标准字段映射）
        """
        try:
            columns = wind_response['data']['data'][0]['columns']
            rows = wind_response['data']['data'][0]['rows']
            
            if not rows:
                return {}
            
            # 提取第一行数据（所有字段）
            row = rows[0]
            result = {}
            
            # 动态解析所有字段（保持 Wind 原始字段名）
            for i, col in enumerate(columns):
                wind_field_name = col['name']
                value = row[i]
                result[wind_field_name] = value
            
            # 同时添加到标准字段的映射（方便外部使用）
            # Wind字段名 -> 标准字段名 的映射表
            standard_mapping = {
                'Wind代码': 'wind_code',
                '证券简称': 'short_name',
                '收盘价': 'close_price',
                '交易时间': 'trade_time',
                '交易币种': 'currency',
                '基金成立日': 'issue_date',
                '基金管理人': 'issuer',
                '基金托管人': 'custodian',
                '现任基金经理姓名': 'fund_manager',
                '上市基金规模_WIND计算': 'wind_scale',
                '投资类型_二级分类': 'invest_type',
                '业绩比较基准': 'benchmark',
                '场内流通份额': 'circulation_shares',
                '上市日期': 'listing_date',
                '单位净值': 'nav',
                '单位净值币种': 'nav_currency',
                '最新单位净值': 'latest_nav',
                '净资产收益率': 'roe',
                '管理费率': 'management_fee_rate',
                '托管费率': 'custody_fee_rate',
                '申购费率': 'subscription_fee_rate',
                '赎回费率': 'redemption_fee_rate',
            }
            
            for wind_field, standard_field in standard_mapping.items():
                if wind_field in result:
                    value = result[wind_field]
                    # 处理费率（去掉 % 符号，转为 float）
                    if standard_field in ['management_fee_rate', 'custody_fee_rate', 'subscription_fee_rate', 'redemption_fee_rate']:
                        if isinstance(value, str):
                            value = value.replace('%', '').strip()
                            try:
                                value = float(value)
                            except:
                                value = None
                    result[standard_field] = value
            
            return result
            
        except Exception as e:
            print(f"  ✗ 解析 Wind 数据异常: {e}")
            return {}
    
    def _load_cache(self, cache_file: Path) -> dict:
        """加载缓存文件（兼容新旧格式）"""
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return None
    
    def _save_cache(self, cache_file: Path, wind_response: dict, parsed_data: dict):
        """保存缓存文件（查询即存储）—— 同时保存原始数据和解析数据"""
        cache_item = {
            'code': cache_file.stem,
            'source': 'wind',
            'endpoint': 'get_fund_info',
            'fetched_at': datetime.now().isoformat(),
            'raw': wind_response,  # 完整原始数据
            'data': parsed_data,    # 解析后的数据（所有字段）
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


def update_etf_with_wind(etf_list: list, dry_run=False) -> tuple:
    """
    用 Wind 数据更新 ETF 列表
    
    Args:
        etf_list: ETF 列表（每个元素是 dict，包含 code, name 等字段）
        dry_run: 是否只模拟，不实际修改
    
    Returns:
        tuple: (updated_count, api_call_count)
    """
    fetcher = WindFetcher()
    updated_count = 0
    api_call_count = 0
    
    for i, etf in enumerate(etf_list):
        code = str(etf['code'])
        name = etf.get('name', '')
        
        print(f"\n[{i+1}/{len(etf_list)}] {code} | {name}")
        
        # 从 Wind 获取数据（或缓存）
        wind_data = fetcher.fetch_etf_info(code, name, force_refresh=False)
        
        if not wind_data:
            print(f"  ✗ 获取失败，跳过")
            continue
        
        # 检查是 API 调用还是缓存命中
        # （通过检查缓存文件的最近修改时间来判断）
        cache_file = CACHE_DIR / f"{code}.json"
        if cache_file.exists():
            mtime = datetime.fromtimestamp(cache_file.stat().st_mtime)
            if datetime.now() - mtime < timedelta(seconds=10):  # 刚创建的缓存 = API 调用
                api_call_count += 1
        
        # 更新 ETF 数据（只填充缺失字段）
        updated_fields = []
        for field, value in wind_data.items():
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
        
        # 避免 QPS 限制，等待 1 秒
        if api_call_count > 0 and api_call_count % 10 == 0:
            print(f"  (已调用 {api_call_count} 次 API，等待 1 秒...)")
            time.sleep(1)
    
    print(f"\n=== 更新完成 ===")
    print(f"处理 ETF 数量: {len(etf_list)}")
    print(f"更新 ETF 数量: {updated_count}")
    print(f"API 调用次数: {api_call_count}")
    print(f"预估消耗积分: {api_call_count * WIND_COST_PER_CALL:.0f}")
    
    return updated_count, api_call_count


if __name__ == '__main__':
    # 命令行测试入口
    import sys
    sys.path.insert(0, str(ROOT))
    
    import argparse
    parser = argparse.ArgumentParser(description='Wind Fetcher 测试')
    parser.add_argument('--code', type=str, help='ETF 代码')
    parser.add_argument('--name', type=str, default='', help='ETF 名称')
    parser.add_argument('--force', action='store_true', help='强制刷新（忽略缓存）')
    args = parser.parse_args()
    
    if not args.code:
        print("请指定 --code")
        sys.exit(1)
    
    fetcher = WindFetcher()
    data = fetcher.fetch_etf_info(args.code, args.name, force_refresh=args.force)
    
    if data:
        print("\n获取到的数据:")
        for k, v in data.items():
            print(f"  {k}: {v}")
    else:
        print("\n获取失败")
