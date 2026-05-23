"""
测试脚本：验证 WeStock L2 数据源集成

测试内容：
1. WeStockFetcher 能调用 CLI 并解析字段
2. WeStockSource 能正确补充 L1 缺失字段
3. API `/api/compare?source=westock` 返回正确数据
"""

import sys
import os
import json
from pathlib import Path

# 添加项目根目录到路径
ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))


def test_westock_fetcher():
    """测试 1: WeStockFetcher 能调用 CLI 并解析字段"""
    print("\n=== 测试 1: WeStockFetcher ===")
    
    try:
        from fetchers.westock_fetcher import WeStockFetcher
    except ImportError as e:
        print(f"✗ 导入 WeStockFetcher 失败: {e}")
        return False
    
    # 创建 fetcher
    fetcher = WeStockFetcher(cache_days=1)
    
    # 测试获取 ETF 信息
    test_code = "510300"
    print(f"  正在获取 {test_code} 的 WeStock 数据...")
    
    data = fetcher.fetch_etf_info(test_code, force_refresh=True)
    
    if not data:
        print(f"✗ 获取 {test_code} 数据失败")
        return False
    
    # 验证返回的字段
    expected_fields = [
        'fee_rate_management', 'fee_rate_custody', 'fee_rate_service',
        'fee_rate', 'premium_discount', 'scale', 'shares',
        'net_inflow_shares', 'net_inflow_ratio', 'net_inflow_5d'
    ]
    
    missing_fields = [f for f in expected_fields if f not in data]
    
    if missing_fields:
        print(f"✗ 缺失字段: {missing_fields}")
        print(f"  实际返回字段: {list(data.keys())}")
        return False
    
    print(f"  ✓ 成功获取 {test_code} 数据")
    print(f"  ✓ 包含字段: {list(data.keys())}")
    
    # 打印部分字段值
    print(f"  - fee_rate: {data.get('fee_rate')}")
    print(f"  - premium_discount: {data.get('premium_discount')}")
    print(f"  - net_inflow_5d: {data.get('net_inflow_5d')}")
    
    return True


def test_westock_source():
    """测试 2: WeStockSource 能正确补充 L1 缺失字段"""
    print("\n=== 测试 2: WeStockSource ===")
    
    try:
        from etf_data_service import WeStockSource
    except ImportError as e:
        print(f"✗ 导入 WeStockSource 失败: {e}")
        return False
    
    # 创建 source
    try:
        source = WeStockSource(cache_dir=str(ROOT / "data" / "cache" / "westock_test"))
    except Exception as e:
        print(f"✗ 创建 WeStockSource 失败: {e}")
        return False
    
    # 测试获取 ETF 数据
    test_codes = ["510300", "510500"]
    print(f"  正在获取 {test_codes} 的 WeStock 数据...")
    
    etfs = source.get_etfs_by_codes(test_codes)
    
    if not etfs:
        print(f"✗ 获取 ETF 数据失败")
        return False
    
    print(f"  ✓ 成功获取 {len(etfs)} 个 ETF 数据")
    
    # 验证每个 ETF 数据
    for etf in etfs:
        code = etf.get('code')
        
        # 验证必要字段
        if 'fee_rate' not in etf:
            print(f"✗ {code} 缺失 fee_rate 字段")
            return False
        
        if 'premium_discount' not in etf:
            print(f"✗ {code} 缺失 premium_discount 字段")
            return False
        
        print(f"  ✓ {code}: fee_rate={etf.get('fee_rate')}, premium_discount={etf.get('premium_discount')}")
    
    return True


def test_api_compare_westock():
    """测试 3: API `/api/compare?source=westock` 返回正确数据"""
    print("\n=== 测试 3: API /api/compare?source=westock ===")
    
    try:
        import app
    except ImportError as e:
        print(f"✗ 导入 app 失败: {e}")
        return False
    
    # 创建测试客户端
    app.app.config['TESTING'] = True
    client = app.app.test_client()
    
    # 测试 API
    test_codes = "510300,510500"
    url = f"/api/compare?codes={test_codes}&source=westock"
    print(f"  正在请求 API: {url}")
    
    response = client.get(url)
    
    if response.status_code != 200:
        print(f"✗ API 返回错误状态码: {response.status_code}")
        print(f"  响应: {response.get_data(as_text=True)}")
        return False
    
    data = json.loads(response.get_data(as_text=True))
    
    # 验证响应结构
    if 'etfs' not in data:
        print(f"✗ 响应缺失 etfs 字段")
        return False
    
    if data['source'] != 'westock':
        print(f"✗ 响应 source 字段不正确: {data['source']}")
        return False
    
    etfs = data['etfs']
    
    if not etfs or len(etfs) == 0:
        print(f"✗ 响应 etfs 为空")
        return False
    
    print(f"  ✓ API 返回 {len(etfs)} 个 ETF 数据")
    print(f"  ✓ source={data['source']}")
    
    # 验证 ETF 数据字段
    for etf in etfs:
        code = etf.get('code')
        
        if 'fee_rate' not in etf:
            print(f"✗ {code} 缺失 fee_rate 字段")
            return False
        
        print(f"  ✓ {code}: fee_rate={etf.get('fee_rate')}, source={data['source']}")
    
    return True


def test_api_compare_local():
    """测试 4: API `/api/compare?source=local` 返回本地数据"""
    print("\n=== 测试 4: API /api/compare?source=local ===")
    
    try:
        import app
    except ImportError as e:
        print(f"✗ 导入 app 失败: {e}")
        return False
    
    # 创建测试客户端
    app.app.config['TESTING'] = True
    client = app.app.test_client()
    
    # 测试 API
    test_codes = "510300,510500"
    url = f"/api/compare?codes={test_codes}&source=local"
    print(f"  正在请求 API: {url}")
    
    response = client.get(url)
    
    if response.status_code != 200:
        print(f"✗ API 返回错误状态码: {response.status_code}")
        print(f"  响应: {response.get_data(as_text=True)[:500]}")
        return False
    
    data_str = response.get_data(as_text=True)
    data = json.loads(data_str)
    
    # 验证响应结构
    if 'etfs' not in data:
        print(f"✗ 响应缺失 etfs 字段")
        print(f"  响应 keys: {list(data.keys())}")
        return False
    
    if data['source'] != 'local_db' and data['source'] != 'local_db_fallback':
        print(f"✗ 响应 source 字段不正确: {data['source']}")
        return False
    
    etfs = data['etfs']
    
    if not etfs or len(etfs) == 0:
        print(f"✗ 响应 etfs 为空")
        return False
    
    print(f"  ✓ API 返回 {len(etfs)} 个 ETF 数据")
    print(f"  ✓ source={data['source']}")
    
    return True


def main():
    """主函数：运行所有测试"""
    print("=" * 60)
    print("WeStock L2 数据源集成测试")
    print("=" * 60)
    
    results = []
    
    # 测试 1: WeStockFetcher
    try:
        result1 = test_westock_fetcher()
        results.append(("WeStockFetcher", result1))
    except Exception as e:
        print(f"✗ 测试 1 异常: {e}")
        results.append(("WeStockFetcher", False))
    
    # 测试 2: WeStockSource
    try:
        result2 = test_westock_source()
        results.append(("WeStockSource", result2))
    except Exception as e:
        print(f"✗ 测试 2 异常: {e}")
        results.append(("WeStockSource", False))
    
    # 测试 3: API /api/compare?source=westock
    try:
        result3 = test_api_compare_westock()
        results.append(("API source=westock", result3))
    except Exception as e:
        print(f"✗ 测试 3 异常: {e}")
        results.append(("API source=westock", False))
    
    # 测试 4: API /api/compare?source=local
    try:
        result4 = test_api_compare_local()
        results.append(("API source=local", result4))
    except Exception as e:
        import traceback
        print(f"✗ 测试 4 异常: {e}")
        traceback.print_exc()
        results.append(("API source=local", False))
    
    # 汇总结果
    print("\n" + "=" * 60)
    print("测试汇总")
    print("=" * 60)
    
    passed = 0
    failed = 0
    
    for name, result in results:
        status = "✓ 通过" if result else "✗ 失败"
        print(f"  {status}: {name}")
        if result:
            passed += 1
        else:
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"总计: {passed} 通过, {failed} 失败")
    print("=" * 60)
    
    return failed == 0


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
