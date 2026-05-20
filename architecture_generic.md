# 通用金融工具架构设计文档

> 日期：2026-05-20  
> 设计人：Software Architect Agent  
> 版本：v2.0 - 通用架构（支持 ETF/股票/期货/指数等）

---

## 一、架构目标

### 1.1 设计目标

1. **通用性** — 一套架构支持多种金融工具（ETF、股票、期货、债券、基金、指数）
2. **可扩展** — 新增金融工具类型只需继承基类，无需修改现有代码
3. **类型安全** — 使用 Python TypeVar + Generic 实现编译时类型检查
4. **向后兼容** — 保留现有 ETF 接口，平滑迁移

### 1.2 架构原则

1. **模型分层** — `FinancialInstrument`（基类）→ `ETF`/`Stock`/`Future`（子类）
2. **Repository 泛型** — `FinancialInstrumentRepository[T]`（通用接口）→ `ETFRepository`（特化接口）
3. **Service 泛型** — `FinancialInstrumentQueryService[T]`（通用服务）→ `ETFQueryService`（特化服务）
4. **依赖倒置** — 高层模块依赖抽象接口，不依赖具体实现

---

## 二、架构分层

```
┌─────────────────────────────────────────────────────────────┐
│                    Route 层（Flask）                          │
│  /api/etfs?type=etf|stock|future  GET  — 通用列表查询      │
│  /api/instruments/<code>         GET  — 通用详情            │
│  /compare                        GET  — 通用对比页           │
│  /api/history/<code>             GET  — 通用历史走势         │
└─────────────────────────┬───────────────────────────────────┘
                          │ 调用 Service（泛型）
                          ▼
┌─────────────────────────────────────────────────────────────┐
│              Service 层（业务逻辑，泛型）                       │
│                                                              │
│  FinancialInstrumentQueryService[T]  — 通用查询              │
│    ├── ETFQueryService  — ETF 查询（扩展）                   │
│    ├── StockQueryService  — 股票查询（未来）                 │
│    └── FutureQueryService  — 期货查询（未来）                │
│                                                              │
│  FinancialInstrumentCompareService[T]  — 通用对比           │
│    └── ETFCompareService  — ETF 对比                        │
│                                                              │
│  FinancialInstrumentHistoryService[T]  — 通用历史           │
│    └── ETFHistoryService  — ETF 历史                        │
│                                                              │
│  FinancialInstrumentScreeningService[T]  — 通用筛选         │
│    └── ETFScreeningService  — ETF 筛选                      │
│                                                              │
│  FinancialInstrumentAnalyticsService[T]  — 通用分析         │
│    └── ETFAnalyticsService  — ETF 分析                      │
│                                                              │
│  Service 只依赖 Repository 接口，不关心数据来源              │
└─────────────────────────┬───────────────────────────────────┘
                          │ 调用 Repository（泛型）
                          ▼
┌─────────────────────────────────────────────────────────────┐
│          Repository 层（数据访问，泛型 + 组合）                │
│                                                              │
│  FinancialInstrumentRepository[T] (ABC)  — 通用接口         │
│    ├── ETFRepository  — ETF 接口（扩展通用接口）             │
│    ├── StockRepository  — 股票接口（未来）                   │
│    └── FutureRepository  — 期货接口（未来）                  │
│                                                              │
│  实现类：                                                     │
│  ├── LocalJSONRepo[T]  — 本地 JSON 存储（通用实现）        │
│  │     ├── LocalJSONETFRepo  — ETF 本地存储                 │
│  │     ├── LocalJSONStockRepo  — 股票本地存储（未来）       │
│  │     └── LocalJSONFutureRepo  — 期货本地存储（未来）     │
│  │                                                          │
│  ├── NeoDataRepo[T]  — NeoData API（通用实现）             │
│  │     ├── NeoDataETFRepo  — ETF NeoData                   │
│  │     └── NeoDataStockRepo  — 股票 NeoData（未来）        │
│  │                                                          │
│  └── CompositeRepo[T]  — 组合 Repository（本地优先）       │
│        ├── CompositeETFRepo  — ETF 组合                     │
│        └── CompositeStockRepo  — 股票组合（未来）            │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 三、核心设计

### 3.1 模型层（`models/financial_instrument.py`）

#### 基类：`FinancialInstrument`

```python
class FinancialInstrument:
    """金融工具基类"""
    
    # 通用字段
    code: str               # 代码
    name: str               # 名称
    instrument_type: InstrumentType  # 类型（ETF/STOCK/FUTURE/...）
    issuer: Optional[str]   # 发行人
    price: Optional[float]  # 最新价格
    scale: Optional[float]  # 规模
    return_1y: Optional[float]  # 年化收益率
    sharpe_ratio: Optional[float]  # 夏普比率
    max_drawdown: Optional[float]  # 最大回撤
    volatility: Optional[float]  # 波动率
    
    # 时间字段
    created_at: datetime
    updated_at: datetime
    
    # 扩展字段
    extra: Dict[str, Any]  # 存储原始数据
```

#### 子类

| 类 | 特有字段 | 说明 |
|----|----------|------|
| `ETF` | `expense_ratio`, `tracking_index`, `holdings`, `category` | ETF 基金 |
| `Stock` | `market`, `industry`, `pe_ratio`, `pb_ratio`, `market_cap` | 股票 |
| `Future` | `underlying`, `contract_multiplier`, `margin_ratio`, `expire_date` | 期货 |
| `Bond` | `coupon_rate`, `maturity_date`, `issuer_rating`, `bond_type` | 债券 |
| `Fund` | `fund_type`, `manager`, `fund_company`, `nav` | 公募基金 |
| `Index` | `publisher`, `base_date`, `base_point`, `components` | 指数 |

#### 类型枚举：`InstrumentType`

```python
class InstrumentType(Enum):
    ETF = "etf"
    STOCK = "stock"
    FUTURE = "future"
    BOND = "bond"
    FUND = "fund"
    INDEX = "index"
```

---

### 3.2 Repository 层（`repositories/`）

#### 通用接口：`FinancialInstrumentRepository[T]`

```python
T = TypeVar('T', bound=FinancialInstrument)

class FinancialInstrumentRepository(ABC, Generic[T]):
    """金融工具数据访问抽象接口（通用）"""
    
    @abstractmethod
    def get_all(self) -> List[T]: ...
    
    @abstractmethod
    def get_by_code(self, code: str) -> Optional[T]: ...
    
    @abstractmethod
    def filter(self, filters: Dict[str, Any]) -> List[T]: ...
    
    @abstractmethod
    def get_history(self, code: str, period: str = '1Y') -> Dict[str, Any]: ...
    
    @abstractmethod
    def save(self, instrument: T) -> None: ...
    
    @abstractmethod
    def save_batch(self, instruments: List[T]) -> None: ...
    
    # 默认实现
    def search(self, keyword: str, limit: int = 10) -> List[T]: ...
    def get_by_type(self, instrument_type: InstrumentType) -> List[T]: ...
    def count(self, filters: Optional[Dict[str, Any]] = None) -> int: ...
```

#### 组合 Repository：`CompositeFinancialInstrumentRepository[T]`

实现"**本地优先 + 在线兜底**"策略：

```python
class CompositeFinancialInstrumentRepository(FinancialInstrumentRepository[T]):
    def __init__(
        self,
        primary: FinancialInstrumentRepository[T],  # 本地存储（优先）
        fallbacks: List[FinancialInstrumentRepository[T]]  # 在线 API（兜底）
    ): ...
    
    def get_by_code(self, code: str) -> Optional[T]:
        # 1. 先查 primary（本地）
        item = self.primary.get_by_code(code)
        if item:
            return item
        
        # 2. 本地没有，查 fallbacks（在线）
        for fallback in self.fallbacks:
            item = fallback.get_by_code(code)
            if item:
                # 3. 查到后写回 primary（缓存）
                self.primary.save(item)
                return item
        
        return None
```

#### ETF 特化接口：`ETFRepository`

```python
class ETFRepository(FinancialInstrumentRepository[ETF]):
    """ETF 数据访问接口（继承通用接口，添加 ETF 特有方法）"""
    
    # 兼容旧接口的方法
    @abstractmethod
    def get_all_etfs(self) -> List[Dict]: ...
    
    @abstractmethod
    def get_etf_by_code(self, code: str) -> Optional[Dict]: ...
    
    # ETF 特有方法
    @abstractmethod
    def get_etf_holdings(self, code: str) -> List[Dict]: ...
    
    @abstractmethod
    def get_etf_by_tracking_index(self, index_code: str) -> List[Dict]: ...
    
    @abstractmethod
    def get_etf_by_category(self, category: str) -> List[Dict]: ...
```

---

### 3.3 Service 层（`services/`）

#### 通用接口

| 服务接口 | 职责 | 主要方法 |
|----------|------|----------|
| `FinancialInstrumentQueryService[T]` | 查询/筛选/搜索 | `get_list()`, `get_detail()`, `search()`, `get_by_type()` |
| `FinancialInstrumentCompareService[T]` | 对比/排名 | `compare()`, `get_compare_metrics()`, `rank()` |
| `FinancialInstrumentHistoryService[T]` | 历史数据 | `get_history()`, `get_multiple_history()`, `calculate_return()` |
| `FinancialInstrumentScreeningService[T]` | 条件筛选 | `screen()`, `get_default_criteria()`, `get_available_filters()` |
| `FinancialInstrumentAnalyticsService[T]` | 风险分析 | `calculate_sharpe_ratio()`, `calculate_max_drawdown()`, `correlation_analysis()` |

#### ETF 特化接口

| 服务接口 | 继承 | ETF 特有方法 |
|----------|------|---------------|
| `ETFQueryService` | `FinancialInstrumentQueryService[ETF]` | `get_etf_list_by_category()`, `get_etf_list_by_tracking_index()` |
| `ETFCompareService` | `FinancialInstrumentCompareService[ETF]` | （无，与通用一致） |
| `ETFHistoryService` | `FinancialInstrumentHistoryService[ETF]` | `get_etf_nav_history()` |
| `ETFScreeningService` | `FinancialInstrumentScreeningService[ETF]` | `screen_by_category()`, `get_etf_screening_templates()` |

---

## 四、文件结构

```
etf-tool-mvp/
├── models/                          ← 模型层（新）
│   ├── __init__.py
│   └── financial_instrument.py     ← FinancialInstrument 基类 + 子类
│
├── repositories/                    ← 数据层（重构）
│   ├── __init__.py
│   ├── financial_instrument_repository.py  ← 通用 Repository 接口
│   ├── composite_repo.py                  ← 组合 Repository（通用）
│   ├── etf_repository.py                  ← ETF Repository 接口（重构）
│   ├── local_json_repo.py                 ← 本地 JSON 实现（待重构）
│   ├── neodata_repo.py                    ← NeoData API 实现（待创建）
│   └── westock_repo.py                    ← Westock API 实现（待创建）
│
├── services/                        ← 业务层（重构）
│   ├── __init__.py
│   ├── financial_instrument_service.py    ← 通用 Service 接口
│   ├── etf_service.py                     ← ETF Service 接口（重构）
│   ├── etf_service_impl.py                ← ETF Service 实现（待重构）
│   ├── stock_service.py                    ← 股票 Service 接口（未来）
│   └── future_service.py                  ← 期货 Service 接口（未来）
│
├── app.py                          ← Route 层（待重构）
├── templates/                      ← 前端（保持）
├── static/                        ← 静态资源（保持）
└── data/                          ← 数据文件（保持）
```

---

## 五、扩展性分析

### 5.1 新增金融工具类型（如股票）

**步骤**：

1. **模型层** — `models/financial_instrument.py` 已包含 `Stock` 类，无需修改
2. **Repository 层** — 创建 `StockRepository` 继承 `FinancialInstrumentRepository[Stock]`
3. **Service 层** — 创建 `StockQueryService` 继承 `FinancialInstrumentQueryService[Stock]`
4. **实现层** — 创建 `LocalJSONStockRepo` 和 `NeoDataStockRepo`
5. **Route 层** — 添加 `/api/stocks` 路由，或复用通用路由 `/api/instruments?type=stock`

**代码量**：~200 行（主要是 Repository 和 Service 实现）

### 5.2 新增数据源（如 iFinD）

**步骤**：

1. **Repository 层** — 创建 `IFinDRepo[T]` 继承 `FinancialInstrumentRepository[T]`
2. **组合配置** — 在 `CompositeRepo` 的 `fallbacks` 中添加 `IFinDRepo`

**代码量**：~100 行（主要是 API 调用逻辑）

### 5.3 新增分析功能（如因子分析）

**步骤**：

1. **Service 层** — 创建 `FinancialInstrumentFactorService[T]` 继承 `FinancialInstrumentAnalyticsService[T]`
2. **实现层** — 实现因子计算逻辑

**代码量**：~300 行（主要是计算逻辑）

---

## 六、迁移计划

### Phase 1：模型层迁移（不影响现有功能）

- [ ] 确认 `models/financial_instrument.py` 设计
- [ ] 创建 `repositories/financial_instrument_repository.py`
- [ ] 重构 `repositories/etf_repository.py` 继承通用接口
- [ ] 创建 `services/financial_instrument_service.py`
- [ ] 重构 `services/etf_service.py` 继承通用接口

**验证**：运行现有测试，确保行为一致

### Phase 2：Repository 实现迁移

- [ ] 重构 `LocalJSONETFRepo` 继承 `ETFRepository`
- [ ] 创建 `NeoDataETFRepo` 继承 `ETFRepository`
- [ ] 创建 `CompositeETFRepo` 继承 `CompositeFinancialInstrumentRepository[ETF]`
- [ ] 测试 CompositeRepo 策略（本地优先 + 在线兜底）

**验证**：访问 `/etf/510300`，确认能从 NeoData 获取最新数据

### Phase 3：Service 实现迁移

- [ ] 重构 `ETFQueryServiceImpl` 继承 `ETFQueryService`
- [ ] 重构 `ETFCompareServiceImpl` 继承 `ETFCompareService`
- [ ] 重构 `ETFHistoryServiceImpl` 继承 `ETFHistoryService`
- [ ] 测试所有 Service 方法

**验证**：运行 Service 层测试（30+ 测试用例）

### Phase 4：Route 层迁移（通用化）

- [ ] 重构 `app.py` 路由，支持 `?type=etf|stock|future`
- [ ] 创建通用路由处理函
- [ ] 测试所有页面（列表/详情/对比/历史）

**验证**：手动测试所有功能

### Phase 5：扩展新类型（股票）

- [ ] 创建 `StockRepository` 接口
- [ ] 创建 `LocalJSONStockRepo` 实现
- [ ] 创建 `StockQueryService` 接口
- [ ] 添加 `/api/stocks` 路由
- [ ] 测试股票查询功能

**验证**：访问 `/api/stocks?keyword=平安`，确认能查到股票

---

## 七、决策记录（ADR）

### ADR-001：采用泛型架构支持多金融工具

**状态**：Proposed

**背景**：
- 现有系统只支持 ETF，用户希望扩展到股票、期货等
- 如果为每种工具创建独立架构，会导致代码重复
- 需要一套通用架构，新增工具类型时只需继承基类

**决策**：
采用 Python `TypeVar` + `Generic` 实现泛型架构：
- `FinancialInstrumentRepository[T]` — 通用数据访问接口
- `FinancialInstrumentQueryService[T]` — 通用查询服务
- `ETFRepository` 继承 `FinancialInstrumentRepository[ETF]` — ETF 特化

**后果**：
- ✅ 新增工具类型只需继承基类（~200 行代码）
- ✅ 类型安全，IDE 能提供更好的补全
- ✅ 代码复用率高，逻辑统一
- ❌ 泛型增加代码复杂度，学习曲线陡峭
- ❌ 需要重构现有代码（ETF Repository/Service）

---

## 八、下一步行动

1. [ ] **确认架构设计** — 你 review 这个通用架构方案，确认是否同意
2. [ ] **开始 Phase 1** — 迁移模型层和接口层，不影响现有功能
3. [ ] **测试验证** — 确保重构后现有测试全部通过
4. [ ] **更新任务列表** — 把架构迁移任务加入工作清单

---

*本文档是通用架构设计方案，具体实现前需要确认技术细节（特别是泛型设计是否过于复杂）。*

*当前进度：已完成模型层和接口层设计（Phase 1 前期），待确认后开始实现。*
