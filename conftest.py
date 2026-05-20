"""
pytest conftest.py - 测试夹具配置
"""
import sys
import os
import pytest
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

@pytest.fixture
def sample_etfs():
    """加载测试 ETF 数据"""
    import json
    with open(project_root / "test_data" / "sample_etfs.json", "r") as f:
        return json.load(f)

@pytest.fixture
def mock_repository():
    """创建 Mock Repository（用于测试 Service 层）"""
    from repositories.etf_repository import ETFRepository
    from typing import List, Dict, Optional, Any
    
    class MockRepo(ETFRepository):
        def __init__(self):
            self._data = [
                {"code": "510300", "name": "沪深300ETF", "category": "宽基", "close": 4.12},
                {"code": "510500", "name": "中证500ETF", "category": "宽基", "close": 6.95},
                {"code": "512480", "name": "半导体ETF", "category": "行业", "close": 1.85}
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
    
    return MockRepo()

@pytest.fixture
def query_service(mock_repository):
    """创建 ETFQueryService 实例（使用 Mock Repository）"""
    from services.etf_service_impl import SimpleETFQueryService
    return SimpleETFQueryService(mock_repository)

@pytest.fixture
def compare_service(mock_repository):
    """创建 ETFCompareService 实例（使用 Mock Repository）"""
    from services.etf_service_impl import SimpleETFCompareService
    return SimpleETFCompareService(mock_repository)
