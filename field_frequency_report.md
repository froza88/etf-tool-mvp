# ETF 数据字段频率分类报告

生成时间: 2026-05-28 22:42
数据来源: etf_standard_data.json (1480只ETF, 31个字段)

## 字段填充率总览

| 字段名 | 填充数 | 填充率 | 分类建议 |
|--------|--------|--------|----------|
| code | 1480 | 100.0% | ✅ 长期不变 |
| name | 1480 | 100.0% | ✅ 长期不变 |
| scale | 1480 | 100.0% | 📈 日度变化 |
| shares | 1480 | 100.0% | 📈 日度变化 |
| top_holdings | 1480 | 100.0% | 📅 季度变化 |
| category | 1480 | 100.0% | ✅ 长期不变 |
| issuer | 1478 | 99.9% | ✅ 长期不变 |
| issuer_full | 1478 | 99.9% | ✅ 长期不变 |
| issuer_short | 1478 | 99.9% | ✅ 长期不变 |
| issue_date | 1466 | 99.1% | ✅ 长期不变 |
| close | 1466 | 99.1% | 📈 日度变化 |
| prev_close | 1466 | 99.1% | 📈 日度变化 |
| year_1_return | 1459 | 98.6% | 📅 年度变化 |
| change_rate | 1455 | 98.3% | 📈 日度变化 |
| change_pct | 1435 | 97.0% | 📈 日度变化 |
| max_drawdown | 1430 | 96.6% | 📈 日度变化* |
| calmar_ratio | 1424 | 96.2% | 📈 日度变化* |
| sharpe_ratio | 1422 | 96.1% | 📈 日度变化* |
| annual_vol | 1422 | 96.1% | 📈 日度变化* |
| year_3_return | 734 | 49.6% | 📅 年度变化 |
| annual_3y | 728 | 49.2% | 📅 年度变化 |
| benchmark | 98 | 6.6% | 📅 年度变化 |
| volume | 84 | 5.7% | 📈 日度变化 |
| custodian | 0 | 0.0% | ✅ 长期不变 |
| management_fee_rate | 0 | 0.0% | ✅ 长期不变 |
| custody_fee_rate | 0 | 0.0% | ✅ 长期不变 |
| fee_rate | 0 | 0.0% | ✅ 长期不变 |
| tracking_error | 0 | 0.0% | 📈 日度变化 |
| premium_discount | 0 | 0.0% | 📈 日度变化 |
| valuation_percentile | 0 | 0.0% | 📈 日度变化 |
| net_inflow_5d | 0 | 0.0% | 📈 日度变化 |

*注: 风险指标(max_drawdown/calmar_ratio/sharpe_ratio/annual_vol)基于滚动窗口计算，每天变化

## 按频率分类 (5个文件)

### 1. etf_static.json (长期不变, 11个字段)
- code (代码)
- name (名称)
- issuer (发行人)
- issuer_full (发行人全称)
- issuer_short (发行人简称)
- issue_date (成立日期)
- custodian (托管人)
- category (分类)
- management_fee_rate (管理费率)
- custody_fee_rate (托管费率)
- fee_rate (综合费率)

### 2. etf_annual.json (年度变化, 4个字段)
- year_1_return (年化收益率)
- year_3_return (3年年化收益率) ⚠️ 当前49.6%需恢复
- annual_3y (3年年度报告)
- benchmark (业绩基准)

### 3. etf_quarterly.json (季度变化, 1个字段)
- top_holdings (前十大持仓)

### 4. etf_monthly.json (月度变化, 0个字段)
- 当前数据无月度字段，预留接口

### 5. etf_daily.json (日度变化, 15个字段)
- scale (规模)
- shares (份额)
- close (收盘价)
- prev_close (昨收价)
- change_pct (涨跌幅)
- change_rate (涨跌额)
- volume (成交量)
- max_drawdown (最大回撤)
- sharpe_ratio (夏普比率)
- annual_vol (年化波动率)
- calmar_ratio (卡玛比率)
- tracking_error (跟踪误差)
- premium_discount (溢价率)
- valuation_percentile (估值分位)
- net_inflow_5d (5日资金流向)

## 待确认问题

1. **风险指标频率**: max_drawdown/sharpe_ratio/annual_vol/calmar_ratio 应该日度更新还是周度/月度？
2. **benchmark字段**: 当前只有6.6%填充率，是否必要？数据来源？
3. **volume字段**: 当前只有5.7%填充率，是否必要？
4. **新增月度字段**: 是否需要添加monthly_return(月度收益率)字段？

## 下一步

请确认以上分类是否正确，特别是标注⚠️的字段。
确认后，我将开始创建新的文件结构。
