# ETF 每日数据更新 - 执行历史

## 2026-05-31

### 执行摘要
- **状态**: 成功
- **时间**: 03:04 - 04:31

### 各步骤状态

| 步骤 | 状态 | 说明 |
|------|------|------|
| 1. pipeline.py --push --no-wind | 成功 | AKShare sync → calc → build → deploy 完成 |
| 2. wequote_daily.py | 成功（第3次） | 前两次因未知原因中断，第3次成功完成并保存 |
| 3. git commit + push | 成功 | 提交 wequote 补充数据 |
| 4. PA 同步 curl | 失败(401) | 未授权，连续第 5 天 |

### 数据更新
- Pipeline: 1486 只 ETF（新增 4 只），git push 成功（2 次 deploy commit），259 个版本
- 风险计算: 57 只需计算，成功 12，失败 45
- WeStock: quote 更新 1486 个字段，etf 更新 1192 个字段，总计 2678 字段
- Git: 2675 行新增，2228 行删除

### 踩坑记录
- wequote_daily.py 前两次运行均在 etf 阶段中途中断（首次到 58/149 批次，第二次未记录），无错误日志，疑似 westock-data CLI 超时或异常退出
- 第 3 次运行成功，历时约 16 分钟（04:15 - 04:31）
- 建议：为 wequote 增加异常捕获和断点续跑机制

### 问题
- PA 同步返回 401 Unauthorized（连续第 5 天），需检查 PythonAnywhere API 认证
- data/meta.json 仍有修改未提交（pipeline 产生，非 wequote）

---

## 2026-05-28

### 执行摘要
- **状态**: 成功
- **时间**: 03:05 - 03:20

### 各步骤状态

| 步骤 | 状态 | 说明 |
|------|------|------|
| 1. pipeline.py --push --no-wind | 成功 | AKShare sync → enrich → calc → build → deploy 完成 |
| 2. wequote_daily.py | 成功 | WeStock 补充行情完成，但 etf_standard_data.json 无实际变化 |
| 3. git commit + push | 跳过 | 无数据变化，无需提交 |
| 4. PA 同步 curl | 失败(401) | 未授权，连续 4 天 |

### 数据更新
- Pipeline: 1480 只 ETF，git push 成功（两次 deploy commit）
- WeStock: quote 查询 1480 个字段，etf 查询约 1184 个字段，但值与 pipeline 一致未产生 diff
- Git: pipeline 提交 2 次（data/meta.json 等仍有未提交修改）

### 问题
- PA 同步返回 401 Unauthorized（连续 4 天），需检查 PythonAnywhere API 认证
- 工作区剩余 data/meta.json 未提交（pipeline deploy 后又被更新）

---

## 2026-05-27

### 执行摘要
- **状态**: 成功
- **时间**: 03:02 - 03:30

### 各步骤状态

| 步骤 | 状态 | 说明 |
|------|------|------|
| 1. pipeline.py --push --no-wind | 成功 | AKShare sync → enrich → calc → build → deploy 完成 |
| 2. wequote_daily.py | 成功 | WeStock 补充行情完成（需 `-u` 无缓冲模式） |
| 3. git commit + push | 成功 | 提交 wequote 补充数据 |
| 4. PA 同步 curl | 失败(401) | 未授权，需检查 API token |

### 数据更新
- Pipeline: 1480 只 ETF（+3），git push 成功，242 个版本
- WeStock: quote 更新 1480 个字段，etf 更新 1184 个字段，总计 2664 字段
- Git: 2673 行新增，2229 行删除

### 踩坑记录
- wequote_daily.py 首次运行因 Python stdout 缓冲被判定超时 kill，改用 `python3 -u` 无缓冲模式解决
- 脚本实际运行约 15 分钟（148 批次 quote + 148 批次 etf，每批 10 个，含 1.5s 间隔）

### 问题
- PA 同步返回 401 Unauthorized（连续 3 天），需检查 PythonAnywhere API 认证

---

## 2026-05-26

### 执行摘要
- **状态**: 成功
- **时间**: 03:01 - 03:24

### 各步骤状态

| 步骤 | 状态 | 说明 |
|------|------|------|
| 1. pipeline.py --push --no-wind | 成功 | AKShare sync → enrich → calc → build → deploy 完成 |
| 2. wequote_daily.py | 成功 | WeStock 补充行情完成 |
| 3. git commit + push | 成功 | 提交 wequote 补充数据 |
| 4. PA 同步 curl | 失败(401) | 未授权，需检查 API token |

### 数据更新
- Pipeline: 1477 只 ETF，git push 成功
- WeStock: quote 更新 1477 个字段，etf 更新 1184 个字段
- Git: 2652 行新增，2208 行删除

### 问题
- PA 同步返回 401 Unauthorized，需检查 PythonAnywhere API 认证

---

## 2026-05-25

### 执行摘要
- **状态**: 成功（含修复）
- **时间**: 03:00 - 03:27

### 各步骤状态

| 步骤 | 状态 | 说明 |
|------|------|------|
| 1. pipeline.py --push --no-wind | 成功 | AKShare sync → enrich → calc → build → deploy 完成 |
| 2. wequote_daily.py | 成功 | WeStock 补充行情完成 |
| 3. git commit + push | 成功 | 提交 wequote 补充数据 |
| 4. PA 同步 curl | 失败(401) | 未授权，需检查 API token |

### 数据更新
- Pipeline: 1475 只 ETF，git push 成功
- WeStock: quote 更新 1475 个字段，etf 更新 592 个字段
- Git: 2066 行新增，1844 行删除

### 修复记录
- 修复 `modules/local_store.py` 中 `create_snapshot` 对 dict 格式数据的兼容问题
- 原代码假设 `etf_standard_data.json` 是列表，实际为 `{"etfs": [...], "updated": "..."}`

### 问题
- PA 同步返回 401 Unauthorized，需检查 PythonAnywhere API 认证
