"""
Integration Tests - 测试多个组件一起工作
"""
import pytest
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class TestRepositoryServiceIntegration:
    """测试 Repository + Service 集成"""
    
    @pytest.fixture
    def mock_repo_and_services(self):
        """创建 Mock Repository 和 Services"""
        from repositories.etf_repository import ETFRepository
        from services.etf_service_impl import (
            SimpleETFQueryService,
            SimpleETFCompareService,
            SimpleETFHistoryService,
            SimpleETFScreeningService
        )
        from typing import List, Dict, Optional, Any
        
        # 创建 Mock Repository
        class MockRepo(ETFRepository):
            def __init__(self):
                self._data = [
                    {"code": "510300", "name": "沪深300ETF", "category": "宽基", "close": 4.12, "year_1_return": 8.5},
                    {"code": "510500", "name": "中证500ETF", "category": "宽基", "close": 6.95, "year_1_return": 12.3},
                    {"code": "512480", "name": "半导体ETF", "category": "行业", "close": 1.85, "year_1_return": -5.2}
                ]
            
            def get_all_etfs(self) -> List[Dict]:
                return self._data
            
            def get_etf_by_code(self, code: str) -> Optional[Dict]:
                for etf in self._data:
                    if etf["code"] == code:
                        return etf
                return None
            
            def filter_etfs(self, filters: Dict[str, Any]) -> List[Dict]:
                if "category" in filters:
                    cat = filters["category"]
                    return [etf for etf in self._data if etf.get("category") == cat]
                return self._data
            
            def get_etf_history(self, code: str, period: str = "1y") -> Dict:
                return {"prices": [4.0, 4.1, 4.2], "dates": ["2025-01-01", "2025-01-02", "2025-01-03"]}
        
        repo = MockRepo()
        query_service = SimpleETFQueryService(repo)
        compare_service = SimpleETFCompareService(repo)
        history_service = SimpleETFHistoryService(repo)
        screening_service = SimpleETFScreeningService(repo)
        
        return {
            "repo": repo,
            "query_service": query_service,
            "compare_service": compare_service,
            "history_service": history_service,
            "screening_service": screening_service
        }
    
    def test_query_service_with_repo(self, mock_repo_and_services):
        """测试 QueryService 通过 Repository 获取数据"""
        query_service = mock_repo_and_services["query_service"]
        
        # 测试获取列表
        result = query_service.get_etf_list()
        assert result["total"] == 3
        assert len(result["etfs"]) == 3
        
        # 测试获取详情
        detail = query_service.get_etf_detail("510300")
        assert detail is not None
        assert detail["code"] == "510300"
        
        # 测试搜索
        results = query_service.search_etfs("沪深")
        assert len(results) >= 1
    
    def test_compare_service_with_repo(self, mock_repo_and_services):
        """测试 CompareService 通过 Repository 获取对比数据"""
        compare_service = mock_repo_and_services["compare_service"]
        
        result = compare_service.compare_etfs(["510300", "510500"])
        assert "etfs" in result
        assert len(result["etfs"]) == 2
        
        # 测试获取对比指标
        metrics = compare_service.get_compare_metrics()
        assert isinstance(metrics, list)
        assert len(metrics) > 0
    
    def test_history_service_with_repo(self, mock_repo_and_services):
        """测试 HistoryService 通过 Repository 获取历史数据"""
        history_service = mock_repo_and_services["history_service"]
        
        result = history_service.get_history("510300")
        assert "prices" in result
        assert "dates" in result
        assert len(result["prices"]) > 0
        
        # 测试获取多只 ETF 历史
        multi_result = history_service.get_multiple_history(["510300", "510500"])
        assert "data" in multi_result
        assert len(multi_result["data"]) == 2
    
    def test_screening_service_with_repo(self, mock_repo_and_services):
        """测试 ScreeningService 通过 Repository 执行筛选"""
        screening_service = mock_repo_and_services["screening_service"]
        
        # 测试获取默认筛选条件
        criteria = screening_service.get_default_screening_criteria()
        assert isinstance(criteria, list)
        assert len(criteria) > 0
        
        # 测试执行筛选（使用默认条件）
        result = screening_service.screen_etfs(criteria)
        assert "total_count" in result
        assert "steps" in result
