# ETF 每日数据更新 - 执行历史

## 2026-06-10

### 执行摘要
- **状态**: 成功（跨会话完成）
- **时间**: ~02:58 - 03:16（pipeline 前序会话，wequote 本会话）

### 各步骤状态

| 步骤 | 状态 | 说明 |
|------|------|------|
| 1. pipeline.py --push --no-wind | 成功 | 02:59-03:01，前序会话；sync 1500(+6) → enrich 0 → calc 166/34 → build 1500 → git push ✅ |
| 2. wequote_daily.py | 成功 | 03:02-03:16，14m8s，一次通过 |
| 3. git commit + push | 成功 | 884c7ca，2415 增/1965 删 |
| 4. PA 同步 curl | 失败(405) | Method Not Allowed，连续第 14 天 |

### 数据更新
- Pipeline: 1500 ETF，sync +6 新增，calc 166成功/34失败，build 1500，部署 2 次 commit
- WeStock: quote 更新 1500 字段，etf 更新 1200 字段，总计 2700 字段
- 字段覆盖率: custodian 1491/1500 (99.4%), fee_rate 899/1500 (59.9%), benchmark 1477/1500 (98.5%), premium_discount 145/1500 (9.7%)
- Git: 2415 行新增，1965 行删除

### 问题
- PA 同步返回 405 Method Not Allowed（连续第 14 天），需检查 API 配置
- logs/ 目录无当天日志文件（pipeline 可能未写入 logs/ 或写入路径不同）

---


### 执行摘要
- **状态**: 成功
- **时间**: 02:59 - 03:14

### 各步骤状态

| 步骤 | 状态 | 说明 |
|------|------|------|
| 1. pipeline.py --push --no-wind | 成功 | 02:59-03:01，~1m51s |
| 2. wequote_daily.py | 成功 | 02:59-03:13，14m24s，一次通过 |
| 3. git commit + push | 成功 | 8770886，2390 增/1940 删 |
| 4. PA 同步 curl | 失败(401) | 未授权，连续第 12 天 |

### 数据更新
- Pipeline: 1492 ETF，sync 0 新增，enrich 0 新增，calc 168成功/32失败，build 1492
- WeStock: quote 更新 1492 字段，etf 更新 1200 字段，总计 2692 字段
- 字段覆盖率: custodian 99.9%, fee_rate 60.3%, benchmark 98.8%, premium_discount 9.5%
- Git: 2390 行新增，1940 行删除

### 问题
- PA 同步返回 401 Unauthorized（连续第 12 天）

---

## 2026-06-07

### 执行摘要
- **状态**: 成功
- **时间**: 02:58 - 03:15

### 各步骤状态

| 步骤 | 状态 | 说明 |
|------|------|------|
| 1. pipeline.py --push --no-wind | 成功 | 02:58-03:00，2 次 deploy commit，284 版本 |
| 2. wequote_daily.py | 成功 | 03:00-03:15，14m43s，一次通过 |
| 3. git commit + push | 成功 | f206404，2390 增/1940 删 |
| 4. PA 同步 curl | 失败(401) | 未授权，连续第 10 天 |

### 数据更新
- Pipeline: 1492 只 ETF，284 个版本，git push 成功（2 次 deploy commit）
- WeStock: quote 更新 1492 个字段，etf 更新 1200 个字段，总计 2692 字段
- 字段覆盖率: custodian 99.9%, fee_rate 60.3%, benchmark 98.8%, premium_discount 9.5%
- Git: 2390 行新增，1940 行删除

### 问题
- PA 同步返回 401 Unauthorized（连续第 10 天）

---

## 2026-06-06

### 执行摘要
- **状态**: 成功（跨会话恢复）
- **时间**: 02:59 - 03:16（pipeline），03:?? wequote 完成（前序会话中断后恢复提交）

### 各步骤状态

| 步骤 | 状态 | 说明 |
|------|------|------|
| 1. pipeline.py --push --no-wind | 成功 | 2 次 deploy commit（aa67b96, c8f67fe），02:59-03:00 |
| 2. wequote_daily.py | 成功 | 前序会话执行，本会话仅提交已产出数据 |
| 3. git commit + push | 成功 | 6216ce7，2391 增/1941 删 |
| 4. PA 同步 curl | 失败(401) | 未授权，连续第 9 天 |

### 数据更新
- Pipeline: 2 次今日 commit（aa67b96, c8f67fe）
- WeStock: 2391 行新增，1941 行删除（volume/null 补全 + 新费率字段）
- Git push: main 已推送

### 问题
- PA 同步返回 401 Unauthorized（连续第 9 天）
- 前序会话 wequote_daily.py 中断，本会话仅恢复提交

## 2026-06-04

### 执行 #2（19:01 手动触发）

- **状态**: 成功
- **时间**: 19:01 - 19:28

**各步骤状态**:

| 步骤 | 状态 | 说明 |
|------|------|------|
| 1. pipeline.py --push --no-wind | 成功 | 19:01:29-19:03:42，2m12s |
| 2. wequote_daily.py | 成功 | 19:10:29-19:27:53，17m23s（需 `-u` 无缓冲） |
| 3. git commit + push | 成功 | fd7dc4d，2412 增/1965 删 |
| 4. PA 同步 curl | 失败(401) | 未授权，连续第 8 天 |

**数据更新**:
- Pipeline: 1490 ETF，版本清单 277 个版本，git push 成功（2 次 deploy commit）
- WeStock: quote 1490 字段 + etf 1192 字段 = 2682 字段
- Git commit: fd7dc4d → main

**踩坑记录**: wequote_daily.py 首次运行 stdout 缓冲无输出，kill 后加 `-u` 解决（已知问题）

### 执行 #1（03:00 自动调度）

- **状态**: 成功
- **时间**: 02:59 - 03:17

### 各步骤状态

| 步骤 | 状态 | 说明 |
|------|------|------|
| 1. pipeline.py --push --no-wind | 成功 | AKShare sync → enrich → calc → build → deploy 完成 |
| 2. wequote_daily.py | 成功 | 一次通过，quote + etf 两阶段均完成 |
| 3. git commit + push | 成功 | 提交 wequote 补充数据 |
| 4. PA 同步 curl | 失败(401) | 未授权，连续第 7 天 |

### 数据更新
- Pipeline: 1490 只 ETF（新增 1 只），git push 成功（2 次 deploy commit），268 个版本
- WeStock: quote 更新 1490 个字段，etf 更新 1192 个字段，总计 2682 字段
- Git: 2689 行新增，2242 行删除

### 踩坑记录
- 无。wequote_daily.py 使用 `-u` 无缓冲模式一次通过

### 问题
- PA 同步返回 401 Unauthorized（连续第 7 天），需检查 PythonAnywhere API 认证
- data/meta.json 等仍有修改未提交（pipeline 产生，非 wequote）

---

## 2026-06-02

### 执行摘要
- **状态**: 成功
- **时间**: 02:58 - 03:17

### 各步骤状态

| 步骤 | 状态 | 说明 |
|------|------|------|
| 1. pipeline.py --push --no-wind | 成功 | AKShare sync → enrich → calc → build → deploy 完成 |
| 2. wequote_daily.py | 成功 | 一次通过，无中断，quote + etf 两阶段均完成 |
| 3. git commit + push | 成功 | 提交 wequote 补充数据 |
| 4. PA 同步 curl | 失败(401) | 未授权，连续第 6 天 |

### 数据更新
- Pipeline: 1489 只 ETF（新增 3 只），git push 成功（2 次 deploy commit），262 个版本
- WeStock: quote 更新 1489 个字段，etf 更新约 1193 个字段，总计 2682 字段
- Git: 2682 行新增，2235 行删除

### 踩坑记录
- 无。wequote_daily.py 使用 `-u` 无缓冲模式一次通过，未出现 5/31 的中断问题

### 问题
- PA 同步返回 401 Unauthorized（连续第 6 天），需检查 PythonAnywhere API 认证
- data/meta.json 仍有修改未提交（pipeline 产生，非 wequote）

---

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
