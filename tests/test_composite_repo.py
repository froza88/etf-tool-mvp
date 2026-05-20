"""
Tests for CompositeRepo - 测试组合 Repository 的 fallback 策略
"""
import pytest
import sys
from pathlib import Path
from typing import List, Dict, Optional, Any

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class TestCompositeRepo:
    """测试 CompositeRepo"""
    
    @pytest.fixture
    def mock_primary_repo(self):
        """创建 Mock Primary Repository（本地）"""
        from repositories.etf_repository import ETFRepository
        
        class MockPrimaryRepo(ETFRepository):
            def __init__(self):
                self._data = {
                    "510300": {"code": "510300", "name": "沪深300ETF", "category": "宽基", "_timestamp": 0}  # 过期数据
                }
                self._update_called = False
            
            def get_all_etfs(self) -> List[Dict]:
                return list(self._data.values())
            
            def get_etf_by_code(self, code: str) -> Optional[Dict]:
                return self._data.get(code)
            
            def filter_etfs(self, filters: Dict[str, Any]) -> List[Dict]:
                return [etf for etf in self._data.values() if etf.get("category") == filters.get("category")]
            
            def get_etf_history(self, code: str, period: str = "1y") -> Dict:
                return {"prices": [4.0], "dates": ["2025-01-01"]}
        
        return MockPrimaryRepo()
    
    @pytest.fixture
    def mock_fallback_repo(self):
        """创建 Mock Fallback Repository（在线）"""
        from repositories.etf_repository import ETFRepository
        
        class MockFallbackRepo(ETFRepository):
            def __init__(self):
                self._data = {
                    "510300": {"code": "510300", "name": "沪深300ETF", "category": "宽基", "close": 4.12},
                    "510500": {"code": "510500", "name": "中证500ETF", "category": "宽基", "close": 6.95}
                }
                self._call_count = 0
            
            def get_all_etfs(self) -> List[Dict]:
                return list(self._data.values())
            
            def get_etf_by_code(self, code: str) -> Optional[Dict]:
                self._call_count += 1
                return self._data.get(code)
            
            def filter_etfs(self, filters: Dict[str, Any]) -> List[Dict]:
                return [etf for etf in self._data.values() if etf.get("category") == filters.get("category")]
            
            def get_etf_history(self, code: str, period: str = "1y") -> Dict:
                return {"prices": [4.0, 4.1], "dates": ["2025-01-01", "2025-01-02"]}
        
        return MockFallbackRepo()
    
    @pytest.fixture
    def composite_repo(self, mock_primary_repo, mock_fallback_repo):
        """创建 CompositeRepo"""
        from repositories.composite_repo import CompositeRepo
        return CompositeRepo(
            primary=mock_primary_repo,
            fallbacks=[mock_fallback_repo],
            cache_write=False  # 测试时不写入缓存
        )
    
    def test_get_all_etfs_from_primary(self, composite_repo, mock_primary_repo):
        """测试 get_all_etfs 直接从 primary 获取"""
        result = composite_repo.get_all_etfs()
        assert len(result) == 1
        assert result[0]["code"] == "510300"
    
    def test_get_etf_by_code_primary_hit(self, composite_repo, mock_primary_repo):
        """测试 get_etf_by_code 命中 primary（未过期）"""
        # 修改 primary 数据为未过期
        mock_primary_repo._data["510300"]["_timestamp"] = sys.maxsize  # 未来时间戳，未过期
        
        result = composite_repo.get_etf_by_code("510300")
        assert result is not None
        assert result["code"] == "510300"
        assert composite_repo.get_stats()["primary_hits"] == 1
    
    def test_get_etf_by_code_primary_expired_fallback_hit(self, composite_repo, mock_fallback_repo):
        """测试 get_etf_by_code primary 过期，fallback 命中"""
        result = composite_repo.get_etf_by_code("510300")
        assert result is not None
        assert result["code"] == "510300"
        assert composite_repo.get_stats()["fallback_hits"] == 1
    
    def test_get_etf_by_code_all_fail(self, composite_repo, mock_fallback_repo):
        """测试 get_etf_by_code 所有数据源都失败"""
        # 让 fallback repo 抛出异常
        def raise_error(code):
            raise Exception("API error")
        mock_fallback_repo.get_etf_by_code = raise_error
        
        result = composite_repo.get_etf_by_code("999999")  # 不存在的 code
        assert result is None
        assert composite_repo.get_stats()["fallback_errors"] == 1
    
    def test_filter_etfs_from_primary(self, composite_repo):
        """测试 filter_etfs 直接从 primary 获取"""
        result = composite_repo.filter_etfs({"category": "宽基"})
        assert len(result) == 1
        assert result[0]["code"] == "510300"
    
    def test_get_etf_history_primary_hit(self, composite_repo):
        """测试 get_etf_history 命中 primary"""
        result = composite_repo.get_etf_history("510300")
        assert len(result["prices"]) > 0
        assert composite_repo.get_stats()["primary_hits"] == 1
    
    def test_get_etf_history_primary_miss_fallback_hit(self, composite_repo, mock_primary_repo, mock_fallback_repo):
        """测试 get_etf_history primary 没有数据，fallback 命中"""
        # 修改 primary repo 的 get_etf_history 返回空数据
        def return_empty(code, period="1y"):
            return {"prices": [], "dates": []}
        mock_primary_repo.get_etf_history = return_empty
        
        result = composite_repo.get_etf_history("510300")
        assert len(result["prices"]) > 0
        assert composite_repo.get_stats()["fallback_hits"] == 1
    
    def test_get_stats(self, composite_repo):
        """测试 get_stats"""
        composite_repo.get_etf_by_code("510300")  # 触发一次查询
        stats = composite_repo.get_stats()
        assert "primary_hits" in stats
        assert "fallback_hits" in stats
        assert "fallback_errors" in stats
        assert "cache_writes" in stats
    
    def test_reset_stats(self, composite_repo):
        """测试 reset_stats"""
        composite_repo.get_etf_by_code("510300")  # 触发一次查询
        composite_repo.reset_stats()
        stats = composite_repo.get_stats()
        assert stats["primary_hits"] == 0
        assert stats["fallback_hits"] == 0
