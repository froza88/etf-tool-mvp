"""
Service 层具体实现

实现 ETFQueryService, ETFCompareService, ETFHistoryService, ETFScreeningService
"""

import sys
from typing import List, Dict, Optional, Any
from abc import ABC, abstractmethod

# 导入 Repository 接口（实际使用时）
# from repositories.etf_repository import ETFRepository

# 导入 Service 接口
from .etf_service import (
    ETFQueryService,
    ETFCompareService,
    ETFHistoryService,
    ETFScreeningService
)


class SimpleETFQueryService(ETFQueryService):
    """
    ETF 查询服务 - 简单实现
    
    职责：
    - 调用 Repository 获取 ETF 数据
    - 执行筛选、排序、分页逻辑
    - 返回标准化结果
    """
    
    def __init__(self, repository):
        """
        初始化
        
        Args:
            repository: ETFRepository 实例（依赖注入）
        """
        self.repo = repository
    
    def get_etf_list(
        self,
        filters: Optional[Dict[str, Any]] = None,
        sort_by: str = 'code',
        sort_order: str = 'asc',
        page: int = 1,
        page_size: int = 50
    ) -> Dict[str, Any]:
        """
        获取 ETF 列表（支持筛选、排序、分页）
        
        实现逻辑：
        1. 调用 repo.filter_etfs(filters) 获取筛选后的列表
        2. 按 sort_by 排序
        3. 按 page/page_size 分页
        4. 返回精简字段（列表页不需要完整数据）
        """
        # 1. 筛选
        filters = filters or {}
        etfs = self.repo.filter_etfs(filters)
        
        # 2. 排序（安全处理 None 值）
        reverse = (sort_order == 'desc')
        def sort_key(e):
            val = e.get(sort_by, 0)
            return val if val is not None else 0
        
        try:
            etfs.sort(key=sort_key, reverse=reverse)
        except Exception as e:
            print(f"排序失败: {e}", file=sys.stderr)
        
        # 3. 分页
        total = len(etfs)
        offset = (page - 1) * page_size
        paged = etfs[offset:offset + page_size]
        
        # 4. 精简字段（列表页只需要这些）
        list_fields = [
            'code', 'name', 'issuer_short', 'scale', 'shares',
            'change_pct', 'change_rate', 'close', 'prev_close',
            'annual_vol', 'year_1_return', 'year_3_return',
            'volume', 'category'
        ]
        slim = []
        for e in paged:
            slim_etf = {k: e.get(k, 0) for k in list_fields}
            slim.append(slim_etf)
        
        return {
            'total': total,
            'page': page,
            'page_size': page_size,
            'total_pages': (total + page_size - 1) // page_size,
            'etfs': slim
        }
    
    def get_etf_detail(self, code: str) -> Optional[Dict[str, Any]]:
        """
        获取单个 ETF 详情（完整字段）
        
        实现逻辑：
        1. 调用 repo.get_etf_by_code(code)
        2. 如果找不到，返回 None
        3. 添加额外信息（如数据来源标记）
        """
        etf = self.repo.get_etf_by_code(code)
        if not etf:
            return None
        
        # 添加标记（可选）
        etf['_data_source'] = 'repository'
        
        return etf
    
    def search_etfs(self, keyword: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        搜索 ETF（关键词匹配名称和代码）
        
        实现逻辑：
        1. 调用 repo.search_etfs(keyword)
        2. 限制返回数量
        """
        results = self.repo.search_etfs(keyword)
        
        # 限制数量
        if limit > 0:
            results = results[:limit]
        
        return results


class SimpleETFCompareService(ETFCompareService):
    """
    ETF 对比服务 - 简单实现
    
    职责：
    - 获取多只 ETF 数据
    - 生成对比表格
    - 计算评分
    """
    
    def __init__(self, repository):
        """
        初始化
        
        Args:
            repository: ETFRepository 实例
        """
        self.repo = repository
    
    def compare_etfs(self, codes: List[str]) -> Dict[str, Any]:
        """
        对比多只 ETF
        
        实现逻辑：
        1. 调用 repo.get_etf_by_code(code) 获取每只 ETF
        2. 定义对比指标列表
        3. 生成对比表格（二维数组）
        """
        # 1. 获取 ETF 数据
        etfs = []
        for code in codes:
            etf = self.repo.get_etf_by_code(code)
            if etf:
                etfs.append(etf)
        
        if not etfs:
            return {
                'etfs': [],
                'metrics': [],
                'table': []
            }
        
        # 2. 定义对比指标
        metrics = self.get_compare_metrics()
        
        # 3. 生成对比表格
        table = []
        for metric in metrics:
            row = [metric]  # 第一列是指标名
            for etf in etfs:
                value = etf.get(metric, '--')
                row.append(value)
            table.append(row)
        
        return {
            'etfs': etfs,
            'metrics': metrics,
            'table': table
        }
    
    def get_compare_metrics(self) -> List[str]:
        """
        获取可对比的指标列表
        
        返回常用的对比指标
        """
        return [
            'code',
            'name',
            'issuer_short',
            'scale',
            'close',
            'change_pct',
            'year_1_return',
            'year_3_return',
            'sharpe_ratio',
            'max_drawdown',
            'annual_vol',
            'volume',
            'category'
        ]


class SimpleETFHistoryService(ETFHistoryService):
    """
    ETF 历史数据服务 - 简单实现
    
    职责：
    - 获取历史价格数据
    - 归一化处理
    """
    
    def __init__(self, repository):
        """
        初始化
        
        Args:
            repository: ETFRepository 实例
        """
        self.repo = repository
    
    def get_history(
        self,
        code: str,
        period: str = '1Y',
        normalized: bool = True
    ) -> Dict[str, Any]:
        """
        获取历史数据
        
        实现逻辑：
        1. 调用 repo.get_etf_history(code, period)
        2. 如果需要归一化，进行归一化处理
        """
        history = self.repo.get_etf_history(code, period)
        
        if not history or not history.get('prices'):
            return {
                'code': code,
                'period': period,
                'dates': [],
                'prices': [],
                'source': 'error'
            }
        
        prices = history['prices']
        dates = history.get('dates', [])
        
        # 归一化（如果需要）
        if normalized and prices:
            base = prices[0]
            if base and base != 0:
                prices = [round(p / base, 4) for p in prices]
        
        return {
            'code': code,
            'period': period,
            'dates': dates,
            'prices': prices,
            'source': history.get('source', 'unknown')
        }
    
    def get_multiple_history(
        self,
        codes: List[str],
        period: str = '1Y'
    ) -> Dict[str, Any]:
        """
        获取多只 ETF 的历史数据
        """
        data = {}
        for code in codes:
            history = self.get_history(code, period, normalized=True)
            data[code] = {
                'dates': history['dates'],
                'prices': history['prices']
            }
        
        return {
            'codes': codes,
            'period': period,
            'data': data
        }


class SimpleETFScreeningService(ETFScreeningService):
    """
    ETF 筛选服务 - 简单实现
    
    职责：
    - 执行多步筛选
    - 生成筛选报告
    """
    
    def __init__(self, repository):
        """
        初始化
        
        Args:
            repository: ETFRepository 实例
        """
        self.repo = repository
    
    def screen_etfs(
        self,
        criteria: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        执行筛选流程
        
        实现逻辑：
        1. 获取所有 ETF
        2. 按 criteria 逐步筛选
        3. 每步记录通过/淘汰数量
        4. 最终推荐（评分排序）
        """
        # 获取所有 ETF
        all_etfs = self.repo.get_all_etfs()
        current_etfs = all_etfs
        
        steps = []
        for criterion in criteria:
            step_num = criterion.get('step', len(steps) + 1)
            step_name = criterion.get('name', f'第{step_num}步')
            step_criteria = criterion.get('criteria', '')
            step_filter = criterion.get('filter', {})
            
            # 执行筛选
            passed = self._apply_filter(current_etfs, step_filter)
            
            steps.append({
                'step': step_num,
                'name': step_name,
                'criteria': step_criteria,
                'passed': passed,
                'eliminated_count': len(current_etfs) - len(passed)
            })
            
            # 更新当前 ETF 列表
            current_etfs = passed
        
        # 最终推荐（评分排序）
        winner = None
        if current_etfs:
            # 简单评分：规模 + 收益率
            for etf in current_etfs:
                score = 0
                score += min((etf.get('scale') or 0) / 100, 1) * 40
                score += max(min((etf.get('year_1_return') or 0) / 50, 1), 0) * 35
                score += min((etf.get('volume') or 0) / 10, 1) * 25
                etf['_score'] = round(score, 2)
            
            sorted_etfs = sorted(current_etfs, key=lambda x: x['_score'], reverse=True)
            winner = sorted_etfs[0] if sorted_etfs else None
        
        return {
            'total_count': len(all_etfs),
            'steps': steps,
            'winner': winner
        }
    
    def get_default_screening_criteria(self) -> List[Dict[str, Any]]:
        """
        获取默认筛选条件（示例：新能源 ETF 筛选）
        """
        return [
            {
                'step': 1,
                'name': '第一层筛选：规模过滤',
                'criteria': '规模 ≥ 10亿 且 ≤ 150亿',
                'filter': {'scale_min': 10, 'scale_max': 150}
            },
            {
                'step': 2,
                'name': '第二层筛选：规模',
                'criteria': '规模 >= 5亿',
                'filter': {'scale_min': 5}
            },
            {
                'step': 3,
                'name': '第三层筛选：流动性',
                'criteria': '日均成交额 >= 1亿',
                'filter': {'volume_min': 1}
            }
        ]
    
    def _apply_filter(self, etfs: List[Dict], filters: Dict) -> List[Dict]:
        """
        应用筛选条件
        
        支持的条件：
        - scale_min/scale_max: 规模范围
        - return_min: 最低收益率
        - volume_min: 最低成交量
        - category: 分类
        - keyword: 关键词
        """
        result = []
        for etf in etfs:
            # scale_min
            if 'scale_min' in filters:
                if (etf.get('scale') or 0) < filters['scale_min']:
                    continue
            
            # scale_max
            if 'scale_max' in filters:
                if (etf.get('scale') or 0) > filters['scale_max']:
                    continue
            
            # return_min
            if 'return_min' in filters:
                if (etf.get('year_1_return') or 0) < filters['return_min']:
                    continue
            
            # volume_min
            if 'volume_min' in filters:
                if (etf.get('volume') or 0) < filters['volume_min']:
                    continue
            
            # category
            if 'category' in filters:
                if etf.get('category') != filters['category']:
                    continue
            
            # keyword
            if 'keyword' in filters:
                keyword = filters['keyword'].lower()
                name = etf.get('name', '').lower()
                code = etf.get('code', '').lower()
                if keyword not in name and keyword not in code:
                    continue
            
            result.append(etf)
        
        return result
