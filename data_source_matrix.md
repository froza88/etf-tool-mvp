# ETF数据源覆盖矩阵

**生成时间**: 2026-05-28 23:15  
**测试标的**: 510300.SH (华泰柏瑞沪深300ETF)

---

## 数据矩阵表格

| 字段类别 | 字段名(中/英) | WeStock | Wind | 盈米 | 推荐数据源 | 抓取频率 |
|---------|---------------|---------|------|------|-----------|-----------|
| **基础信息** | | | | | | |
| | 代码 (code) | ✅ | ✅ | ✅ | WeStock | 长期 |
| | 名称 (name) | ✅ | ✅ | ✅ | WeStock | 长期 |
| | 发行人 (issuer) | ✅ | ✅ (基金管理人) | ❌ | WeStock | 长期 |
| | 成立日期 (establish_date) | ✅ | ✅ | ❌ | WeStock | 长期 |
| | 基金类型 (fund_type) | ✅ | ✅ (投资类型) | ❌ | WeStock | 长期 |
| | 跟踪指数代码 (track_index_code) | ✅ | ✅ | ❌ | WeStock | 长期 |
| | 跟踪指数名称 (track_index_name) | ✅ | ✅ | ❌ | WeStock | 长期 |
| | 管理费率 (management_fee) | ✅ | ❌ | ❌ | WeStock | 长期 |
| | 托管费率 (custody_fee) | ✅ | ❌ | ❌ | WeStock | 长期 |
| | 总资产 (total_asset) | ✅ | ✅ (资产合计) | ❌ | WeStock | 日度 |
| **规模数据** | | | | | | |
| | 规模 (scale) | ✅ | ✅ (资产合计) | ❌ | WeStock | 日度 |
| | 份额 (shares) | ✅ | ❌ | ❌ | WeStock | 日度 |
| **价格数据** | | | | | | |
| | 最新价 (latest_price) | ✅ | ✅ (最新成交价) | ✅ | WeStock | 日度 |
| | 涨跌幅 (change_pct) | ✅ | ✅ | ✅ | WeStock | 日度 |
| | 昨收 (prev_close) | ✅ | ❌ | ❌ | WeStock | 日度 |
| **收益率** | | | | | | |
| | 年初至今收益率 (ytd_return) | ✅ (returnYTD) | ✅ | ❌ | WeStock | 日度 |
| | 近1月收益率 (return_1m) | ✅ (return1M) | ✅ | ❌ | WeStock | 月度 |
| | 近3月收益率 (return_3m) | ✅ (return3M) | ✅ | ❌ | WeStock | 月度 |
| | 近6月收益率 (return_6m) | ✅ (return6M) | ✅ | ❌ | WeStock | 月度 |
| | 近1年收益率 (return_1y) | ✅ (return1Y) | ✅ | ✅ | WeStock | 年度 |
| | 近3年收益率 (return_3y) | ✅ (return3Y) | ✅ | ✅ | WeStock | 年度 |
| **风险指标** | | | | | | |
| | 最大回撤-近1月 (max_dd_1m) | ✅ (maxDrawdown1M) | ✅ | ❌ | Wind | 日度 |
| | 最大回撤-近3月 (max_dd_3m) | ✅ (maxDrawdown3M) | ✅ | ❌ | Wind | 日度 |
| | 最大回撤-近6月 (max_dd_6m) | ✅ (maxDrawdown6M) | ✅ | ❌ | Wind | 日度 |
| | 最大回撤-近1年 (max_dd_1y) | ✅ (maxDrawdown1Y) | ✅ | ✅ | Wind | 日度 |
| | 最大回撤-近3年 (max_dd_3y) | ✅ (maxDrawdown3Y) | ✅ | ✅ | Wind | 日度 |
| | 夏普比率-近1年 (sharpe_1y) | ❌ | ✅ | ✅ | Wind | 日度 |
| | 年化波动率-近1年 (volatility_1y) | ❌ | ✅ | ✅ | Wind | 日度 |
| | 卡玛比率-近1年 (calmar_1y) | ❌ | ❌ | ✅ | 盈米 | 日度 |
| **持仓数据** | | | | | | |
| | 前十大持仓 (top_holdings) | ✅ | ✅ | ❌ | WeStock | 季度 |
| | 持股数量 (holding_amount) | ✅ | ✅ | ❌ | Wind | 季度 |
| | 持股市值 (holding_value) | ✅ | ✅ | ❌ | Wind | 季度 |
| **财务数据** | | | | | | |
| | 基金资产合计 (total_assets) | ❌ | ✅ | ❌ | Wind | 季度 |
| | 基金收入合计 (total_income) | ❌ | ✅ | ❌ | Wind | 季度 |
| | 基金净利润 (net_profit) | ❌ | ✅ | ❌ | Wind | 季度 |
| | 银行存款 (bank_deposit) | ❌ | ✅ | ❌ | Wind | 季度 |
| | 应收利息 (interest_receivable) | ❌ | ✅ | ❌ | Wind | 季度 |

---

## 数据源能力总结

### WeStock (免费，主要数据源)
**优势**:
- ✅ 基础信息完整（代码/名称/发行人/费率）
- ✅ 价格数据实时（最新价/涨跌幅）
- ✅ 收益率数据全面（1月/3月/6月/1年/3年）
- ✅ 持仓数据（前十大重仓股）
- ✅ API稳定，免费

**劣势**:
- ❌ 风险指标不完整（缺夏普/波动率）
- ❌ 财务数据无

**适用字段**: 基础信息、价格、收益率、持仓

---

### Wind (付费，权威数据源)
**优势**:
- ✅ 风险指标权威（夏普/波动率/最大回撤）
- ✅ 财务数据完整（资产/收入/利润）
- ✅ 持仓数据详细（持股数量/市值）
- ✅ 数据质量高

**劣势**:
- ❌ 付费（需要积分/订阅）
- ❌ API可能限流

**适用字段**: 风险指标、财务数据、详细持仓

---

### 盈米 (免费/付费未知)
**优势**:
- ✅ 风险指标完整（夏普/波动率/卡玛）
- ✅ 收益率数据（1年/3年）

**劣势**:
- ❌ 基础信息无
- ❌ 持仓数据无
- ❌ 财务数据无

**适用字段**: 风险指标（备选，Wind优先）

---

## 抓取方案

### 方案原则
1. **本地优先**: 先读本地文件，有数据就不调API
2. **免费优先**: WeStock免费，优先用；Wind付费，只在必要时用
3. **权威优先**: 风险指标用Wind（比盈米权威）
4. **增量合并**: 每次只更新变化的字段，不覆盖已有数据

---

### 抓取频率与数据源分配

#### 1. 长期不变数据 (etf_static.json)
**更新频率**: 手动触发（ETF发行/退市时）  
**数据源**: WeStock  
**字段**:
- code, name, issuer, establish_date, fund_type
- track_index_code, track_index_name
- management_fee, custody_fee

**抓取逻辑**:
```python
# 只在ETF首次入库或手动触发时抓取
if etf['code'] not in local_data:
    data = fetch_westock(etf['code'])
    save_to_etf_static(data)
```

---

#### 2. 年度变化数据 (etf_annual.json)
**更新频率**: 每年1月（年报发布后）  
**数据源**: WeStock (return_1y/return_3y)  
**字段**:
- return_1y, return_3y
- year_report (年报URL，可选)

**抓取逻辑**:
```python
# 每年1月批量更新
if today.month == 1 and today.day <= 31:
    data = fetch_westock(etf['code'], fields=['return1Y', 'return3Y'])
    merge_to_etf_annual(etf['code'], data)
```

---

#### 3. 季度变化数据 (etf_quarterly.json)
**更新频率**: 每季度结束后的月份（1/4/7/10月）  
**数据源**: WeStock (持仓) + Wind (财务)  
**字段**:
- top_holdings (WeStock)
- total_assets, total_income, net_profit (Wind，可选)

**抓取逻辑**:
```python
# 每季度结束后的15天（季报发布期）批量更新
quarter_end_months = [1, 4, 7, 10]
if today.month in quarter_end_months and 1 <= today.day <= 15:
    # WeStock - 持仓
    holdings = fetch_westock(etf['code'], fields=['holdings'])
    save_to_etf_quarterly(etf['code'], 'holdings', holdings)
    
    # Wind - 财务（可选，积分不够可跳过）
    if wind_quota_enough():
        financials = fetch_wind(etf['code'], fields=['total_assets', 'net_profit'])
        save_to_etf_quarterly(etf['code'], 'financials', financials)
```

---

#### 4. 月度变化数据 (etf_monthly.json)
**更新频率**: 每月1-5号  
**数据源**: WeStock  
**字段**:
- return_1m, return_3m, return_6m

**抓取逻辑**:
```python
# 每月1-5号批量更新
if 1 <= today.day <= 5:
    data = fetch_westock(etf['code'], fields=['return1M', 'return3M', 'return6M'])
    merge_to_etf_monthly(etf['code'], data)
```

---

#### 5. 日度变化数据 (etf_daily.json)
**更新频率**: 每天收盘后（15:30后）  
**数据源**: WeStock (价格/规模) + Wind (风险指标)  
**字段**:
- latest_price, change_pct, prev_close (WeStock)
- scale, total_asset (WeStock)
- max_dd_1y, sharpe_1y, volatility_1y (Wind)

**抓取逻辑**:
```python
# 每天15:30后批量更新
if now.hour >= 15 and now.minute >= 30:
    # WeStock - 价格/规模（免费，必抓）
    price_data = fetch_westock(etf['code'], fields=['latestPrice', 'changePct', 'scale'])
    merge_to_etf_daily(etf['code'], price_data)
    
    # Wind - 风险指标（付费，积分够才抓）
    if wind_quota_enough():
        risk_data = fetch_wind(etf['code'], fields=['maxDrawdown1Y', 'sharpeRatio1Y', 'volatility1Y'])
        merge_to_etf_daily(etf['code'], risk_data)
    else:
        log_warning(f"Wind quota insufficient, skip risk metrics for {etf['code']}")
```

---

### 抓取优先级与降级策略

#### 优先级排序
1. **P0 (必须)**: WeStock - 基础/价格/收益率/持仓（免费）
2. **P1 (重要)**: Wind - 风险指标（付费，但核心）
3. **P2 (可选)**: Wind - 财务数据（积分不够可放弃）

#### 降级策略
| 场景 | 降级方案 |
|------|-----------|
| WeStock API失败 | 重试3次 → 跳过该ETF → 记录日志 |
| Wind API限流 | 等待60秒 → 重试 → 仍失败则跳过，明天再试 |
| Wind积分不足 | 放弃Wind，用盈米补充风险指标（如果盈米免费） |
| 本地已有数据 | 绝不覆盖，只补充缺失字段 |

---

### 实施步骤（P0，今明两天）

#### 第1步：创建新文件结构（今天晚上）
```bash
etf-tool-mvp/
├── etf_static.json      # 长期不变
├── etf_annual.json      # 年度变化
├── etf_quarterly.json   # 季度变化
├── etf_monthly.json     # 月度变化
├── etf_daily.json       # 日度变化
└── etf_standard.json    # 标准表（合并上面5个，对外展示）
```

#### 第2步：数据迁移（明天上午）
- 从 `etf_standard_data.json` (备份) 按频率拆分到5个文件
- **本地优先**: 已有数据直接搬，不重新抓取
- **缺的标记**: 记录哪些字段/ETF缺失，生成待补清单

#### 第3步：修复pipeline逻辑（明天下午）
- `step_build()` 改为：读5个文件 → 只更新对应频率的字段 → 合并成 `etf_standard.json`
- 加入"本地优先"逻辑：先检查本地文件，有就不调API

#### 第4步：测试+部署（后天）
- 跑一次pipeline，确认数据不丢失
- 部署到PythonAnywhere

---

## 待确认问题

### 问题1：Wind积分管理
**问**: Wind API有积分限制吗？每次调用消耗多少积分？  
**建议**: 如果积分有限，风险指标可以：
- A. 每天只更新Top 200 ETF（流动性好的）
- B. 每周更新一次（而不是每天）
- C. 用盈米补充（如果盈米免费）

### 问题2：财务数据是否必要？
**问**: 财务数据（资产/收入/利润）对ETF对比重要吗？  
**建议**: 
- A. 保留，逐步补全（Wind积分够的话）
- B. 删除，不重要（ETF主要看净值/风险，不是财务）

### 问题3：抓取时间窗口
**问**: 日度数据每天几点开始抓？Wind风险指标每天必须抓吗？  
**建议**:
- WeStock价格/规模：每天15:30后（收盘后）
- Wind风险指标：每周一抓一次（风险指标变化慢）

---

**请确认以上方案，特别是**:
1. Wind积分管理策略（问题1）
2. 财务数据是否保留（问题2）
3. 抓取时间窗口（问题3）

确认后，我立即开始实施第1步（创建新文件结构）。
