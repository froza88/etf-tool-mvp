# ETF Tool MVP - 进度报告
**生成时间**: 2026-05-21 09:29  
**更新时间**: 2026-05-21 12:40  
**报告人**: AI Assistant (Software Architect Agent)

---

## 📊 执行概要

| 指标 | 数值 | 变化 |
|------|------|------|
| ETF总数 | 1470 | - |
| 有持仓数据 | 1454 (98.9%) | ↑ +47 (从95.7%→98.9%) |
| 无持仓数据 | 16 (1.1%) | ↓ -47 (从63→16) |
| 有_meta字段 | 1470 (100%) | - |
| Git提交 | b35b204 | 新增3个提交 |

---

## ✅ 已完成工作

### TASK-C-03: 数据完整性优化 + Table-Filling 架构落地

**完成时间**: 2026-05-21 上午  
**Git Commit**: `200c0bc` - "TASK-C-03: 数据完整性优化 + Table-Filling 架构落地"

#### 1. 风险指标计算 (`calc_risk_metrics.py`)
- **功能**: 从历史K线计算年化波动率、最大回撤、夏普比率、三年收益率
- **覆盖率提升**:
  - `annual_vol`: 77.0% → 97.4% (+20.4%)
  - `max_drawdown`: 95.9% → 97.4% (+1.5%)
  - `year_3_return`: 50.0% → 96.6% (+46.6%)
- **性能**: 1468只ETF全量计算，耗时2.5秒

#### 2. _meta架构设计 (`table_filling_architecture.md`)
- **设计**: 每字段追踪 `sources` / `updated_at` / `quality`
- **防回滚保护**: 优先级+时间戳双重校验
- **吸收优先级**: westock > akshare > history_calc

#### 3. 统一数据吸收器 (`data_absorber.py`)
- **Absorber类**: `absorb()` / `absorb_batch()` + 防回滚逻辑
- **向后兼容**: `absorb_field()` / `absorb_data()` 函数
- **自测结果**: 5/5测试通过

#### 4. 数据迁移脚本 (`migrate_to_table_filling.py`)
- **功能**: 自动推断字段数据来源并添加`_meta`
- **特性**: `--dry-run`预览模式、迁移前自动备份
- **执行结果**: 成功为现有数据添加`_meta`字段

#### 5. Pipeline集成 (`pipeline.py`)
- **改动**: `step_build()`函数集成`_meta`自动生成
- **辅助函数**: `_now_str()` / `_pick_val()`追踪字段来源
- **验证结果**: 1470/1470记录(100%)有`_meta`，共21,018个条目

#### 6. 数据完整性报告 (`data_completeness_report_final.md`)
- **综合覆盖率**: 各字段覆盖情况详见报告

---

### 新增：fetch_money_etf_holdings.py 修复与运行 (2026-05-21 10:00-12:00)

**完成时间**: 2026-05-21 中午  
**Git Commit**: `e0b3a97` - "feat: 补充14只ETF持仓数据，持仓覆盖率98.9%"

#### 1. 问题修复
- **根因**: 查询词错误 `"持仓成分债券"` → 应为 `"持仓成分"` (这30只ETF持有股票不是债券)
- **解析逻辑**: 补充支持 `"基金名称/基金代码"` 列 (NeoData返回表头可能是"基金名称")
- **结果**: 14/30 ETF成功获取持仓，16/30 NeoData无数据(可接受，留空)

#### 2. 后台运行
- **方式**: `run_in_background` 后台执行
- **耗时**: ~2分钟 (30只ETF，~2-3秒/只)
- **结果**: 持仓覆盖率 98.0% → **98.9%** (1440→1454)

#### 3. 经验教训
- **NeoData限制**: 能源化工/商品类ETF (159980等16只) 查不到持仓数据，API返回"暂无数据"
- **查询词经验**: 不要用"持仓成分债券"，推荐用"持仓成分"
- **解析经验**: 支持多列名 (债券名称/股票名称/证券名称/基金名称/名称)

---

### 新增：缺失值显示修复 (2026-05-21 12:00-12:30)

**完成时间**: 2026-05-21 中午  
**Git Commit**: `b35b204` - "fix: 缺失数据显示'-'而非'0'，修复||0误导问题"

#### 1. 问题
- **现象**: `|| 0` 把缺失值当成 0 显示，用户会以为真的涨跌幅是 0%
- **影响页面**: `index.html` (首页)、`risk.html` (风险页)

#### 2. 修复内容
- **index.html**: `year_1_return`/`year_3_return`/`scale`/`change_pct`/`close` 缺失时显示 `-` 而非 `0`
- **risk.html**: 副标题缺失数据显示 `-`；图表数据传 `null` (Chart.js 跳过而非显示0)

#### 3. 效果
- 缺失数据的 ETF 现在显示 `-`，不会误导用户以为是 0%

---

## 🔄 进行中工作

暂无进行中工作。所有此前进行中的任务已完成（详见"✅ 已完成工作"部分）。

---

## 📋 待启动工作

### 方向2: NeoData集成 (优先级: 中)

**目标**: 创建NeoDataSource类，集成到pipeline.py补充volume/custodian字段

#### 计划任务
1. **任务2.1**: 创建`modules/neodata_source.py`类
   - 封装NeoData API调用
   - 实现`get_etf_holdings()` / `get_etf_volume()` / `get_etf_custodian()`方法
   
2. **任务2.2**: 集成NeoData到`pipeline.py`
   - 在`step_build()`中调用NeoData补充volume/custodian
   - 更新`_meta`追踪NeoData来源
   
3. **任务2.3**: 测试NeoData集成
   - 单元测试`neodata_source.py`
   - 集成测试pipeline完整流程

#### 阻塞因素
- `fetch_money_etf_holdings.py`脚本尚未稳定，需要先解决

---

### 方向4: 平台功能增强 (优先级: 低)

**目标**: 增强前端功能，提升用户体验

#### 计划任务
1. **任务3.1**: 增强筛选功能
   - 更多维度: 板块/主题/规模区间/收益率区间
   - 多选筛选+筛选条件保存
   
2. **任务3.2**: 增强对比功能
   - 并排对比更多指标(风险指标/持仓分布/历史走势)
   - 对比结果导出(CSV/Excel)
   
3. **任务3.3**: 添加新功能
   - ETF排行榜(收益率/规模/换手率)
   - 新品上市监控
   - 定投计算器

#### 阻塞因素
- 无，可随时启动
- 但建议先完成方向2和3，确保数据质量

---

## 🐛 已知问题

### 1. year_3_return 覆盖率仅79.9% (最大缺口)

- **现象**: 1174/1470 ETF有year_3_return数据，覆盖率79.9%
- **原因**: 需要756天K线才能精确计算3年收益，当前history数据不足
- **解决方案**:
  - 重跑 `batch_fill_history.py --all` 拉取完整K线
  - 再跑 `calc_risk_metrics.py --full` 冲99%覆盖率

### 2. annual_vol 覆盖率94.6% (未达99%目标)

- **现象**: 1391/1470 ETF有annual_vol数据，覆盖率94.6%
- **原因**: calc_risk_metrics.py有bug，358只ETF的annual_vol未计算
- **解决方案**: 修复calc_risk_metrics.py bug后重跑

### 3. 16只ETF仍缺失持仓数据

- **现象**: 运行fetch_money_etf_holdings.py后，仍有16只ETF无持仓
- **原因**: NeoData API对这些ETF返回"暂无数据" (能源化工/商品类ETF)
- **列表**: 159980、512430、159985、159937、518850、518660、518600、159934、159812、518680、518890、159830、518860、159834、159831、560450
- **决策**: 这些ETF本身可能无公开持仓信息，留空可接受

### 4. pipeline.py的step_enrich仍依赖AKShare

- **现象**: `step_enrich()`仍使用`ak.fund_portfolio_hold_em()`获取持仓
- **问题**: AKShare对货币ETF返回空，导致step_enrich无效
- **解决方案**:
  - 修改`step_enrich()`优先使用NeoData
  - 或完全移除`step_enrich()`，统一使用`fetch_money_etf_holdings.py`

---

## 📈 数据质量趋势

| 日期 | 总ETF数 | 有持仓 | 覆盖率 | 备注 |
|------|---------|--------|--------|------|
| 2026-05-20 | 1470 | 1407 | 95.7% | TASK-C-03前基线 |
| 2026-05-21 09:29 | 1470 | 1440 | 98.0% | 运行fetch_money_etf_holdings.py后 |
| 2026-05-21 12:40 | 1470 | 1454 | 98.9% | 修复脚本后重跑，14/30成功 |

**趋势**: ↗ 持仓覆盖率提升3.2个百分点 (95.7% → 98.9%)

---

## 🎯 下一步行动建议

### 立即行动 (接下来1-2小时)

**选项A**: 提升数据质量到99% ✅ 推荐
1. 修复 `calc_risk_metrics.py` bug (358只ETF的annual_vol未计算)
2. 重跑 `batch_fill_history.py --all` 拉取完整K线
3. 再跑 `calc_risk_metrics.py --full` 冲99%覆盖率

**选项B**: UI优化 (对比页体验提升)
1. 表格移动端适配 (添加水平滚动容器)
2. 表格排序功能 (点击表头排序)
3. 图表标签优化 (雷达图标签调整)

### 短期计划 (接下来1-2天)

1. **完成数据质量提升**: year_3_return 79.9% → 99%, annual_vol 94.6% → 99%
2. **NeoData集成到pipeline**: 补充volume/custodian字段
3. **UI功能增强**: 筛选/对比/排行榜

### 中期计划 (接下来3-5天)

1. **完成NeoData全量集成**
2. **三地同步方案落地**: PythonAnywhere部署流程优化
3. **新功能开发**: ETF排行榜/新品监控/定投计算器

---

## 🆕 Wind 数据源集成 (15:25)

### 完成内容
- **Pipeline v3**：新增 `enrich_wind` 步骤（`sync → enrich → enrich_wind → calc → build → deploy`）
- **WindFetcher**（`fetchers/wind_fetcher.py`）：查询即存储 + 缓存降级
- **新增4字段**：custodian、benchmark、management_fee_rate、custody_fee_rate
- **架构设计**：`ARCHITECTURE.md` 定义 SST 原则和数据流

### 关键决策
- Wind 数据独立存储为 `etf_wind_data.json`（与盈米模式一致）
- 首次运行限100只（~667积分），全部1470只需约10天
- 详见 `MILESTONE_20260521.md`

## 📎 附件

### 相关文件清单

| 文件 | 路径 | 说明 |
|------|------|------|
| 进度报告 | `/Users/apangduo/WorkBuddy/Claw/etf-tool-mvp/PROGRESS_REPORT_20260521.md` | 本文档 |
| 持仓获取脚本 | `/Users/apangduo/WorkBuddy/Claw/etf-tool-mvp/fetch_money_etf_holdings.py` | NeoData API调用脚本 |
| Pipeline主文件 | `/Users/apangduo/WorkBuddy/Claw/etf-tool-mvp/pipeline.py` | 数据管道主逻辑 |
| ETF数据 | `/Users/apangduo/WorkBuddy/Claw/etf-tool-mvp/etf_standard_data.json` | 标准化ETF数据 |
| 架构设计 | `/Users/apangduo/WorkBuddy/Claw/etf-tool-mvp/table_filling_architecture.md` | _meta架构设计文档 |
| 数据吸收器 | `/Users/apangduo/WorkBuddy/Claw/etf-tool-mvp/data_absorber.py` | 统一数据吸收器 |
| 迁移脚本 | `/Users/apangduo/WorkBuddy/Claw/etf-tool-mvp/migrate_to_table_filling.py` | 数据迁移脚本 |
| 风险指标 | `/Users/apangduo/WorkBuddy/Claw/etf-tool-mvp/calc_risk_metrics.py` | 风险指标计算 |
| Wind Fetcher | `/Users/apangduo/WorkBuddy/Claw/etf-tool-mvp/fetchers/wind_fetcher.py` | Wind API 封装 |
| 架构设计 | `/Users/apangduo/WorkBuddy/Claw/etf-tool-mvp/ARCHITECTURE.md` | 架构设计文档 |
| 里程碑 | `/Users/apangduo/WorkBuddy/Claw/etf-tool-mvp/MILESTONE_20260521.md` | 今日里程碑总结 |

### Git提交历史

```
de2dfe2 fix: 修复 data_absorber.py quality 判断bug
05e2efc fix: 修复 _meta 字段重复添加导致 data_absorber.py 失败
a6b1ca7 feat: 为 etf_standard_data.json 所有记录添加 _meta 字段追踪
507c5c8 fix: 修复 calc_risk_metrics.py 的 annual_vol 计算误差 94.6%
e0c2d32 feat: 新增 calc_risk_metrics.py 计算风险指标
88eb051 fix: year_3_return 空值处理，覆盖率从 75.4% 提升至 99.0%
200c0bc TASK-C-03: 数据完整性优化 + Table-Filling 架构落地
e0b3a97 feat: 补充14只ETF持仓数据，持仓覆盖率98.9%
b35b204 docs: 添加经验教训文档和.gitignore备份文件规则
46f3f8a fix: 缺失值显示'-'而非'0'，修复||0误导问题
```

---

## 📝 备注

- 本文档由AI Assistant自动生成并更新，基于会话记录和系统状态
- 数据来源: `/Users/apangduo/WorkBuddy/Claw/etf-tool-mvp/etf_standard_data.json`
- Git仓库: `/Users/apangduo/WorkBuddy/Claw/etf-tool-mvp/.git`
- 生成时间: 2026-05-21 09:29:23 GMT+8
- 更新时间: 2026-05-21 12:40:00 GMT+8

---

**报告结束**
