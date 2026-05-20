# ETF 工具 MVP — 架构重设计方案

> 日期：2026-05-20  
> 设计人：Software Architect Agent  
> 目标：可扩展、本地优先、在线兜底、NeoData 集成

---

## 一、当前架构诊断

### 现有结构

```
app.py              ← Route 层（HTTP 接口）
etf_data.py         ← 数据层（硬编码 JSON 读取，无抽象）
templates/*.html    ← 前端（Jinja2）
modules/local_store.py ← 本地存储（pipeline 用，非运行时）
```

### 核心问题

| 问题 | 影响 |
|------|------|
| `etf_data.py` 直接读 JSON，无接口抽象 | 无法切换数据源，NeoData 接不进来 |
| 业务逻辑在 `app.py` 路由里 | 无法复用，无法测试 |
| 无在线查询能力 | 数据靠 pipeline 离线灌，时效性差 |
| `local_store.py` 是 pipeline 工具，非运行时库 | 运行时和 ETL 混在一起 |

---

## 二、目标架构：「本地优先 + 在线兜底」

### 核心原则

1. **本地数据作主库** — 快、稳、可离线
2. **在线 API 作补丁** — 鲜、全、兜底用
3. **写穿缓存** — 查在线 → 存本地 → 下次直接读本地
4. **NeoData 优先接入** — 你评估最有价值的数据源先集成

### 架构分层

```
┌──────────────────────────────────────────────────────────┐
│                    Route 层（Flask）                      │
│  /api/etfs  GET  — 列表查询+筛选+排序+分页              │
│  /etf/<code>  GET  — ETF 详情                          │
│  /compare     GET  — 对比页                             │
│  /api/etf/<code>/history  GET  — 历史走势              │
└────────────────────────┬─────────────────────────────────┘
                         │ 调用 Service
                         ▼
┌──────────────────────────────────────────────────────────┐
│                  Service 层（业务逻辑）                    │
│                                                          │
│  ETFQueryService     — 查询/筛选/排序 ETF 列表            │
│  ETFCompareService  — 多只 ETF 对比                     │
│  ETFDetailService   — 单只 ETF 详情+历史                │
│  ETFScreenService   — 条件筛选（进阶）                   │
│                                                          │
│  Service 只依赖 Repository 接口，不关心数据来源           │
└────────────────────────┬─────────────────────────────────┘
                         │ 调用 Repository
                         ▼
┌──────────────────────────────────────────────────────────┐
│              Repository 层（数据源抽象）                   │
│                                                          │
│  ETFRepository (ABC)  — 接口定义                        │
│    .list_etfs() → List[ETF]                            │
│    .get_etf(code) → ETF                                │
│    .search(keyword) → List[ETF]                        │
│    .save_etf(etf) → None  (写回本地)                   │
│                                                          │
│  实现：                                                   │
│  ├── LocalJSONRepo  — 读本地 etf_standard_data.json     │
│  │     （优先，快，~10ms）                               │
│  ├── NeoDataRepo    — 调 NeoData API                    │
│  │     （兜底，鲜，~500ms，有额度限制）                  │
│  └── WestockRepo   — 调 westock-data API               │
│        （备用，鲜，~300ms）                              │
│                                                          │
│  CompositeRepo — 组合以上 Repo，实现"本地优先"策略       │
└──────────────────────────────────────────────────────────┘
```

---

## 三、Repository 层设计

### 接口定义（`repositories/base.py`）

```python
from abc import ABC, abstractmethod
from typing import List, Optional
from dataclasses import dataclass

@dataclass
class ETF:
    code: str
    name: str
    issuer: Optional[str] = None
    scale: Optional[float] = None
    year_1_return: Optional[float] = None
    sharpe_ratio: Optional[float] = None
    # ... 其他字段

class ETFRepository(ABC):
    @abstractmethod
    def list_etfs(self, filters: dict) -> List[ETF]:
        """列出 ETF（支持筛选）"""
        ...

    @abstractmethod
    def get_etf(self, code: str) -> Optional[ETF]:
        """获取单只 ETF"""
        ...

    @abstractmethod
    def search(self, keyword: str) -> List[ETF]:
        """关键词搜索"""
        ...
```

### CompositeRepo（「本地优先」策略实现）

```python
class CompositeRepo(ETFRepository):
    """组合多个数据源，实现本地优先 + 在线兜底"""

    def __init__(self, local: ETFRepository, online: ETFRepository):
        self.local = local    # LocalJSONRepo（优先）
        self.online = online  # NeoDataRepo（兜底）

    def get_etf(self, code: str) -> Optional[ETF]:
        # 1. 先查本地
        etf = self.local.get_etf(code)
        if etf:
            return etf

        # 2. 本地没有，查在线
        etf = self.online.get_etf(code)
        if etf:
            # 3. 写回本地（下次直接命中）
            self.local.save_etf(etf)
            return etf

        # 4. 都找不到
        return None
```

---

## 四、NeoData 集成方案

### 调用方式

NeoData 是 MCP 工具（`mcp__neodata-financial-search__`），在 WorkBuddy 里可以直接调用。

但在 Flask 应用里，需要通过 **CLI 调用** 或 **HTTP API** 来访问 NeoData。

**方案 A：CLI 调用（推荐，简单）**

```python
# repositories/neodata_repo.py
import subprocess, json

class NeoDataRepo(ETFRepository):
    def search(self, keyword: str) -> List[ETF]:
        """用 NeoData 自然语言搜索"""
        cmd = [
            'node',  # 或 npx
            '/path/to/neodata-cli.js',
            'search',
            keyword
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        data = json.loads(result.stdout)
        return [self._to_etf(item) for item in data]

    def _to_etf(self, item: dict) -> ETF:
        return ETF(
            code=item['code'],
            name=item['name'],
            # ... 映射字段
        )
```

**方案 B：HTTP API（如果 NeoData 提供）**

```python
import requests

class NeoDataRepo(ETFRepository):
    def search(self, keyword: str):
        resp = requests.post(
            'https://api.neodata.com/v1/search',
            json={'query': keyword},
            headers={'Authorization': 'Bearer xxx'}
        )
        return resp.json()
```

### NeoData 接入优先级

| 功能 | NeoData 能力 | 接入优先级 |
|------|--------------|------------|
| ETF 列表查询 | `search "所有ETF"` | P0（先接这个） |
| 单只 ETF 详情 | `search "510300 详情"` | P0 |
| ETF 对比 | `search "510300 vs 510500"` | P1 |
| 历史走势 | `search "510300 历史净值"` | P1 |
| 条件筛选 | `search "规模>10亿 年化>5%"` | P2 |

---

## 五、迁移步骤（不中断现有功能）

### Phase 1：抽 Repository 层（不影响线上）

**目标**：把 `etf_data.py` 的逻辑抽到 `repositories/local_json_repo.py`，`etf_data.py` 变成兼容壳。

```
新建：repositories/
  __init__.py
  base.py              ← ETFRepository ABC
  local_json_repo.py   ← 现有 etf_data.py 逻辑移过来
  composite_repo.py    ← 本地优先组合器

修改：etf_data.py        ← 变成 repositories/local_json_repo.py 的兼容壳
```

**验证**：跑现有测试，确保行为完全一致。

### Phase 2：接 NeoData（新功能可用）

**目标**：实现 `repositories/neodata_repo.py`，在对比页/详情页用上。

```
新建：repositories/
  neodata_repo.py     ← NeoData 数据源

修改：app.py            ← /etf/<code> 路由改用 CompositeRepo
```

**验证**：访问 `/etf/510300`，确认能从 NeoData 获取最新数据。

### Phase 3：优化查询页（本地+在线混合）

**目标**：`/api/etfs` 支持 `source=local|online|auto` 参数，可选在线查询。

```
修改：app.py            ← /api/etfs 支持 source 参数
新建：services/
  query_service.py     ← ETF 查询业务逻辑
```

### Phase 4：完善本地数据库（后台持续填充）

**目标**：pipeline 持续从 NeoData/Westock 拉数据，填充本地 JSON。

```
修改：pipeline.py       ← enrich 步骤接入 NeoDataRepo
新建：tasks/
  sync_neodata.py     ← 定时从 NeoData 同步 ETF 数据
```

---

## 六、文件结构（目标）

```
etf-tool-mvp/
├── app.py                  ← Route 层（保持）
├── etf_data.py             ← 兼容壳（委托给 repositories/）
│
├── repositories/           ← 数据层（新）
│   ├── __init__.py
│   ├── base.py            ← ETFRepository ABC
│   ├── local_json_repo.py ← 本地 JSON（现有逻辑）
│   ├── neodata_repo.py    ← NeoData API
│   ├── westock_repo.py    ← Westock API（备用）
│   └── composite_repo.py  ← 本地优先组合器
│
├── services/               ← 业务层（新）
│   ├── __init__.py
│   ├── query_service.py    ← 查询/筛选
│   ├── compare_service.py  ← 对比
│   └── detail_service.py   ← 详情/历史
│
├── templates/              ← 前端（保持）
├── static/                ← 静态资源（保持）
├── modules/               ← pipeline 工具（保持）
└── data/                  ← 数据文件（保持）
```

---

## 七、决策记录（ADR）

### ADR-001：采用「本地优先 + 在线兜底」架构

**状态**：Accepted

**背景**：
- 现有系统完全依赖本地 JSON，数据时效性差
- 用户希望先实现查询/对比功能，再建数据库
- NeoData 等在线 API 有额度限制，不能全量依赖

**决策**：
采用 Composite Repo 模式：本地 JSON 优先，在线 API 兜底，查在线时自动写回本地。

**后果**：
- ✅ 功能可快速上线（用在线数据）
- ✅ 本地数据逐渐丰富（自动缓存）
- ✅ 在线 API 挂了不影响已缓存数据
- ❌ 首次查询在线数据会慢（~500ms）
- ❌ 需要处理在线 API 的限流/超时

---

## 八、下一步行动

1. [ ] **确认架构方向** — 你 review 这个设计方案，确认是否同意
2. [ ] **Phase 1 开始** — 抽 Repository 层，不影响线上功能
3. [ ] **NeoData 接入验证** — 先手动测一下 NeoData 查询 ETF 的效果
4. [ ] **更新任务列表** — 把架构迁移任务加入工作清单

---

*本文档是架构设计方案，具体实现前需要确认技术细节（特别是 NeoData 的调用方式）。*
