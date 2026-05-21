# 经验教训总结 - ETF Tool MVP

> 生成时间: 2026-05-21 10:08
> 目的: 避免重复犯错，淘汰浪费时间的操作

---

## 1. 数据质量相关教训

### 1.1 `year_3_return` 默认值 bug（已修复）

**问题**: `calc_risk_metrics.py` 中 `year_3_return` 默认值是 `0`，导致：
- 数据库里存了大量 `year_3_return: 0`（假数据）
- 覆盖率计算时 `0` 被算作"有数据"，实际应该是"无数据"
- 修复后覆盖率从 75.4% 跳升到 99.0%

**教训**: 
- 数值型字段的"无数据"应该用 `None`，不要用 `0`
- `0` 是有意义的值（如收益率可以为 0），不能作为缺失标记
- 所有数值字段默认值检查：`annual_vol`、`max_drawdown`、`sharpe_ratio` 是否也有同样问题

**已修复文件**:
- `calc_risk_metrics.py`: `year_3_return` 默认 `None`
- `build_standard_data.py`: 同
- `multi_source_fetcher.py`: 同

---

### 1.2 `fetch_money_etf_holdings.py` 查询词错误（已修复）

**问题**: 查询词写的是 `"159980能源化工ETF的持仓成分债券"`，但这 30 只 ETF 是**黄金/跨境/商品类**，持有的是**股票**不是债券。

**后果**: NeoData API 返回空数据，误以为这些 ETF 真的没有持仓数据。

**教训**:
- 查询词要**通用**，不要预设资产类型（"债券"）
- 应该用 `"持仓成分"` 或 `"持仓股票"`，让 API 自己返回
- **测试第一位**: 改查询词后先用 `--dry-run --limit=2` 验证，不要直接全量跑

**已修复**: 查询词改为 `"{code} {name} 持仓成分"`

---

### 1.3 `_parse_markdown_table` 缺列名（已修复）

**问题**: 解析逻辑只认 `债券名称/股票名称/证券名称`，但 NeoData 返回的实际列名是 `基金名称`。

**后果**: 解析失败，返回 0 个持仓。

**教训**:
- Markdown 表格解析要**预判多种列名变体**
- 列名列表要全面：`名称/基金名称/股票名称/债券名称/证券名称`
- 同理代码列：`代码/基金代码/股票代码/债券代码/证券代码`

**已修复**: 增加 `基金名称`、`基金代码` 到解析逻辑

---

### 1.4 `batch_fill_history.py` 硬编码 `limit=500`（已修复）

**问题**: `get_ohlcs()` 函数硬编码 `limit=500`，导致每只 ETF 最多只拉到 ~500 天 K 线。

**后果**: `calc_risk_metrics.py` 只能用 ~500 天数据计算，`year_3_return` 只能近似 2 年，无法精确 3 年。

**教训**:
- **不要硬编码 limit**，除非 API 有明确限制
- 如果 API 支持"不传 limit 返回全部"，就应该不传
- 修改后要用 `--dry-run` 验证新逻辑是否真的拉到更多数据

**已修复**: `limit=500` → `limit=None`，不传 limit 时 API 返回全部

---

## 2. Git 操作教训

### 2.1 `git pull` 导致死循环（历史问题，已记录）

**问题**: PA 部署时用 `git pull`，但 PA 的 remote URL 是旧的，导致一直 "Already up to date"。

**教训**: PA 是生产环境，用 `git reset --hard origin/main`，不用 `git pull`。

**已记录**: `PYTHONANYWHERE_DEPLOY_RULES.md`（工作记忆）

---

### 2.2 `git rebase` 冲突处理不当

**问题**: 本次会话中，本地有 8 个提交，远程有 1 个新提交。尝试 `git pull --rebase` 遇到冲突，处理混乱。

**正确做法**:
1. 如果本地提交还没推过：`git reset --hard origin/main` 丢弃本地提交，重新 apply 改动
2. 如果本地提交已推过：`git push --force-with-lease`（谨慎）

**本次做法**（最终成功）:
```bash
git rebase --abort          # 取消失败的 rebase
git reset --hard origin/main # 丢弃本地提交，回到远程状态
git stash pop              # 把未提交的改动 apply 回来
# 解决冲突（etf_standard_data.json）
git add etf_standard_data.json
git commit
git push origin main
```

---

## 3. 调试效率教训

### 3.1 不要"猜"，要"看"

**坏模式**: 看到 `0 个持仓` 就猜是 API 问题，然后去改查询词、改解析逻辑，反复试。

**好模式**: 
1. 先 `print(content[:2000])` 看 API 到底返回了什么
2. 确认有数据后，再调试解析逻辑
3. 用 `python3 -c "..."` 快速测试，不要每次都跑整个脚本

**本次改进**: 最后用 `python3 -c` 直接测试 `_parse_markdown_table`，快速定位到 `基金名称` 缺失。

---

### 3.2 后台任务进度不可见

**问题**: `run_in_background` 后，任务在跑但看不到实时进度，只能等 `TaskOutput`。

**改进方向**:
- 脚本输出写到文件（`tee` 或 `>> log.txt`）
- 或者用 `tail -f log.txt` 在另一个终端看
- 本次没有改进，下次可以考虑

---

## 4. 需要淘汰的浪费时间操作

### 4.1 重复备份 `etf_standard_data.json`

**问题**: 每次改动都自动备份（`etf_standard_data.json.backup_20260521_XXXXXX`），导致 repo 里有一堆备份文件。

**浪费**: 这些备份文件不应该进 git，每次都要 `git reset HEAD` 去掉。

**改进**: 
- 备份逻辑改为写到 `data/backup/daily/` 或 `/tmp/`，不要写项目根目录
- 或者干脆不备份，用 git 版本控制就够了

---

### 4.2 `fetch_money_etf_holdings.py` 的 `time.sleep(1)`

**问题**: 每只 ETF 间隔 1 秒，30 只就要 30 秒。

**可以优化**: NeoData API 如果不限速，可以去掉 `sleep`，或者减到 0.3 秒。

**风险**: 可能触发 API 限流。先不优化，等下次需要跑大量 ETF 时再考虑。

---

### 4.3 `calc_risk_metrics.py` 重复计算

**问题**: 每次 `--full` 都重新计算所有 1468 只 ETF 的风险指标，耗时 2.5 秒。

**可以优化**: 只计算 `_meta` 里 `updated_at` 超过 7 天的 ETF。

**风险**: 逻辑复杂，容易漏算。当前 2.5 秒可以接受，不优化。

---

## 5. 下次优先事项

1. **`year_3_return` 覆盖率 79.9%** → 需要重跑 `batch_fill_history.py --all` 拉取完整 K 线，再跑 `calc_risk_metrics.py --full`
2. **部署到 PythonAnywhere** → 让线上版本可用
3. **Web UI 功能增强** → 筛选/对比/排行榜

---

*本文档由 AI Assistant 根据 2026-05-21 会话记录整理*
