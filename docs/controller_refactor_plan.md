# Controller 层重构方案（Phase 3 准备）

## 目标

将 `app.py` 中的路由从**直接调用 `etf_data.py`** 改为**通过 Service 层调用**，实现清晰的三层架构：
- **Controller（路由）**：只负责 HTTP 请求解析和响应渲染
- **Service（业务）**：封装业务逻辑（筛选/对比/排序/分页）
- **Repository（数据）**：抽象数据访问（本地/在线）

## 当前问题分析

### 问题1：业务逻辑散落在路由中

**示例**：`/api/etfs` 路由（第39-86行）包含了：
- 参数解析（filters/sort_by/page）
- 筛选逻辑（`etf_data.filter_etfs`）
- 排序逻辑（`etfs.sort(key=sort_key)`）
- 分页逻辑（`offset:offset+page_size`）
- 字段精简逻辑（`list_fields`）

**问题**：路由函数太长（47行），难以测试，难以复用。

### 问题2：直接依赖 `etf_data.py`

**示例**：7个路由直接调用 `etf_data.xxx()`：
- 第62行：`etf_data.filter_etfs(filters)`
- 第95行：`etf_data.get_etf_by_code(code)`
- 第113行：`etf_data.get_etf_by_code(code)`
- 第127行：`etf_data.get_etf_by_code(code)`
- 第136行：`etf_data.get_all_etfs()`
- 第222行：`etf_data.get_etf_by_code(code)`
- 第336行：`etf_data.get_etf_by_code(code)`

**问题**：如果 `etf_data.py` 接口变化，所有路由都要改。

### 问题3：`/api/etf/<code>/history` 逻辑过于复杂

**现状**：第228-358行（130行代码）包含了4层降级逻辑：
1. 本地历史文件
2. 本地缓存文件
3. AKShare 实时
4. 模拟数据

**问题**：路由函数超过100行，应该移到 Repository 层。

---

## 重构方案

### 架构目标

```
Flask 路由（Controller）
    ↓ 调用
Service 层（业务逻辑）
    ↓ 调用
Repository 层（数据访问）
    ↓ 实现
LocalJSONRepo / NeoDataRepo / CompositeRepo
```

### 路由重构清单

| 路由 | 当前行数 | 重构方案 | 调用 Service 方法 |
|------|---------|----------|-----------------|
| `/` | 36行 | **保持** - 不涉及业务逻辑 | - |
| `/api/etfs` | 47行 | **重构** - 移到 Service | `query_svc.get_etf_list()` |
| `/etf/<code>` | 14行 | **重构** - 移到 Service | `query_svc.get_etf_detail()` |
| `/compare` | 13行 | **重构** - 移到 Service | `compare_svc.compare_etfs()` |
| `/compare/wind` | 11行 | **重构** - 移到 Service | `compare_svc.compare_etfs()` |
| `/screening-demo` | 84行 | **重构** - 移到 Service | `screening_svc.screen_etfs()` |
| `/api/etf/<code>` | 7行 | **重构** - 移到 Service | `query_svc.get_etf_detail()` |
| `/api/etf/<code>/history` | 130行 | **重构** - 移到 Service | `history_svc.get_history()` |
| `/api/risk/<code>` | 74行 | **保持** - 风险逻辑独立 | - |
| `/risk/<code>` | 4行 | **保持** | - |
| `/api/data-status` | 30行 | **保持** - 基础设施 | - |
| `/api/version` | 13行 | **保持** | - |
| `/api/sync` | 44行 | **保持** - Git操作 | - |

**统计**：
- ✅ 保持（6个路由）：`/`, `/risk/<code>`, `/api/risk/<code>`, `/api/data-status`, `/api/version`, `/api/sync`
- 🔄 重构（6个路由）：`/api/etfs`, `/etf/<code>`, `/compare`, `/compare/wind`, `/screening-demo`, `/api/etf/<code>`, `/api/etf/<code>/history`

---

## 详细重构步骤

### Step 1：创建 Service 工厂函数

**文件**：`app.py`（顶部）

**目标**：创建 `get_service()` 函数，懒加载 Service 实例。

```python
# app.py 顶部（替换 import etf_data）

from services.etf_service_impl import (
    SimpleETFQueryService,
    SimpleETFCompareService,
    SimpleETFHistoryService,
    SimpleETFScreeningService
)
from repositories.composite_repo import CompositeRepo
from repositories.local_json_repo import LocalJSONRepo
from repositories.neodata_repo import NeoDataRepo

# 全局 Service 实例（懒加载）
_services = {}

def get_service(service_name: str):
    """
    获取 Service 实例（单例模式）
    
    Args:
        service_name: 'query' | 'compare' | 'history' | 'screening'
    """
    global _services
    
    if service_name not in _services:
        # 创建 Repository（共享实例）
        if 'repo' not in _services:
            local = LocalJSONRepo()
            online = NeoDataRepo()
            repo = CompositeRepo(local, online)
            _services['repo'] = repo
        
        repo = _services['repo']
        
        # 创建 Service
        if service_name == 'query':
            _services[service_name] = SimpleETFQueryService(repo)
        elif service_name == 'compare':
            _services[service_name] = SimpleETFCompareService(repo)
        elif service_name == 'history':
            _services[service_name] = SimpleETFHistoryService(repo)
        elif service_name == 'screening':
            _services[service_name] = SimpleETFScreeningService(repo)
    
    return _services[service_name]
```

---

### Step 2：重构 `/api/etfs` 路由

**当前代码**（第39-86行）：
```python
@app.route('/api/etfs')
def get_etfs():
    filters = {...}
    sort_by = request.args.get('sort_by', 'code')
    sort_order = request.args.get('sort_order', 'asc')
    page = int(request.args.get('page', 1))
    page_size = int(request.args.get('page_size', 50))
    
    etfs = etf_data.filter_etfs(filters)
    # ... 排序、分页、精简字段
```

**重构后**：
```python
@app.route('/api/etfs')
def get_etfs():
    """API：获取ETF列表（支持筛选、排序、分页）"""
    # 1. 解析参数
    filters = {
        "type": request.args.get('type', ''),
        "scale_min": request.args.get('scale_min', ''),
        "scale_max": request.args.get('scale_max', ''),
        "return_min": request.args.get('return_min', ''),
        "category": request.args.get('category', ''),
        "keyword": request.args.get('keyword', '')
    }
    filters = {k: v for k, v in filters.items() if v}
    
    sort_by = request.args.get('sort_by', 'code')
    sort_order = request.args.get('sort_order', 'asc')
    page = int(request.args.get('page', 1))
    page_size = int(request.args.get('page_size', 50))
    
    # 2. 调用 Service（所有业务逻辑都在 Service 里）
    query_svc = get_service('query')
    result = query_svc.get_etf_list(
        filters=filters,
        sort_by=sort_by,
        sort_order=sort_order,
        page=page,
        page_size=page_size
    )
    
    # 3. 返回 JSON（Controller 只管渲染）
    return jsonify(result)
```

**变化**：
- 路由从 47行 → 30行
- 排序/分页/字段精简逻辑移到 `SimpleETFQueryService.get_etf_list()`
- 路由只做：解析参数 → 调用 Service → 返回 JSON

---

### Step 3：重构 `/etf/<code>` 路由

**当前代码**（第89-102行）：
```python
@app.route('/etf/<code>')
def etf_detail(code):
    etf = etf_data.get_etf_by_code(code)
    if not etf:
        return "ETF不存在", 404
    etf['_price_source'] = 'local_cache'
    return render_template('detail.html', etf=etf)
```

**重构后**：
```python
@app.route('/etf/<code>')
def etf_detail(code):
    """ETF详情页"""
    query_svc = get_service('query')
    etf = query_svc.get_etf_detail(code)
    
    if not etf:
        return "ETF不存在", 404
    
    # 标记数据来源（Controller 逻辑）
    etf['_price_source'] = etf.get('_data_source', 'unknown')
    
    return render_template('detail.html', etf=etf)
```

---

### Step 4：重构 `/compare` 和 `/compare/wind` 路由

**当前代码**（第105-130行）：
```python
@app.route('/compare')
def compare():
    codes = request.args.get('codes', '').split(',')
    codes = [c for c in codes if c]
    etfs = []
    for code in codes:
        etf = etf_data.get_etf_by_code(code)
        if etf:
            etfs.append(etf)
    return render_template('compare.html', etfs=etfs)
```

**重构后**：
```python
@app.route('/compare')
def compare():
    """ETF对比页"""
    codes = request.args.get('codes', '').split(',')
    codes = [c for c in codes if c]
    
    compare_svc = get_service('compare')
    result = compare_svc.compare_etfs(codes)
    
    return render_template('compare.html', etfs=result['etfs'])

@app.route('/compare/wind')
def compare_wind():
    """ETF对比页 - Wind风格专业版"""
    codes = request.args.get('codes', '').split(',')
    codes = [c for c in codes if c]
    
    compare_svc = get_service('compare')
    result = compare_svc.compare_etfs(codes)
    
    return render_template('compare_v2_wind.html', etfs=result['etfs'])
```

---

### Step 5：重构 `/screening-demo` 路由

**当前代码**（第133-216行，84行）：
- 包含完整的筛选逻辑（3步筛选 + 评分）
- 应该移到 `SimpleETFScreeningService.screen_etfs()`

**重构后**：
```python
@app.route('/screening-demo')
def screening_demo():
    """筛选演示页 - 新能源ETF筛选过程"""
    screening_svc = get_service('screening')
    
    # 使用默认筛选条件（或从请求参数读取）
    criteria = screening_svc.get_default_screening_criteria()
    result = screening_svc.screen_etfs(criteria)
    
    return render_template(
        'screening-demo-v2.html',
        total_count=result['total_count'],
        screening_steps=result['steps'],
        winner=result['winner']
    )
```

---

### Step 6：重构 `/api/etf/<code>/history` 路由

**当前代码**（第228-358行，130行）：
- 4层降级逻辑（本地文件 → 本地缓存 → AKShare → 模拟）
- 应该移到 `SimpleETFHistoryService.get_history()`

**重构后**：
```python
@app.route('/api/etf/<code>/history')
def get_etf_history(code):
    """API：获取ETF历史净值（用于走势图）"""
    period = request.args.get('period', '1Y')
    
    history_svc = get_service('history')
    result = history_svc.get_history(code, period, normalized=True)
    
    return jsonify(result)
```

**关键**：4层降级逻辑已经在 `LocalJSONRepo.get_etf_history()` 里实现了（Task #17 的任务）。这里只需要简单调用 Service。

---

## 迁移顺序

### 阶段 A：准备（1天）

1. ✅ Task #21：创建 `ETFRepository` 抽象接口
2. ⏳ Task #17：创建 `LocalJSONRepo` 实现
3. ⏳ Task #19：创建 `NeoDataRepo` 实现
4. ⏳ Task #20：创建 `CompositeRepo` 组合实现

### 阶段 B：重构（2-3天）

5. ✅ Service 接口设计（已完成）
6. ✅ Service 实现（已完成）
7. **Task #18**：修改 `app.py` 接入 Service 层

### 阶段 C：验证（1天）

8. 测试所有路由功能
9. 部署到 PythonAnywhere
10. 监控错误日志

---

## 风险评估

### 高风险点

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| `/api/etf/<code>/history` 重构失败 | 历史走势图不可用 | 保留旧代码作为备用，逐步切换 |
| Service 层性能问题 | 响应变慢 | 加缓存，Profile 分析瓶颈 |
| Repository 层 bug | 所有功能失败 | 单元测试覆盖，灰度发布 |

### 回滚方案

如果重构后出现问题，可以快速回滚：
1. Git revert 重构提交
2. 重启 PythonAnywhere 应用
3. 恢复 `etf_data.py` 调用

---

## 验收标准

### 功能验收

- [ ] 首页加载正常（`/`）
- [ ] ETF 列表 API 正常（`/api/etfs`）
- [ ] ETF 详情页正常（`/etf/510300`）
- [ ] 对比页正常（`/compare?codes=510300,510500`）
- [ ] 筛选演示页正常（`/screening-demo`）
- [ ] 历史数据 API 正常（`/api/etf/510300/history`）

### 代码验收

- [ ] 所有 `etf_data.` 调用已移除
- [ ] 所有业务逻辑已移到 Service 层
- [ ] Controller 层只做参数解析和响应渲染
- [ ] 单元测试覆盖率 > 80%

---

## 附录：文件变更清单

| 文件 | 变更类型 | 说明 |
|------|----------|------|
| `app.py` | 🔄 重构 | 6个路由改为调用 Service |
| `services/etf_service_impl.py` | ✅ 已完成 | Service 层实现 |
| `repositories/composite_repo.py` | ⏳ 待完成 | CompositeRepo 组合实现 |
| `repositories/local_json_repo.py` | ⏳ 待完成 | LocalJSONRepo 实现 |
| `repositories/neodata_repo.py` | ⏳ 待完成 | NeoDataRepo 实现 |
| `etf_data.py` | 🗑️ 待删除 | 重构完成后删除 |
| `test_controller_refactor.py` | ✅ 新建 | Controller 层重构测试 |

---

**文档版本**: v1.0  
**创建时间**: 2026-05-20  
**作者**: AI Architect Agent
