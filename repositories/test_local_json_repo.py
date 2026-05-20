"""
Task #17 验收测试脚本
验证 LocalJSONRepo 所有功能
"""

import sys
from pathlib import Path

# 确保可以导入
root = Path(__file__).parent.parent
sys.path.insert(0, str(root))

from repositories.local_json_repo import LocalJSONRepo


def test_instantiation():
    """测试1: 实例化"""
    repo = LocalJSONRepo(root_path=root)
    assert repo.root == root, f"root 不匹配: {repo.root}"
    assert str(repo.data_dir).endswith("data"), f"data_dir 不匹配: {repo.data_dir}"
    print("✅ 1. 实例化成功（root/data_dir 正确）")
    return repo


def test_get_all_etfs(repo):
    """测试2: 获取所有 ETF"""
    etfs = repo.get_all_etfs()
    assert isinstance(etfs, list), f"返回值不是列表: {type(etfs)}"
    assert len(etfs) > 0, "ETF 列表为空"
    print(f"✅ 2. get_all_etfs() 返回 {len(etfs)} 只 ETF")


def test_get_etf_by_code(repo):
    """测试3-4: 根据代码获取 ETF"""
    # 存在的 ETF
    etf = repo.get_etf_by_code("510300")
    if etf:
        assert isinstance(etf, dict), f"返回值不是字典: {type(etf)}"
        assert "code" in etf, "缺少 code 字段"
        assert "name" in etf, "缺少 name 字段"
        print(f"✅ 3. get_etf_by_code('510300') 找到: {etf.get('name')}")
    else:
        print("⚠️ 3. get_etf_by_code('510300') 返回 None（数据源中无此 ETF）")

    # 不存在的 ETF
    result = repo.get_etf_by_code("999999")
    assert result is None, f"应为 None，实际: {result}"
    print("✅ 4. get_etf_by_code('999999') 返回 None（正确）")


def test_filter_etfs(repo):
    """测试5-6: 筛选 ETF"""
    # 关键词搜索
    results = repo.filter_etfs({"keyword": "300"})
    assert isinstance(results, list), f"返回值不是列表: {type(results)}"
    assert len(results) > 0, "搜索 '300' 无结果"
    print(f"✅ 5. filter_etfs({{'keyword': '300'}}) 返回 {len(results)} 条")

    # 规模筛选
    results = repo.filter_etfs({"scale_min": 50})
    print(f"✅ 6. filter_etfs({{'scale_min': 50}}) 返回 {len(results)} 只")


def test_get_etf_history(repo):
    """测试7: 历史数据"""
    hist = repo.get_etf_history("510300", "1Y")
    assert isinstance(hist, dict), f"返回值不是字典: {type(hist)}"
    assert "prices" in hist, "缺少 prices 字段"
    assert "source" in hist, "缺少 source 字段"
    assert len(hist["prices"]) > 0, "prices 为空"
    print(
        f"✅ 7. get_etf_history('510300', '1Y'): "
        f"source={hist.get('source')}, count={hist.get('count')}"
    )


def test_reload(repo):
    """测试8: 重新加载"""
    count_before = len(repo.get_all_etfs())
    repo.reload_data()
    count_after = len(repo.get_all_etfs())
    assert count_before == count_after, f"重新加载后数据量不一致: {count_before} vs {count_after}"
    print(f"✅ 8. reload_data() 后数据一致（{count_after} 只）")


def test_search_etfs(repo):
    """测试9: 搜索 ETF（默认实现）"""
    results = repo.search_etfs("300")
    assert isinstance(results, list), f"返回值不是列表: {type(results)}"
    print(f"✅ 9. search_etfs('300') 搜索到 {len(results)} 只 ETF")


def run_all_tests():
    print("=" * 60)
    print("   Task #17 LocalJSONRepo 验收测试")
    print("=" * 60)

    try:
        repo = test_instantiation()
        test_get_all_etfs(repo)
        test_get_etf_by_code(repo)
        test_filter_etfs(repo)
        test_get_etf_history(repo)
        test_reload(repo)
        test_search_etfs(repo)

        print("=" * 60)
        print("   🎉 全部 9 项测试通过！")
        print("=" * 60)
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    run_all_tests()