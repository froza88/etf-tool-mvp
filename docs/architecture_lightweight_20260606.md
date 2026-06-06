# ETF 工具 — 轻量架构方案对比

> 日期：2026-06-06  
> 目标：轻便、好维护、少出 Bug

---

## 当前架构（方案 A）问题回顾

```
pipeline.py (869行)
  → etf_standard_data.json (1.6MB)
  → _normalize_units() 单位转换
  → LocalJSONSource 读快照
  → WeStockSource 叠加 L2 (但 scale 已排除)
  → 服务端 L1+L2 merge → Jinja2 渲染
  → 客户端二次 fetch /api/compare?fresh=1
```

**痛点**：
1. 服务端 + 客户端两次数据合并，逻辑重复
2. Jinja2 模板里嵌 JS，数据和渲染混在一起
3. L1/L2 merge 容易出 Bug（scale 字段被覆盖）
4. 模板多（8个），改一处要改多处

---

## 方案 D：纯静态 + 客户端渲染（最轻量）

### 架构图

```
构建时（每日一次）：
  pipeline.py / 或直接读 etf_standard_data.json
    → 生成 static/api/etf_list.json          # 全量列表（首页用）
    → 生成 static/api/etf_510300.json       # 单只 ETF 详情（对比页用）
    → 生成 static/api/etf_510300_518880.json # 对比数据（预生成常用组合？）

运行时（PythonAnywhere 或 GitHub Pages）：
  index.html  ← 静态文件服务（或 CDN）
  compare.html ← 静态文件服务
  static/api/*.json ← 静态 JSON（超快，无后端）

实时行情（客户端直调）：
  对比页加载后 → fetch('https://api.westock.com/...') ← CORS proxy 或后端小接口
```

### 文件结构

```
etf-tool-mvp/
├── build.py              # 构建脚本（~100行，生成所有静态文件）
├── app.py               # 最小 Flask（仅本地开发 + CORS proxy）
├── static/
│   ├── index.html       # 首页（SPA，客户端渲染列表）
│   ├── compare.html     # 对比页（SPA，客户端 fetch JSON）
│   ├── app.js          # 共享 JS（路由、渲染、图表）
│   ├── api/            # 构建时生成（gitignore）
│   │   ├── etf_list.json
│   │   ├── etf_510300.json
│   │   └── ...
│   └── assets/
├── data/
│   └── etf_standard_data.json
└── requirements.txt     # 只有 flask（本地开发用）
```

### 优点
- ✅ **零后端逻辑**（构建时已完成所有数据处理）
- ✅ **超快**（静态 JSON，CDN 可缓存）
- ✅ **部署极简**（把 `static/` 扔到任何静态托管）
- ✅ **无 L1/L2 merge Bug**（数据构建时就合并好了）

### 缺点
- ❌ **实时行情需要额外处理**（客户端 CORS 或后端小 proxy）
- ❌ **构建时间较长**（1490 只 ETF，每只生成一个 JSON = 1490 个文件）
- ❌ **数据非实时**（每日构建，当日行情看不到）

### 适合场景
- 工具主要是"数据浏览/对比"，对实时性要求不高
- 想部署到 GitHub Pages / Cloudflare Pages（免费 + 快）

---

## 方案 E：超简 Flask + SPA（平衡方案）

### 架构图

```
运行时：
  浏览器 → GET / → Flask 返回 index.html（静态）
  浏览器 → GET /compare → Flask 返回 compare.html（静态）
  浏览器 → GET /api/etfs → Flask 读 etf_standard_data.json 返回 JSON
  浏览器 → GET /api/compare?codes=510300,518880 → Flask 合并 L1+L2 返回 JSON
  浏览器 → POST /api/realtime → Flask 调 WeStock API 返回实时数据

Flask 只做 3 件事：
  1.  serve_static（index.html, compare.html, app.js, chart.js...）
  2.  GET /api/etfs（列表）
  3.  GET/POST /api/compare（对比数据）
```

### 文件结构

```
etf-tool-mvp/
├── app.py               # 唯一后端文件（~200行）
├── static/
│   ├── index.html       # 首页 SPA（hash 路由 #/）
│   ├── compare.html      # 对比页 SPA
│   ├── app.js           # 前端逻辑（路由、API 调用、渲染）
│   └── chart.js         # Chart.js 封装
├── data/
│   └── etf_standard_data.json
└── requirements.txt     # flask  only
```

### `app.py` 核心代码（~200行）

```python
from flask import Flask, jsonify, send_from_directory
import json, os

app = Flask(__name__, static_folder='static')
DATA_FILE = 'data/etf_standard_data.json'

def load_etfs():
    with open(DATA_FILE) as f:
        data = json.load(f)
    return data if isinstance(data, list) else data['etfs']

@app.route('/')
def index():
    return send_from_directory('static', 'index.html')

@app.route('/compare')
def compare():
    return send_from_directory('static', 'compare.html')

@app.route('/api/etfs')
def api_etfs():
    etfs = load_etfs()
    # 只返回列表所需字段（code, name, scale, category）
    brief = [{'code': e['code'], 'name': e['name'], 'scale': e.get('scale'), 'category': e.get('category')} for e in etfs]
    return jsonify(brief)

@app.route('/api/compare')
def api_compare():
    codes = request.args.get('codes', '').split(',')
    etfs = load_etfs()
    result = [e for e in etfs if e['code'] in codes]
    # TODO: 合并 L2 实时数据（调 WeStock API）
    return jsonify(result)

@app.route('/api/realtime', methods=['POST'])
def api_realtime():
    codes = request.json['codes']
    # 调 WeStock API 获取实时行情
    # ...
    return jsonify(realtime_data)

if __name__ == '__main__':
    app.run(port=5000, debug=True)
```

### 前端 `app.js` 核心逻辑

```javascript
// 路由（hash 模式）
function router() {
    const hash = location.hash.slice(2);
    if (hash.startsWith('compare/')) {
        const codes = hash.split('/')[1].split(',');
        renderCompare(codes);
    } else {
        renderHome();
    }
}
window.addEventListener('hashchange', router);

// 对比页渲染
async function renderCompare(codes) {
    // 1. 加载基础数据（来自 /api/compare）
    const etfs = await fetch(`/api/compare?codes=${codes.join(',')}`).then(r => r.json());
    
    // 2. 加载实时数据（来自 /api/realtime）
    const realtime = await fetch('/api/realtime', {
        method: 'POST',
        body: JSON.stringify({codes})
    }).then(r => r.json());
    
    // 3. 合并数据并渲染
    etfs.forEach(etf => Object.assign(etf, realtime[etf.code]));
    renderCharts(etfs);
    renderTable(etfs);
}
```

### 优点
- ✅ **后端极简**（1 个文件，200 行，逻辑清晰）
- ✅ **前端 SPA**（无 Jinja2，无模板，纯客户端渲染）
- ✅ **实时数据简单**（客户端调 `/api/realtime` 即可）
- ✅ **易调试**（浏览器 DevTools 直接看 API 响应）
- ✅ **无 L1/L2 merge Bug**（合并逻辑只在 `/api/compare` 一处）

### 缺点
- ❌ **首次加载需要等 API**（但可加 loading 状态）
- ❌ **Flask 仍需运行**（不能纯静态部署）

### 适合场景
- 想保留实时行情功能
- 希望架构简单、易维护
- 愿意接受"首次加载稍慢"（可优化：首屏数据内联到 HTML）

---

## 方案对比表

| 维度 | 当前（方案 A） | 方案 D（纯静态） | 方案 E（超简 SPA） |
|------|----------------|-------------------|---------------------|
| **文件数** | 225 | ~15 | ~10 |
| **后端代码行数** | 2538 | 0（或 ~50 行 proxy） | ~200 |
| **模板文件** | 8 个 Jinja2 | 0 | 0（纯静态 HTML） |
| **实时行情** | 服务端 merge（易出 Bug） | 客户端直调（需 CORS） | 客户端调 `/api/realtime` |
| **部署** | PythonAnywhere（需运行 Flask） | 任意静态托管（GitHub Pages 等） | PythonAnywhere（Flask 很小） |
| **数据新鲜度** | 实时（L2 叠加） | 每日构建 | 实时（API 调用） |
| **首次加载速度** | 快（服务端渲染） | 最快（静态 HTML） | 中等（需等 API） |
| **调试难度** | 高（服务端 + 客户端） | 低（纯客户端） | 低（API 可浏览器直接看） |

---

## 推荐：方案 E（超简 SPA）

**理由**：
1. **足够简单**（1 个后端文件 + 2 个前端 HTML）
2. **保留实时功能**（不用放弃 WeStock 实时数据）
3. **易部署**（Flask 很小，PythonAnywhere 免费版够用）
4. **易调试**（API 直接在浏览器看）

**下一步**：要不要我写一个方案 E 的原型（最小可运行版本）？预计 1-2 小时能跑起来。

---

## 附录：方案 E 原型开发计划

### 第 1 步：创建 `app.py`（~200 行）
- `GET /` → `static/index.html`
- `GET /compare` → `static/compare.html`
- `GET /api/etfs` → 返回 ETF 列表 JSON
- `GET /api/compare?codes=xxx` → 返回对比数据 JSON
- `POST /api/realtime` → 调 WeStock 返回实时数据

### 第 2 步：创建 `static/index.html`（~100 行）
- 搜索框 + ETF 列表
- 点击"对比"跳转到 `#/compare/510300,518880`

### 第 3 步：创建 `static/compare.html`（~200 行）
- 加载动画
- 调用 `/api/compare` 和 `/api/realtime`
- 渲染图表（Chart.js）和表格

### 第 4 步：本地测试
```bash
cd /Users/apangduo/WorkBuddy/Claw/etf-tool-mvp
python3 app_simple.py  # 新文件，不覆盖现有 app.py
# 浏览器访问 http://127.0.0.1:5001/
```

---

**你觉得方案 E 怎么样？要不要我直接开始写原型？**
