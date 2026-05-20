"""
Tests for Service Layer (ETFQueryService, ETFCompareService, etc.)
"""
import pytest

class TestETFQueryService:
    """测试 ETFQueryService"""
    
    def test_get_etf_list(self, query_service):
        """测试获取 ETF 列表"""
        result = query_service.get_etf_list()
        assert result['total'] == 3  # Mock 数据有 3 只 ETF
        assert len(result['etfs']) == 3
        assert result['etfs'][0]["code"] == "510300"
    
    def test_get_etf_list_with_filter(self, query_service):
        """测试带筛选条件获取 ETF 列表"""
        result = query_service.get_etf_list(filters={"category": "宽基"})
        assert result['total'] == 2  # 510300 和 510500 是宽基
        assert all(etf["category"] == "宽基" for etf in result['etfs'])
    
    def test_get_etf_detail(self, query_service):
        """测试获取 ETF 详情"""
        result = query_service.get_etf_detail("510300")
        assert result is not None
        assert result["code"] == "510300"
        assert result["name"] == "沪深300ETF"
    
    def test_get_etf_detail_not_found(self, query_service):
        """测试获取不存在的 ETF"""
        result = query_service.get_etf_detail("999999")
        assert result is None
    
    def test_search_etfs(self, query_service):
        """测试搜索 ETF"""
        result = query_service.search_etfs("沪深")
        assert len(result) >= 1
        assert any(etf["code"] == "510300" for etf in result)


class TestETFCompareService:
    """测试 ETFCompareService"""
    
    def test_compare_etfs(self, compare_service):
        """测试对比 ETF"""
        result = compare_service.compare_etfs(["510300", "510500"])
        assert "etfs" in result
        assert len(result["etfs"]) == 2
        assert any(etf["code"] == "510300" for etf in result["etfs"])
        assert any(etf["code"] == "510500" for etf in result["etfs"])
    
    def test_compare_etfs_empty(self, compare_service):
        """测试对比空列表"""
        result = compare_service.compare_etfs([])
        assert result["etfs"] == []
    
    def test_get_compare_metrics(self, compare_service):
        """测试获取对比指标"""
        result = compare_service.get_compare_metrics()
        assert isinstance(result, list)
        assert len(result) > 0


class TestETFScreeningService:
    """测试 ETFScreeningService"""
    
    def test_get_default_screening_criteria(self):
        """测试获取默认筛选条件"""
        from services.etf_service_impl import SimpleETFScreeningService
        from repositories.etf_repository import ETFRepository
        
        # 创建 Mock Repository
        class MockRepo(ETFRepository):
            def get_all_etfs(self):
                return []
            def get_etf_by_code(self, code):
                return None
            def filter_etfs(self, filters):
                return []
            def get_etf_history(self, code, period="1y"):
                return {}
        
        service = SimpleETFScreeningService(MockRepo())
        criteria = service.get_default_screening_criteria()
        assert isinstance(criteria, list)
        assert len(criteria) > 0
        assert "step" in criteria[0]
        assert "name" in criteria[0]
