# ETF 数据字段频率分类报告（最终版）

生成时间: 2026-05-28 22:58  
数据来源: etf_standard_data.json (1480只ETF, 31个字段) + WeStock API测试结果

---

## 一、字段填充率与去留决策

| 中文字段名 | 英文字段名 | 填充率 | WeStock API | 决策 |
|-------------|-----------|--------|--------------|------|
| 代码 | code | 100.0% | ✅ 有 | ✅ 保留 |
| 名称 | name | 100.0% | ✅ 有 | ✅ 保留 |
| 规模 | scale | 100.0% | ✅ size | ✅ 保留 |
| 份额 | shares | 100.0% | ✅ shares | ✅ 保留 |
| 前十大持仓 | top_holdings | 100.0% | ✅ holdings | ✅ 保留 |
| 分类 | category | 100.0% | ❌ 无 | ✅ 保留(本地) |
| 发行人 | issuer | 99.9% | ✅ manageInstitution | ✅ 保留 |
| 成立日期 | issue_date | 99.1% | ✅ establishDate | ✅ 保留 |
| 收盘价 | close | 99.1% | ✅ closePrice | ✅ 保留 |
| 昨收价 | prev_close | 99.1% | ❌ 无 | ✅ 保留(计算) |
| 年化收益率(1年) | year_1_return | 98.6% | ✅ return1Y | ✅ 保留 |
| 涨跌幅 | change_rate | 98.3% | ✅ changePct | ✅ 保留 |
| 涨跌额 | change_pct | 97.0% | ❌ 无 | ✅ 保留(计算) |
| 最大回撤 | max_drawdown | 96.6% | ✅ maxDrawdown1Y | ✅ 保留 |
| 卡玛比率 | calmar_ratio | 96.2% | ❌ 无 | ✅ 保留(盈米) |
| 夏普比率 | sharpe_ratio | 96.1% | ❌ 无 | ✅ 保留(盈米) |
| 年化波动率 | annual_vol | 96.1% | ❌ 无 | ✅ 保留(盈米) |
| 年化收益率(3年) | year_3_return | 49.6% | ✅ return3Y | ✅ 保留 |
| 3年年度报告 | annual_3y | 49.2% | ❌ 无 | ✅ 保留(计算) |
| 业绩基准 | benchmark | 6.6% | ❌ 无 | ❌ **删除** |
| 成交量 | volume | 5.7% | ❌ 无 | ❌ **删除** |
| 托管人 | custodian | 0.0% | ✅ trusteeInstitution | ✅ 保留 |
| 管理费率 | management_fee_rate | 0.0% | ✅ managementFee | ✅ 保留 |
| 托管费率 | custody_fee_rate | 0.0% | ✅ custodyFee | ✅ 保留 |
| 综合费率 | fee_rate | 0.0% | ❌ 无 | ✅ 保留(计算) |
| 跟踪误差 | tracking_error | 0.0% | ❌ 无 | ❌ **删除** |
| 溢价率 | premium_discount | 0.0% | ❌ 无 | ❌ **删除** |
| 估值分位 | valuation_percentile | 0.0% | ❌ 无 | ❌ **删除** |
| 5日资金流向 | net_inflow_5d | 0.0% | ❌ 无 | ❌ **删除** |

---

## 二、新增字段（从WeStock API发现）

| 中文字段名 | 英文字段名 | 说明 | 频率 |
|-------------|-----------|------|------|
| 年初至今收益率 | ytd_return | 今年以来收益 | 📅 年度 |
| 1个月收益率 | return_1m | 近1月收益 | 📆 月度 |
| 3个月收益率 | return_3m | 近3月收益 | 📆 月度 |
| 6个月收益率 | return_6m | 近6月收益 | 📆 月度 |
| 1个月最大回撤 | max_drawdown_1m | 近1月最大回撤 | 📈 日度 |
| 3个月最大回撤 | max_drawdown_3m | 近3月最大回撤 | 📈 日度 |
| 6个月最大回撤 | max_drawdown_6m | 近6月最大回撤 | 📈 日度 |
| 1年最大回撤 | max_drawdown_1y | 近1年最大回撤 | 📈 日度 |
| 3年最大回撤 | max_drawdown_3y | 近3年最大回撤 | 📈 日度 |
| 年初至今最大回撤 | ytd_max_drawdown | 今年以来最大回撤 | 📅 年度 |

---

## 三、按更新频率分类（5个文件 + 新增字段）

### 1. 长期不变数据 `etf_static.json` (12个字段)

| 中文字段名 | 英文字段名 |
|-------------|-------------|
| 代码 | code |
| 名称 | name |
| 发行人 | issuer |
| 成立日期 | issue_date |
| 托管人 | custodian |
| 分类 | category |
| 管理费率 | management_fee_rate |
| 托管费率 | custody_fee_rate |
| 综合费率 | fee_rate |
| 跟踪指数代码 | track_index_code |
| 跟踪指数名称 | track_index_name |

### 2. 年度变化数据 `etf_annual.json` (6个字段)

| 中文字段名 | 英文字段名 | 说明 |
|-------------|-------------|------|
| 年化收益率(1年) | year_1_return | |
| 年化收益率(3年) | year_3_return | ⚠️ 需恢复至99% |
| 年初至今收益率 | ytd_return | 新增 |
| 年初至今最大回撤 | ytd_max_drawdown | 新增 |
| 3年年度报告 | annual_3y | |
| 跟踪指数年度收益 | index_1y_return | 新增 |

### 3. 季度变化数据 `etf_quarterly.json` (1个字段)

| 中文字段名 | 英文字段名 |
|-------------|-------------|
| 前十大持仓 | top_holdings |

### 4. 月度变化数据 `etf_monthly.json` (3个字段)

| 中文字段名 | 英文字段名 |
|-------------|-------------|
| 1个月收益率 | return_1m |
| 3个月收益率 | return_3m |
| 6个月收益率 | return_6m |

### 5. 日度变化数据 `etf_daily.json` (19个字段)

| 中文字段名 | 英文字段名 | 数据源 |
|-------------|-------------|---------|
| 规模 | scale | WeStock |
| 份额 | shares | WeStock |
| 收盘价 | close | WeStock |
| 昨收价 | prev_close | 计算 |
| 涨跌幅 | change_rate | WeStock |
| 涨跌额 | change_pct | 计算 |
| 最大回撤(1年) | max_drawdown | WeStock |
| 夏普比率 | sharpe_ratio | 盈米 |
| 年化波动率 | annual_vol | 盈米 |
| 卡玛比率 | calmar_ratio | 盈米 |
| 1个月最大回撤 | max_drawdown_1m | WeStock |
| 3个月最大回撤 | max_drawdown_3m | WeStock |
| 6个月最大回撤 | max_drawdown_6m | WeStock |
| 1年最大回撤 | max_drawdown_1y | WeStock |
| 3年最大回撤 | max_drawdown_3y | WeStock |
| 换手率 | turnover_rate | WeStock |
| 成交额 | turnover_value | WeStock |
| 溢价率 | discount_ratio | WeStock |
| 资产配比-股票 | stock_ratio | WeStock |

---

## 四、数据来源优先级

1. **WeStock API** - 基础数据、价格、收益率、回撤、持仓
2. **盈米 API** - 风险指标(Sharpe/Vol/Calmar)
3. **AKShare** - 备用(ETF列表、实时行情)
4. **本地计算** - prev_close, change_pct, fee_rate等

---

## 五、下一步行动

1. ✅ **确认字段分类** - 请确认上面"二、新增字段"和"三、按更新频率分类"是否正确
2. 🔧 **开始数据迁移** - 从 etf_standard_data.json 按频率拆分到5个文件
3. 📋 **生成待补清单** - 哪些ETF缺失 year_3_return 等字段，需要人工填补

**请确认或提出修改意见，我立即开始数据迁移。**
