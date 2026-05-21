# ETF工具MVP - 工作进度报告（2026-05-21）

## 已完成的任务

### A. 数据质量修复（用户指令：先做A）

**目标**：修复 `year_3_return` 默认值为0导致数据质量误判的问题

**完成工作**：
1. 修复3个Python文件中的默认值逻辑（0 → None）
   - `calc_risk_metrics.py:124` — 默认结果 `year_3_return/annual_vol` 从 `0.0` 改为 `None`
   - `build_standard_data.py:356` — `or 0` 去掉，保留 `None`
   - `multi_source_fetcher.py:217` — `else 0` 改为 `else None`
2. 重新运行 `calc_risk_metrics.py --full` 全量计算风险指标
3. 重新构建 `etf_standard_data.json`（通过 `build_standard_data.py`）

**成果**：
- `year_3_return` 覆盖率：**99.6%** (1464/1470) ✅ 达99%目标
- `annual_vol` 覆盖率：94.6% (1391/1470) ⚠️ 未达99%（疑似脚本bug，358只ETF未计算）
- `max_drawdown` 覆盖率：95.6% (1406/1470)
- `sharpe_ratio` 覆盖率：75.6% (1112/1470)

**Commit**: `88eb051`, `507c5c8`

---

### C1. Task #29 填表式存储方案 - 子任务2.1 & 2.2（用户指令：然后C）

**目标**：设计并实现填表式数据存储架构（_meta字段）

**完成工作**：

1. **子任务2.1**：创建 `migrate_to_table_filling.py` 迁移脚本
   - 为现有 `etf_standard_data.json` 每条记录添加 `_meta` 字段
   - `_meta[field]` 结构：`{"sources": ["akshare"], "updated_at": "...", "quality": "medium"}`
   - 数据源推断规则（启发式）：akshare/calculated/westock/manual/unknown

2. **子任务2.2**：修复 `data_absorber.py` bug（quality比较逻辑错误）
   - Bug位置：第186-188行 `_source_index(quality_string)` → 应该用 `quality_order.get()` 比较分数
   - 修复后：`quality_order = {"high":3, "medium":2, "low":1}` 正确比较

**成果**：
- `migrate_to_table_filling.py` 脚本可运行，生成正确 `_meta` 结构
- `etf_standard_data.json` 已迁移（含 `sources` 列表结构）
- `data_absorber.py` bug已修复

**Commit**: `a6b1ca7`, `05e2efc`, `de2dfe2`

---

## 进行中的任务

### C2. Task #29 填表式存储方案 - 子任务2.3

**目标**：更新 Pipeline 支持多数据源协同工作

**当前状态**：Pending（未开始）

**下一步**：
- 阅读 `pipeline.py` 了解当前流程
- 设计多数据源协同方案（absorb westock → absorb akshare → absorb yingmi → build）
- 实现并测试

---

## 待完成任务

1. **Task #28 收尾**：`annual_vol` 覆盖率94.6% → 99%+（调试 `calc_risk_metrics.py` 为什么358只ETF未计算）
2. **Task #29 子任务2.3**：Pipeline多数据源协同（进行中）
3. **Task #30**：本地一键部署脚本（TASK-C-02）
4. **Task #31**：ETF工具前端功能优化

---

## 关键决策点（需要您确认）

1. **优先级**：接下来先做哪个？
   - A. 继续 Task #29（完成子任务2.3 Pipeline协同）
   - B. 切换 Task #30（本地一键部署脚本）
   - C. 收尾 Task #28（调试 annual_vol bug）

2. **Task #28 annual_vol bug**：是否值得花时间调试？还是接受94.6%覆盖率，先推进其他任务？

3. **今日工作节奏**：已从 08:05 工作至今（约45分钟+），是否继续？还是休息切换模型？

---

## 项目Git状态

- **分支**: main（与 origin/main 分叉，我7 commits vs origin 1 commit）
- **未提交**: `.workbuddy/.../memory.md`（无关）
- **未跟踪**: `TAST-C-03_*` 文件、`apply_fix.py`、`fix_bug.py`（可清理）
- **建议**: 先 `git push origin main` 推送今日工作，或继续工作后再推？

---

_报告生成时间：2026-05-21 08:35（预估）_
