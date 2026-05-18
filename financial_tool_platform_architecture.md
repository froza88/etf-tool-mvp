# 金融数据工具平台 - 架构设计

## 核心理念

```
MVP = 本地历史数据库 + 每日增量更新 + 按需查询接口
↓
可复用到：股票工具、基金工具、期货工具、外汇工具...
↓
金融数据工具系列
```

---

## 架构设计（可复用）

### 第1层：数据采集层（通用）

```python
# 所有金融工具共用同一套数据采集框架
financial_data_fetcher/
├── base_fetcher.py          # 基础获取器（重试、缓存、验证）
├── multi_source_fetcher.py  # 多源数据获取（AKShare、非凸、盈米...）
├── cache_manager.py         # 缓存管理器（永久缓存历史，增量更新实时）
├── rate_limiter.py          # 限流管理器（指数退避、多账号轮换）
└── data_validator.py       # 数据验证器（交叉验证、异常检测）
```

**通用逻辑（适用于所有金融工具）：**
```python
class FinancialDataFetcher:
    def __init__(self, data_type):  # 'etf', 'stock', 'fund', 'future', 'forex'
        self.data_type = data_type
        self.sources = self._load_sources(data_type)
        self.cache = self._load_cache(data_type)
    
    def fetch(self, code, fields=None):
        """获取单只产品的数据（多源 + 缓存）"""
        # 1. 检查缓存
        if self._in_cache(code, fields):
            return self.cache[code]
        
        # 2. 多源获取
        data = self._fetch_multi_source(code, fields)
        
        # 3. 验证
        if self._validate(data, fields):
            # 4. 存入缓存
            self.cache[code] = data
            self._save_cache()
            
        return data
    
    def daily_update(self):
        """每日更新（智能分批 + 增量）"""
        # 1. 加载所有产品列表
        all_codes = self._get_all_codes()
        
        # 2. 分类：无缓存 vs 有缓存
        no_cache = [c for c in all_codes if c not in self.cache]
        has_cache = [c for c in all_codes if c in self.cache]
        
        # 3. 分批处理（避免限流）
        batch_size = 200
        target = no_cache[:batch_size]
        
        # 4. 全量获取（无缓存的）
        for code in target:
            data = self.fetch(code)
            self._save_to_cache(code, data)
        
        # 5. 增量更新（有缓存的）
        for code in has_cache:
            data = self._fetch_incremental(code)  # 只获取最新1天
            self._update_cache(code, data)
        
        # 6. 保存
        self._save_cache()
```

---

### 第2层：数据模型层（每个工具不同）

```python
# ETF 数据模型
etf/models.py
├── ETFBase(BaseModel)        # 基础字段（代码、名称、发行人、规模）
├── ETFPrice(PriceModel)      # 价格字段（最新价、涨跌幅、昨收）
├── ETFHistory(HistoryModel)  # 历史K线（价格序列、日期序列）
├── ETFRisk(RiskModel)        # 风险指标（夏普、回撤、年化收益）
└── ETFHoldings(HoldingsModel) # 持仓数据（成分股、权重）

# 股票 数据模型（可复用部分模型）
stock/models.py
├── StockBase(BaseModel)      # 基础字段（代码、名称、行业、市值）
├── StockPrice(PriceModel)    # 价格字段（最新价、涨跌幅、昨收）
├── StockHistory(HistoryModel) # 历史K线
├── StockRisk(RiskModel)      # 风险指标
└── StockFinancials(FinancialModel) # 财务数据（ETF没有这个）

# 基金 数据模型
fund/models.py
├── FundBase(BaseModel)      # 基础字段（代码、名称、基金管理人、规模）
├── FundPrice(PriceModel)     # 净值（不是价格）
├── FundHistory(HistoryModel) # 历史净值
├── FundRisk(RiskModel)      # 风险指标
└── FundHoldings(HoldingsModel) # 持仓数据

# 期货 数据模型
future/models.py
├── FutureBase(BaseModel)    # 基础字段（代码、名称、交易所、杠杆）
├── FuturePrice(PriceModel)   # 价格字段（最新价、涨跌幅、昨结算价）
├── FutureHistory(HistoryModel) # 历史K线
└── FutureRisk(RiskModel)     # 风险指标（杠杆风险）

# 外汇 数据模型
forex/models.py
├── ForexBase(BaseModel)     # 基础字段（货币对、名称、国家）
├── ForexPrice(PriceModel)    # 价格字段（最新汇率、涨跌幅）
├── ForexHistory(HistoryModel) # 历史汇率
└── ForexRisk(RiskModel)     # 风险指标（波动率）
```

**共用的模型（可以抽象出来）：**
```python
# base/models.py
class BaseModel:
    code: str
    name: str
    updated: datetime

class PriceModel(BaseModel):
    close: float
    change_pct: float
    prev_close: float
    volume: float

class HistoryModel(BaseModel):
    prices: List[float]
    dates: List[str]
    count: int

class RiskModel(BaseModel):
    sharpe_ratio: float
    max_drawdown: float
    annual_vol: float
    year_1_return: float
    year_3_return: float
```

---

### 第3层：查询接口层（通用）

```python
# API 接口（所有工具共用）
api/
├── query.py          # 查询接口（按代码、按条件筛选）
├── compare.py        # 对比接口（多只产品对比）
├── screen.py         # 筛选接口（按指标筛选）
└── export.py         # 导出接口（Excel、PDF、图片）
```

**通用查询逻辑：**
```python
def query(code, fields=None):
    """查询单只产品的数据（从缓存读取）"""
    if code in cache:
        data = cache[code]
        if fields:
            return {f: data[f] for f in fields if f in data}
        return data
    else:
        # 缓存没有，实时获取
        return fetch_realtime(code, fields)

def compare(codes, fields):
    """对比多只产品"""
    result = []
    for code in codes:
        data = query(code, fields)
        result.append(data)
    return result

def screen(criteria):
    """筛选产品"""
    # criteria = {'year_1_return': '>10', 'sharpe_ratio': '>1'}
    result = []
    for code, data in cache.items():
        if matches_criteria(data, criteria):
            result.append(data)
    return sorted(result, key=lambda x: x['year_1_return'], reverse=True)
```

---

### 第4层：前端展示层（每个工具不同）

```python
# ETF 工具前端
etf/templates/
├── index.html        # 列表页
├── detail.html       # 详情页
├── compare.html      # 对比页
└── screen.html       # 筛选页

# 股票 工具前端（可复用 ETF 的模板结构）
stock/templates/
├── index.html        # 列表页（复用 ETF 的）
├── detail.html       # 详情页（适配股票字段）
├── compare.html      # 对比页（复用 ETF 的）
└── screen.html       # 筛选页（适配股票指标）

# 基金 工具前端
fund/templates/
├── index.html
├── detail.html       # 显示净值曲线（不是价格曲线）
├── compare.html
└── screen.html

# 期货 工具前端
future/templates/
├── index.html
├── detail.html       # 显示杠杆、保证金等
├── compare.html
└── screen.html

# 外汇 工具前端
forex/templates/
├── index.html
├── detail.html       # 显示货币对走势
├── compare.html
└── screen.html
```

---

## 实施计划

### 第1阶段：重构 ETF 工具（作为模板）（3-5天）

```bash
# 1. 重构数据采集层
#   - 创建 financial_data_fetcher/
#   - 实现通用获取、缓存、验证逻辑

# 2. 重构数据模型层
#   - 创建 etf/models.py
#   - 继承通用模型

# 3. 重构查询接口层
#   - 创建 api/query.py
#   - 实现通用查询、对比、筛选

# 4. 测试
#   - 确保 ETF 工具功能正常
```

---

### 第2阶段：扩展股票工具（2-3天）

```bash
# 1. 复用数据采集层
#   - 只需添加新的数据源（股票特有的）

# 2. 创建股票数据模型
#   - stock/models.py
#   - 继承通用模型 + 添加股票特有字段（财报、PE/PB等）

# 3. 复用查询接口层
#   - api/query.py 已经通用，只需添加股票特有字段的处理

# 4. 适配前端模板
#   - 复用 ETF 的模板结构
#   - 修改字段显示（价格 → 股价，净值 → 不适用）
```

---

### 第3阶段：扩展基金工具（2-3天）

```bash
# 类似股票工具，但：
#   - 价格 → 净值
#   - 持仓 → 基金经理 + 前十大重仓股
#   - 风险指标 → 同类排名
```

---

### 第4阶段：扩展期货工具（2-3天）

```bash
# 类似 ETF 工具，但：
#   - 价格 → 最新价（带杠杆）
#   - 风险指标 → 波动率 + 杠杆风险
#   - 添加保证金计算
```

---

### 第5阶段：扩展外汇工具（2-3天）

```bash
# 类似 ETF 工具，但：
#   - 价格 → 汇率
#   - 历史数据 → 汇率走势
#   - 风险指标 → 波动率
```

---

## 自动化任务合并

### 当前任务

| ID | 名称 | 时间 | 状态 | 说明 |
|----|----|------|------|------|
| automation-1778740392532 | ETF数据每日自动更新 | 每日 02:00 | ACTIVE | 需要删除 |
| automation-1779098526760 | ETF工具每日数据更新 | 每日 15:30 | ACTIVE | 保留，优化 |
| automation-1778742191295 | ETF工具自动部署 | 每10分钟 | PAUSED | 暂停，不需要 |

---

### 合并后的任务

```python
# 保留一个任务：ETF工具每日数据更新
{
  "name": "ETF工具每日数据更新（智能缓存）",
  "scheduleType": "recurring",
  "rrule": "RRULE:FREQ=DAILY;BYHOUR=15;BYMINUTE=30",
  "prompt": """
    执行 ETF 工具每日数据更新：
    1. 运行 daily_update.py（智能缓存策略）
    2. 优先构建缓存（每天200只无缓存ETF）
    3. 增量更新已有缓存的ETF（只获取最新1天）
    4. 完成后 git push
    5. 生成数据质量报告
  """,
  "status": "ACTIVE"
}
```

**优化点：**
- ✅ 智能分批（避免限流）
- ✅ 增量更新（快）
- ✅ 生成数据质量报告（监控）

---

## 立即行动

### 第1步：确认删除冗余自动化任务

**请在上方卡片中点击「确认删除」**，删除 `automation-1778740392532`（ETF数据每日自动更新 02:00）

### 第2步：优化保留的自动化任务

```python
# 更新 automation-1779098526760 的 prompt
automation_update(
    mode='update',
    id='automation-1779098526760',
    name='ETF工具每日数据更新（智能缓存）',
    prompt='''
        执行 ETF 工具每日数据更新：
        1. cd /Users/apangduo/WorkBuddy/Claw/etf-tool-mvp
        2. python3 daily_update.py --push
        3. 检查输出：缓存构建进度、成功率、失败率
        4. 如有失败，记录到日志
        5. 生成简要报告（缓存覆盖率、数据质量）
    '''
)
```

### 第3步：开始重构 ETF 工具（作为模板）

```bash
# 1. 创建通用数据采集框架
mkdir -p financial_data_fetcher
touch financial_data_fetcher/{__init__.py,base_fetcher.py,multi_source_fetcher.py,cache_manager.py}

# 2. 重构 daily_update.py
#   - 使用通用框架
#   - 保留智能缓存逻辑

# 3. 测试
python3 daily_update.py
```

---

## 预期效果

### 短期（1-2周）

```
✅ ETF 工具重构完成（作为模板）
✅ 自动化任务合并完成（一个任务，智能缓存）
✅ 数据覆盖率：从 34% → 100%（8天后）
✅ 执行时间：从 220秒 → 10秒（第9天开始）
```

### 中期（1-2个月）

```
✅ 股票工具上线（复用 ETF 架构）
✅ 基金工具上线（复用 ETF 架构）
✅ 期货工具上线（复用 ETF 架构）
✅ 外汇工具上线（复用 ETF 架构）
```

### 长期（3-6个月）

```
✅ 金融数据工具系列完整
✅ 每个工具都是：本地缓存 + 每日增量 + 按需查询
✅ 可快速扩展新的金融工具（加密货币、债券等）
✅ 数据质量监控系统（自动报警）
```

---

## 总结

**你的战略思路完全正确！**

```
MVP = 本地历史数据库 + 每日增量更新 + 按需查询接口
↓
可复用到：股票、基金、期货、外汇...
↓
金融数据工具系列（持续输出）
```

**立即行动：**
1. ✅ 确认删除冗余自动化任务
2. 📝 优化保留的自动化任务（智能缓存）
3. 🏗️ 开始重构 ETF 工具（作为模板）
4. 🚀 扩展到其他金融工具

---

## 🤔 你的选择？

**A. 立即开始重构 ETF 工具（作为模板）**  
→ 我会创建 `financial_data_fetcher/` 通用框架

**B. 先优化自动化任务**  
→ 我会更新 `automation-1779098526760` 的 prompt

**C. 先查看完整架构设计**  
→ 我打开刚才生成的架构设计文档

**D. 其他想法**  
→ 告诉我你的想法

---

**或者直接告诉我：**
- "开始重构" → 我创建通用框架
- "优化任务" → 我更新自动化任务
- "看架构" → 我打开设计文档"

你怎么选？😊
