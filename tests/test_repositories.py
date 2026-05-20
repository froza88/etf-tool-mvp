"""
Tests for Repository Layer (ETFRepository, LocalJSONRepo, etc.)
"""
import pytest
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class TestETFRepositoryInterface:
    """测试 ETFRepository 抽象接口"""
    
    def test_cannot_instantiate_abstract_class(self):
        """测试不能实例化抽象类"""
        from repositories.etf_repository import ETFRepository
        
        with pytest.raises(TypeError):
            repo = ETFRepository()  # 应该报错，因为有抽象方法
    
    def test_concrete_class_must_implement_abstract_methods(self):
        """测试具体类必须实现所有抽象方法"""
        from repositories.etf_repository import ETFRepository
        
        # 只实现部分抽象方法，应该还是抽象类
        class PartialImpl(ETFRepository):
            def get_all_etfs(self):
                pass
            # 缺少 get_etf_by_code, filter_etfs, get_etf_history
        
        with pytest.raises(TypeError):
            repo = PartialImpl()  # 应该报错


class TestMockRepository:
    """测试 Mock Repository（用于单元测试）"""
    
    @pytest.fixture
    def mock_repo(self):
        """创建 Mock Repository"""
        from repositories.etf_repository import ETFRepository
        from typing import List, Dict, Optional, Any
        
        class MockRepo(ETFRepository):
            def __init__(self):
                self._data = [
                    {"code": "510300", "name": "沪深300ETF", "category": "宽基"},
                    {"code": "510500", "name": "中证500ETF", "category": "宽基"},
                    {"code": "512480", "name": "半导体ETF", "category": "行业"}
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
                return {"prices": [4.0, 4.1], "dates": ["2025-01-01", "2025-01-02"]}
        
        return MockRepo()
    
    def test_get_all_etfs(self, mock_repo):
        """测试 get_all_etfs"""
        result = mock_repo.get_all_etfs()
        assert len(result) == 3
        assert result[0]["code"] == "510300"
    
    def test_get_etf_by_code(self, mock_repo):
        """测试 get_etf_by_code"""
        result = mock_repo.get_etf_by_code("510300")
        assert result is not None
        assert result["name"] == "沪深300ETF"
    
    def test_get_etf_by_code_not_found(self, mock_repo):
        """测试获取不存在的 ETF"""
        result = mock_repo.get_etf_by_code("999999")
        assert result is None
    
    def test_filter_etfs(self, mock_repo):
        """测试 filter_etfs"""
        result = mock_repo.filter_etfs({"category": "宽基"})
        assert len(result) == 2
        assert all(etf["category"] == "宽基" for etf in result)
    
    def test_get_etf_history(self, mock_repo):
        """测试 get_etf_history"""
        result = mock_repo.get_etf_history("510300")
        assert "prices" in result
        assert "dates" in result
    
    def test_search_etfs(self, mock_repo):
        """测试 search_etfs（继承自抽象类的默认实现）"""
        result = mock_repo.search_etfs("沪深")
        assert len(result) >= 1
        assert any("沪深" in etf["name"] for etf in result)
