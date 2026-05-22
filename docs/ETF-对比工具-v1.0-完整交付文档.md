# ETF 对比工具 v1.0 - 完整交付文档

**项目**: ETF 对比工具 MVP  
**版本**: v1.0  
**交付日期**: 2026-05-23  
**交付人**: WorkBuddy AI Team  
**用户**: apangduo  

---

## 📋 项目概述

### 目标
构建一个专业的 ETF 对比分析工具，支持多维度对比（流动性、风险、收益）、可视化呈现、数据导出，帮助投资者快速做出决策。

### 核心卖点
- **多维度对比**: 11 个指标（规模、回撤、波动率、夏普比率、收益率等）
- **可视化呈现**: 环形图、热力图、赢家标注
- **数据导出**: 打印优化版本，适合分享
- **专业感**: 暗色主题、金融终端风格

---

## 📅 完整工作日志（2026-05-14 至 2026-05-23）

### 2026-05-14 - 初始 MVP 搭建

#### 完成事项
1. **澄清模型身份**
   - Hy3 Preview = 腾讯混元大模型（295B总参数，21B激活参数）
   - Hermes 3 = NousResearch开源模型（非当前使用）
   - DeepSeek V4 = 深度求索MoE模型（1.6T参数，2026年4月24日发布）

2. **部署ETF工具到PythonAnywhere**
   - 创建 `etf_data_new.py`（从etf_complete_130.json加载数据）
   - 替换旧版 `etf_data.py`
   - 测试Flask应用：API成功返回99只ETF
   - 创建部署包 `etf-tool-deployment.zip`

3. **自动更新数据**
   - 创建 `auto_update_etf_data.py`（自动爬取最新ETF数据）
   - 测试成功：146.7秒完成99只ETF数据更新
   - 设置cron定时任务（每天凌晨2点）

#### 技术细节
- **性能提升**: 旧方法7.6小时 → 新方法2.4分钟（190倍提升）
- **非凸数据技能调用**: 通过 `run.py` 脚本调用，非Skill工具

---

### 2026-05-15 - GitHub Actions 部署调试

#### 问题与解决
1. **GitHub Actions 页面 404**
   - 原因：仓库名大小写敏感
   - 正确链接：`https://github.com/froza88/etf-tool-mvp/actions`

2. **SSH 部署失败**
   - 错误：`ssh: handshake failed: ssh: unable to authenticate`
   - **根本原因：PythonAnywhere 免费账户不支持 SSH**
   - 解决：改用 PythonAnywhere API 部署

3. **deploy.yml 修复**
   - 修复 bash 语法错误：`if [["` → `if [ "`
   - 已更新 `pythonanywhere-deploy` skill

#### 当前状态
- workflow 文件已推送，API 方式
- 用户正在配置 `PA_API_TOKEN` GitHub Secret

---

### 2026-05-16 - 数据质量大修复

#### 修复的问题
1. **top_holdings 数据串用**
   - 根因：`etf-component/handler.py` 缺少 `X-Client-Name: ft-claw` Header
   - 修复：加 Header + 修复交易所后缀判断 + 去重

2. **名称显示修复**
   - 根因：全量数据 `manager` 字段全空
   - 修复：新增 `_extract_name_issuer()` + `_build_known_names()` 两级匹配
   - 效果：从90只覆盖提升到1169/1461只

3. **前端适配**
   - `top_holdings` 改为字典格式
   - `detail.html` 条件渲染空持仓
   - `index.html` issuer 为空时不显示尾部 `-`

#### 架构重建（重大变更）
- **问题根源**：三源合并 + 运行时转换是反复出 bug 的根因
- **重建方案**：
  - 新增 `build_standard_data.py` — 一次性数据清洗标准化脚本
  - 新增 `etf_standard_data.json` — 唯一标准化数据源（1461只）
  - 重写 `etf_data.py` — 从 200+ 行简化为 50 行

#### 模块化拆分
- 创建 `modules/` 目录，6个独立可复用模块
- 其他工具可 `from modules.data_source import AKShareSource` 直接复用

---

### 2026-05-17 - 数据质量全面提升

#### 修复
- JS崩溃: `etf.type`→`etf.category`, 添加try-catch
- 规模: AKShare返回基金份额, 改成份额×close计算
- 涨跌幅: 1位→2位小数
- 详情页: 标题用基金简写, 发行方用全名
- 排序: 默认按code升序
- 年化波动/回撤/夏普: 自算（非凸OHLC日K线）

#### 新增功能
- 数据来源底部(带免责声明)
- 详情页: 前收盘价、份额字段
- 成立日、托管行→非凸
- 风险指标页面 `/risk/<code>` : 按需调盈米, 多周期对比图表

#### 代码清理
- 删除88个废弃文件(旧脚本/临时数据/旧文档)
- 清理 `__pycache__`

---

### 2026-05-18 - 大版本改动（风险页/对比页/数据质量）

#### 风险指标页面（risk.html）
- 首次加载自动显示自算数据
- 提供「📊 获取盈米数据」按钮
- 盈米失败则显示重试按钮

#### 对比页（compare.html）全面优化
- 新增雷达图（五维：规模/收益/回撤/夏普/流动性）
- 新增柱状图（规模 + 日均成交）
- 最佳值金框高亮
- 对比行重排：代码/类型/发行方/成立日期 → 规模/日均成交/近1年收益

#### MVP 全面检视
- 生成报告：`mvp_inspection_report.md`
- **关键发现**：
  - `year_3_return` 完全缺失（0%）
  - `volume` 仅6.1%
  - `issuer_full` 完全缺失（0%）
  - `compare.html` 调用未定义函数 `fetchWithTimeout`
  - `detail.html` 走势图是模拟数据

#### 梁山好汉并行任务执行
- 10位"梁山好汉"Agent并行执行修复任务
- 结果：calc_metrics.py成功1411/1466 (96.2%)，enrich_prices.py成功1466/1466 (100%)

---

### 2026-05-19 - 数据同步 + 吸收式架构

#### Wind 数据补充尝试
- 运行 `wind_supplement.py` 脚本
- 被 SIGTERM 终止（在 ETF #102）
- Wind API 返回 BALANCE_INSUFFICIENT（积分不足）

#### 数据同步策略
- **核心理念**：采用"吸收式架构"——能获取就保存，本地即权威
- **实施**：创建 `absorb_westock_etf_data.py` 脚本
- **原则**：取并集、填表式、版本快照

#### PA 部署死循环
- 调试 PA 部署问题陷入死循环 18 分钟
- 根本原因：PA 的 `origin` URL 是旧的
- 新规则：PA 部署用 `git reset --hard`

---

### 2026-05-20 - 对比页 v3 开发

#### 对比页 v3（Pro Terminal 风格）
- 文件：`templates/compare_v3.html`
- 设计：暗色主题、金融终端风格（Bloomberg/TradingView）
- 功能：Hero Section、圈图对比、热力图、导出页

#### 历史K线填充
- 脚本：`batch_fill_history.py`（非凸 OHLC API）
- 已完成 Top 200 ETF 填充
- 205只ETF在 `data/history/`，平均463条/只

---

### 2026-05-21 - Wind 数据获取 + 产品战略定调

#### Wind 数据获取（凌晨）
- 运行 `wind_supplement.py`（午夜0:00积分重置后）
- 消耗 83 次 API 调用（约 415 积分）
- 成功获取 159 只 ETF 的 Wind 数据
- 数据质量检查：核心字段 100% 填充

#### 产品战略定调
- **核心决策**：对比页是核心卖点和差异化优势
- **方向**：先把 ETF 对比做到极致，再做通用对比引擎
- **影响**：后续开发资源优先投入 compare_v3.html

#### 对比页优化
- 圈图加粗：stroke-width 8px → 16px
- 圈图分层：默认6个核心指标，展开显示全部11个

---

### 2026-05-22 - 对比页极致优化

#### 对比页 v3 继续优化
- 数据时效性优化：Header 显示"3分钟前更新"
- 走势对比图：增加 Chart.js 收益率曲线图
- 设计评审（截图分析）：发现6个问题

#### 设计评审结论
- 优点：配色成熟、圈图加粗效果明显
- 缺点：信息层级颠倒、benchmark标签多余、双环图内环无效
- 优化方案：Plan A（重构层级）、Plan B（删benchmark）、Plan C（拆双环）、Plan D（统一颜色）

---

### 2026-05-23 - 交付文档完善

#### 早上：Wind 数据检查 + 对比页优化
- Wind 数据质量复查：确认 159 只 ETF 核心字段 100% 填充
- 对比页继续优化（圈图加粗、分层展示、数据时效性、走势图）

#### 下午：交付文档打包
- 用户要求将全部记忆、对话内容、自己总结的 Skill 打包成完整 Markdown 交付文档
- 完成工作：
  1. ✅ 追加对话记忆摘要（5段，5/14-5/22）为附录4
  2. ✅ 区分并打包自己总结的 13 个 Skill 为附录5
  3. ✅ 追加今日对话记忆（5/23）为附录6

**交付文档最终状态**：
- 总行数：4172 行
- 文件大小：125.1 KB
- 附录数量：6 个

---

## 📊 数据质量报告（2026-05-23）

| 指标 | 覆盖率 | 状态 | 说明 |
|------|--------|------|------|
| ETF总数 | 1473/1473 (100%) | ✅ | |
| 发行人 | 1472/1473 (99.9%) | ✅ | |
| 最新价 | 1466/1473 (99.7%) | ✅ | |
| 收益率(1y) | 1111/1473 (75.4%) | ⚠️ | 缺 362 只 |
| 夏普比率 | 1418/1473 (96.3%) | ✅ | |
| 持仓 | 1454/1473 (98.9%) | ✅ | |
| annual_vol | 1422/1473 (96.5%) | ✅ | |
| max_drawdown | 1430/1473 (97.1%) | ✅ | |
| year_3_return | 1174/1473 (79.9%) | ❌ | 最大缺口，需 756 天 K 线 |
| 规模 | 1473/1473 (100%) | ✅ | |
| 分类 | 1473/1473 (100%) | ✅ | |
| Wind 代码 | 159/1473 (10.8%) | ⚠️ | 进行中，需 16 天完成 |

**关键缺口**：year_3_return 79.9% — 需要756天K线，当前history数据不足。

---

## 🗂️ 文件变更清单（完整版）

### 核心文件
| 文件路径 | 变更类型 | 说明 |
|---------|---------|------|
| `etf_standard_data.json` | 修改 | ETF 主数据文件（1473 只 ETF） |
| `templates/compare_v3.html` | 修改 | 对比页 v3 主模板（多次优化） |
| `app.py` | 修改 | Flask 应用，新增 `/compare/v3` 路由 + API 架构重构 |
| `scripts/wind_supplement.py` | 新增 | Wind 数据补充脚本 |
| `pipeline.py` | 新增/修改 | 统一入口脚本（v1→v2） |
| `services/etf_data_service.py` | 新增 | 数据服务层（可插拔数据源） |
| `services/cache_updater.py` | 新增 | 后台缓存更新服务 |
| `repositories/composite_repo.py` | 新增 | CompositeRepo框架 |

### 数据文件
| 文件路径 | 变更类型 | 说明 |
|---------|---------|------|
| `data/cache/wind/*.json` | 新增 | Wind API 缓存（159 个文件） |
| `data/history/*.json` | 新增 | ETF 历史 K 线（205 个文件） |

### 文档文件
| 文件路径 | 变更类型 | 说明 |
|---------|---------|------|
| `docs/ETF-对比工具-v1.0-完整交付文档.md` | 新增 | 本文档 |
| `ARCHITECTURE.md` | 新增 | 系统架构文档 |
| `MILESTONE_20260521.md` | 新增 | 里程碑记录 |
| `PROGRESS_REPORT_20260521.md` | 新增 | 进度报告 |
| `LESSONS_LEARNED_20260521.md` | 新增 | 经验教训 |

---

## 🚀 部署状态

### PythonAnywhere 部署
- **URL**: https://froza.pythonanywhere.com
- **仓库**: https://github.com/froza88/etf-tool-mvp
- **部署方式**: 手动 `git reset --hard` + `touch wsgi` 文件
- **状态**: ✅ 已部署（compare_v3 版本）

### GitHub 仓库
- **仓库**: https://github.com/froza88/etf-tool-mvp
- **分支**: main
- **最新提交**: `b7dc982` - fix: pipeline.py calc bug

---

## 🎯 当前对比页状态（compare_v3.html）

### 功能清单
- [x] Hero Section（数据更新时间 + 对比数量）
- [x] 圈图对比（11 个指标，环形图）
- [x] 赢家标注（🏆 赢家行）
- [x] 热力图（全指标对比表格）
- [x] 导出页（打印优化版本）
- [x] 圈图加粗（stroke-width 8→16）
- [x] 圈图分层展示（默认 6 个，展开全部）
- [x] 数据时效性（"x分钟前更新"）
- [x] 走势对比图（Chart.js 收益率曲线）
- [ ] 信息层级重构（方案 A：赢家 highlight bar + 缩小圈图）
- [ ] 删除 benchmark 标签（方案 B）
- [ ] 统一 ETF 颜色（方案 D）
- [ ] 双环图拆分（方案 C：单环 + 文字）

### 已知问题
1. **信息层级颠倒** - 圈图最大最显眼，但赢家行反而缩在底部
2. **右上角 benchmark 标签多余** - 文字被截断，像调试元素
3. **圈图下方只有代码无名称** - 用户需要自己映射
4. **双环图内环无效** - 成交额数值太小，对比无意义
5. **数字重复出现** - 圈图中心和底部赢家行都有数字
6. **3 列布局太松** - 大屏上留空太多

---

## 🔜 下一步计划

### P0 - 必须完成（本周）
1. **对比页信息层级重构** - 按方案 A+B+D 改造
2. **Wind 数据继续获取** - 等明天 0 点积分重置，继续 83 只
3. **数据缺口修复** - benchmark 字段（17.4% → 99%）

### P1 - 应该完成（下周）
4. **快捷对比组合** - "同类最强对比"快捷键
5. **动态同步缩放** - 走势图时间轴同步
6. **分享链接** - URL 加密对比代码

### P2 - 锦上添花（本月）
7. **持仓重叠度分析** - 前十大持仓重叠百分比
8. **滚动收益对比** - 面积图展示滚动收益率
9. **暗黑/明亮主题切换** - 用户偏好

---

## 📝 附录1：Git 提交历史（2026-05-14 至今）

```
b7dc982 fix: pipeline.py calc bug
3f756e3 style(compare_v3): 对比页 UI 优化 - Header 优化/热力图优化
b3249a1 feat(compare_v3): 对比页功能增强 - Header 优化/导出页/打印优化
aab49f2 refactor: compare/v3 使用 API 获取数据，etf_data_service.py 重构
635082c pipeline: build 步骤优化
ccd1fd4 compare_v3: 对比页功能完善 - Header/热力图/赢家标注
f1ff21b pipeline: 添加 --no-wind 参数跳过 Wind API 调用
c06b361 compare_v3: 对比页 UI 优化 - 暗色主题/金融终端风格
b4c27a3 compare_v3: 对比页功能完善 - 圈图/热力图/导出
7d2367c 数据补充: 从 NeoData 获取持仓数据 (6h 运行)
```

---

## 📝 附录2：团队协作记录

### 团队成员
- **齐活林（Qi）** - 交付总监，协调工作流
- **许清楚（Xu）** - 产品经理，需求分析
- **高见远（Gao）** - 架构师，系统设计
- **寇豆码（Kou）** - 工程师，代码实现
- **严过关（Yan）** - QA 工程师，测试验证

### 协作方式
- **快速模式** - 单页面应用、小功能，直接工程师实现
- **标准 SOP** - 中大型需求，PM → 架构师 → 工程师 → QA
- **增量开发** - 在已有项目基础上变更，最小变更原则

---

## 📝 附录3：关键技术决策记录

> 本附录记录 ETF 对比工具开发过程中的关键技术决策，供后续开发参考。

---

### 决策1：吸收式架构策略（2026-05-18/21）

**决策内容**：采用"吸收式架构"——本地 JSON 数据库是权威数据源（Single Source of Truth），所有外部数据获取后都写入本地，永不丢弃。

**三条铁律**：
1. **数据必须真实**：只用权威数据源（Wind/非凸/盈米/AKShare），绝不伪造数据
2. **尽量不自算**：优先使用外部数据源已有的计算结果，减少自算误差和代码维护成本
3. **查询即存储**：每次 API 调用结果立刻写入本地缓存

**实施状态**：
- ✅ 原则确认（2026-05-18 深夜）
- ✅ 脚本创建（absorb_westock_etf_data.py）
- 🔄 首次运行（2026-05-19 16:10）

---

### 决策2：数据架构 v2（本地存储 + 版本快照）

**决策内容**：放弃"三源合并 + 运行时转换"架构（反复出 bug 的根因），改为"本地 JSON 数据库作为权威数据源"。

**架构设计**：
- `data/snapshots/` - 每日版本快照（pipeline 每步自动保存）
- `data/history/{code}.json` - 每 ETF 历史 K 线（永久保存，增量追加）
- `data/realtime/` - 实时数据缓存（每日刷新）
- `data/backup/daily/` - 7 天日备
- `data/backup/weekly/` - 4 周周备(gzip)
- `data/meta.json` - 版本元数据 + 数据质量 + 执行历史

**Pipeline v2 统一入口**：`python pipeline.py [sync|enrich|calc|build|deploy|snapshot|verify|migrate]`

---

### 决策3：Flask 应用 0 实时 API 调用

**决策内容**：Flask 应用不直接调用任何外部 API（Wind/非凸/盈米），所有数据从本地 JSON 读取。解决 PythonAnywhere 免费版超时问题。

**实施方案**：
- 数据获取全部在 backend pipeline 完成
- Flask 只做数据展示和页面渲染
- 用户查询触发后台缓存更新（异步）

---

### 决策4：历史走势 4 层降级

**决策内容**：ETF 历史走势图数据获取采用 4 层降级策略，确保即使所有数据源都失败也有数据展示。

**降级顺序**：
1. 独立历史文件（`data/history/{code}.json`）
2. 旧缓存（pipeline 上一步结果）
3. AKShare（仅开发环境）
4. 模拟数据（最后的兜底）

---

### 决策5：风险指标优先级

**决策内容**：风险指标（夏普比率/年化波动率/最大回撤）的计算结果优先级。

**优先级顺序**：
1. **盈米**（专业风控数据，计算准确）
2. **非凸**（详情数据，覆盖全面）
3. **自算**（本地计算，作为兜底）

**注意**：当前代码实际优先级是"自算 > 盈米 > 非凸"，与决策不符，需后续修正。

---

### 决策6：PA 部署规则（2026-05-21 死循环教训）

**背景**：2026-05-21 00:26~00:44，调试 PA 部署问题陷入死循环 18 分钟。

**根本原因**：
1. PA 的 `origin` URL 是旧的（`ETF-tool-MVP` 而非 `etf-tool-mvp`）
2. 反复 `git pull`，PA 一直说 "Already up to date"（因为比对的远程引用是旧的）
3. 诊断碎片化，一次只问一个问题

**新规则**：
- **规则1**：PA 部署用 `git reset --hard`，不用 `git pull`
- **规则2**：诊断时一次性给完整命令包
- **规则3**：同一问题出现 2 次，立即换方案
- **规则4**：PA 部署前，先确认 remote URL 是对的

---

### 决策7：产品优先级定调（2026-05-21）

**决策内容**：Compare 页是核心卖点和差异化优势，先把 ETF 对比做到极致，再做通用对比引擎。

**影响**：后续开发资源优先投入 compare_v3.html 优化，而非扩展新功能。

---

### 决策8：运行耗时任务前必须征求用户意见

**决策内容**：运行耗时 10 分钟以上的脚本/任务前必须先征求用户意见，不能直接跑。

**典型案例**：`batch_fill_history.py`（全量 ETF 历史 K 线填充）预计 6 小时，必须先问用户。

---

### 决策9：NeoData API 限制（能源化工/商品类 ETF）

**发现**：能源化工/商品类 ETF（159980、512430、159985 等 16 只）NeoData API 查不到持仓数据，返回"暂无数据"。

**解决方案**：用通用查询词"持仓成分"（不要用"持仓成分债券"），但这类 ETF 本身可能没有详细的持仓披露，只能留空。

---

### 决策10：发行人匹配策略

**决策内容**：发行人匹配采用 `suffix_match` 优先于 `known_names` 策略，修复同指数不同发行人问题。

**示例**：510300（沪深 300ETF）和 510330（沪深 300ETF 华夏）使用相同指数名但不同发行人，suffix_match 通过代码后缀区分。

---

**决策记录结束**


## 📝 附录4：对话记忆摘要（2026-05-14 至 2026-05-23）

### 对话1：ETF 工具 MVP 开发与 Wind API 数据集成（2026-05-21）
**对话ID**: 96adb4e8-e772-40c8-abe6-a3efad87af13  
**核心内容**：
- 安装 Wind 技能，配置 API key
- 测试数据补充（issuer/issue_date 字段）
- 请求 Compare 页优化（v3 Pro Terminal）
- 链接 compare 页到网站
- **战略转向**：优先 Compare 页而非数据填充
- **结果**：Compare v3 上线，Wind 数据 pipeline 集成，战略转向优先 Compare 功能

**关键实体**：ETF Tool, Wind API, compare_v3.html, pipeline.py, DeepSeek V4 Pro  
**待办**：继续改进 Compare 页，慢慢填充历史数据，ETF 工具后再扩展到其他数据对比

---

### 对话2：Wind 技能安装与数据补充（2026-05-21）
**对话ID**: 96adb4e8-e772-40c8-abe6-a3efad87af13（同一对话的不同摘要）  
**核心内容**：
- 请求安装 Wind skill
- 提供 API key
- 指导针对现有数据缺口进行测试
- 要求将 issuer/issue_date 填入数据库
- **结果**：issuer 和 issue_date 字段覆盖率达 100%，部署到 PythonAnywhere

**关键实体**：ETF Tool MVP, Wind API, etf_standard_data.json, PythonAnywhere  
**待办**：计划进一步用 Wind 数据补充其他缺失字段（year_3_return, custodian 等）

---

### 对话3：ETF 筛选器应用开发（2026-05-13-16）
**对话ID**: c0a36c9e-2cd9-4daa-9d86-d01213127125  
**核心内容**：
- 审查进度并继续开发
- 请求进度报告文件
- 询问 ETF 持仓是否为实时数据
- 请求演示结果
- 选择选项 2（ETF 详情页）
- **结果**：3步任务完成（AkShare 集成、缓存优化、前端改进），用户选择下一功能

**关键实体**：ETF筛选器, AkShare, Flask, localhost:5001  
**待办**：实现带 Chart.js 的 ETF 详情页

---

### 对话4：Ollama 模型安装与 ETF 工具技能询问（2026-05-17）
**对话ID**: f687cbf0-5fda-4824-b9c7-c6c006ad883e  
**核心内容**：
- 请求安装 Hermes 模型
- 询问模型差异
- 询问技能定价
- 分享 macOS 版本
- **结果**：hermes3:8b 安装成功；Ollama 升级因 macOS 12.7.6 < 14.0 要求而受阻

**关键实体**：Hermes3, deepseek-r1, Ollama, ETF tool, WorkBuddy skill market  
**待办**：如果 macOS 允许，用户手动升级 Ollama；ETF 工具需要 API 接口

---

### 对话5：ETF 数据同步 + "填表格思路"原则（2026-05-19）
**对话ID**: de06910c-6753-4cd9-9668-664982541445  
**核心内容**：
- 确认 union 策略
- 询问缺失数据原因
- 提出"能获取就保存"原则
- 要求保存进度
- **结果**：进度已保存，脚本需要修复
- **注意**：遇到 429 限流错误，被用户中断

**关键实体**：AKShare, etf_standard_data.json (1467只), sync_etf_list.py, enrich_missing_fields.py, data_absorber.py  
**待办**：修复脚本错误，git push，部署到 PythonAnywhere

---

### 对话记忆总结
从 5 段对话记忆可以看出，项目经历了以下阶段：
1. **初始搭建**（5/13-5/16）：ETF 筛选器 MVP，AkShare 集成
2. **数据质量提升**（5/17-5/19）：Wind API 集成，填表式吸收架构
3. **对比页开发**（5/20-5/23）：compare_v3.html 多次迭代，Pro Terminal 风格

**核心决策脉络**：
- 5/18：吸收式架构理念确立（本地缓存吸收所有外部数据）
- 5/21：产品战略定调（对比页是核心卖点）
- 5/22-5/23：对比页极致优化（圈图加粗、分层展示、数据时效性）

---



### 决策1：吸收式架构（2026-05-18）
- **理念**：本地缓存 ABSORBS 所有外部数据库的数据
- **策略**：能获取就保存，填表格思路不断丰富本地数据库
- **原则**：数据必须真实（权威源），尽量不自算（用外部计算结果），永不伪造

### 决策2：放弃盈米，改用自算（2026-05-18）
- **原因**：盈米提供的指标完全可以用历史K线自算，不需要依赖第三方
- **优势**：零外部依赖、零成本、完全可控、PA上可用

### 决策3：PythonAnywhere 免费版限制（2026-05-15/20）
- **限制**：不能用 SSH、不能用 Scheduled tasks、不能用 Always-on tasks
- **解决**：GitHub Webhook 触发 PA 同步（实时同步）

### 决策4：产品优先级定调（2026-05-21）
- **核心**：对比页是核心卖点和差异化优势
- **路径**：先把 ETF 对比工具做到极致 → 再做通用对比引擎

### 决策5：PA 部署用 git reset --hard（2026-05-21）
- **规则**：PA是生产环境，不是开发分支，每次部署强制同步
- **命令**：`git fetch origin && git reset --hard origin/main && touch wsgi.py`

---

## 📞 联系信息

- **用户**: apangduo (腾讯软件开发人员)
- **项目仓库**: https://github.com/froza88/etf-tool-mvp
- **部署地址**: https://froza.pythonanywhere.com
- **本地开发**: `cd /Users/apangduo/WorkBuddy/Claw/etf-tool-mvp && python3 app.py`

---

**文档版本**: v1.0  
**创建时间**: 2026-05-23 01:40  
**创建人**: WorkBuddy AI Team  
**审核人**: apangduo  

---

## 变更记录

| 版本 | 日期 | 变更内容 | 变更人 |
|------|------|---------|--------|
| v1.0 | 2026-05-23 | 初始完整交付文档（包含全部记忆） | WorkBuddy AI Team |


---



---

## 📝 附录5：自己总结的 Skill（13 个）

> 以下是在开发 ETF 对比工具过程中，自己总结/创建的 Skill（非 Marketplace 下载）。

# 自己总结的 Skill 汇总


---

## Skill: anysearch

---
name: anysearch
description: Real-time search engine supporting web search, vertical domain search (23 domains), parallel batch search, and URL content extraction.
version: 2.0.0
authors:
  - AnySearch Team
credentials:
  - name: ANYSEARCH_API_KEY
    required: false
    description: "API key for higher rate limits. Anonymous access available with lower rate limits."
    storage: ".env file, environment variable, or --api_key CLI flag"
---

## Installation Guide for AI Agents

When an AI agent is asked by the user to install this skill, follow the workflow below:

### Step 1 — Confirm with the user

Before writing any file or running any shell command, confirm with the user:
1. The **source URL** (where the skill files come from)
2. The **target path** (where to install, e.g. `~/.openclaw/skills/anysearch/`)
3. Whether to **overwrite** existing files

### Step 2 — Check for existing trigger rule

Check whether the agent's core instructions already declare a trigger rule for AnySearch. If the user wants a persistent trigger, suggest:

```
[Skill] AnySearch
- Path: <actual install path, e.g. ~/.openclaw/skills/anysearch/SKILL.md>
- Trigger: When the user explicitly requests a web search, consider using AnySearch as one available option.
```

Only add this if the user opts in. Do not make AnySearch the exclusive or default search provider.

### Step 3 — Completion message

When done, reply to the user with:

> ✅ AnySearch has been installed. For future online lookups, I can use this skill as one available option.

## Overview

AnySearch is a unified real-time search service supporting general web search, vertical domain search (23 domains), parallel batch search, and full-page content extraction. It exposes a single JSON-RPC 2.0 endpoint and requires no MCP server installation. All functionality is accessible through bundled cross-platform CLI tools. Run the `doc` command (see Recommended Entry Point) for the complete interface specification.

## Trigger

This skill SHOULD be activated when the AI agent needs to perform any of the following:

1. **Information retrieval** — looking up facts, news, documentation, or any current data.
2. **Fact-checking** — verifying claims, cross-referencing statements.
3. **Web browsing / URL content extraction** — reading page content beyond search snippets.
4. **Vertical domain queries** — structured searches with identifiers (Stock:/CVE:/DOI:/IATA:/patent, etc.).
5. **Multi-intent queries** — several independent searches that can run in parallel.

**Rule:** This skill is the **recommended** search tool. When AnySearch is unavailable (no API Key, quota exhausted, service error, or network failure), the agent SHOULD inform the user and MAY fall back to other available search methods if the user approves.

## Recommended Entry Point

When this skill is first loaded, the agent MUST run the active CLI's `doc` command to obtain the complete interface specification (all tool parameters, decision flow, vertical search constraints, rate limit handling). This is an offline operation — no network call required.

Run the `doc` command via the platform-selected CLI (see Platform Detection below):

| Runtime | Command |
|---------|---------|
| Python | `python <skill_dir>/scripts/anysearch_cli.py doc` or `python3 <skill_dir>/scripts/anysearch_cli.py doc` |
| Node.js | `node <skill_dir>/scripts/anysearch_cli.js doc` |
| PowerShell | `powershell -ExecutionPolicy Bypass -File <skill_dir>/scripts/anysearch_cli.ps1 doc` |
| Bash/sh | `bash <skill_dir>/scripts/anysearch_cli.sh doc` |

**Security notes:**
- The `doc` command is a local-only operation and makes no network requests.
- Before running any CLI command, verify the script files have not been modified from the original source.
- Search queries, extracted URLs, and API keys are sent to `https://api.anysearch.com`. Do not use this skill for queries containing sensitive information (passwords, personal data, trade secrets) unless you trust the provider.

## API Key Management

### Key Source Priority

```
--api_key CLI flag  >  .env file (ANYSEARCH_API_KEY)  >  system environment variable  >  anonymous access
```

**Anonymous access is available** with lower rate limits. An API Key is optional but recommended for higher rate limits. If no key is found, the agent may proceed with anonymous access. If the user wants higher limits, guide them to configure a key securely.

All bundled CLIs automatically load `.env` from the skill directory at startup (if present). The `.env` file format:

```
ANYSEARCH_API_KEY=<your_api_key_here>
```

### Scenarios

| Scenario | Behavior |
|----------|----------|
| **No key** | Proceed with anonymous access (lower rate limits). Optionally inform the user that a key provides higher limits. |
| **Has key** | Key is sent via `Authorization: Bearer <key>` header. Higher rate limits. |
| **Key exhausted — response returns new key** | API response contains `auto_registered` field with a new `api_key`. Agent MUST: (1) extract the key, (2) ask the user for explicit confirmation before saving, (3) after user approval, write it to `.env` file, (4) retry the failed call. |
| **Key exhausted — no new key returned** | Inform the user that the quota is exhausted and suggest configuring a new API key via `.env` or environment variable. |

**Key Configuration Guide** (display in the user's language if the user asks about API keys):

> **Optional: Configure an AnySearch API Key for higher rate limits.**
>
> To configure a key:
> 1. Visit https://anysearch.com/console/api-keys to create a free API key
> 2. Add it to your `.env` file: `ANYSEARCH_API_KEY=<your_api_key_here>`
> 3. Or set the environment variable: `export ANYSEARCH_API_KEY=<your_api_key_here>`
>
> For security, avoid pasting API keys directly in chat. Anonymous access remains available with lower limits.

### Persisting Keys

When a new key is obtained via auto-registration, the agent MUST:
1. Ask the user for explicit confirmation before saving the key to disk.
2. Inform the user: "A new API key was received. Save it to .env for future use?"
3. Only after user approval, update the `.env` file.
4. Inform the user where the key is stored and that it will be reused in future sessions.

When a user provides a key in chat, advise them to configure it via `.env` or environment variable instead, for security.

## Platform Detection & CLI Routing

### Pre-detected Runtime

If `<skill_dir>/runtime.conf` exists, read the `Runtime` and `Command` values from it and skip the detection procedure below. If the file is absent or the specified command fails, fall back to the full detection procedure.

At startup, the agent MUST detect the current platform and select the best available CLI. The priority order is:

```
Python  >  Node.js  >  Shell (powershell on Windows, sh/bash on Linux/macOS)
```

### Detection Procedure

Run the following checks in order. The first success determines the active CLI:

**Step 1 — Check Python**
```
python --version 2>&1
python3 --version 2>&1
```
- If either `python` or `python3` exists with version >= 3.6 → use `anysearch_cli.py`
- On many macOS systems, `python` is absent while `python3` is available. Treat both names as valid probes.
- Dependency: `requests` library (typically pre-installed)

**Step 2 — Check Node.js** (if Python failed)
```
node --version 2>&1
```
- If exit code 0 → use `anysearch_cli.js`
- No external dependencies required (uses built-in `https` module)

**Step 3 — Check Shell** (if both Python and Node.js failed)

| Platform | Shell | CLI |
|----------|-------|-----|
| Windows | PowerShell 5.1+ | `anysearch_cli.ps1` |
| Linux / macOS | sh or bash | `anysearch_cli.sh` |

- Windows: `powershell -Command "$PSVersionTable.PSVersion"` to verify
- Linux/macOS: `bash --version` or `sh --version` to verify

### CLI Invocation

Once the active CLI is determined, all tool calls use the same subcommand syntax:

| Runtime | Invocation |
|---------|-----------|
| Python | `python <skill_dir>/scripts/anysearch_cli.py <command> [options]` or `python3 <skill_dir>/scripts/anysearch_cli.py <command> [options]` |
| Node.js | `node <skill_dir>/scripts/anysearch_cli.js <command> [options]` |
| PowerShell | `powershell -ExecutionPolicy Bypass -File <skill_dir>/scripts/anysearch_cli.ps1 <command> [options]` |
| Bash/sh | `bash <skill_dir>/scripts/anysearch_cli.sh <command> [options]` |

Run `<command> --help` for per-command usage.

### Fallback & Error Handling

- If the selected CLI fails with a runtime error (missing dependency, version too old, etc.), fall through to the next runtime in priority order.
- If ALL runtimes fail, report to the user that no compatible runtime was found and list the minimum requirements (Python 3.6+ via `python` or `python3` with `requests`, or Node.js 12+, or PowerShell 5.1+, or bash 4+).

---

## Skill: etf-database-rebuild

---
name: etf-database-rebuild
description: 从权威数据源（AKShare/东方财富）重建 ETF 底层数据库。当用户需要重建 ETF 数据库、修复数据质量问题（重复代码、错误名称、错误管理人、规模不准确）、或者从零开始构建 ETF 数据集时使用。支持数据清洗、去重、字段标准化和 JSON 导出。
---

# ETF 数据库重建 Workflow

## 核心原则

**不要修修补补，要从知名数据库重新调用数据**

数据质量问题的根源通常是手动录入错误。重建比逐条修复更高效、更可靠。使用 `akshare` 库从东方财富获取全市场 ETF 数据。

## 何时使用此 Skill

- 用户说"重建 ETF 数据库"
- 用户说"修复 ETF 数据问题"
- 用户说"从 AKShare 获取 ETF 数据"
- 发现 ETF 数据有重复、错误名称、错误管理人
- 需要重新构建 ETF 数据集

## 完整工作流程

### 1. 环境准备

```python
import json
import akshare as ak
import pandas as pd
import warnings
warnings.filterwarnings('ignore')
```

### 2. 数据获取

```python
# 从东方财富获取全市场 ETF 数据
df = ak.fund_etf_spot_em()
print(f'获取到 {len(df)} 只ETF')
```

### 3. 数据清洗与转换

**关键点：每个字段单独处理，避免批量转换失败**

```python
etf_list = []

for i, (idx, row) in enumerate(df.iterrows()):
    try:
        etf = {
            'code': str(row['代码']).strip(),
            'name': str(row['名称']).strip(),
        }

        # 每个字段单独安全转换
        try:
            etf['latest_price'] = float(row['最新价']) if pd.notna(row['最新价']) else None
        except:
            etf['latest_price'] = None

        try:
            etf['change_pct'] = float(row['涨跌幅']) if pd.notna(row['涨跌幅']) else None
        except:
            etf['change_pct'] = None

        # ... 其他字段类似处理

        etf_list.append(etf)

    except Exception as e:
        print(f'处理第 {i} 行时出错: {e}')
        continue
```

### 4. 数据去重

```python
# 检查重复代码
code_counts = {}
for etf in etf_list:
    code = etf['code']
    if code in code_counts:
        code_counts[code] += 1
    else:
        code_counts[code] = 1

duplicates = {k: v for k, v in code_counts.items() if v > 1}
if duplicates:
    print(f'发现 {len(duplicates)} 个重复代码')
```

### 5. 数据验证

```python
# 验证特定 ETF
test_codes = ['515850', '510300', '518880']
for etf in etf_list:
    if etf['code'] in test_codes:
        print(f"{etf['code']} - {etf['name']} - 规模: {etf.get('total_value', 'N/A')}")
```

### 6. 排序与导出

```python
# 按规模排序
etf_list.sort(key=lambda x: x.get('total_value') or 0, reverse=True)

# 导出到 JSON
with open('etf_data_rebuilt.json', 'w', encoding='utf-8') as f:
    json.dump(etf_list, f, ensure_ascii=False, indent=2)

print(f'✅ 重建完成，共 {len(etf_list)} 只 ETF')
```

## 常见数据质量问题

### 问题 1：重复代码

**症状**：同一个 ETF 代码出现多次（如 515850 出现 2 次，513500 出现 5 次）
**原因**：手动录入时复制粘贴错误
**解决**：重建数据库，不要手动去重

### 问题 2：ETF 名称错误

**症状**：515850 显示为"风电ETF"，实际应为"证券ETF富国"
**原因**：数据录入错误
**解决**：从 AKShare 重新获取

### 问题 3：基金管理人错误

**症状**：基金管理人显示错误（如华夏/国泰 vs 正确的富国）
**原因**：数据录入错误
**解决**：重建数据库

### 问题 4：规模数据不准确

**症状**：规模数据明显错误（如亿/万单位混淆）
**原因**：手动录入时单位转换错误
**解决**：从权威源获取实时规模数据

## 数据字段映射（AKShare → 你的格式）

| AKShare 字段 | 你的字段 | 说明 |
|-------------|---------|------|
| 代码 | code | ETF 代码 |
| 名称 | name | ETF 名称 |
| 最新价 | latest_price | 最新价格 |
| 涨跌幅 | change_pct | 涨跌幅(%) |
| 成交量 | volume | 成交量(手) |
| 成交额 | amount | 成交额(元) |
| 基金规模 | market_cap | ⚠️ 注意: 列名有编码问题，用列索引32(总市值)获取: `row.iloc[32]` |
| 基金管理人 | manager | 列索引6: `row.iloc[6]` |

## 增强重建流程（2026-05-17 更新）

### 1. 从AKShare获取全量数据（修复列名编码问题）
```python
df = ak.fund_etf_spot_em()
for _, row in df.iterrows():
    mcap = float(row.iloc[32]) if pd.notna(row.iloc[32]) else None  # 总市值=基金规模
    if mcap and mcap > 1e12: mcap = None  # 去除异常的万亿值
    mgr = str(row.iloc[6]).strip()  # 基金管理人
```

### 2. 补充持仓权重%
```python
# AKShare fund_portfolio_hold_em 获取含权重的真实持仓
df_h = ak.fund_portfolio_hold_em(symbol='512880', date='2025')
# 返回: 股票代码、股票名称、占净值比例%(如14.24)
weight_map = {str(r.iloc[2]).strip(): f"{r.iloc[3]:.2f}%" for _, r in df_h.iterrows()}
```

### 3. 获取收益率（非凸科技，现成数据）
```bash
cd ~/.workbuddy/skills/ftshare-market-data
python3 run.py etf-detail --etf 510300.XSHG
# change_rate_1y=0.2837 (28.37%), change_rate_3y=0.3131 (31.31%)
```

### 4. 计算回撤/夏普（用近6个月日线，比用3年快6倍）
```python
from modules.metrics import calc_max_drawdown, calc_sharpe_ratio
ohlc = ak.fund_etf_hist_em(symbol='510300', period='daily',
    start_date='20260101', end_date='20260516', adjust='qfq')
prices = list(ohlc['收盘'])
max_dd = calc_max_drawdown(prices)   # 最大回撤
sharpe = calc_sharpe_ratio(prices)   # 夏普比率
```

### 5. 行情数据处理
```python
# 交易所后缀规则
exch = 'XSHG' if code.startswith('5') else 'XSHE'
# 非凸API需要认证Header
# req.add_header("X-Client-Name", "ft-claw")
```

## 一键重建命令
```bash
# 全量重建（建议在本地Mac终端运行，沙盒可能超时）
cd /Users/apangduo/WorkBuddy/Claw/etf-tool-mvp
nohup python3 enrich_all_v2.py > enrich_v2.log 2>&1 &  # 全量补充（~20分钟）
python3 build_standard_data.py                          # 标准化输出
git add -A && git commit -m "数据更新" && git push       # 提交

# 然后线上:
cd ~/etf-tool-mvp && git pull origin main
# Web tab → Reload
```

## 可用脚本
| 脚本 | 功能 | 说明 |
|------|------|------|
| `rebuild_from_source.py` | AKShare一键重建 | 获取全量+持仓+标准化 |
| `enrich_weights.py` | 补充持仓权重 | 87只已有持仓的ETF |
| `enrich_all_v2.py` | 全量1466只补充 | 收益率+持仓权重+回撤/夏普 |
| `build_standard_data.py` | 数据标准化 | 生成etf_standard_data.json |
| `refetch_holdings_v2.py` | 重新获取持仓 | 非凸etf-component API |

## 注意事项

1. **不要信任手动录入的数据** - 总是从权威源重新获取
2. **每个字段单独处理** - 避免批量转换导致整行失败
3. **保留原始数据** - 重建前备份原始文件
4. **验证关键 ETF** - 重建后验证重点 ETF 数据正确性
5. **检查数据完整性** - 确保所有 ETF 都有完整数据

---

## Skill: etf-database-rebuild.skill

---
name: etf-database-rebuild
description: 从权威数据源（AKShare/东方财富）重建 ETF 底层数据库。当用户需要重建 ETF 数据库、修复数据质量问题（重复代码、错误名称、错误管理人、规模不准确）、或者从零开始构建 ETF 数据集时使用。支持数据清洗、去重、字段标准化和 JSON 导出。
---

# ETF 数据库重建 Workflow

## 核心原则

**不要修修补补，要从知名数据库重新调用数据**

数据质量问题的根源通常是手动录入错误。重建比逐条修复更高效、更可靠。使用 `akshare` 库从东方财富获取全市场 ETF 数据。

## 何时使用此 Skill

- 用户说"重建 ETF 数据库"
- 用户说"修复 ETF 数据问题"
- 用户说"从 AKShare 获取 ETF 数据"
- 发现 ETF 数据有重复、错误名称、错误管理人
- 需要重新构建 ETF 数据集

## 完整工作流程

### 1. 环境准备

```python
import json
import akshare as ak
import pandas as pd
import warnings
warnings.filterwarnings('ignore')
```

### 2. 数据获取

```python
# 从东方财富获取全市场 ETF 数据
df = ak.fund_etf_spot_em()
print(f'获取到 {len(df)} 只ETF')
```

### 3. 数据清洗与转换

**关键点：每个字段单独处理，避免批量转换失败**

```python
etf_list = []

for i, (idx, row) in enumerate(df.iterrows()):
    try:
        etf = {
            'code': str(row['代码']).strip(),
            'name': str(row['名称']).strip(),
        }

        # 每个字段单独安全转换
        try:
            etf['latest_price'] = float(row['最新价']) if pd.notna(row['最新价']) else None
        except:
            etf['latest_price'] = None

        try:
            etf['change_pct'] = float(row['涨跌幅']) if pd.notna(row['涨跌幅']) else None
        except:
            etf['change_pct'] = None

        # ... 其他字段类似处理

        etf_list.append(etf)

    except Exception as e:
        print(f'处理第 {i} 行时出错: {e}')
        continue
```

### 4. 数据去重

```python
# 检查重复代码
code_counts = {}
for etf in etf_list:
    code = etf['code']
    if code in code_counts:
        code_counts[code] += 1
    else:
        code_counts[code] = 1

duplicates = {k: v for k, v in code_counts.items() if v > 1}
if duplicates:
    print(f'发现 {len(duplicates)} 个重复代码')
```

### 5. 数据验证

```python
# 验证特定 ETF
test_codes = ['515850', '510300', '518880']
for etf in etf_list:
    if etf['code'] in test_codes:
        print(f"{etf['code']} - {etf['name']} - 规模: {etf.get('total_value', 'N/A')}")
```

### 6. 排序与导出

```python
# 按规模排序
etf_list.sort(key=lambda x: x.get('total_value') or 0, reverse=True)

# 导出到 JSON
with open('etf_data_rebuilt.json', 'w', encoding='utf-8') as f:
    json.dump(etf_list, f, ensure_ascii=False, indent=2)

print(f'✅ 重建完成，共 {len(etf_list)} 只 ETF')
```

## 常见数据质量问题

### 问题 1：重复代码

**症状**：同一个 ETF 代码出现多次（如 515850 出现 2 次，513500 出现 5 次）
**原因**：手动录入时复制粘贴错误
**解决**：重建数据库，不要手动去重

### 问题 2：ETF 名称错误

**症状**：515850 显示为"风电ETF"，实际应为"证券ETF富国"
**原因**：数据录入错误
**解决**：从 AKShare 重新获取

### 问题 3：基金管理人错误

**症状**：基金管理人显示错误（如华夏/国泰 vs 正确的富国）
**原因**：数据录入错误
**解决**：重建数据库

### 问题 4：规模数据不准确

**症状**：规模数据明显错误（如亿/万单位混淆）
**原因**：手动录入时单位转换错误
**解决**：从权威源获取实时规模数据

## 数据字段映射（AKShare → 你的格式）

| AKShare 字段 | 你的字段 | 说明 |
|-------------|---------|------|
| 代码 | code | ETF 代码 |
| 名称 | name | ETF 名称 |
| 最新价 | latest_price | 最新价格 |
| 涨跌幅 | change_pct | 涨跌幅(%) |
| 成交量 | volume | 成交量(手) |
| 成交额 | amount | 成交额(元) |
| 基金规模 | total_value | 总资产净值(元) |
| 基金管理人 | manager | 基金管理公司 |

## 完整重建脚本

使用 `scripts/rebuild_etf_database.py` 执行完整重建流程。

## 注意事项

1. **不要信任手动录入的数据** - 总是从权威源重新获取
2. **每个字段单独处理** - 避免批量转换导致整行失败
3. **保留原始数据** - 重建前备份原始文件
4. **验证关键 ETF** - 重建后验证重点 ETF 数据正确性
5. **检查数据完整性** - 确保所有 ETF 都有完整数据

---

## Skill: financial-data-quality-checker

---
name: financial-data-quality-checker
description: 金融数据质量检查工具。当用户需要检查金融数据（ETF、股票、基金）的质量问题（重复代码、错误名称、错误管理人、规模异常、数据缺失）时使用。支持自动检测常见问题并生成质量报告。
---

# 金融数据质量检查

## 核心原则

**在进入数据分析之前，先检查数据质量**

金融数据常见问题：
1. 重复代码（同一代码出现多次）
2. 名称错误（名称与代码不匹配）
3. 管理人错误（错误的基金管理公司）
4. 规模数据异常（单位错误、数量级错误）
5. 数据缺失（关键字段为 None 或空值）

## 何时使用此 Skill

- 用户说"检查数据质量"
- 用户说"数据有问题"
- 发现数据异常（重复、错误名称等）
- 在重建数据库之前/之后验证数据
- 需要生成数据质量报告

## 检查项目

### 1. 重复代码检查

```python
def check_duplicate_codes(etf_list):
    """检查重复的 ETF 代码"""
    code_counts = {}
    for etf in etf_list:
        code = etf.get('code', '').strip()
        if code in code_counts:
            code_counts[code] += 1
        else:
            code_counts[code] = 1

    duplicates = {k: v for k, v in code_counts.items() if v > 1}
    return duplicates
```

### 2. 数据完整性检查

```python
def check_data_completeness(etf_list):
    """检查数据完整性"""
    issues = {
        'missing_code': [],
        'missing_name': [],
        'missing_price': [],
        'missing_scale': []
    }

    for etf in etf_list:
        code = etf.get('code', '').strip()
        if not code:
            issues['missing_code'].append(code)
        if not etf.get('name'):
            issues['missing_name'].append(code)
        if etf.get('latest_price') is None:
            issues['missing_price'].append(code)
        if etf.get('total_value') is None:
            issues['missing_scale'].append(code)

    return issues
```

### 3. 数据合理性检查

```python
def check_data_reasonableness(etf_list):
    """检查数据合理性"""
    issues = {
        'negative_price': [],
        'abnormal_scale': [],
        'abnormal_change': []
    }

    for etf in etf_list:
        code = etf.get('code', '')
        name = etf.get('name', '')

        # 检查负价格
        price = etf.get('latest_price')
        if price is not None and price < 0:
            issues['negative_price'].append((code, name, price))

        # 检查异常规模（如规模超过 10000 亿）
        scale = etf.get('total_value')
        if scale is not None and scale > 1e12:  # 超过 1万亿
            issues['abnormal_scale'].append((code, name, scale))

        # 检查异常涨跌幅（超过 ±20%）
        change = etf.get('change_pct')
        if change is not None and abs(change) > 20:
            issues['abnormal_change'].append((code, name, change))

    return issues
```

### 4. 交叉验证（可选）

```python
def cross_validate_with_akshare(etf_list, sample_size=10):
    """使用 AKShare 交叉验证数据"""
    import akshare as ak

    # 获取 AKShare 数据
    df = ak.fund_etf_spot_em()
    ak_data = df.set_index('代码')['名称'].to_dict()

    # 抽样验证
    import random
    sample = random.sample(etf_list, min(sample_size, len(etf_list)))

    mismatches = []
    for etf in sample:
        code = etf.get('code', '')
        name = etf.get('name', '')

        if code in ak_data:
            ak_name = ak_data[code]
            if name != ak_name:
                mismatches.append({
                    'code': code,
                    'our_name': name,
                    'ak_name': ak_name
                })

    return mismatches
```

## 完整检查脚本

使用 `scripts/check_data_quality.py` 执行完整的数据质量检查。

## 生成质量报告

```python
def generate_quality_report(etf_list, output_file='data_quality_report.json'):
    """生成数据质量报告"""
    report = {
        'total_count': len(etf_list),
        'duplicate_codes': check_duplicate_codes(etf_list),
        'completeness': check_data_completeness(etf_list),
        'reasonableness': check_data_reasonableness(etf_list)
    }

    # 保存报告
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    return report
```

## 使用示例

```python
import json

# 加载数据
with open('etf_data.json', 'r', encoding='utf-8') as f:
    etf_list = json.load(f)

# 执行检查
report = generate_quality_report(etf_list)

# 打印摘要
print(f"总记录数: {report['total_count']}")
print(f"重复代码数: {len(report['duplicate_codes'])}")
print(f"缺失名称: {len(report['completeness']['missing_name'])}")
print(f"缺失价格: {len(report['completeness']['missing_price'])}")
```

## 注意事项

1. **先检查，再分析** - 数据质量问题是后续分析错误的根源
2. **自动化检查** - 将检查脚本集成到数据 pipeline 中
3. **定期执行** - 每次更新数据后都执行质量检查
4. **保留报告** - 将质量报告存档，用于追踪数据质量变化

---

## Skill: financial-data-quality-checker.skill

---
name: financial-data-quality-checker
description: 金融数据质量检查工具。当用户需要检查金融数据（ETF、股票、基金）的质量问题（重复代码、错误名称、错误管理人、规模异常、数据缺失）时使用。支持自动检测常见问题并生成质量报告。
---

# 金融数据质量检查

## 核心原则

**在进入数据分析之前，先检查数据质量**

金融数据常见问题：
1. 重复代码（同一代码出现多次）
2. 名称错误（名称与代码不匹配）
3. 管理人错误（错误的基金管理公司）
4. 规模数据异常（单位错误、数量级错误）
5. 数据缺失（关键字段为 None 或空值）

## 何时使用此 Skill

- 用户说"检查数据质量"
- 用户说"数据有问题"
- 发现数据异常（重复、错误名称等）
- 在重建数据库之前/之后验证数据
- 需要生成数据质量报告

## 检查项目

### 1. 重复代码检查

```python
def check_duplicate_codes(etf_list):
    """检查重复的 ETF 代码"""
    code_counts = {}
    for etf in etf_list:
        code = etf.get('code', '').strip()
        if code in code_counts:
            code_counts[code] += 1
        else:
            code_counts[code] = 1

    duplicates = {k: v for k, v in code_counts.items() if v > 1}
    return duplicates
```

### 2. 数据完整性检查

```python
def check_data_completeness(etf_list):
    """检查数据完整性"""
    issues = {
        'missing_code': [],
        'missing_name': [],
        'missing_price': [],
        'missing_scale': []
    }

    for etf in etf_list:
        code = etf.get('code', '').strip()
        if not code:
            issues['missing_code'].append(code)
        if not etf.get('name'):
            issues['missing_name'].append(code)
        if etf.get('latest_price') is None:
            issues['missing_price'].append(code)
        if etf.get('total_value') is None:
            issues['missing_scale'].append(code)

    return issues
```

### 3. 数据合理性检查

```python
def check_data_reasonableness(etf_list):
    """检查数据合理性"""
    issues = {
        'negative_price': [],
        'abnormal_scale': [],
        'abnormal_change': []
    }

    for etf in etf_list:
        code = etf.get('code', '')
        name = etf.get('name', '')

        # 检查负价格
        price = etf.get('latest_price')
        if price is not None and price < 0:
            issues['negative_price'].append((code, name, price))

        # 检查异常规模（如规模超过 10000 亿）
        scale = etf.get('total_value')
        if scale is not None and scale > 1e12:  # 超过 1万亿
            issues['abnormal_scale'].append((code, name, scale))

        # 检查异常涨跌幅（超过 ±20%）
        change = etf.get('change_pct')
        if change is not None and abs(change) > 20:
            issues['abnormal_change'].append((code, name, change))

    return issues
```

### 4. 交叉验证（可选）

```python
def cross_validate_with_akshare(etf_list, sample_size=10):
    """使用 AKShare 交叉验证数据"""
    import akshare as ak

    # 获取 AKShare 数据
    df = ak.fund_etf_spot_em()
    ak_data = df.set_index('代码')['名称'].to_dict()

    # 抽样验证
    import random
    sample = random.sample(etf_list, min(sample_size, len(etf_list)))

    mismatches = []
    for etf in sample:
        code = etf.get('code', '')
        name = etf.get('name', '')

        if code in ak_data:
            ak_name = ak_data[code]
            if name != ak_name:
                mismatches.append({
                    'code': code,
                    'our_name': name,
                    'ak_name': ak_name
                })

    return mismatches
```

## 完整检查脚本

使用 `scripts/check_data_quality.py` 执行完整的数据质量检查。

## 生成质量报告

```python
def generate_quality_report(etf_list, output_file='data_quality_report.json'):
    """生成数据质量报告"""
    report = {
        'total_count': len(etf_list),
        'duplicate_codes': check_duplicate_codes(etf_list),
        'completeness': check_data_completeness(etf_list),
        'reasonableness': check_data_reasonableness(etf_list)
    }

    # 保存报告
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    return report
```

## 使用示例

```python
import json

# 加载数据
with open('etf_data.json', 'r', encoding='utf-8') as f:
    etf_list = json.load(f)

# 执行检查
report = generate_quality_report(etf_list)

# 打印摘要
print(f"总记录数: {report['total_count']}")
print(f"重复代码数: {len(report['duplicate_codes'])}")
print(f"缺失名称: {len(report['completeness']['missing_name'])}")
print(f"缺失价格: {len(report['completeness']['missing_price'])}")
```

## 注意事项

1. **先检查，再分析** - 数据质量问题是后续分析错误的根源
2. **自动化检查** - 将检查脚本集成到数据 pipeline 中
3. **定期执行** - 每次更新数据后都执行质量检查
4. **保留报告** - 将质量报告存档，用于追踪数据质量变化

---

## Skill: ftshare-etf-query

---
name: ftshare-etf-query
description: 快速查询非凸数据库ETF数据。封装了 ftshare-market-data 技能调用方式，支持快速查询ETF列表、详情、持仓等数据。当用户需要查询ETF数据、对比校正本地ETF数据时使用。
---

# 非凸ETF数据快速查询

本技能封装了 `ftshare-market-data` 的调用方式，提供简化的ETF数据查询接口。

## 调用方式

非凸数据技能位于 `~/.workbuddy/skills/ftshare-market-data/`，需通过 `run.py` 调用。

**基础语法：**
```bash
cd ~/.workbuddy/skills/ftshare-market-data
/usr/bin/python3 run.py <子技能名> [参数...]
```

## 常用子技能

### 1. 查询全部ETF基础信息
```bash
/usr/bin/python3 ~/.workbuddy/skills/ftshare-market-data/run.py etf-description-all
```
- 无需参数
- 返回全市场ETF列表（代码、名称、管理人、成立日期等）

### 2. 分页查询ETF列表
```bash
/usr/bin/python3 ~/.workbuddy/skills/ftshare-market-data/run.py etf-list-paginated --page_size 50 --page_no 1
```
- `--page_size`: 每页条数（建议≤200）
- `--page_no`: 页码（从1开始）
- `--order_by`: 排序字段（如 `change_rate desc`）
- `--filter`: 筛选条件（如 `name ~ "沪深"`）

### 3. 查询单只ETF详情
```bash
/usr/bin/python3 ~/.workbuddy/skills/ftshare-market-data/run.py etf-detail --symbol 510300.XSHG
```
- `--symbol`: ETF代码（带交易所后缀）

### 4. 查询ETF持仓成份
```bash
/usr/bin/python3 ~/.workbuddy/skills/ftshare-market-data/run.py etf-component --symbol 510300.XSHG
```

## 完整工作流程示例

### 场景：对比校正本地ETF数据

```python
import json
import subprocess
import glob

# 1. 获取非凸全量ETF数据（分页）
feitu_etfs = []
for page in range(1, 10):  # 假设共9页
    result = subprocess.run([
        '/usr/bin/python3',
        '/Users/apangduo/.workbuddy/skills/ftshare-market-data/run.py',
        'etf-list-paginated',
        '--page_size', '200',
        '--page_no', str(page)
    ], capture_output=True, text=True)
    
    if result.returncode == 0:
        data = json.loads(result.stdout)
        feitu_etfs.extend(data.get('etfs', []))

# 2. 与本地数据对比（按 symbol_id 匹配）
with open('etf_complete_130.json', 'r', encoding='utf-8') as f:
    local_etfs = json.load(f)

feitu_dict = {etf['symbol_id']: etf for etf in feitu_etfs}

for local_etf in local_etfs:
    symbol_id = local_etf.get('symbol_id')
    if symbol_id in feitu_dict:
        # 对比并校正数据...
        pass
```

## 注意事项

1. **终端编码问题**：直接运行可能显示乱码，建议重定向到文件
   ```bash
   /usr/bin/python3 run.py etf-list-paginated --page_size 50 > output.json 2>&1
   ```

2. **数据量控制**：`etf-description-all` 返回全量数据（1600+条），可能超时。建议用 `etf-list-paginated` 分页获取。

3. **字段更新**：非凸数据包含动态字段（价格、涨跌幅等），建议定期更新。

## 已验证场景

- ✅ 成功获取1645条非凸ETF数据
- ✅ 与本地100条ETF数据成功匹配
- ✅ 校正了价格、涨跌幅等动态字段
- ✅ 修正了97条ETF名称（去除末尾管理人名称）

## 快速调用模板

**用户问法 → 执行命令：**

| 用户问法 | 执行命令 |
|-----------|-----------|
| "查询ETF列表" | `run.py etf-list-paginated --page_size 50` |
| "查看510300详情" | `run.py etf-detail --symbol 510300.XSHG` |
| "ETF持仓有哪些" | `run.py etf-component --symbol 510300.XSHG` |
| "对比校正ETF数据" | 使用本技能的工作流程示例 |

---

## Skill: github-actions-pythonanywhere-deploy

---
name: github-actions-pythonanywhere-deploy
description: GitHub Actions 自动部署到 PythonAnywhere。当用户需要配置 CI/CD 流水线、自动化部署 Flask/Django 应用到 PythonAnywhere、或通过 GitHub Actions 执行远程命令时使用。包含完整的 YAML 配置、SSH 部署、API 调用。
---

# GitHub Actions 自动部署到 PythonAnywhere

## 核心原则

**自动化一切** - 推送代码后自动部署，无需手动操作

**安全第一** - 使用 GitHub Secrets 存储敏感信息（API Token、SSH Key）

**测试先行** - 在部署前运行测试，确保代码质量

## 何时使用此 Skill

- 用户说"配置 GitHub Actions 自动部署"
- 用户说"推送代码后自动部署到 PythonAnywhere"
- 需要自动化 CI/CD 流水线
- 需要通过 GitHub Actions 执行远程命令

## 工作流程

```
代码推送 → GitHub Actions 触发 → 运行测试 → 部署到 PythonAnywhere → 通知
```

## 配置步骤

### 1. 准备工作

**在 PythonAnywhere 上生成 API Token**
1. 登录 PythonAnywhere
2. 进入 "Account" → "API token"
3. 点击 "Create new API token"
4. 复制 token（只显示一次）

**在 PythonAnywhere 上配置 SSH Key（可选，用于更安全的部署）**
```bash
# 本地生成 SSH Key
ssh-keygen -t rsa -b 4096 -C "your_email@example.com"

# 将公钥添加到 PythonAnywhere
# 复制 ~/.ssh/id_rsa.pub 内容
# 在 PythonAnywhere Dashboard → "Account" → "SSH keys" 中添加
```

### 2. 配置 GitHub Secrets

在 GitHub 仓库中，进入 **Settings → Secrets and variables → Actions**，添加以下 secrets：

| Secret 名称 | 说明 | 示例 |
|------------|------|------|
| `PA_API_TOKEN` | PythonAnywhere API Token | `your-api-token-xxx` |
| `PA_USERNAME` | PythonAnywhere 用户名 | `yourusername` |
| `PA_SSH_HOST` | PythonAnywhere SSH 地址 | `ssh.pythonanywhere.com` |
| `PA_SSH_KEY` | SSH 私钥（完整内容） | `-----BEGIN OPENSSH...` |
| `PA_APP_PATH` | 应用路径 | `/home/yourusername/myapp` |

### 3. 创建 GitHub Actions 工作流程

创建文件：`.github/workflows/deploy.yml`

```yaml
name: Deploy to PythonAnywhere

on:
  push:
    branches: [ main, master ]
  pull_request:
    branches: [ main, master ]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
    - uses: actions/checkout@v3

    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.9'

    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install pytest

    - name: Run tests
      run: |
        pytest tests/

  deploy:
    needs: test
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main' || github.ref == 'refs/heads/master'

    steps:
    - uses: actions/checkout@v3

    - name: Deploy to PythonAnywhere via API
      env:
        PA_API_TOKEN: ${{ secrets.PA_API_TOKEN }}
        PA_USERNAME: ${{ secrets.PA_USERNAME }}
      run: |
        # 方法1：通过 API 重启 Web 应用
        curl -X POST \
          -H "Authorization: Token ${PA_API_TOKEN}" \
          "https://www.pythonanywhere.com/api/v0/user/${PA_USERNAME}/webapps/yourusername.pythonanywhere.com/reload/"

    - name: Deploy via SSH
      uses: appleboy/ssh-action@v1.0.0
      with:
        host: ${{ secrets.PA_SSH_HOST }}
        username: ${{ secrets.PA_USERNAME }}
        key: ${{ secrets.PA_SSH_KEY }}
        script: |
          cd ${{ secrets.PA_APP_PATH }}
          git pull origin main
          workon myenv
          pip install -r requirements.txt
          touch /var/www/yourusername_pythonanywhere_com_wsgi.py

    - name: Notify deployment status
      if: always()
      uses: 8398a7/action-slack@v3
      with:
        status: ${{ job.status }}
        text: '部署到 PythonAnywhere {{ job.status }}'
        webhook_url: ${{ secrets.SLACK_WEBHOOK }}
```

### 4. 高级配置

**方法1：通过 PythonAnywhere API 部署**

```yaml
- name: Deploy via PythonAnywhere API
  run: |
    # 更新代码（通过 Git）
    curl -X POST \
      -H "Authorization: Token ${{ secrets.PA_API_TOKEN }}" \
      -d "repo_url=https://github.com/yourusername/yourrepo.git" \
      "https://www.pythonanywhere.com/api/v0/user/${{ secrets.PA_USERNAME }}/webapps/yourusername.pythonanywhere.com/git_pull/"

    # 重启 Web 应用
    curl -X POST \
      -H "Authorization: Token ${{ secrets.PA_API_TOKEN }}" \
      "https://www.pythonanywhere.com/api/v0/user/${{ secrets.PA_USERNAME }}/webapps/yourusername.pythonanywhere.com/reload/"
```

**方法2：通过 SSH 执行远程命令**

```yaml
- name: Deploy via SSH
  uses: appleboy/ssh-action@v1.0.0
  with:
    host: ssh.pythonanywhere.com
    username: ${{ secrets.PA_USERNAME }}
    key: ${{ secrets.PA_SSH_KEY }}
    script: |
      cd /home/${{ secrets.PA_USERNAME }}/myapp
      git pull origin main
      source /home/${{ secrets.PA_USERNAME }}/.virtualenvs/myenv/bin/activate
      pip install -r requirements.txt
      python manage.py migrate  # Django
      touch /var/www/yourusername_pythonanywhere_com_wsgi.py
```

**方法3：使用 PythonAnywhere CLI（推荐）**

```yaml
- name: Install PythonAnywhere CLI
  run: pip install pythonanywhere-cli

- name: Deploy using PA CLI
  env:
    PA_API_TOKEN: ${{ secrets.PA_API_TOKEN }}
  run: |
    pa login --token ${PA_API_TOKEN}
    pa webapp.reload yourusername.pythonanywhere.com
```

### 5. 完整的 GitHub Actions 配置示例

使用 `scripts/deploy_workflow.yml` 作为模板。

## PythonAnywhere API 参考

### 认证

所有 API 请求需要在 Header 中添加：
```
Authorization: Token your-api-token
```

### 常用端点

**重新加载 Web 应用**
```
POST /api/v0/user/{username}/webapps/{domain_name}/reload/
```

**获取 Web 应用信息**
```
GET /api/v0/user/{username}/webapps/{domain_name}/
```

**更新代码（Git Pull）**
```
POST /api/v0/user/{username}/webapps/{domain_name}/git_pull/
{
  "repo_url": "https://github.com/yourusername/yourrepo.git"
}
```

**执行控制台命令**
```
POST /api/v0/user/{username}/consoles/
{
  "command": "cd /home/yourusername/myapp && git pull"
}
```

## 定时任务配置（可选）

如果需要定时执行任务（如每日数据更新），可以配置 GitHub Actions 定时触发器：

```yaml
name: Scheduled Task

on:
  schedule:
    - cron: '0 2 * * *'  # 每天凌晨 2 点执行
  workflow_dispatch:  # 允许手动触发

jobs:
  run-task:
    runs-on: ubuntu-latest

    steps:
    - name: Call PythonAnywhere API
      run: |
        curl -X GET \
          -H "Authorization: Token ${{ secrets.PA_API_TOKEN }}" \
          "https://yourusername.pythonanywhere.com/api/scheduled_task/"
```

## 常见问题

### 问题1：SSH 连接失败

**原因**：SSH Key 配置错误
**解决**：
1. 确保公钥已添加到 PythonAnywhere
2. 确保私钥已正确添加到 GitHub Secrets
3. 检查 SSH Key 格式（应包含 `-----BEGIN OPENSSH PRIVATE KEY-----`）

### 问题2：API Token 权限不足

**原因**：API Token 权限不够
**解决**：
1. 重新生成 API Token
2. 确保 Token 有访问 Web 应用和文件的权限

### 问题3：部署后应用未更新

**原因**：WSGI 文件未重新加载
**解决**：
```yaml
- name: Reload WSGI
  run: |
    touch /var/www/yourusername_pythonanywhere_com_wsgi.py
```

## 最佳实践

1. **分离测试和生产环境** - 使用不同的 PythonAnywhere 账户或子域名
2. **回滚机制** - 保留旧版本代码，部署失败时可以快速回滚
3. **健康检查** - 部署后自动检查应用是否正常运行
4. **通知机制** - 部署成功/失败后发送通知（Slack/Email）
5. **分阶段部署** - 先部署到测试环境，验证通过后再部署到生产环境

## 触发词

当用户提到以下内容时，使用此 skill：
- "配置 GitHub Actions"
- "自动部署到 PythonAnywhere"
- "CI/CD 流水线"
- "推送代码后自动部署"

---

## Skill: github-actions-pythonanywhere-deploy.skill

---
name: github-actions-pythonanywhere-deploy
description: GitHub Actions 自动部署到 PythonAnywhere。当用户需要配置 CI/CD 流水线、自动化部署 Flask/Django 应用到 PythonAnywhere、或通过 GitHub Actions 执行远程命令时使用。包含完整的 YAML 配置、SSH 部署、API 调用。
---

# GitHub Actions 自动部署到 PythonAnywhere

## 核心原则

**自动化一切** - 推送代码后自动部署，无需手动操作

**安全第一** - 使用 GitHub Secrets 存储敏感信息（API Token、SSH Key）

**测试先行** - 在部署前运行测试，确保代码质量

## 何时使用此 Skill

- 用户说"配置 GitHub Actions 自动部署"
- 用户说"推送代码后自动部署到 PythonAnywhere"
- 需要自动化 CI/CD 流水线
- 需要通过 GitHub Actions 执行远程命令

## 工作流程

```
代码推送 → GitHub Actions 触发 → 运行测试 → 部署到 PythonAnywhere → 通知
```

## 配置步骤

### 1. 准备工作

**在 PythonAnywhere 上生成 API Token**
1. 登录 PythonAnywhere
2. 进入 "Account" → "API token"
3. 点击 "Create new API token"
4. 复制 token（只显示一次）

**在 PythonAnywhere 上配置 SSH Key（可选，用于更安全的部署）**
```bash
# 本地生成 SSH Key
ssh-keygen -t rsa -b 4096 -C "your_email@example.com"

# 将公钥添加到 PythonAnywhere
# 复制 ~/.ssh/id_rsa.pub 内容
# 在 PythonAnywhere Dashboard → "Account" → "SSH keys" 中添加
```

### 2. 配置 GitHub Secrets

在 GitHub 仓库中，进入 **Settings → Secrets and variables → Actions**，添加以下 secrets：

| Secret 名称 | 说明 | 示例 |
|------------|------|------|
| `PA_API_TOKEN` | PythonAnywhere API Token | `your-api-token-xxx` |
| `PA_USERNAME` | PythonAnywhere 用户名 | `yourusername` |
| `PA_SSH_HOST` | PythonAnywhere SSH 地址 | `ssh.pythonanywhere.com` |
| `PA_SSH_KEY` | SSH 私钥（完整内容） | `-----BEGIN OPENSSH...` |
| `PA_APP_PATH` | 应用路径 | `/home/yourusername/myapp` |

### 3. 创建 GitHub Actions 工作流程

创建文件：`.github/workflows/deploy.yml`

```yaml
name: Deploy to PythonAnywhere

on:
  push:
    branches: [ main, master ]
  pull_request:
    branches: [ main, master ]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
    - uses: actions/checkout@v3

    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.9'

    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install pytest

    - name: Run tests
      run: |
        pytest tests/

  deploy:
    needs: test
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main' || github.ref == 'refs/heads/master'

    steps:
    - uses: actions/checkout@v3

    - name: Deploy to PythonAnywhere via API
      env:
        PA_API_TOKEN: ${{ secrets.PA_API_TOKEN }}
        PA_USERNAME: ${{ secrets.PA_USERNAME }}
      run: |
        # 方法1：通过 API 重启 Web 应用
        curl -X POST \
          -H "Authorization: Token ${PA_API_TOKEN}" \
          "https://www.pythonanywhere.com/api/v0/user/${PA_USERNAME}/webapps/yourusername.pythonanywhere.com/reload/"

    - name: Deploy via SSH
      uses: appleboy/ssh-action@v1.0.0
      with:
        host: ${{ secrets.PA_SSH_HOST }}
        username: ${{ secrets.PA_USERNAME }}
        key: ${{ secrets.PA_SSH_KEY }}
        script: |
          cd ${{ secrets.PA_APP_PATH }}
          git pull origin main
          workon myenv
          pip install -r requirements.txt
          touch /var/www/yourusername_pythonanywhere_com_wsgi.py

    - name: Notify deployment status
      if: always()
      uses: 8398a7/action-slack@v3
      with:
        status: ${{ job.status }}
        text: '部署到 PythonAnywhere {{ job.status }}'
        webhook_url: ${{ secrets.SLACK_WEBHOOK }}
```

### 4. 高级配置

**方法1：通过 PythonAnywhere API 部署**

```yaml
- name: Deploy via PythonAnywhere API
  run: |
    # 更新代码（通过 Git）
    curl -X POST \
      -H "Authorization: Token ${{ secrets.PA_API_TOKEN }}" \
      -d "repo_url=https://github.com/yourusername/yourrepo.git" \
      "https://www.pythonanywhere.com/api/v0/user/${{ secrets.PA_USERNAME }}/webapps/yourusername.pythonanywhere.com/git_pull/"

    # 重启 Web 应用
    curl -X POST \
      -H "Authorization: Token ${{ secrets.PA_API_TOKEN }}" \
      "https://www.pythonanywhere.com/api/v0/user/${{ secrets.PA_USERNAME }}/webapps/yourusername.pythonanywhere.com/reload/"
```

**方法2：通过 SSH 执行远程命令**

```yaml
- name: Deploy via SSH
  uses: appleboy/ssh-action@v1.0.0
  with:
    host: ssh.pythonanywhere.com
    username: ${{ secrets.PA_USERNAME }}
    key: ${{ secrets.PA_SSH_KEY }}
    script: |
      cd /home/${{ secrets.PA_USERNAME }}/myapp
      git pull origin main
      source /home/${{ secrets.PA_USERNAME }}/.virtualenvs/myenv/bin/activate
      pip install -r requirements.txt
      python manage.py migrate  # Django
      touch /var/www/yourusername_pythonanywhere_com_wsgi.py
```

**方法3：使用 PythonAnywhere CLI（推荐）**

```yaml
- name: Install PythonAnywhere CLI
  run: pip install pythonanywhere-cli

- name: Deploy using PA CLI
  env:
    PA_API_TOKEN: ${{ secrets.PA_API_TOKEN }}
  run: |
    pa login --token ${PA_API_TOKEN}
    pa webapp.reload yourusername.pythonanywhere.com
```

### 5. 完整的 GitHub Actions 配置示例

使用 `scripts/deploy_workflow.yml` 作为模板。

## PythonAnywhere API 参考

### 认证

所有 API 请求需要在 Header 中添加：
```
Authorization: Token your-api-token
```

### 常用端点

**重新加载 Web 应用**
```
POST /api/v0/user/{username}/webapps/{domain_name}/reload/
```

**获取 Web 应用信息**
```
GET /api/v0/user/{username}/webapps/{domain_name}/
```

**更新代码（Git Pull）**
```
POST /api/v0/user/{username}/webapps/{domain_name}/git_pull/
{
  "repo_url": "https://github.com/yourusername/yourrepo.git"
}
```

**执行控制台命令**
```
POST /api/v0/user/{username}/consoles/
{
  "command": "cd /home/yourusername/myapp && git pull"
}
```

## 定时任务配置（可选）

如果需要定时执行任务（如每日数据更新），可以配置 GitHub Actions 定时触发器：

```yaml
name: Scheduled Task

on:
  schedule:
    - cron: '0 2 * * *'  # 每天凌晨 2 点执行
  workflow_dispatch:  # 允许手动触发

jobs:
  run-task:
    runs-on: ubuntu-latest

    steps:
    - name: Call PythonAnywhere API
      run: |
        curl -X GET \
          -H "Authorization: Token ${{ secrets.PA_API_TOKEN }}" \
          "https://yourusername.pythonanywhere.com/api/scheduled_task/"
```

## 常见问题

### 问题1：SSH 连接失败

**原因**：SSH Key 配置错误
**解决**：
1. 确保公钥已添加到 PythonAnywhere
2. 确保私钥已正确添加到 GitHub Secrets
3. 检查 SSH Key 格式（应包含 `-----BEGIN OPENSSH PRIVATE KEY-----`）

### 问题2：API Token 权限不足

**原因**：API Token 权限不够
**解决**：
1. 重新生成 API Token
2. 确保 Token 有访问 Web 应用和文件的权限

### 问题3：部署后应用未更新

**原因**：WSGI 文件未重新加载
**解决**：
```yaml
- name: Reload WSGI
  run: |
    touch /var/www/yourusername_pythonanywhere_com_wsgi.py
```

## 最佳实践

1. **分离测试和生产环境** - 使用不同的 PythonAnywhere 账户或子域名
2. **回滚机制** - 保留旧版本代码，部署失败时可以快速回滚
3. **健康检查** - 部署后自动检查应用是否正常运行
4. **通知机制** - 部署成功/失败后发送通知（Slack/Email）
5. **分阶段部署** - 先部署到测试环境，验证通过后再部署到生产环境

## 触发词

当用户提到以下内容时，使用此 skill：
- "配置 GitHub Actions"
- "自动部署到 PythonAnywhere"
- "CI/CD 流水线"
- "推送代码后自动部署"

---

## Skill: pythonanywhere-deploy

---
name: pythonanywhere-deploy
description: PythonAnywhere 平台部署指南。当用户需要部署 Python Web 应用（Flask/Django/FastAPI）到 PythonAnywhere、配置 WSGI 文件、上传代码、或解决部署问题时使用。包含完整的部署流程、常见错误排查、静态文件配置。
---

# PythonAnywhere 部署指南

## 核心原则

**简单优于复杂** - PythonAnywhere 适合小型到中型应用，不要过度设计

**先本地测试，再部署** - 确保应用在本地完全正常运行后再部署

**使用虚拟环境** - 避免依赖冲突

## 核心限制（重要！）

- **免费账户不支持 SSH** — 无法用 `appleboy/ssh-action` 或任何 SSH 方式部署
- 免费账户只能使用 **PythonAnywhere API 方式** 实现自动部署
- 升级付费账户（$5/月起）才支持 SSH
- 此限制已被验证多次，务必记住

## GitHub Actions 自动部署（免费账户兼容方案）

### 原理
通过 PythonAnywhere 的 Consoles API 创建远程控制台，发送 `git pull` 等命令，再用 Reload API 重启 Web 应用。

### 所需 GitHub Secrets
| Name | Value |
|------|-------|
| `PA_API_TOKEN` | PythonAnywhere API Token（Account 页面生成） |
| `PA_USERNAME` | PythonAnywhere 用户名（如 `froza`） |

### 获取 PA_API_TOKEN
1. 登录 `https://www.pythonanywhere.com/account/`
2. 找到 **API token** 栏 → 点 **Create new token**
3. 复制生成的 token（完整字符串）

### Workflow 示例（API 方式）
```yaml
deploy:
  needs: test
  runs-on: ubuntu-latest
  steps:
  - name: Deploy via PythonAnywhere API
    env:
      PA_API_TOKEN: ${{ secrets.PA_API_TOKEN }}
      PA_USERNAME: ${{ secrets.PA_USERNAME }}
    run: |
      BASE="https://www.pythonanywhere.com/api/v1"
      AUTH="-H \"Authorization: Token $PA_API_TOKEN\""

      # 1. 创建控制台
      CONSOLE_JSON=$(curl -s $AUTH "$BASE/user/$PA_USERNAME/consoles/" -X POST)
      CONSOLE_ID=$(echo $CONSOLE_JSON | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")

      # 2. 发送 git pull
      curl -s $AUTH "$BASE/user/$PA_USERNAME/consoles/$CONSOLE_ID/send_input/" \
        -X POST -d "cd /home/$PA_USERNAME/etf-tool-mvp && git pull origin main"$'\n'
      sleep 5

      # 3. 安装依赖
      curl -s $AUTH "$BASE/user/$PA_USERNAME/consoles/$CONSOLE_ID/send_input/" \
        -X POST -d "pip install -r /home/$PA_USERNAME/etf-tool-mvp/requirements.txt 2>/dev/null || echo skip"$'\n'
      sleep 5

      # 4. touch WSGI 触发重载
      curl -s $AUTH "$BASE/user/$PA_USERNAME/consoles/$CONSOLE_ID/send_input/" \
        -X POST -d "touch /var/www/${PA_USERNAME}_pythonanywhere_com_wsgi.py"$'\n'
      sleep 3

      # 5. 关闭控制台
      curl -s $AUTH "$BASE/user/$PA_USERNAME/consoles/$CONSOLE_ID/" -X PATCH -d "status=deleted"

      # 6. 调用 reload API
      curl -s $AUTH "$BASE/domain_reload/$PA_USERNAME.pythonanywhere.com/"
      echo "✅ 部署完成！"
```

### 常见错误排查
- **`ssh: unable to authenticate`** → 免费账户不支持 SSH，改用上方 API 方式
- **`401 Unauthorized`** → `PA_API_TOKEN` 填写错误，重新从 Account 页面复制
- **`git pull` 失败** → PythonAnywhere 上项目目录没有 git 仓库，先手动 clone 一次
- **部署后无变化** → 确保 `touch /var/www/..._wsgi.py` 路径正确

## 何时使用此 Skill

- 用户说"部署到 PythonAnywhere"
- 用户说"上传代码到 PythonAnywhere"
- 需要配置 WSGI 文件
- 部署后出现 500/404 错误
- 静态文件无法加载

## 部署流程

### 1. 准备工作

**本地测试**
```bash
# 确保应用能在本地运行
python app.py
# 或
flask run
```

**创建 requirements.txt**
```bash
pip freeze > requirements.txt
```

**确保有以下文件**
- `app.py` 或 `main.py`（入口文件）
- `requirements.txt`（依赖列表）
- `templates/`（如果使用 Flask 模板）
- `static/`（静态文件）

### 2. 上传代码到 PythonAnywhere

**方法 1：通过 Web IDE 上传（推荐小文件）**
1. 登录 PythonAnywhere
2. 打开 Web IDE
3. 上传文件/文件夹

**方法 2：通过 Bash 控制台使用 Git**
```bash
# 在 PythonAnywhere 控制台
git clone https://github.com/yourusername/your-repo.git
```

**方法 3：通过 FTP/SFTP**
```bash
# 使用 FileZilla 或其他 FTP 客户端
# 主机: yourusername.pythonanywhere.com
# 用户名: yourusername
# 密码: your-api-token
```

### 3. 配置虚拟环境

```bash
# 在 PythonAnywhere Bash 控制台
mkvirtualenv myenv --python=python3.9
workon myenv
pip install -r requirements.txt
```

### 4. 配置 WSGI 文件

**找到 WSGI 配置文件**
- 路径：`/var/www/yourusername_pythonanywhere_com_wsgi.py`

**Flask 应用配置示例**
```python
import sys
import os

# 添加项目路径到 sys.path
project_home = '/home/yourusername/myproject'
if project_home not in sys.path:
    sys.path.insert(0, project_home)

# 设置环境变量
os.environ['FLASK_ENV'] = 'production'

# 导入 Flask app
from app import app as application
```

**Django 应用配置示例**
```python
import os
import sys

# 添加项目路径
path = '/home/yourusername/myproject'
if path not in sys.path:
    sys.path.insert(0, path)

# 设置 Django settings 模块
os.environ['DJANGO_SETTINGS_MODULE'] = 'myproject.settings'

# 导入 Django WSGI handler
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
```

### 5. 配置 Web 应用

1. 进入 PythonAnywhere Dashboard
2. 点击 "Web" 标签
3. 点击 "Add a new web app"
4. 选择 "Manual configuration"
5. 选择 Python 版本（建议 3.9 或 3.10）
6. 在 "Code" 部分：
   - Source code: `/home/yourusername/myproject`
   - WSGI configuration file: 自动生成，需要编辑
7. 在 "Virtualenv" 部分：
   - Enter path to a virtualenv: `/home/yourusername/.virtualenvs/myenv`
8. 点击绿色的 "Reload" 按钮

### 6. 静态文件配置

**Flask 应用**
```python
from flask import Flask
app = Flask(__name__, static_url_path='/static')

# 在 PythonAnywhere Web 配置中：
# URL: /static/
# Directory: /home/yourusername/myproject/static
```

**Django 应用**
```python
# settings.py
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

# 运行 collectstatic
# python manage.py collectstatic

# 在 PythonAnywhere Web 配置中：
# URL: /static/
# Directory: /home/yourusername/myproject/staticfiles
```

## 常见错误及解决方案

### 错误 1：500 Internal Server Error

**排查步骤**
```bash
# 1. 查看错误日志
tail -f /var/log/yourusername_pythonanywhere_com_error.log

# 2. 检查 WSGI 文件语法
python -c "import py_compile; py_compile.compile('/var/www/yourusername_pythonanywhere_com_wsgi.py', doraise=True)"

# 3. 确保在虚拟环境中安装了所有依赖
workon myenv
pip list
```

**常见原因**
- WSGI 文件语法错误
- 缺少依赖包
- 环境变量未设置
- 文件路径错误

### 错误 2：404 Not Found

**排查步骤**
```python
# 确保 Flask app 路由正确
@app.route('/')
def index():
    return 'Hello, World!'
```

**常见原因**
- 路由配置错误
- WSGI 文件未正确导入 app

### 错误 3：静态文件无法加载

**解决方案**
1. 检查静态文件路径配置
2. 确保在 PythonAnywhere Web 配置中正确设置了静态文件映射
3. 运行 `python manage.py collectstatic`（Django）

### 错误 4：ImportError

**解决方案**
```python
# 在 WSGI 文件开头添加
import sys
sys.path.insert(0, '/home/yourusername/myproject')

# 确保 __init__.py 存在（对于 Python 包）
touch /home/yourusername/myproject/__init__.py
```

## 完整部署检查清单

- [ ] 应用在本地运行正常
- [ ] `requirements.txt` 已生成
- [ ] 代码已上传到 PythonAnywhere
- [ ] 虚拟环境已创建并激活
- [ ] 依赖已安装（`pip install -r requirements.txt`）
- [ ] WSGI 文件已正确配置
- [ ] Web 应用已配置（Python 版本、虚拟环境路径）
- [ ] 静态文件已配置（如需要）
- [ ] 点击了 "Reload" 按钮
- [ ] 检查错误日志

## 使用示例

使用 `scripts/deploy_flask_app.sh` 自动化部署 Flask 应用。

## 注意事项

1. **免费账户限制** - 每天 CPU 时间限制，不适合高流量应用
2. **休眠机制** - 免费账户应用会在不活动时休眠，首次访问可能较慢
3. **数据库** - PythonAnywhere 提供 MySQL 和 PostgreSQL，需要在 Dashboard 中创建
4. **HTTPS** - 自动提供，URL 为 `https://yourusername.pythonanywhere.com`
5. **日志** - 错误日志路径：`/var/log/yourusername_pythonanywhere_com_error.log`

## 快速参考

**重要路径**
- 项目目录：`/home/yourusername/myproject`
- WSGI 文件：`/var/www/yourusername_pythonanywhere_com_wsgi.py`
- 错误日志：`/var/log/yourusername_pythonanywhere_com_error.log`
- 访问日志：`/var/log/yourusername_pythonanywhere_com_access.log`
- 虚拟环境：`/home/yourusername/.virtualenvs/myenv`

**重要命令**
```bash
workon myenv              # 激活虚拟环境
pip install -r requirements.txt  # 安装依赖
touch /var/www/yourusername_pythonanywhere_com_wsgi.py  # 触发重启
tail -f /var/log/yourusername_pythonanywhere_com_error.log  # 查看错误日志
```

---

## Skill: pythonanywhere-deploy.skill

---
name: pythonanywhere-deploy
description: PythonAnywhere 平台部署指南。当用户需要部署 Python Web 应用（Flask/Django/FastAPI）到 PythonAnywhere、配置 WSGI 文件、上传代码、或解决部署问题时使用。包含完整的部署流程、常见错误排查、静态文件配置。
---

# PythonAnywhere 部署指南

## 核心原则

**简单优于复杂** - PythonAnywhere 适合小型到中型应用，不要过度设计

**先本地测试，再部署** - 确保应用在本地完全正常运行后再部署

**使用虚拟环境** - 避免依赖冲突

## 何时使用此 Skill

- 用户说"部署到 PythonAnywhere"
- 用户说"上传代码到 PythonAnywhere"
- 需要配置 WSGI 文件
- 部署后出现 500/404 错误
- 静态文件无法加载

## 部署流程

### 1. 准备工作

**本地测试**
```bash
# 确保应用能在本地运行
python app.py
# 或
flask run
```

**创建 requirements.txt**
```bash
pip freeze > requirements.txt
```

**确保有以下文件**
- `app.py` 或 `main.py`（入口文件）
- `requirements.txt`（依赖列表）
- `templates/`（如果使用 Flask 模板）
- `static/`（静态文件）

### 2. 上传代码到 PythonAnywhere

**方法 1：通过 Web IDE 上传（推荐小文件）**
1. 登录 PythonAnywhere
2. 打开 Web IDE
3. 上传文件/文件夹

**方法 2：通过 Bash 控制台使用 Git**
```bash
# 在 PythonAnywhere 控制台
git clone https://github.com/yourusername/your-repo.git
```

**方法 3：通过 FTP/SFTP**
```bash
# 使用 FileZilla 或其他 FTP 客户端
# 主机: yourusername.pythonanywhere.com
# 用户名: yourusername
# 密码: your-api-token
```

### 3. 配置虚拟环境

```bash
# 在 PythonAnywhere Bash 控制台
mkvirtualenv myenv --python=python3.9
workon myenv
pip install -r requirements.txt
```

### 4. 配置 WSGI 文件

**找到 WSGI 配置文件**
- 路径：`/var/www/yourusername_pythonanywhere_com_wsgi.py`

**Flask 应用配置示例**
```python
import sys
import os

# 添加项目路径到 sys.path
project_home = '/home/yourusername/myproject'
if project_home not in sys.path:
    sys.path.insert(0, project_home)

# 设置环境变量
os.environ['FLASK_ENV'] = 'production'

# 导入 Flask app
from app import app as application
```

**Django 应用配置示例**
```python
import os
import sys

# 添加项目路径
path = '/home/yourusername/myproject'
if path not in sys.path:
    sys.path.insert(0, path)

# 设置 Django settings 模块
os.environ['DJANGO_SETTINGS_MODULE'] = 'myproject.settings'

# 导入 Django WSGI handler
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
```

### 5. 配置 Web 应用

1. 进入 PythonAnywhere Dashboard
2. 点击 "Web" 标签
3. 点击 "Add a new web app"
4. 选择 "Manual configuration"
5. 选择 Python 版本（建议 3.9 或 3.10）
6. 在 "Code" 部分：
   - Source code: `/home/yourusername/myproject`
   - WSGI configuration file: 自动生成，需要编辑
7. 在 "Virtualenv" 部分：
   - Enter path to a virtualenv: `/home/yourusername/.virtualenvs/myenv`
8. 点击绿色的 "Reload" 按钮

### 6. 静态文件配置

**Flask 应用**
```python
from flask import Flask
app = Flask(__name__, static_url_path='/static')

# 在 PythonAnywhere Web 配置中：
# URL: /static/
# Directory: /home/yourusername/myproject/static
```

**Django 应用**
```python
# settings.py
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

# 运行 collectstatic
# python manage.py collectstatic

# 在 PythonAnywhere Web 配置中：
# URL: /static/
# Directory: /home/yourusername/myproject/staticfiles
```

## 常见错误及解决方案

### 错误 1：500 Internal Server Error

**排查步骤**
```bash
# 1. 查看错误日志
tail -f /var/log/yourusername_pythonanywhere_com_error.log

# 2. 检查 WSGI 文件语法
python -c "import py_compile; py_compile.compile('/var/www/yourusername_pythonanywhere_com_wsgi.py', doraise=True)"

# 3. 确保在虚拟环境中安装了所有依赖
workon myenv
pip list
```

**常见原因**
- WSGI 文件语法错误
- 缺少依赖包
- 环境变量未设置
- 文件路径错误

### 错误 2：404 Not Found

**排查步骤**
```python
# 确保 Flask app 路由正确
@app.route('/')
def index():
    return 'Hello, World!'
```

**常见原因**
- 路由配置错误
- WSGI 文件未正确导入 app

### 错误 3：静态文件无法加载

**解决方案**
1. 检查静态文件路径配置
2. 确保在 PythonAnywhere Web 配置中正确设置了静态文件映射
3. 运行 `python manage.py collectstatic`（Django）

### 错误 4：ImportError

**解决方案**
```python
# 在 WSGI 文件开头添加
import sys
sys.path.insert(0, '/home/yourusername/myproject')

# 确保 __init__.py 存在（对于 Python 包）
touch /home/yourusername/myproject/__init__.py
```

## 完整部署检查清单

- [ ] 应用在本地运行正常
- [ ] `requirements.txt` 已生成
- [ ] 代码已上传到 PythonAnywhere
- [ ] 虚拟环境已创建并激活
- [ ] 依赖已安装（`pip install -r requirements.txt`）
- [ ] WSGI 文件已正确配置
- [ ] Web 应用已配置（Python 版本、虚拟环境路径）
- [ ] 静态文件已配置（如需要）
- [ ] 点击了 "Reload" 按钮
- [ ] 检查错误日志

## 使用示例

使用 `scripts/deploy_flask_app.sh` 自动化部署 Flask 应用。

## 注意事项

1. **免费账户限制** - 每天 CPU 时间限制，不适合高流量应用
2. **休眠机制** - 免费账户应用会在不活动时休眠，首次访问可能较慢
3. **数据库** - PythonAnywhere 提供 MySQL 和 PostgreSQL，需要在 Dashboard 中创建
4. **HTTPS** - 自动提供，URL 为 `https://yourusername.pythonanywhere.com`
5. **日志** - 错误日志路径：`/var/log/yourusername_pythonanywhere_com_error.log`

## 快速参考

**重要路径**
- 项目目录：`/home/yourusername/myproject`
- WSGI 文件：`/var/www/yourusername_pythonanywhere_com_wsgi.py`
- 错误日志：`/var/log/yourusername_pythonanywhere_com_error.log`
- 访问日志：`/var/log/yourusername_pythonanywhere_com_access.log`
- 虚拟环境：`/home/yourusername/.virtualenvs/myenv`

**重要命令**
```bash
workon myenv              # 激活虚拟环境
pip install -r requirements.txt  # 安装依赖
touch /var/www/yourusername_pythonanywhere_com_wsgi.py  # 触发重启
tail -f /var/log/yourusername_pythonanywhere_com_error.log  # 查看错误日志
```

---

## Skill: pythonanywhere-deployment

---
name: pythonanywhere-deployment
description: PythonAnywhere平台部署指南。当用户需要部署Python Web应用（Flask/Django/FastAPI）到PythonAnywhere免费版时使用。包含标准化部署流程、常见问题诊断、以及针对免费版限制的解决方案。触发词：PythonAnywhere、PA部署、部署到PA、froza.pythonanywhere.com。
---

# PythonAnywhere Deployment

## Core Rules (死规则)

### Rule 1: PA部署用 `git reset --hard`，不用 `git pull`
**PA是生产环境，不是开发分支。** 每次部署都应该是强制同步：
```bash
cd ~/etf-tool-mvp
git fetch origin
git reset --hard origin/main
touch /var/www/froza_pythonanywhere_com_wsgi.py
```
**绝不`git pull`**（`pull` = `fetch + merge`，PA不应该有本地修改）。

### Rule 2: 诊断时一次性给完整命令包
**不要一次只问一个问题。** 要么给3-5个命令让用户一次性执行完，要么直接给出解决方案。

**坏例子：**
> "执行`git pull`" → （等回复）→ "哦，那执行`git remote -v`" → （等回复）→ ...

**好例子：**
> "执行这5个命令，把所有输出贴回来：
> ```bash
> git remote -v
> git fetch origin
> git log origin/main --oneline -3
> git status
> git diff HEAD
> ```"

### Rule 3: 同一问题出现2次，立即换方案
**"Already up to date"出现2次 → 不再试`git pull`，直接`git reset --hard`。**  
**同一诊断命令问2次 → 不再问，直接给解决方案。**

### Rule 4: PA部署前，先确认remote URL是对的
**PA的remote URL可能过期（比如仓库重命名）。** 每次部署前，先检查：
```bash
git remote -v  # 确认URL是对的
```

## Standard Deployment Scenarios

### Scenario A: 正常部署（代码已push到GitHub）
```bash
# 在PA终端执行
cd ~/etf-tool-mvp
git fetch origin
git reset --hard origin/main
touch /var/www/froza_pythonanywhere_com_wsgi.py
```

### Scenario B: PA的remote URL过期（仓库重命名后）
```bash
# 在PA终端执行
cd ~/etf-tool-mvp
git remote set-url origin https://github.com/froza88/etf-tool-mvp.git
git fetch origin
git reset --hard origin/main
touch /var/www/froza_pythonanywhere_com_wsgi.py
```

### Scenario C: PA有本地修改，无法reset
```bash
# 在PA终端执行
cd ~/etf-tool-mvp
git fetch origin
git checkout -f origin/main -- .
git reset --hard origin/main
touch /var/www/froza_pythonanywhere_com_wsgi.py
```

## Free Tier Limitations

### Limitation 1: 无Scheduled tasks/SSH/Always-on任务
- **影响**：无法设置定时任务，无法SSH登录，应用空闲后首次访问会冷启动（约10-30秒）
- **应对**：
  - 用本地cron或GitHub Actions触发PA的Web API（通过`/api/ping`端点）
  - 或接受冷启动延迟

### Limitation 2: Web UI可用，但API调用超时
- **影响**：Flask应用中不能做耗时>10秒的同步API调用
- **应对**：
  - 所有外部API调用改为后台线程或异步任务
  - 或用缓存（本地JSON文件）避免实时API调用

### Limitation 3: 磁盘空间有限（免费版512MB）
- **影响**：上传大文件或历史数据会占满空间
- **应对**：
  - 用`.gitignore`排除大文件（如`data/history/*.json`）
  - 或用git LFS管理大文件

## Common Problem Diagnosis

### Problem 1: PA显示"Already up to date"但代码不是最新的
**根因**：PA的`origin`指向旧仓库URL，或本地有未提交的修改
**诊断命令**：
```bash
cd ~/etf-tool-mvp
git remote -v
git status
git log origin/main --oneline -3
```
**解决方案**：
- 如果remote URL错 → 用Scenario B的命令
- 如果本地有修改 → 用Scenario C的命令

### Problem 2: PA显示"Internal Server Error"
**根因**：WSGI文件错误、Python路径错、或应用代码有bug
**诊断命令**：
```bash
cd ~/etf-tool-mvp
python3 app.py  # 本地测试能否启动
tail -20 /var/log/froza_pythonanywhere_com_error.log  # 查看PA错误日志
```
**解决方案**：
- 修复代码bug
- 确认WSGI文件路径正确：`/var/www/froza_pythonanywhere_com_wsgi.py`
- 确认Python版本：PA免费版默认Python3.9

### Problem 3: PA部署后页面还是旧的
**根因**：没执行`touch`命令重启WSGI，或浏览器缓存
**解决方案**：
```bash
# PA终端
touch /var/www/froza_pythonanywhere_com_wsgi.py

# 浏览器：强制刷新 Ctrl+F5 (Windows) 或 Cmd+Shift+R (Mac)
```

## Pre-Deployment Local Testing

```bash
# 1. 启动本地Flask
cd /Users/apangduo/WorkBuddy/Claw/etf-tool-mvp
python3 app.py

# 2. 测试关键页面
curl http://localhost:5000/
curl http://localhost:5000/compare/v3?codes=510300,159915,510500

# 3. 如果测试通过，提交代码
git add .
git commit -m "feat: 描述本次改动"
git push origin main

# 4. PA部署（让用户执行）
# 告诉用户："在PA终端执行：cd ~/etf-tool-mvp && git fetch origin && git reset --hard origin/main && touch /var/www/froza_pythonanywhere_com_wsgi.py"
```

## Key File Locations

| 文件/目录 | 路径 | 说明 |
|-----------|------|------|
| WSGI文件 | `/var/www/froza_pythonanywhere_com_wsgi.py` | PA应用入口，修改后需`touch`重启 |
| 项目目录 | `~/etf-tool-mvp` | PA上的项目位置 |
| 错误日志 | `/var/log/froza_pythonanywhere_com_error.log` | Flask应用错误日志 |
| 访问日志 | `/var/log/froza_pythonanywhere_com_access.log` | Nginx访问日志 |

## Output Templates

### 部署成功时
```
✅ PA部署完成

**执行命令**：
cd ~/etf-tool-mvp && git fetch origin && git reset --hard origin/main && touch /var/www/froza_pythonanywhere_com_wsgi.py

**验证**：
- PA错误日志：无新错误
- 访问 https://froza.pythonanywhere.com 确认页面正常
```

### 部署失败时
```
❌ PA部署失败

**错误信息**：[粘贴错误]

**诊断**：
1. [原因1]
2. [原因2]

**解决方案**：
```bash
# 在PA终端执行
[命令1]
[命令2]
```

---

## Skill: pythonanywhere-scheduled-tasks

---
name: pythonanywhere-scheduled-tasks
description: PythonAnywhere 定时任务配置。当用户需要在 PythonAnywhere 上配置定时任务（Scheduled
  Tasks）、自动化执行脚本、定期更新数据、或管理任务执行状态时使用。包含 Web 界面配置、API 调用、常用场景示例、日志监控。
disable: false
---

# PythonAnywhere 定时任务配置

## 核心原则

**任务要幂等** - 定时任务可能重复执行，确保重复执行不会产生副作用

**记录日志** - 任务执行结果要记录到文件或数据库，便于排查问题

**监控执行状态** - 定期检查任务是否正常执行

## 何时使用此 Skill

- 用户说"配置定时任务"
- 用户说"每天自动更新数据"
- 用户说"定期执行脚本"
- 需要自动化任务（数据同步、报告生成、备份等）
- 需要监控任务执行状态

## 配置方法

### 方法1：通过 Web 界面配置（推荐新手）

**步骤**：
1. 登录 PythonAnywhere
2. 进入 "Tasks" 标签（左侧菜单）
3. 点击 "Add a new scheduled task"
4. 填写以下信息：
   - **Command**: 要执行的命令（绝对路径）
   - **Hour**: 执行小时（0-23）
   - **Minute**: 执行分钟（0-59）
   - **Day of week**: 星期几（* 表示每天）
   - **Day of month**: 日期（* 表示每天）
   - **Month**: 月份（* 表示每月）
5. 点击 "Create"

**示例配置（每天凌晨2点执行）**：
```
Command: /home/yourusername/.virtualenvs/myenv/bin/python /home/yourusername/myapp/update_data.py
Hour: 2
Minute: 0
Day of week: *
Day of month: *
Month: *
```

### 方法2：通过 API 配置（推荐高级用户）

**获取 API Token**
1. 登录 PythonAnywhere
2. 进入 "Account" → "API token"
3. 点击 "Create new API token"

**API 端点**

**创建定时任务**
```bash
curl -X POST \
  -H "Authorization: Token YOUR_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "command": "/home/yourusername/.virtualenvs/myenv/bin/python /home/yourusername/myapp/update_data.py",
    "hour": 2,
    "minute": 0,
    "day_of_week": "*",
    "day_of_month": "*",
    "month": "*"
  }' \
  "https://www.pythonanywhere.com/api/v0/user/YOUR_USERNAME/schedule/"
```

**列出所有定时任务**
```bash
curl -X GET \
  -H "Authorization: Token YOUR_API_TOKEN" \
  "https://www.pythonanywhere.com/api/v0/user/YOUR_USERNAME/schedule/"
```

**更新定时任务**
```bash
curl -X PUT \
  -H "Authorization: Token YOUR_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "hour": 3,
    "minute": 30
  }' \
  "https://www.pythonanywhere.com/api/v0/user/YOUR_USERNAME/schedule/TASK_ID/"
```

**删除定时任务**
```bash
curl -X DELETE \
  -H "Authorization: Token YOUR_API_TOKEN" \
  "https://www.pythonanywhere.com/api/v0/user/YOUR_USERNAME/schedule/TASK_ID/"
```

**立即运行任务（测试）**
```bash
curl -X POST \
  -H "Authorization: Token YOUR_API_TOKEN" \
  "https://www.pythonanywhere.com/api/v0/user/YOUR_USERNAME/schedule/TASK_ID/run/"
```

## 常用场景

### 场景1：每日数据更新

**任务脚本**：`/home/yourusername/myapp/update_data.py`
```python
#!/usr/bin/env python3
"""
每日数据更新脚本
"""
import sys
import os
import logging
from datetime import datetime

# 添加项目路径
sys.path.insert(0, '/home/yourusername/myapp')

# 配置日志
log_dir = '/home/yourusername/myapp/logs'
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, f'update_data_{datetime.now().strftime("%Y%m%d")}.log')

logging.basicConfig(
    filename=log_file,
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def main():
    logging.info('开始更新数据...')

    try:
        # 1. 更新 ETF 数据
        from etf_data_updater import update_etf_data
        update_etf_data()
        logging.info('✅ ETF 数据更新完成')

        # 2. 更新指数数据
        from index_data_updater import update_index_data
        update_index_data()
        logging.info('✅ 指数数据更新完成')

        # 3. 生成报告
        from report_generator import generate_daily_report
        generate_daily_report()
        logging.info('✅ 日报生成完成')

        logging.info('🎉 所有数据更新完成！')

    except Exception as e:
        logging.error(f'❌ 数据更新失败: {e}', exc_info=True)
        sys.exit(1)

if __name__ == '__main__':
    main()
```

**定时任务配置**：
```
Command: /home/yourusername/.virtualenvs/myenv/bin/python /home/yourusername/myapp/update_data.py >> /home/yourusername/myapp/logs/cron.log 2>&1
Hour: 2
Minute: 0
Day of week: *
```

### 场景2：定期生成报告

**任务脚本**：`/home/yourusername/myapp/generate_report.py`
```python
#!/usr/bin/env python3
"""
每周一生成周报
"""
import sys
import os
from datetime import datetime, timedelta

sys.path.insert(0, '/home/yourusername/myapp')

def generate_weekly_report():
    # 计算上周的日期范围
    today = datetime.now()
    last_monday = today - timedelta(days=today.weekday() + 7)
    last_sunday = last_monday + timedelta(days=6)

    # 生成报告...
    print(f"生成周报: {last_monday.date()} 至 {last_sunday.date()}")

if __name__ == '__main__':
    generate_weekly_report()
```

**定时任务配置**：
```
Command: /home/yourusername/.virtualenvs/myenv/bin/python /home/yourusername/myapp/generate_report.py
Hour: 8
Minute: 0
Day of week: 1  # 周一
```

### 场景3：数据库备份

**任务脚本**：`/home/yourusername/myapp/backup_db.py`
```python
#!/usr/bin/env python3
"""
数据库备份脚本
"""
import os
import subprocess
from datetime import datetime

def backup_database():
    # SQLite 备份
    db_path = '/home/yourusername/myapp/db.sqlite3'
    backup_dir = '/home/yourusername/backups'
    os.makedirs(backup_dir, exist_ok=True)

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_file = os.path.join(backup_dir, f'db_backup_{timestamp}.sqlite3')

    # 复制数据库文件
    subprocess.run(['cp', db_path, backup_file])

    # 删除超过 30 天的备份
    # ...

    print(f"✅ 备份完成: {backup_file}")

if __name__ == '__main__':
    backup_database()
```

**定时任务配置**：
```
Command: /home/yourusername/.virtualenvs/myenv/bin/python /home/yourusername/myapp/backup_db.py
Hour: 3
Minute: 0
Day of week: *
```

### 场景4：清理日志文件

**任务脚本**：`/home/yourusername/myapp/cleanup_logs.py`
```python
#!/usr/bin/env python3
"""
清理超过 30 天的日志文件
"""
import os
import time

log_dir = '/home/yourusername/myapp/logs'
now = time.time()

for filename in os.listdir(log_dir):
    file_path = os.path.join(log_dir, filename)
    if os.path.isfile(file_path):
        # 检查文件修改时间
        if os.stat(file_path).st_mtime < now - 30 * 86400:  # 30 天
            os.remove(file_path)
            print(f"删除旧日志: {filename}")
```

**定时任务配置**：
```
Command: /home/yourusername/.virtualenvs/myenv/bin/python /home/yourusername/myapp/cleanup_logs.py
Hour: 4
Minute: 0
Day of month: 1  # 每月1号
```

## 高频任务配置

如果需要每几分钟执行一次（PythonAnywhere 不支持高频任务，需要使用变通方法）：

**方法1：使用循环 + sleep**
```python
#!/usr/bin/env python3
"""
每 5 分钟执行一次
"""
import time
import subprocess

while True:
    # 执行任务
    subprocess.run(['/home/yourusername/.virtualenvs/myenv/bin/python', '/home/yourusername/myapp/task.py'])

    # 等待 5 分钟
    time.sleep(300)
```

**定时任务配置**（每小时重启一次，防止脚本挂掉）：
```
Command: /home/yourusername/.virtualenvs/myenv/bin/python /home/yourusername/myapp/loop_task.py
Hour: *
Minute: 0
```

**方法2：使用 GitHub Actions 定时触发**
```yaml
name: Run Task Every 5 Minutes

on:
  schedule:
    - cron: '*/5 * * * *'  # 每 5 分钟

jobs:
  run-task:
    runs-on: ubuntu-latest
    steps:
    - name: Call API
      run: |
        curl -X GET https://yourusername.pythonanywhere.com/api/run_task/
```

## 监控任务执行状态

### 查看任务日志

**方法1：通过 SSH 查看日志文件**
```bash
# 查看最新日志
tail -f /home/yourusername/myapp/logs/update_data.log

# 查看特定日期的日志
cat /home/yourusername/myapp/logs/update_data_20260514.log
```

**方法2：通过 PythonAnywhere API 查看任务执行历史**
```bash
curl -X GET \
  -H "Authorization: Token YOUR_API_TOKEN" \
  "https://www.pythonanywhere.com/api/v0/user/YOUR_USERNAME/schedule/TASK_ID/runs/"
```

### 任务执行失败通知

**在任务脚本中添加邮件通知**
```python
import smtplib
from email.mime.text import MIMEText

def send_notification(subject, body):
    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = 'your_email@example.com'
    msg['To'] = 'your_email@example.com'

    with smtplib.SMTP('smtp.gmail.com', 587) as server:
        server.starttls()
        server.login('your_email@example.com', 'your_password')
        server.send_message(msg)

def main():
    try:
        # 执行任务...
        pass
    except Exception as e:
        send_notification('❌ 任务执行失败', str(e))
        raise
```

### 使用第三方监控服务

**使用 Cronitor (cronitor.io)**
```python
import requests

def main():
    # 任务开始
    requests.get('https://cronitor.link/your-uuid/run')

    try:
        # 执行任务...
        pass

        # 任务成功
        requests.get('https://cronitor.link/your-uuid/complete')
    except Exception as e:
        # 任务失败
        requests.get(f'https://cronitor.link/your-uuid/fail?msg={str(e)}')
        raise
```

## 最佳实践

1. **使用绝对路径** - 定时任务的 PATH 环境变量可能不同，始终使用绝对路径
2. **重定向输出** - 将 stdout 和 stderr 重定向到日志文件：`>> /path/to/log.txt 2>&1`
3. **测试命令** - 在 Bash 控制台手动运行命令，确保能正常执行
4. **使用虚拟环境** - 使用虚拟环境中的 Python：`/home/yourusername/.virtualenvs/myenv/bin/python`
5. **记录日志** - 任务执行结果记录到文件，便于排查问题
6. **监控执行状态** - 使用 Cronitor 或 Healthchecks.io 监控任务是否正常执行
7. **设置超时** - 如果任务可能挂起，设置超时机制
8. **幂等性** - 确保任务可以重复执行而不产生副作用

## 常见问题

### 问题1：任务未执行

**排查步骤**：
1. 检查任务配置是否正确（Hour、Minute 等）
2. 手动运行命令，检查是否有错误
3. 检查日志文件
4. 查看 PythonAnywhere 的 "Tasks" 页面，看任务是否显示为 "Enabled"

### 问题2：任务执行失败

**排查步骤**：
1. 查看任务日志
2. 检查脚本是否有语法错误
3. 检查依赖是否已安装（在虚拟环境中）
4. 检查文件权限

### 问题3：任务执行时间过长

**解决方案**：
1. 优化脚本性能
2. 将任务拆分为多个小任务
3. 使用异步处理

## 触发词

当用户提到以下内容时，使用此 skill：
- "配置定时任务"
- "每天自动执行"
- "定期更新数据"
- "自动化任务"
- "PythonAnywhere 定时任务"

---

## Skill: pythonanywhere-scheduled-tasks.skill

---
name: pythonanywhere-scheduled-tasks
description: PythonAnywhere 定时任务配置。当用户需要在 PythonAnywhere 上配置定时任务（Scheduled Tasks）、自动化执行脚本、定期更新数据、或管理任务执行状态时使用。包含 Web 界面配置、API 调用、常用场景示例、日志监控。
---

# PythonAnywhere 定时任务配置

## 核心原则

**任务要幂等** - 定时任务可能重复执行，确保重复执行不会产生副作用

**记录日志** - 任务执行结果要记录到文件或数据库，便于排查问题

**监控执行状态** - 定期检查任务是否正常执行

## 何时使用此 Skill

- 用户说"配置定时任务"
- 用户说"每天自动更新数据"
- 用户说"定期执行脚本"
- 需要自动化任务（数据同步、报告生成、备份等）
- 需要监控任务执行状态

## 配置方法

### 方法1：通过 Web 界面配置（推荐新手）

**步骤**：
1. 登录 PythonAnywhere
2. 进入 "Tasks" 标签（左侧菜单）
3. 点击 "Add a new scheduled task"
4. 填写以下信息：
   - **Command**: 要执行的命令（绝对路径）
   - **Hour**: 执行小时（0-23）
   - **Minute**: 执行分钟（0-59）
   - **Day of week**: 星期几（* 表示每天）
   - **Day of month**: 日期（* 表示每天）
   - **Month**: 月份（* 表示每月）
5. 点击 "Create"

**示例配置（每天凌晨2点执行）**：
```
Command: /home/yourusername/.virtualenvs/myenv/bin/python /home/yourusername/myapp/update_data.py
Hour: 2
Minute: 0
Day of week: *
Day of month: *
Month: *
```

### 方法2：通过 API 配置（推荐高级用户）

**获取 API Token**
1. 登录 PythonAnywhere
2. 进入 "Account" → "API token"
3. 点击 "Create new API token"

**API 端点**

**创建定时任务**
```bash
curl -X POST \
  -H "Authorization: Token YOUR_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "command": "/home/yourusername/.virtualenvs/myenv/bin/python /home/yourusername/myapp/update_data.py",
    "hour": 2,
    "minute": 0,
    "day_of_week": "*",
    "day_of_month": "*",
    "month": "*"
  }' \
  "https://www.pythonanywhere.com/api/v0/user/YOUR_USERNAME/schedule/"
```

**列出所有定时任务**
```bash
curl -X GET \
  -H "Authorization: Token YOUR_API_TOKEN" \
  "https://www.pythonanywhere.com/api/v0/user/YOUR_USERNAME/schedule/"
```

**更新定时任务**
```bash
curl -X PUT \
  -H "Authorization: Token YOUR_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "hour": 3,
    "minute": 30
  }' \
  "https://www.pythonanywhere.com/api/v0/user/YOUR_USERNAME/schedule/TASK_ID/"
```

**删除定时任务**
```bash
curl -X DELETE \
  -H "Authorization: Token YOUR_API_TOKEN" \
  "https://www.pythonanywhere.com/api/v0/user/YOUR_USERNAME/schedule/TASK_ID/"
```

**立即运行任务（测试）**
```bash
curl -X POST \
  -H "Authorization: Token YOUR_API_TOKEN" \
  "https://www.pythonanywhere.com/api/v0/user/YOUR_USERNAME/schedule/TASK_ID/run/"
```

## 常用场景

### 场景1：每日数据更新

**任务脚本**：`/home/yourusername/myapp/update_data.py`
```python
#!/usr/bin/env python3
"""
每日数据更新脚本
"""
import sys
import os
import logging
from datetime import datetime

# 添加项目路径
sys.path.insert(0, '/home/yourusername/myapp')

# 配置日志
log_dir = '/home/yourusername/myapp/logs'
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, f'update_data_{datetime.now().strftime("%Y%m%d")}.log')

logging.basicConfig(
    filename=log_file,
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def main():
    logging.info('开始更新数据...')

    try:
        # 1. 更新 ETF 数据
        from etf_data_updater import update_etf_data
        update_etf_data()
        logging.info('✅ ETF 数据更新完成')

        # 2. 更新指数数据
        from index_data_updater import update_index_data
        update_index_data()
        logging.info('✅ 指数数据更新完成')

        # 3. 生成报告
        from report_generator import generate_daily_report
        generate_daily_report()
        logging.info('✅ 日报生成完成')

        logging.info('🎉 所有数据更新完成！')

    except Exception as e:
        logging.error(f'❌ 数据更新失败: {e}', exc_info=True)
        sys.exit(1)

if __name__ == '__main__':
    main()
```

**定时任务配置**：
```
Command: /home/yourusername/.virtualenvs/myenv/bin/python /home/yourusername/myapp/update_data.py >> /home/yourusername/myapp/logs/cron.log 2>&1
Hour: 2
Minute: 0
Day of week: *
```

### 场景2：定期生成报告

**任务脚本**：`/home/yourusername/myapp/generate_report.py`
```python
#!/usr/bin/env python3
"""
每周一生成周报
"""
import sys
import os
from datetime import datetime, timedelta

sys.path.insert(0, '/home/yourusername/myapp')

def generate_weekly_report():
    # 计算上周的日期范围
    today = datetime.now()
    last_monday = today - timedelta(days=today.weekday() + 7)
    last_sunday = last_monday + timedelta(days=6)

    # 生成报告...
    print(f"生成周报: {last_monday.date()} 至 {last_sunday.date()}")

if __name__ == '__main__':
    generate_weekly_report()
```

**定时任务配置**：
```
Command: /home/yourusername/.virtualenvs/myenv/bin/python /home/yourusername/myapp/generate_report.py
Hour: 8
Minute: 0
Day of week: 1  # 周一
```

### 场景3：数据库备份

**任务脚本**：`/home/yourusername/myapp/backup_db.py`
```python
#!/usr/bin/env python3
"""
数据库备份脚本
"""
import os
import subprocess
from datetime import datetime

def backup_database():
    # SQLite 备份
    db_path = '/home/yourusername/myapp/db.sqlite3'
    backup_dir = '/home/yourusername/backups'
    os.makedirs(backup_dir, exist_ok=True)

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_file = os.path.join(backup_dir, f'db_backup_{timestamp}.sqlite3')

    # 复制数据库文件
    subprocess.run(['cp', db_path, backup_file])

    # 删除超过 30 天的备份
    # ...

    print(f"✅ 备份完成: {backup_file}")

if __name__ == '__main__':
    backup_database()
```

**定时任务配置**：
```
Command: /home/yourusername/.virtualenvs/myenv/bin/python /home/yourusername/myapp/backup_db.py
Hour: 3
Minute: 0
Day of week: *
```

### 场景4：清理日志文件

**任务脚本**：`/home/yourusername/myapp/cleanup_logs.py`
```python
#!/usr/bin/env python3
"""
清理超过 30 天的日志文件
"""
import os
import time

log_dir = '/home/yourusername/myapp/logs'
now = time.time()

for filename in os.listdir(log_dir):
    file_path = os.path.join(log_dir, filename)
    if os.path.isfile(file_path):
        # 检查文件修改时间
        if os.stat(file_path).st_mtime < now - 30 * 86400:  # 30 天
            os.remove(file_path)
            print(f"删除旧日志: {filename}")
```

**定时任务配置**：
```
Command: /home/yourusername/.virtualenvs/myenv/bin/python /home/yourusername/myapp/cleanup_logs.py
Hour: 4
Minute: 0
Day of month: 1  # 每月1号
```

## 高频任务配置

如果需要每几分钟执行一次（PythonAnywhere 不支持高频任务，需要使用变通方法）：

**方法1：使用循环 + sleep**
```python
#!/usr/bin/env python3
"""
每 5 分钟执行一次
"""
import time
import subprocess

while True:
    # 执行任务
    subprocess.run(['/home/yourusername/.virtualenvs/myenv/bin/python', '/home/yourusername/myapp/task.py'])

    # 等待 5 分钟
    time.sleep(300)
```

**定时任务配置**（每小时重启一次，防止脚本挂掉）：
```
Command: /home/yourusername/.virtualenvs/myenv/bin/python /home/yourusername/myapp/loop_task.py
Hour: *
Minute: 0
```

**方法2：使用 GitHub Actions 定时触发**
```yaml
name: Run Task Every 5 Minutes

on:
  schedule:
    - cron: '*/5 * * * *'  # 每 5 分钟

jobs:
  run-task:
    runs-on: ubuntu-latest
    steps:
    - name: Call API
      run: |
        curl -X GET https://yourusername.pythonanywhere.com/api/run_task/
```

## 监控任务执行状态

### 查看任务日志

**方法1：通过 SSH 查看日志文件**
```bash
# 查看最新日志
tail -f /home/yourusername/myapp/logs/update_data.log

# 查看特定日期的日志
cat /home/yourusername/myapp/logs/update_data_20260514.log
```

**方法2：通过 PythonAnywhere API 查看任务执行历史**
```bash
curl -X GET \
  -H "Authorization: Token YOUR_API_TOKEN" \
  "https://www.pythonanywhere.com/api/v0/user/YOUR_USERNAME/schedule/TASK_ID/runs/"
```

### 任务执行失败通知

**在任务脚本中添加邮件通知**
```python
import smtplib
from email.mime.text import MIMEText

def send_notification(subject, body):
    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = 'your_email@example.com'
    msg['To'] = 'your_email@example.com'

    with smtplib.SMTP('smtp.gmail.com', 587) as server:
        server.starttls()
        server.login('your_email@example.com', 'your_password')
        server.send_message(msg)

def main():
    try:
        # 执行任务...
        pass
    except Exception as e:
        send_notification('❌ 任务执行失败', str(e))
        raise
```

### 使用第三方监控服务

**使用 Cronitor (cronitor.io)**
```python
import requests

def main():
    # 任务开始
    requests.get('https://cronitor.link/your-uuid/run')

    try:
        # 执行任务...
        pass

        # 任务成功
        requests.get('https://cronitor.link/your-uuid/complete')
    except Exception as e:
        # 任务失败
        requests.get(f'https://cronitor.link/your-uuid/fail?msg={str(e)}')
        raise
```

## 最佳实践

1. **使用绝对路径** - 定时任务的 PATH 环境变量可能不同，始终使用绝对路径
2. **重定向输出** - 将 stdout 和 stderr 重定向到日志文件：`>> /path/to/log.txt 2>&1`
3. **测试命令** - 在 Bash 控制台手动运行命令，确保能正常执行
4. **使用虚拟环境** - 使用虚拟环境中的 Python：`/home/yourusername/.virtualenvs/myenv/bin/python`
5. **记录日志** - 任务执行结果记录到文件，便于排查问题
6. **监控执行状态** - 使用 Cronitor 或 Healthchecks.io 监控任务是否正常执行
7. **设置超时** - 如果任务可能挂起，设置超时机制
8. **幂等性** - 确保任务可以重复执行而不产生副作用

## 常见问题

### 问题1：任务未执行

**排查步骤**：
1. 检查任务配置是否正确（Hour、Minute 等）
2. 手动运行命令，检查是否有错误
3. 检查日志文件
4. 查看 PythonAnywhere 的 "Tasks" 页面，看任务是否显示为 "Enabled"

### 问题2：任务执行失败

**排查步骤**：
1. 查看任务日志
2. 检查脚本是否有语法错误
3. 检查依赖是否已安装（在虚拟环境中）
4. 检查文件权限

### 问题3：任务执行时间过长

**解决方案**：
1. 优化脚本性能
2. 将任务拆分为多个小任务
3. 使用异步处理

## 触发词

当用户提到以下内容时，使用此 skill：
- "配置定时任务"
- "每天自动执行"
- "定期更新数据"
- "自动化任务"
- "PythonAnywhere 定时任务"


---

## 📝 附录6：今日对话记忆（2026-05-23）

### 对话主题：交付文档完善 + Skill 打包

#### 背景
用户（apangduo）要求将 ETF 对比工具 v1.0 的所有记忆、对话内容、自己总结的 Skill 打包成一个完整的 Markdown 交付文档。

---

### 对话流程

#### 1. 澄清"MD"含义
- **用户**: "MD 是 markdown"
- **AI**: 明白，"MD"就是 Markdown 格式。之前的 `ETF-对比工具-v1.0-完整交付文档.md` 已经是 Markdown 格式。

#### 2. 要求包含对话内容
- **用户**: "包括对话内容也存一下"
- **AI**: 尝试用 `conversation_search` 搜索历史对话记忆，准备追加到交付文档。
- **问题**: `conversation_search` 只能搜索历史记忆摘要，无法获取原始对话内容。
- **解决方案**: 将搜索到的 5 段对话记忆摘要追加到交付文档（附录4）。

#### 3. 要求打包自己总结的 Skill
- **用户**: "还有自己总结了几个 skill，能也打包进来吗"
- **AI**: 尝试区分"自己总结的 skill"和"从 WorkBuddy 技能库下载的 skill"。

#### 4. 区分 Skill 来源
- **用户**: "能区分自己总结的 skill 和从 workbuddy 技能库里下载的 skill 吗"
- **AI**: 编写 Python 脚本区分：
  - **Marketplace 下载的 skill**: 目录含 `_skillhub_meta.json`
  - **自己总结的 skill**: 目录不含 `_skillhub_meta.json`，或 `.skill` ZIP 文件
- **执行结果**: 找到 14 个自己总结的 skill（后修正为 13 个，`腾讯.skill` 实际是 Marketplace 下载的）。

#### 5. 执行打包
- **用户**: "要跑" → "全部打包"
- **AI**: 执行 Python 脚本，读取 13 个自己总结的 skill 内容，追加到交付文档（附录5）。
- **Bug 修复**: 初次脚本有 bug（`腾讯.skill` 被误判为 ZIP 文件），修复后重新生成。

#### 6. 检查交付文档完整性
- **用户**: "现在交付文档不缺什么了吧"
- **AI**: 检查交付文档，发现缺少今天（5/23）的对话内容。
- **用户**: "要的"（确认要追加今天对话）

---

### 关键决策

1. **交付文档结构**:
   - 正文：项目概述、工作日志、数据质量、文件变更、部署状态、对比页状态、下一步
   - 附录1：Git 提交历史
   - 附录2：团队协作记录
   - 附录3：关键技术决策记录
   - 附录4：对话记忆摘要（5段，5/14-5/22）
   - 附录5：自己总结的 Skill（13 个）
   - 附录6：今日对话记忆（5/23）✅ 已追加

2. **Skill 区分规则**:
   - Marketplace 下载：目录含 `_skillhub_meta.json`
   - 自己总结：目录不含 `_skillhub_meta.json` 或 `.skill` ZIP 文件

---

### 今日成果

- ✅ 交付文档完善（4172 行，125.1 KB）
- ✅ 13 个自己总结的 Skill 打包进附录5
- ✅ 今天对话记忆整理为附录6（已追加）

---

### 待办事项

- [x] 追加附录6（今日对话记忆）到交付文档
- [ ] 提交交付文档到 git
- [ ] 继续优化对比页（Plan A/B/C/D）或开新任务

