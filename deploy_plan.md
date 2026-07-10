# ETF 对比网站 · 三版本同步部署计划（deploy_plan）

> 制定时间：2026-07-10 14:43
> 目标：将 v1 / v2 / v3 三个版本以**子目录隔离**方式同步到 GitHub 与 EdgeOne，**不触碰 `main` 分支**，**不同步 PA**（PA 保留为 API 后端）。

---

## 1. 隔离策略

按路径隔离，每个版本放入独立子目录并自带 `etf_data_embed.js`，避免数据串版：

```
/            → 保持现状（v3 线上版，不破坏现有 URL）
/v1/         → v1 原始 2026-06-22（index.html + etf_data_embed.js）
/v2/         → v2 封版 2026-07-06（index.html + etf_data_embed.js）
/v3/         → v3 升级 2026-07-10（index.html + etf_data_embed.js + xuanzongti.otf）
```

各版本 HTML 均用相对路径引用 `etf_data_embed.js`，子目录内自洽，互不干扰。

---

## 2. 版本 → 数据文件配对（已校验 MD5 / 字节）

| 版本 | index.html 来源 | etf_data_embed.js 来源 | 大小 |
|------|----------------|----------------------|------|
| v1 | `prototypes-v1-backup/v10_full_1470/deploy/index.html.bak`（Jun 22, 33.6KB） | `main:prototypes/v10_full_1470/deploy/etf_data_embed.js`（217KB，v1 时代数据） | 21 字段 |
| v2 | `db8aa73:index.html`（34.7KB，与 main 部署版同源） | `db8aa73:etf_data_embed.js`（771KB） | 21 字段 |
| v3 | `8b2ebad(HEAD):index.html`（55.3KB） | 工作区根 `etf_data_embed.js`（2.7MB） | 51 字段 |

> 注：`db8aa73` 仅改了数据文件，`index.html` 与 `main` 的 v10_full_1470/deploy 版 MD5 一致（e54204f4），属同源 UI。

---

## 3. 目标执行步骤

### 3.1 GitHub（不碰 main）
- 在 `edgeone-deploy` 当前内容（根目录 v3）基础上，新增 `v1/ v2/ v3/` 子目录。
- 提交后创建**新分支 `site-versions`**（从 edgeone-deploy 派生），推送 `origin/site-versions`。
- `main` 分支**完全不动**。
- （可选后续）在 GitHub 仓库 Settings → Pages 将源分支切换为 `site-versions`、目录 `/`（root），即可通过 GitHub Pages 访问 `/v1 /v2 /v3`。

### 3.2 EdgeOne
- EdgeOne 部署 `edgeone-deploy` 分支根目录（`edgeone.json` outputDirectory="."）。
- 当前根目录已是 v3；新增 `v1/ v2/ v3/` 子目录后，推送 `origin/edgeone-deploy` 触发自动构建。
- 路径隔离：`your-edgeone-domain/v1/`、`/v2/`、`/v3/` 分别对应三版本，根路径仍为 v3 线上版。

### 3.3 PA（本次不同步）
- PA 为 Flask API 后端（`app.py` 路由 `/`、`/api/*`、`/compare` 等），不托管静态对比站。
- 保留现状，避免改动生产代码。

---

## 4. 安全性与回滚

- **非破坏性**：仅新增子目录 + 新建 `site-versions` 分支，`main` 与现有文件零改动。
- **回滚**：若 EdgeOne 构建异常，删除 `v1/ v2/ v3/` 子目录并提交即可恢复纯 v3 根部署；`site-versions` 分支可直接删除。
- **数据隔离**：各子目录 `etf_data_embed.js` 独立，版本间不共享，杜绝串版。

---

## 5. 验收清单

- [ ] `v1/index.html` + `v1/etf_data_embed.js` 存在且可独立加载
- [ ] `v2/index.html` + `v2/etf_data_embed.js` 存在且可独立加载
- [ ] `v3/index.html` + `v3/etf_data_embed.js` + `v3/xuanzongti.otf` 存在且可独立加载
- [ ] `git push origin edgeone-deploy` 成功，EdgeOne 自动构建通过
- [ ] `git push origin site-versions` 成功（新分支）
- [ ] `main` 分支未被任何改动（`git diff main..edgeone-deploy` 仅含新增子目录）
- [ ] 根目录 v3 线上访问不受影响

---

## 6. 后续（修改工作）

三版本安全归档后，再基于报告《etf_site_code_analysis_2026-07-10.md》的推荐架构（v3 信息架构 + v1 加载模型）生成融合版，届时仅在 `site-versions` 或新建 `v4-fusion` 分支上操作，不影响已归档的三版本。
