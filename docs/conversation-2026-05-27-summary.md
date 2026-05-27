# ETF Tool MVP — 对话总结与技术经验文档

**日期**：2026-05-27  
**对话范围**：compare_v3.html 多轮迭代，涵盖 AI 对话框、L1/L2 缓存污染、导出按钮恢复、Jinja2 模板错误修复

---

## 一、对话总览

本次对话围绕 ETF 对比工具（`compare_v3.html`）的多轮迭代展开，主要工作包括：

1. **AI 聊天对话框功能开发**（前期）
2. **L1/L2 数据缓存污染问题排查与修复**（核心问题）
3. **导出按钮功能恢复**（从旧版本恢复）
4. **Jinja2 模板错误 `'colors' is undefined` 修复**
5. **防御性 JS 修复**（`undefined` 字符串显示问题）

---

## 二、问题清单与解决方案

### 问题 1：L1 请求被 L2 缓存污染（核心 Bug）

**现象**：
- 表格"基本信息"全部显示 "-"（`tracking_index`、`issuer_full`、`establishment_date` 等字段缺失）
- 环形图标签显示 `510300 - undefined -`

**根因分析**：
- `app.py` 中 `/api/compare` 路由的 L1 分支（`source='local'`）也会检查 `_l2_memory_cache`
- L2（WeStock API）返回的数据字段少（只有 `scale`、`close`、`change_pct` 等价格相关字段）
- L1 请求命中 L2 缓存后，返回的是字段不全的 WeStock 数据
- 前端 `e.name` 为 `undefined`，字符串拼接时变成 `"undefined"`

**修复方案**：
```python
# app.py 第 278-293 行
# 修复前：L1 也查 _l2_memory_cache
else:
    cache_key = ','.join(sorted(codes))
    cache_entry = _l2_memory_cache.get(cache_key)
    if cache_entry and (datetime.now().timestamp() - cache_entry["cached_at"]) < _L2_CACHE_TTL:
        etfs = cache_entry["etfs"]  # ← 返回的是 L2 数据（字段不全）
        data_source = "memory_cache"
    else:
        service = get_default_service()
        local_source = service.local_source
        etfs = local_source.get_etfs_by_codes(codes)
        data_source = "local_db"

# 修复后：L1 直接查本地数据库，不走 L2 缓存
else:
    # L1: 直接使用本地数据库（不走 L2 缓存，避免字段不全）
    service = get_default_service()
    local_source = service.local_source
    etfs = local_source.get_etfs_by_codes(codes)
    data_source = "local_db"
```

**验证方式**：
```bash
cd ~/WorkBuddy/Claw/etf-tool-mvp && python3 app.py
# 浏览器访问 http://localhost:5000/compare/v3?codes=510300,510500,159915
```

---

### 问题 2：环形图标签显示 `undefined`

**现象**：三个 ETF 环形图下方标签显示 `510300 - undefined -`

**根因**：同上（L2 数据没有 `name` 字段），JS 字符串拼接时 `e.name` 为 `undefined`

**修复方案**：
```javascript
// templates/compare_v3.html 第 466 行
// 修复前
'<div class="hero-ring-label">...</div>' + e.code + ' - ' + e.name + ' - ' + (e.issuer_short || '') + '</div>'

// 修复后（防御性处理）
'<div class="hero-ring-label">...</div>' + e.code + ' - ' + (e.name || '') + ' - ' + (e.issuer_short || '') + '</div>'
```

**经验教训**：
- JavaScript 中 `undefined + '字符串'` 会变成 `"undefined字符串"`
- 所有模板渲染处的变量引用都需要防御性检查（`|| ''` 或 `if (v)` 判断）

---

### 问题 3：导出按钮功能丢失

**现象**：右上角导出按钮（截图/打印功能）被删除，替换为单按钮

**根因**：某次修改中误删了导出下拉菜单的 HTML/CSS/JS 代码

**修复方案**：从 `commit 1226b99` 之前的版本恢复导出功能
- CSS：恢复 `.btn-export`、`.export-dropdown`、`.export-menu`、`.export-menu-item`
- HTML：在 header 右侧加入导出下拉菜单（4-5 个选项）
- JS：新增 `toggleExportMenu()`、`screenCaptureVisible()`、`openPrintPage()` 函数

**当前状态**：
- 导出下拉菜单已恢复（可见区域截图、全页面截图、打印版页面、直接打印）
- 但 `openPrintPage()` 函数可能仍有问题（需测试）

---

### 问题 4：Jinja2 模板错误 `'colors' is undefined`

**现象**：访问 `/compare/v3/print` 时报 `UndefinedError: 'colors' is undefined`

**根因**：`compare_v3_print` 路由渲染 `compare_print.html` 时未传递 `colors` 变量

**修复方案**：
```python
# app.py 第 306-318 行
@ app.route('/compare/v3/print')
def compare_v3_print():
    """ETF对比页 - 打印友好版"""
    codes = request.args.get('codes', '').split(',')
    codes = [c for c in codes if c]
    etfs = []
    for code in codes:
        etf = etf_data.get_etf_by_code(code)
        if etf:
            etfs.append(etf)
    from datetime import datetime
    colors = ['#00d4ff', '#f59e0b', '#f97316', '#7c3aed', '#ec4899', '#06b6d4']
    return render_template('compare_print.html', etfs=etfs, now=datetime.now().strftime('%Y-%m-%d %H:%M'), colors=colors)
```

---

## 三、经验与教训

### 1. L1/L2 数据架构设计原则

**问题**：L2 数据是 L1 数据的"子集"（字段更少），混用会导致字段缺失

**教训**：
- L1（本地数据库）应该只从本地文件读取，不走任何 L2 缓存
- L2（WeStock API）数据应该只用于实时价格更新，不应该污染 L1 缓存
- 如果需要在 L1 请求中返回 L2 数据，必须做字段合并（`{**l1_data, **l2_data}`），而不是完全替换

**推荐架构**：
```
L1 请求（source='local'）
  └─ 只查本地数据库（etf_standard_data.json）
  └─ 返回完整字段（name, issuer_full, benchmark, ...）

L2 请求（source='westock'）
  └─ 调用 WeStock API
  └─ 返回字段少（只有价格/规模等）
  └─ 可选：合并 L1 数据补全字段
```

---

### 2. JavaScript 模板渲染的防御性编程

**问题**：`e.name` 为 `undefined` 时，字符串拼接产生 `"undefined"` 文本

**教训**：
- 所有动态数据渲染前必须检查 `undefined`/`null`
- 使用 `|| ''` 提供默认值，或使用 `if (v)` 条件判断
- 特别是从 API 获取的数据，字段可能缺失

**检查清单**：
```javascript
// ✅ 正确：防御性检查
(e.name || '')
if (e.name) { ... }
v === undefined || v === null

// ❌ 错误：直接拼接
e.name + ''
```

---

### 3. Flask/Jinja2 模板变量传递

**问题**：路由渲染模板时忘记传递某些变量，导致 `UndefinedError`

**教训**：
- 路由函数中使用的所有模板变量都必须在 `render_template()` 中显式传递
- 使用 `jinja2.exceptions.UndefinedError` 错误信息快速定位缺失变量
- 建议在路由函数顶部声明所有模板变量，避免遗漏

**检查清单**：
```python
# 路由函数顶部
colors = [...]  # 声明所有模板变量
now = datetime.now().strftime(...)
return render_template('template.html', 
    etfs=etfs, 
    now=now, 
    colors=colors  # ← 不要遗漏
)
```

---

### 4. Git 版本管理与回退策略

**问题**：多次修改后出现问题，难以定位是哪个改动引起的

**教训**：
- 每次修改后提交（commit），提交信息清晰描述改动
- 使用 `git log --oneline` 快速查看历史
- 使用 `git diff HEAD~3 --stat` 查看最近几次改动的统计
- 使用 `git show <commit>:<file>` 查看某个提交时的文件内容（用于恢复旧版本）

**常用命令**：
```bash
# 查看最近 10 次提交
git log --oneline -10

# 查看某个文件的历史提交
git log --oneline -- <file>

# 查看某个提交时的文件内容
git show <commit>:<file>

# 恢复某个文件到某个提交
git checkout <commit> -- <file>
```

---

### 5. 用户反馈处理方式

**问题**：用户反馈"现在能显示的数据好像比调用 L1 时候少"，但问题描述不够具体

**教训**：
- 用户反馈问题时，要求提供截图或具体现象描述
- 使用 `grep`/`find` 等工具快速定位问题代码
- 先复现问题（本地运行 + 浏览器测试），再修复
- 修复后验证（检查相关功能是否受影响）

**推荐流程**：
1. 用户反馈问题 → 要求截图/录屏
2. 分析截图 → 定位问题现象（哪个字段/哪个区域）
3. 检查代码 → 使用 `grep` 找到相关代码段
4. 本地复现 → 运行服务，浏览器访问，打开开发者工具
5. 修复问题 → 修改代码，再次测试
6. 验证影响 → 检查其他功能是否正常

---

## 四、技术技巧与 Skill

### 技巧 1：快速定位前端问题（浏览器开发者工具）

**场景**：页面显示异常，需要快速定位是哪个 JS 函数或 DOM 元素的问题

**步骤**：
1. 浏览器打开页面，按 `F12` 打开开发者工具
2. 查看 `Console` 标签页，看是否有 JS 错误
3. 查看 `Network` 标签页，看 API 请求是否正常返回
4. 使用 `Elements` 标签页，检查 DOM 结构和样式
5. 在 `Sources` 标签页中设置断点，逐步调试 JS 代码

**关键命令**：
```javascript
// 在 Console 中快速检查数据
JSON.stringify(etfs, null, 2)

// 检查某个 DOM 元素
document.querySelector('.hero-ring-label')

// 手动调用渲染函数
renderHero()
```

---

### 技巧 2：Python 后端调试（Flask + print 日志）

**场景**：API 返回数据不正确，需要查看后端处理逻辑

**步骤**：
1. 在 `app.py` 的关键位置加入 `print()` 语句（输出到 stderr）
2. 运行 `python3 app.py`，观察终端输出
3. 使用 `curl` 测试 API 接口

**示例代码**：
```python
@app.route('/api/compare')
def api_compare():
    # ...
    print(f"[API] L1 请求，codes={codes}", file=sys.stderr)
    print(f"[API] 返回数据字段: {list(etfs[0].keys()) if etfs else '空'}", file=sys.stderr)
    return jsonify({...})
```

**测试命令**：
```bash
# 测试 API 接口
curl "http://localhost:5000/api/compare?codes=510300,510500"

# 格式化 JSON 输出
curl "http://localhost:5000/api/compare?codes=510300,510500" | python3 -m json.tool
```

---

### 技巧 3：Git 历史版本对比与恢复

**场景**：某次改动后出现问题，需要找回旧版本的正确代码

**步骤**：
1. 使用 `git log --oneline -- <file>` 查看文件历史
2. 使用 `git show <commit>:<file>` 查看旧版本内容
3. 使用 `git checkout <commit> -- <file>` 恢复旧版本

**示例**：
```bash
# 查看 compare_v3.html 的历史提交
git log --oneline -- templates/compare_v3.html

# 查看某个提交时的 compare_v3.html
git show 1226b99:templates/compare_v3.html | grep -A 10 "export-dropdown"

# 恢复某个提交时的文件
git checkout 1226b99 -- templates/compare_v3.html
```

---

### 技巧 4：ETF 数据结构快速检查

**场景**：需要确认 `etf_standard_data.json` 中某个 ETF 的字段是否完整

**步骤**：
1. 使用 `python3 -c` 快速加载 JSON 并检查字段
2. 使用 `jq` 工具快速查询 JSON 数据

**示例**：
```bash
# 快速检查某个 ETF 的字段
python3 -c "
import json
with open('etf_standard_data.json') as f:
    data = json.load(f)
etfs = data if isinstance(data, list) else data.get('etfs', [])
for e in etfs:
    if e.get('code') == '510300':
        print(json.dumps(e, ensure_ascii=False, indent=2))
        break
"

# 使用 jq 快速查询
jq '.[] | select(.code=="510300") | {code, name, benchmark, issuer_full}' etf_standard_data.json
```

---

### Skill 1：L1/L2 数据架构设计规范

**适用场景**：设计多数据源架构，避免数据污染

**核心原则**：
1. L1（本地数据）只从本地文件读取，不走任何远程缓存
2. L2（实时 API）数据只用于补充 L1 数据的实时字段（价格/规模）
3. L2 数据返回后，应该合并到 L1 数据上（`{**l1, **l2}`），而不是替换 L1 数据
4. 内存缓存应该按数据源类型分开（`_l1_cache` vs `_l2_cache`）

**代码示例**：
```python
# ✅ 正确：L1 和 L2 缓存分开
_l1_cache = {}  # 本地数据缓存
_l2_cache = {}  # WeStock API 数据缓存

@app.route('/api/compare')
def api_compare():
    if source == 'local':
        # L1: 只查本地，不走 L2 缓存
        etfs = local_source.get_etfs_by_codes(codes)
    else:
        # L2: 查 WeStock API，写入 L2 缓存
        etfs = westock_source.get_etfs_by_codes(codes)
        _l2_cache[cache_key] = etfs
```

---

### Skill 2：JavaScript 防御性编程模板

**适用场景**：前端模板渲染，防止 `undefined`/`null` 导致页面异常

**核心模式**：
```javascript
// 模式 1：默认值
function safeStr(v) {
    if (v === undefined || v === null || v === '') return '-';
    return String(v);
}

// 模式 2：条件渲染
if (e.name) {
    html += '<span>' + e.name + '</span>';
}

// 模式 3：模板字符串防御
var nameStr = (e.name || '') + ' - ' + (e.issuer_short || '');

// 模式 4：循环中的防御
etfs.forEach(function(e) {
    if (!e || !e.code) return;  // 跳过无效数据
    // ...
});
```

---

### Skill 3：Flask/Jinja2 模板变量检查清单

**适用场景**：Flask 路由渲染模板前，检查所有变量是否已传递

**检查清单**：
```python
# 在 render_template() 调用前，检查所有变量
def render_my_template():
    # 1. 声明所有模板变量
    etfs = [...]
    now = datetime.now().strftime(...)
    colors = [...]
    data_source = '...'
    
    # 2. 检查是否有 None 值（可能导致模板错误）
    if etfs is None:
        etfs = []
    
    # 3. 传递所有变量
    return render_template('template.html',
        etfs=etfs,
        now=now,
        colors=colors,
        data_source=data_source
    )
```

**常见错误**：
- 忘记传递某个变量 → `UndefinedError: 'xxx' is undefined`
- 传递了 `None` 值 → 模板中 `if xxx` 判断失败
- 传递了错误类型的值（如传递列表而不是字典）→ 模板中 `xxx.key` 报错

---

## 五、ETF 数据结构与更新机制

### 5.1 数据文件结构

**主要数据文件**：
- `etf_standard_data.json` — 标准 ETF 数据（L1 本地缓存）
- `etf_merged_all_data.json` — 合并后的全量数据（含 Wind 补充字段）
- `etf_complete_all.json` — 完整版数据（字段最全）
- `data/meta.json` — 数据更新元数据（最后更新时间、统计信息）

**数据格式**：
```json
// etf_standard_data.json 格式（两种）
// 格式 1：纯数组
[
  {
    "code": "510300",
    "name": "华泰柏瑞沪深300ETF",
    "issuer_full": "华泰柏瑞基金管理有限公司",
    "issuer_short": "华泰柏瑞",
    "benchmark": "沪深300指数",
    "scale": 15600000000,
    "close": 4.521,
    "change_rate": 0.0125,
    "year_1_return": 0.0825,
    "year_3_return": 0.0540,
    "fee_rate": 0.0025,
    "tracking_error": 0.015,
    "sharpe_ratio": 0.85,
    "max_drawdown": -0.185,
    "top_holdings": [...],
    ...
  }
]

// 格式 2：对象（含元数据）
{
  "etfs": [...],
  "meta": {...}
}
```

---

### 5.2 数据更新流程

**自动更新**（每天凌晨 3 点）：
1. `cron` 任务触发 `update_data.py` 脚本
2. 脚本调用 AKShare API 获取最新行情数据
3. 脚本调用 WeStock API 获取实时价格
4. 数据写入 `etf_standard_data.json`
5. 更新 `data/meta.json` 中的 `last_update` 时间戳

**手动更新**：
```bash
# 运行数据更新脚本
cd ~/WorkBuddy/Claw/etf-tool-mvp
python3 update_data.py

# 检查数据更新时间
python3 -c "
import json, os
mtime = os.path.getmtime('etf_standard_data.json')
print('数据更新时间:', __import__('datetime').datetime.fromtimestamp(mtime))
"
```

---

### 5.3 数据字段说明

**核心字段**（L1 本地数据）：
| 字段名 | 类型 | 说明 | 示例 |
|--------|------|------|------|
| `code` | string | ETF 代码 | `"510300"` |
| `name` | string | ETF 名称 | `"华泰柏瑞沪深300ETF"` |
| `issuer_full` | string | 发行方全称 | `"华泰柏瑞基金管理有限公司"` |
| `issuer_short` | string | 发行方简称 | `"华泰柏瑞"` |
| `benchmark` | string | 跟踪指数 | `"沪深300指数"` |
| `scale` | number | 规模（元） | `15600000000` |
| `close` | number | 收盘价 | `4.521` |
| `change_rate` | number | 涨跌幅 | `0.0125` (1.25%) |
| `year_1_return` | number | 近1年收益率 | `0.0825` (8.25%) |
| `year_3_return` | number | 近3年收益率 | `0.0540` (5.4%) |
| `fee_rate` | number | 费率 | `0.0025` (0.25%) |
| `tracking_error` | number | 跟踪误差 | `0.015` |
| `sharpe_ratio` | number | 夏普比率 | `0.85` |
| `max_drawdown` | number | 最大回撤 | `-0.185` (-18.5%) |
| `top_holdings` | array | 前五大持仓 | `[{name, weight}, ...]` |

**L2 补充字段**（WeStock API，字段少）：
| 字段名 | 类型 | 说明 |
|--------|------|------|
| `scale` | number | 规模（可能单位不同） |
| `close` | number | 收盘价 |
| `change_rate` | number | 涨跌幅 |
| `volume` | number | 成交量 |
| `net_inflow_5d` | number | 近5日净流入 |

---

### 5.4 数据质量检查

**检查脚本**：`detailed_data_completeness.py`

**运行方式**：
```bash
cd ~/WorkBuddy/Claw/etf-tool-mvp
python3 detailed_data_completeness.py
```

**输出报告**：`detailed_data_completeness_report.md`

**关键指标**：
- `benchmark` 完整度：97.8%（目标 100%）
- `tracking_error` 完整度：85%（目标 95%）
- `top_holdings` 完整度：90%（目标 95%）

---

## 六、当前项目状态（2026-05-27）

### 6.1 功能状态

| 功能 | 状态 | 说明 |
|------|------|------|
| ETF 列表页 | ✅ 正常 | 支持筛选、排序、分页 |
| ETF 对比页（compare_v3） | ⚠️ 部分功能待测试 | 环形图、表格、AI 对话框 |
| AI 聊天对话框 | ✅ 已完成（规则引擎） | 未接真实 AI API |
| 导出功能（截图/打印） | ✅ 已恢复 | 需测试 `openPrintPage()` |
| 风险指标页 | ✅ 正常 | 依赖盈米数据 |
| PythonAnywhere 部署 | ⚠️ 需手动部署 | `pa_deploy.sh` 待修复 |

---

### 6.2 已知问题（待修复）

1. **`openPrintPage()` 函数可能仍有问题** — 打印页面功能未完全测试
2. **AI 聊天是规则引擎** — 未接真实 AI API（需 API Key）
3. **前端 markdown 渲染基础** — 只转 `**粗体**` 和 `\n`
4. **PythonAnywhere 部署** — `pa_deploy.sh` WSGI 路径问题待修复

---

### 6.3 下次对话建议

1. **测试导出功能** — Mac 本地运行，测试截图/打印是否正常工作
2. **修复 `openPrintPage()`** — 如果打印页面有问题，检查 `compare_v3_print` 路由和模板
3. **接真实 AI API** — 如果需要 AI 聊天功能，需用户提供 API Key（Claude/GPT 等）
4. **部署到 PythonAnywhere** — 修复 `pa_deploy.sh`，推送到 GitHub，手动部署

---

## 七、快速参考

### 7.1 常用命令

```bash
# 本地运行项目
cd ~/WorkBuddy/Claw/etf-tool-mvp && python3 app.py

# 测试 API 接口
curl "http://localhost:5000/api/compare?codes=510300,510500,159915" | python3 -m json.tool

# 查看最近提交
git log --oneline -10

# 恢复某个文件到旧版本
git checkout <commit> -- <file>

# 检查数据更新时间
ls -lh etf_standard_data.json
```

---

### 7.2 重要文件位置

| 文件 | 路径 | 说明 |
|------|------|------|
| 项目根目录 | `~/WorkBuddy/Claw/etf-tool-mvp` | 项目主目录 |
| 主应用 | `app.py` | Flask 应用入口 |
| 对比页模板 | `templates/compare_v3.html` | ETF 对比页（核心） |
| 打印页模板 | `templates/compare_print.html` | 打印友好版 |
| 数据文件 | `etf_standard_data.json` | L1 本地缓存 |
| 数据更新脚本 | `update_data.py` | 自动更新数据 |
| 部署脚本 | `pa_deploy.sh` | PythonAnywhere 部署 |
| Wind fetcher | `fetchers/wind_fetcher.py` | Wind API 数据获取 |

---

### 7.3 关键联系人/资源

- **PythonAnywhere 部署地址**：`https://froza.pythonanywhere.com/`
- **GitHub 仓库**：`https://github.com/froza88/etf-tool-mvp`
- **Wind API Key**：`~/.wind-aifinmarket/config`
- **Wind MCP CLI**：`~/.agents/skills/wind-mcp-skill/scripts/cli.mjs`

---

## 八、总结

本次对话主要解决了 **L1/L2 数据缓存污染** 这一核心问题，并修复了多个前端显示 bug。关键经验包括：

1. **数据架构设计**：L1 和 L2 数据应该严格分离，避免字段缺失的 L2 数据污染 L1 缓存
2. **防御性编程**：JavaScript 模板渲染必须检查 `undefined`/`null`
3. **Flask 模板变量**：路由函数必须显式传递所有模板变量
4. **Git 版本管理**：每次修改后提交，方便回退和问题定位
5. **用户反馈处理**：要求截图/录屏，先复现再修复

---

**文档版本**：v1.0  
**最后更新**：2026-05-27 14:30  
**作者**：WorkBuddy AI Assistant
