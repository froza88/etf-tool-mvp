#!/usr/bin/env python3
"""
测试 Service 层实现

使用 Mock Repository 测试 Service 逻辑，不依赖真实数据
"""

import sys
import json
from pathlib import Path

# 添加项目根目录到路径
ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))


class MockRepository:
    """Mock Repository，用于测试 Service 层"""
    
    def __init__(self, etf_data=None):
        self.etf_data = etf_data or self._create_mock_data()
        self.etf_map = {etf['code']: etf for etf in self.etf_data}
    
    def _create_mock_data(self):
        """创建测试用的 Mock ETF 数据"""
        return [
            {
                'code': '510300',
                'name': '沪深300ETF',
                'issuer_short': '华泰柏瑞',
                'scale': 100.5,
                'shares': 50.2,
                'change_pct': 0.02,
                'change_rate': 0.01,
                'close': 4.12,
                'prev_close': 4.10,
                'annual_vol': 0.18,
                'year_1_return': 5.2,
                'year_3_return': 12.5,
                'volume': 2.5,
                'category': '宽基',
                'sharpe_ratio': 0.85,
                'max_drawdown': -0.15
            },
            {
                'code': '510500',
                'name': '中证500ETF',
                'issuer_short': '南方基金',
                'scale': 80.3,
                'shares': 30.1,
                'change_pct': -0.01,
                'change_rate': -0.005,
                'close': 6.45,
                'prev_close': 6.51,
                'annual_vol': 0.22,
                'year_1_return': 3.8,
                'year_3_return': 10.2,
                'volume': 1.8,
                'category': '宽基',
                'sharpe_ratio': 0.72,
                'max_drawdown': -0.18
            },
            {
                'code': '159915',
                'name': '创业板ETF',
                'issuer_short': '易方达',
                'scale': 60.1,
                'shares': 25.5,
                'change_pct': 0.03,
                'change_rate': 0.015,
                'close': 2.85,
                'prev_close': 2.78,
                'annual_vol': 0.25,
                'year_1_return': 8.5,
                'year_3_return': 15.2,
                'volume': 1.2,
                'category': '宽基',
                'sharpe_ratio': 0.68,
                'max_drawdown': -0.22
            }
        ]
    
    def get_all_etfs(self):
        return self.etf_data
    
    def get_etf_by_code(self, code):
        return self.etf_map.get(code)
    
    def filter_etfs(self, filters):
        result = []
        for etf in self.etf_data:
            # 简单筛选逻辑（仅测试用）
            if 'keyword' in filters:
                keyword = filters['keyword'].lower()
                if keyword not in etf['name'].lower() and keyword not in etf['code'].lower():
                    continue
            if 'scale_min' in filters:
                if (etf.get('scale') or 0) < filters['scale_min']:
                    continue
            result.append(etf)
        return result
    
    def get_etf_history(self, code, period='1Y'):
        return {
            'prices': [1.0, 1.02, 1.05],
            'dates': ['2025-01-01', '2025-01-02', '2025-01-03'],
            'source': 'mock'
        }
    
    def search_etfs(self, keyword):
        return self.filter_etfs({'keyword': keyword})


def test_query_service():
    """测试 ETFQueryService"""
    print("=== 测试 ETFQueryService ===")
    
    from services.etf_service_impl import SimpleETFQueryService
    
    repo = MockRepository()
    service = SimpleETFQueryService(repo)
    
    # 测试1：获取 ETF 列表
    print("\n测试1：get_etf_list()")
    result = service.get_etf_list()
    print(f"  总数: {result['total']}")
    print(f"  页数: {result['total_pages']}")
    print(f"  第一页数据量: {len(result['etfs'])}")
    assert result['total'] == 3, "总数应该是3"
    assert len(result['etfs']) == 3, "第一页应该有3条"
    print("  ✅ 通过")
    
    # 测试2：筛选 ETF
    print("\n测试2：get_etf_list(filters={'keyword': '300'})")
    result = service.get_etf_list(filters={'keyword': '300'})
    print(f"  筛选结果: {result['total']} 条")
    assert result['total'] == 1, "应该只有1条"
    assert result['etfs'][0]['code'] == '510300', "应该是510300"
    print("  ✅ 通过")
    
    # 测试3：获取 ETF 详情
    print("\n测试3：get_etf_detail('510300')")
    result = service.get_etf_detail('510300')
    print(f"  ETF: {result['code']} - {result['name']}")
    assert result['code'] == '510300', "代码应该是510300"
    assert '_data_source' in result, "应该有数据来源标记"
    print("  ✅ 通过")
    
    # 测试4：获取不存在的 ETF
    print("\n测试4：get_etf_detail('999999')")
    result = service.get_etf_detail('999999')
    print(f"  结果: {result}")
    assert result is None, "不存在的ETF应该返回None"
    print("  ✅ 通过")
    
    # 测试5：搜索 ETF
    print("\n测试5：search_etfs('ETF')")
    result = service.search_etfs('ETF')
    print(f"  搜索结果: {len(result)} 条")
    assert len(result) == 3, "应该搜索到3条"
    print("  ✅ 通过")
    
    print("\n✅ ETFQueryService 所有测试通过！\n")


def test_compare_service():
    """测试 ETFCompareService"""
    print("=== 测试 ETFCompareService ===")
    
    from services.etf_service_impl import SimpleETFCompareService
    
    repo = MockRepository()
    service = SimpleETFCompareService(repo)
    
    # 测试1：对比 ETF
    print("\n测试1：compare_etfs(['510300', '510500'])")
    result = service.compare_etfs(['510300', '510500'])
    print(f"  对比ETF数: {len(result['etfs'])}")
    print(f"  对比指标数: {len(result['metrics'])}")
    print(f"  对比表格行数: {len(result['table'])}")
    assert len(result['etfs']) == 2, "应该对比2只ETF"
    assert len(result['metrics']) > 0, "应该有对比指标"
    assert len(result['table']) == len(result['metrics']), "表格行数应该等于指标数"
    print("  ✅ 通过")
    
    # 测试2：获取对比指标列表
    print("\n测试2：get_compare_metrics()")
    metrics = service.get_compare_metrics()
    print(f"  指标列表: {metrics[:3]}...")
    assert len(metrics) > 0, "应该有指标"
    assert 'code' in metrics, "应该包含code指标"
    print("  ✅ 通过")
    
    print("\n✅ ETFCompareService 所有测试通过！\n")


def test_history_service():
    """测试 ETFHistoryService"""
    print("=== 测试 ETFHistoryService ===")
    
    from services.etf_service_impl import SimpleETFHistoryService
    
    repo = MockRepository()
    service = SimpleETFHistoryService(repo)
    
    # 测试1：获取历史数据
    print("\n测试1：get_history('510300', '1Y')")
    result = service.get_history('510300', '1Y')
    print(f"  代码: {result['code']}")
    print(f"  周期: {result['period']}")
    print(f"  价格点数: {len(result['prices'])}")
    print(f"  数据源: {result['source']}")
    assert result['code'] == '510300', "代码应该是510300"
    assert len(result['prices']) == 3, "应该有3个价格点"
    assert result['source'] == 'mock', "数据源应该是mock"
    print("  ✅ 通过")
    
    # 测试2：获取多只ETF历史数据
    print("\n测试2：get_multiple_history(['510300', '510500'], '1Y')")
    result = service.get_multiple_history(['510300', '510500'], '1Y')
    print(f"  ETF数量: {len(result['codes'])}")
    print(f"  数据keys: {list(result['data'].keys())}")
    assert len(result['codes']) == 2, "应该有2只ETF"
    assert '510300' in result['data'], "应该包含510300的数据"
    assert '510500' in result['data'], "应该包含510500的数据"
    print("  ✅ 通过")
    
    print("\n✅ ETFHistoryService 所有测试通过！\n")


def test_screening_service():
    """测试 ETFScreeningService"""
    print("=== 测试 ETFScreeningService ===")
    
    from services.etf_service_impl import SimpleETFScreeningService
    
    repo = MockRepository()
    service = SimpleETFScreeningService(repo)
    
    # 测试1：执行筛选
    print("\n测试1：screen_etfs(criteria)")
    criteria = service.get_default_screening_criteria()
    result = service.screen_etfs(criteria)
    print(f"  总ETF数: {result['total_count']}")
    print(f"  筛选步数: {len(result['steps'])}")
    print(f"  推荐ETF: {result['winner']['code'] if result['winner'] else None}")
    assert result['total_count'] == 3, "总ETF数应该是3"
    assert len(result['steps']) == 3, "应该有3步筛选"
    print("  ✅ 通过")
    
    # 测试2：获取默认筛选条件
    print("\n测试2：get_default_screening_criteria()")
    criteria = service.get_default_screening_criteria()
    print(f"  默认条件数: {len(criteria)}")
    assert len(criteria) == 3, "应该有3个默认条件"
    assert criteria[0]['step'] == 1, "第一步应该是1"
    print("  ✅ 通过")
    
    print("\n✅ ETFScreeningService 所有测试通过！\n")


def main():
    """主测试函数"""
    print("开始测试 Service 层实现...\n")
    
    try:
        test_query_service()
        test_compare_service()
        test_history_service()
        test_screening_service()
        
        print("=" * 50)
        print("🎉 所有测试通过！Service 层实现正确。")
        print("=" * 50)
        
    except AssertionError as e:
        print(f"\n❌ 测试失败: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 异常: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
