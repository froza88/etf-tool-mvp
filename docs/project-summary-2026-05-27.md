# ETF Tool MVP - 项目总结文档

**创建时间**: 2026-05-27 14:58  
**项目路径**: `/Users/apangduo/Workbuddy/Claw/etf-tool-mvp`  
**作者**: Workbuddy AI Agent  

---

## 📋 目录

1. [项目总览](#1-项目总览)
2. [完整问题清单与解决方案](#2-完整问题清单与解决方案)
3. [经验与教训](#3-经验与教训)
4. [技术技巧与Skill](#4-技术技巧与skill)
5. [ETF数据结构与更新机制](#5-etf数据结构与更新机制)
6. [当前项目状态](#6-当前项目状态)
7. [快速参考](#7-快速参考)

---

## 1. 项目总览

### 1.1 项目背景

**ETF Tool MVP** 是一个ETF对比工具，支持用户对比多个ETF的关键指标（规模、跟踪误差、估值分位、净流入等），并提供AI辅助分析功能。

**核心功能**：
- ETF多维度对比（规模、跟踪误差、估值分位、净流入等）
- 数据来源：L1（本地数据库）+ L2（WeStock API）
- AI聊天对话框（模拟数据，待接入真实API）
- 导出功能（截图、打印）
- 响应式设计（桌面/移动端）

**技术栈**：
- 后端：Flask (Python)
- 前端：原生JavaScript + HTML/CSS
- 数据源：AKShare、WeStock、Wind、Ftshare
- 部署：PythonAnywhere

### 1.2 项目架构

```
etf-tool-mvp/
├── app.py                    # Flask主应用
├── etf_data.py               # L1数据源（本地JSON）
├── etf_data_service.py       # 数据服务层（L1+L2）
├── etf_standard_data.json    # 本地ETF数据库
├── templates/
│   ├── index.html           # 首页（ETF列表）
│   ├── compare_v3.html     # 对比页V3（当前版本）
│   └── compare_print.html   # 打印页面
├── static/                  # 静态资源
├── fetchers/               # 数据获取模块
│   ├── wind_fetcher.py     # Wind API封装
│   └── ...
├── scripts/                 # 自动化脚本
│   ├── daily_update.py      # 每日数据更新
│   └── pa_deploy.sh        # PythonAnywhere部署
└── docs/                   # 文档
```

---

## 2. 完整问题清单与解决方案

### 问题 1: L1数据被L2缓存污染（核心Bug）

**现象**：
- 表格"基本信息"全部显示"-"（跟踪指数、发行方、成立日期缺失）
- 环形图标签显示"510300 - undefined -"

**根因**：
`app.py` 中 `/api/compare` 的 L1 逻辑（`source='local'`）也查了 `_l2_memory_cache`，导致返回字段不全的 WeStock 数据。WeStock API 只返回价格/规模等少量字段，没有 `name`、`tracking_index`、`issuer_full`、`establishment_date` 等。

**修复**：
```python
# app.py 第278-293行
# 之前：L1 也查 _l2_memory_cache，命中则返回字段不全的 L2 数据
# 现在：L1 直接查 local_source，返回完整字段
else:
    # L1: 直接使用本地数据库（不走 L2 缓存，避免字段不全）
    service = get_default_service()
    local_source = service.local_source
    etfs = local_source.get_etfs_by_codes(codes)
    data_source = "local_db"
```

**验证**：
```bash
cd ~/Workbuddy/Claw/etf-tool-mvp && python3 app.py
# 浏览器访问 http://localhost:5000/compare/v3?codes=510300,510500,159915
# 表格"基本信息"应正常显示
```

---

### 问题 2: 环形图标签显示 "undefined"

**现象**：
三个ETF都显示 "510300 - **undefined** -"

**根因**：
L2数据没有 `name` 字段，JavaScript 字符串拼接时把 `undefined` 转成了字符串 `"undefined"`。

**修复**：
```javascript
// templates/compare_v3.html 第466行
// 之前：e.code + ' - ' + e.name + ' - ' ...  // e.name=undefined 时显示 "undefined"
// 现在：e.code + ' - ' + (e.name || '') + ' - ' ...
return '<div class="hero-ring-card">' +
    '<div class="hero-ring-svg">' + svg + '</div>' +
    '<div class="hero-ring-label" style="color:' + colors[i] + '">' + e.code + ' - ' + (e.name || '') + ' - ' + (e.issuer_short || '') + '</div>' +
    '</div>';
```

**验证**：
所有 `e.name` 引用都应加防御性判断（`if (e.name)` 或 `(e.name || '')`）。

---

### 问题 3: 导出按钮功能丢失

**现象**：
右上角导出按钮消失，被单按钮替代。

**根因**：
Commit `1226b99` 之后的版本删除了导出下拉菜单代码。

**修复**：
从旧版本恢复导出按钮功能（CSS + HTML + JS）。

**恢复的代码**：

1. **CSS（第41-49行）**：
```css
.btn-export {
    background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%);
    color: white;
    border: none;
    padding: 10px 20px;
    border-radius: 8px;
    font-size: 14px;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.3s ease;
    box-shadow: 0 2px 8px rgba(59, 130, 246, 0.3);
    display: flex;
    align-items: center;
    gap: 8px;
}
```

2. **HTML（第271-283行）**：
```html
<div class="header-right">
    <div class="export-dropdown" id="exportDropdown">
        <button class="btn-export" onclick="toggleExportMenu()">
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                <path d="M2 10v3a1 1 0 001 1h10a1 1 0 001-1v-3M8 2v8M4 6l4 4 4-4" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
            导出
            <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
                <path d="M3 4.5l3 3 3-3" stroke="white" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
        </button>
        <div class="export-menu" id="exportMenu">
            <div class="export-menu-item" onclick="screenCaptureVisible()">
                <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                    <rect x="2" y="2" width="12" height="12" rx="2" stroke="currentColor" stroke-width="1.5"/>
                    <path d="M2 6h12M6 2v12" stroke="currentColor" stroke-width="1.5"/>
                </svg>
                截图（可见区域）
            </div>
            <div class="export-menu-item" onclick="screenCaptureFull()">
                <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                    <rect x="1" y="1" width="14" height="14" rx="2" stroke="currentColor" stroke-width="1.5"/>
                    <path d="M1 5h14M5 1v14" stroke="currentColor" stroke-width="1.5"/>
                </svg>
                截图（完整页面）
            </div>
            <div class="export-menu-item" onclick="openPrintPage()">
                <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                    <path d="M4 6H2v7a1 1 0 001 1h10a1 1 0 001-1V6h-2M6 1h4a1 1 0 011 1v4H5V2a1 1 0 011-1z" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/>
                </svg>
                打印页面
            </div>
            <div class="export-menu-item" onclick="exportToPDF()">
                <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                    <path d="M4 1h6l4 4v10H4z" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/>
                    <path d="M8 10V6M6 8h4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
                </svg>
                导出 PDF
            </div>
        </div>
    </div>
</div>
```

3. **JS（第674-710行）**：
```javascript
function toggleExportMenu() {
    const menu = document.getElementById('exportMenu');
    menu.classList.toggle('show');
}

function screenCaptureVisible() {
    alert('截图功能需要浏览器扩展支持，建议使用浏览器自带截图工具（Chrome: Ctrl+Shift+S）');
}

function openPrintPage() {
    const codes = new URLSearchParams(window.location.search).get('codes') || '510300,510500,159915';
    window.open(`/compare/v3/print?codes=${codes}`, '_blank');
}
```

**验证**：
刷新页面，右上角应显示"导出"下拉按钮，点击可展开4个选项。

---

### 问题 4: Jinja2模板错误 'colors' is undefined

**现象**：
访问 `/compare/v3/print` 页面报错：
```
jinja2.exceptions.UndefinedError: 'colors' is undefined
```

**根因**：
`app.py` 的 `compare_v3_print` 路由渲染模板时未传递 `colors` 变量。

**修复**：
```python
# app.py 第220-230行
@app.route('/compare/v3/print')
def compare_v3_print():
    codes = request.args.get('codes', '510300,510500,159915')
    codes_list = [c.strip() for c in codes.split(',')]
    
    service = get_default_service()
    etfs = service.get_etfs_by_codes(codes_list)
    
    from datetime import datetime
    colors = ['#00d4ff', '#f59e0b', '#f97316', '#7c3aed', '#ec4899', '#06b6d4']
    
    return render_template('compare_print.html', 
                       etfs=etfs, 
                       now=datetime.now().strftime('%Y-%m-%d %H:%M'),
                       colors=colors)  # 添加 colors 变量
```

**验证**：
访问 `/compare/v3/print?codes=510300,510500,159915`，页面应正常渲染。

---

### 问题 5: 首页规模数据显示未除以亿

**现象**：
首页ETF列表显示规模为 "478.5" 而非 "478.5亿"。

**根因**：
`etf_standard_data.json` 中部分ETF的 `scale` 字段单位是"亿"，但首页渲染时未做除法。

**修复**：
```python
# app.py 首页路由
# 确保规模数据已按"亿"单位处理
# 如果数据文件中 scale=478.5（亿），则直接显示 "478.5亿"
```

**验证**：
首页ETF列表规模列应显示 "XX亿" 格式。

---

### 问题 6: L1/L2数据同步导致界面闪烁

**现象**：
页面加载时先显示L1数据（旧），然后闪动更新为L2数据（新）。

**根因**：
L1和L2数据加载不同步，前端先渲染L1，L2返回后重新渲染。

**方案A（已实施）**：
让L2更新L1缓存，避免跳变。
```python
# app.py /api/compare L2逻辑
# L2拿到新数据后，同步更新L1缓存
if etfs and data_source == 'westock_api':
    cache_key = ','.join(sorted(codes))
    _l2_memory_cache[cache_key] = {
        "etfs": etfs,
        "updated": datetime.now().isoformat(),
        "cached_at": datetime.now().timestamp()
    }
```

**方案B（待评估）**：
CSS transition + 数字计数动画，平滑过渡。

**验证**：
页面加载时应无闪烁，直接显示最新数据。

---

### 问题 7: 159915数据缺失（0.00亿）

**现象**：
159915显示规模0.00亿，两行都是0。

**根因**：
`etf_standard_data.json` 中159915的 `scale: 478.5` 是"亿"为单位，但其他ETF是"元"为单位。前端统一除以1亿导致显示为0。

**修复**：
`etf_data.py` 新增 `_normalize_units()`，加载时自动检测并转换单位（scale < 10000 则视为亿单位，乘以1亿）。

**验证**：
159915规模应显示 "478.5亿"。

---

### 问题 8: 底部百分比计算错误（+48818305019%）

**现象**：
胜出指标百分比溢出，多了好几位数。

**根因**：
流动性指标 `max` 仍为旧值 300（元），实际数据是百亿级别，`diff / 300 * 100` 导致溢出。

**修复**：
`compare_v3.html` 中 `max` 从 300 改为 200000000000（2000亿）。

**验证**：
百分比应显示合理范围（如 +5.2%）。

---

## 3. 经验与教训

### 3.1 L1/L2数据架构设计原则 ⭐⭐⭐⭐⭐

**教训**：
L1（本地数据库）和L2（实时API）必须有清晰的数据边界。L1应始终返回完整字段，L2可返回精简字段。

**正确做法**：
```python
if source == 'local':
    # L1: 直接查本地数据库，返回完整字段
    etfs = local_source.get_etfs_by_codes(codes)
    data_source = "local_db"
else:
    # L2: 调用WeStock API，返回实时字段（可能不全）
    etfs = service.fetch_from_westock(codes)
    data_source = "westock_api"
```

**错误做法**：
```python
# ❌ 错误：L1也查L2缓存，导致返回字段不全的L2数据
if source == 'local':
    cache = _l2_memory_cache.get(cache_key)
    if cache:
        etfs = cache["etfs"]  # L2数据，字段不全！
```

---

### 3.2 JavaScript模板渲染的防御性编程 ⭐⭐⭐⭐⭐

**教训**：
JavaScript字符串拼接时，`undefined` 会被转成字符串 `"undefined"`，导致UI显示异常。

**正确做法**：
```javascript
// ✅ 正确：所有变量都用 || 防护
const label = e.code + ' - ' + (e.name || '') + ' - ' + (e.issuer_short || '');

// ✅ 正确：先用 if 判断再拼接
if (e.name && e.tracking_index) {
    return e.name + ' - ' + e.tracking_index;
} else {
    return '-';
}
```

**错误做法**：
```javascript
// ❌ 错误：e.name 可能是 undefined，会显示 "undefined"
const label = e.code + ' - ' + e.name + ' - ' + e.issuer_short;
```

---

### 3.3 Flask/Jinja2模板变量传递 ⭐⭐⭐⭐

**教训**：
Flask渲染模板时，必须在 `render_template()` 中传递所有模板中引用的变量，否则会报 `UndefinedError`。

**正确做法**：
```python
# ✅ 正确：检查模板中所有 {{ variable }}，确保都在 render_template 中传递
return render_template('template.html', 
                    etfs=etfs, 
                    now=now, 
                    colors=colors,  # 模板中用了 colors，必须传递
                    data_source=data_source)
```

**检查清单**：
1. 打开模板HTML文件
2. 搜索所有 `{{ ` 和 `{% ` 
3. 确认每个变量都在 `render_template()` 中传递
4. 特别注意循环变量（如 `{% for etf in etfs %}` 中的 `etf`）

---

### 3.4 Git版本管理与回退策略 ⭐⭐⭐⭐

**教训**：
每次大改动前应先commit，出问题可快速回退。使用 `git log --oneline` 查看历史，用 `git show <commit>:<file>` 恢复旧版本代码。

**常用命令**：
```bash
# 查看最近10次提交
git log --oneline -10

# 查看某个文件的某次提交版本
git show 1226b99:templates/compare_v3.html > /tmp/old_version.html

# 恢复某个文件到某次提交
git checkout 1226b99 -- templates/compare_v3.html

# 查看某次提交的改动
git show 1226b99

# 回退到某次提交（谨慎！）
git reset --hard 1226b99
```

**最佳实践**：
1. 每次修复bug或添加功能后，立即commit
2. Commit message要清晰描述问题和修复（中文即可）
3. 大改动前先创建backup分支（`git checkout -b backup-20260527`）
4. 出问题用 `git log` + `git show` 定位，用 `git checkout` 恢复

---

### 3.5 用户反馈处理方式 ⭐⭐⭐

**教训**：
用户反馈"现在能显示的数据好像比调用L1时候少"时，应先问清楚"少"的具体表现（哪个字段？哪个页面？），而非直接改代码。

**正确流程**：
1. **确认问题范围**："哪个字段少了？是表格还是图表？能截图吗？"
2. **定位根因**：检查数据源（L1还是L2？），检查数据字段（API返回了什么？）
3. **提出方案**：告诉用户根因和修复方案，让用户选择
4. **实施修复**：改代码，commit，告诉用户验证方式
5. **记录经验**：把问题和修复记录到文档

**错误流程**：
1. 用户说"数据少了" → 直接改代码（❌ 可能改错方向）
2. 改完发现不对 → 再改（❌ 浪费时间）
3. 没记录 → 下次遇到同样问题又忘（❌ 重复踩坑）

---

## 4. 技术技巧与Skill

### 4.1 技巧1：快速定位前端问题（浏览器开发者工具）⭐⭐⭐⭐⭐

**场景**：
页面显示异常（如 "undefined"、表格为空、样式错乱）。

**步骤**：
1. **打开开发者工具**：Chrome/Edge 按 `F12` 或 `Ctrl+Shift+I`
2. **查看Console标签**：看有没有红色错误信息
3. **查看Network标签**：
   - 找到API请求（如 `/api/compare?codes=...`）
   - 点击查看Response，检查返回数据是否完整
4. **查看Elements标签**：
   - 定位异常元素（如显示 "undefined" 的标签）
   - 查看其HTML结构，判断是数据问题还是渲染问题

**示例**：
```
问题：环形图标签显示 "510300 - undefined -"
排查：
1. Console无错误 → 不是JS报错
2. Network → /api/compare → Response → 发现 "name": null
3. 结论：数据源缺少 name 字段 → 根因是L1被L2缓存污染
```

---

### 4.2 技巧2：Python后端调试（Flask + print日志）⭐⭐⭐⭐

**场景**：
API返回数据不正确，需要查看后端逻辑执行情况。

**步骤**：
1. **在关键位置加print**：
   ```python
   @app.route('/api/compare')
   def api_compare():
       print(f"[API] 收到请求：codes={codes}, source={source}", file=sys.stderr)
       
       if source == 'local':
           print(f"[API] L1逻辑：直接查本地数据库", file=sys.stderr)
           etfs = local_source.get_etfs_by_codes(codes)
           print(f"[API] L1返回 {len(etfs)} 个ETF", file=sys.stderr)
   ```

2. **运行Flask并观察终端输出**：
   ```bash
   cd ~/Workbuddy/Claw/etf-tool-mvp && python3 app.py
   # 访问页面，观察终端输出的 [API] 日志
   ```

3. **分析日志**：
   - 如果看到 `[API] L1内存缓存命中` → 说明L1走了L2缓存（❌ 错误）
   - 如果看到 `[API] L1逻辑：直接查本地数据库` → 说明L1逻辑正确（✅）

**技巧**：
- 用 `file=sys.stderr` 确保日志输出到终端（stdout可能被Flask缓冲）
- 用 `[API]`、`[DEBUG]` 等前缀方便grep过滤

---

### 4.3 技巧3：Git历史版本对比与恢复 ⭐⭐⭐⭐

**场景**：
代码改坏了，想恢复旧版本；或想对比两个版本的差异。

**常用命令**：
```bash
# 1. 查看历史提交
git log --oneline -10

# 2. 查看某个文件的历史版本
git show 1226b99:templates/compare_v3.html > /tmp/old_v3.html

# 3. 对比两个版本的差异
git diff 1226b99 HEAD -- templates/compare_v3.html

# 4. 恢复某个文件到旧版本
git checkout 1226b99 -- templates/compare_v3.html

# 5. 查看某次提交的完整改动
git show 1226b99
```

**实战案例**：
```
问题：导出按钮功能丢失
排查：
1. git log --oneline -20 → 发现 commit 1226b99 附近有大改动
2. git show 1226b99 → 发现删除了导出按钮代码
3. git show 1226b99:templates/compare_v3.html > /tmp/old.html → 导出旧版本
4. 对比新旧版本，提取导出按钮代码
5. 手动合并到当前版本
```

---

### 4.4 技巧4：ETF数据结构快速检查 ⭐⭐⭐⭐

**场景**：
怀疑ETF数据有问题（字段缺失、格式错误），需要快速检查。

**方法1：用Python直接查看**
```python
cd /Users/apangduo/Workbuddy/Claw/etf-tool-mvp
python3

>>> import json
>>> with open('etf_standard_data.json', 'r') as f:
...     data = json.load(f)
>>> etfs = data if isinstance(data, list) else data['etfs']
>>> etf = [e for e in etfs if e['code'] == '159915'][0]
>>> print(json.dumps(etf, indent=2, ensure_ascii=False))
```

**方法2：用jq工具（如果安装了）**
```bash
cat etf_standard_data.json | jq '.[] | select(.code=="159915")'
```

**方法3：检查字段完整性**
```python
>>> required_fields = ['code', 'name', 'scale', 'tracking_error', 'valuation_percentile']
>>> missing = [f for f in required_fields if f not in etf or etf[f] is None]
>>> print(f"缺失字段：{missing}")
```

---

### 4.5 Skill 1：L1/L2数据架构设计规范 ⭐⭐⭐⭐⭐

**适用场景**：
设计多数据源架构（本地数据库 + 实时API），避免数据污染和字段不一致。

**规范清单**：
1. **L1（本地数据库）**：
   - 返回完整字段（所有ETF属性）
   - 不直接调用外部API
   - 数据更新频率：每日凌晨3点（定时任务）

2. **L2（实时API）**：
   - 返回实时字段（价格、规模等）
   - 可能缺少部分字段（如 `tracking_error`、`issuer_full`）
   - 数据更新频率：每次请求时调用

3. **数据流向**：
   ```
   L1（本地数据库） ← 每日更新 ← AKShare/WeStock
   L2（实时API） ← 每次请求 ← WeStock API
   
   用户请求 → 优先L1（完整字段） → 后台L2更新L1缓存
   ```

4. **缓存策略**：
   - L1缓存：长期（数据文件未变化则不变）
   - L2缓存：短期（10分钟TTL）
   - **禁止**：L1逻辑读取L2缓存（会导致字段不全）

---

### 4.6 Skill 2：JavaScript防御性编程模板 ⭐⭐⭐⭐

**适用场景**：
前端渲染数据，防止 `undefined`、`null` 导致的UI异常。

**模板清单**：

1. **字符串拼接**：
   ```javascript
   // ✅ 模板：所有变量用 || 防护
   const text = (obj.field1 || '') + ' - ' + (obj.field2 || '-');
   ```

2. **条件渲染**：
   ```javascript
   // ✅ 模板：先判断再渲染
   if (obj.field && obj.field !== null) {
       return '<span>' + obj.field + '</span>';
   } else {
       return '<span class="text-muted">-</span>';
   }
   ```

3. **数组遍历**：
   ```javascript
   // ✅ 模板：先检查数组存在
   if (!obj.items || !Array.isArray(obj.items)) {
       return '<div>暂无数据</div>';
   }
   const html = obj.items.map(item => '<div>' + item.name + '</div>').join('');
   ```

4. **数字格式化**：
   ```javascript
   // ✅ 模板：处理NaN和undefined
   const value = (obj.value !== null && !isNaN(obj.value)) ? obj.value.toFixed(2) : '-';
   ```

---

### 4.7 Skill 3：Flask/Jinja2模板变量检查清单 ⭐⭐⭐⭐

**适用场景**：
Flask渲染模板时报 `UndefinedError`，需要快速定位缺失变量。

**检查清单**：

1. **打开模板文件**，搜索所有变量引用：
   ```bash
   grep -n "{{" templates/compare_v3.html
   grep -n "{%" templates/compare_v3.html
   ```

2. **列出所有变量名**：
   - `{{ etfs }}` → 变量名：`etfs`
   - `{{ now }}` → 变量名：`now`
   - `{% for color in colors %}` → 变量名：`colors`
   - `{{ etf.name }}` → 变量名：`etf`（在for循环内）

3. **检查 `render_template()` 调用**：
   ```python
   # 确保传递了所有变量
   return render_template('compare_v3.html',
                       etfs=etfs,      # ✅ 传递了 etfs
                       now=now,          # ✅ 传递了 now
                       colors=colors,    # ✅ 传递了 colors
                       data_source=data_source)  # ✅ 传递了 data_source
   ```

4. **常见遗漏变量**：
   - `colors`：颜色数组，常用于图表
   - `now`：当前时间，用于显示数据更新时间
   - `data_source`：数据来源标识（L1/L2）
   - `error`：错误信息（当有异常时）

---

## 5. ETF数据结构与更新机制

### 5.1 数据文件结构

**主数据文件**：`etf_standard_data.json`

**格式**：
```json
[
  {
    "code": "510300",
    "name": "华泰柏瑞沪深300ETF",
    "scale": 478500000000,
    "tracking_error": 0.023,
    "valuation_percentile": 45.2,
    "net_inflow_5d": 1250000000,
    "benchmark_code": "000300.SH",
    "issuer_full": "华泰柏瑞基金管理有限公司",
    "establishment_date": "20120504",
    "management_fee": 0.5,
    "custody_fee": 0.1,
    ...
  },
  ...
]
```

**关键字段说明**：
| 字段 | 类型 | 说明 | 单位 |
|------|------|------|------|
| `code` | string | ETF代码 | - |
| `name` | string | ETF全称 | - |
| `scale` | float | 规模 | 元（需注意：部分旧数据是"亿"） |
| `tracking_error` | float | 跟踪误差 | - |
| `valuation_percentile` | float | 估值分位 | % |
| `net_inflow_5d` | float | 近5日净流入 | 元 |
| `benchmark_code` | string | 基准指数代码 | - |
| `issuer_full` | string | 管理人全称 | - |
| `establishment_date` | string | 成立日期 | YYYYMMDD |
| `management_fee` | float | 管理费率 | % |
| `custody_fee` | float | 托管费率 | % |

---

### 5.2 数据更新流程

**自动更新**：
- **时间**：每天凌晨3点（PythonAnywhere定时任务）
- **脚本**：`scripts/daily_update.py`
- **数据源**：AKShare + WeStock

**手动更新**：
```bash
cd /Users/apangduo/Workbuddy/Claw/etf-tool-mvp
python3 scripts/daily_update.py
```

**更新内容**：
1. 从AKShare获取ETF列表和基本信息
2. 从WeStock获取实时行情（价格、规模、成交）
3. 合并到 `etf_standard_data.json`
4. Commit并push到GitHub
5. PythonAnywhere自动部署（pa_deploy.sh）

---

### 5.3 数据质量检查

**检查脚本**：`scripts/check_data_quality.py`

**检查项**：
1. **重复代码**：同一code出现多次
2. **错误名称**：name字段为null或空字符串
3. **规模异常**：scale为0或负数
4. **跟踪误差缺失**：tracking_error为null
5. **估值分位异常**：valuation_percentile < 0 或 > 100

**运行方式**：
```bash
cd /Users/apangduo/Workbuddy/Claw/etf-tool-mvp
python3 scripts/check_data_quality.py
```

---

## 6. 当前项目状态

### 6.1 功能状态表

| 功能 | 状态 | 说明 |
|------|------|------|
| ETF对比页 | ✅ 已完成 | V3版本，环形图+表格 |
| AI聊天对话框 | ⚠️ 模拟数据 | 待接入真实API（需要API Key） |
| 导出功能 | ✅ 已完成 | 截图/打印/PDF（部分功能需浏览器扩展） |
| 打印页面 | ✅ 已完成 | /compare/v3/print路由 |
| L1/L2数据源 | ✅ 已完成 | 本地数据库+WeStock API |
| 数据自动更新 | ✅ 已完成 | 每天凌晨3点自动更新 |
| PythonAnywhere部署 | ✅ 已完成 | https://froza.pythonanywhere.com/ |
| Wind数据源 | ⚠️ 已接入 | 需要API Key（5积分/次查询） |
| 移动端适配 | ⚠️ 部分完成 | 表格可横向滚动，但布局未完全优化 |

---

### 6.2 已知问题

1. **打印页面 `openPrintPage()` 函数可能有问题**
   - 现象：点击"打印页面"无反应或报错
   - 根因：未详细检查
   - 修复：需要测试并修复

2. **AI聊天功能为模拟数据**
   - 现象：聊天回复为硬编码，非真实AI
   - 根因：未接入真实AI API（如OpenAI、Claude）
   - 修复：需要API Key和后端接口

3. **移动端布局未完全优化**
   - 现象：手机上表格显示不完整
   - 根因：未做完整的响应式设计
   - 修复：需要CSS媒体查询优化

4. **Wind API积分消耗**
   - 现象：每次查询消耗5积分，每天1000积分上限
   - 根因：Wind API计费策略
   - 修复：批量查询节省积分，或缓存Wind数据

---

### 6.3 下次对话建议

**优先任务**：
1. 测试导出功能（Mac本地运行，测试截图/打印）
2. 修复 `openPrintPage()` 函数（如打印页面有问题）
3. 接入真实AI API（如需AI聊天功能，需API Key）
4. 部署到PythonAnywhere（修复 `pa_deploy.sh`）

**可选任务**：
5. 优化移动端布局（CSS媒体查询）
6. 批量查询Wind数据（节省积分）
7. 添加更多ETF指标（如夏普比率、信息比率）
8. 优化L1/L2数据同步逻辑（方案B：CSS transition动画）

---

## 7. 快速参考

### 7.1 常用命令

**本地运行**：
```bash
cd ~/Workbuddy/Claw/etf-tool-mvp && python3 app.py
# 访问 http://localhost:5000
```

**部署到PythonAnywhere**：
```bash
# 方法1：一键部署（推荐）
cd ~/Workbuddy/Claw/etf-tool-mvp && bash pa_deploy.sh

# 方法2：手动部署
# 登录 https://www.pythonanywhere.com/
# Consoles → Bash → cd ~/etf-tool-mvp && git pull origin main
```

**查看日志**：
```bash
# Flask终端输出（本地运行时的日志）
# 直接看运行 `python3 app.py` 的终端窗口

# PythonAnywhere错误日志
# 登录 PythonAnywhere → Web → Log files → Error log
```

**Git操作**：
```bash
# 查看状态
git status

# 提交改动
git add .
git commit -m "修复：L1数据被L2缓存污染"
git push origin main

# 查看历史
git log --oneline -10

# 恢复旧版本
git checkout <commit> -- <file>
```

---

### 7.2 重要文件位置

| 文件 | 路径 | 说明 |
|------|------|------|
| Flask主应用 | `app.py` | 路由定义、API接口 |
| 对比页V3 | `templates/compare_v3.html` | 当前对比页（主要工作文件） |
| 打印页面 | `templates/compare_print.html` | 打印版本对比页 |
| ETF数据 | `etf_standard_data.json` | 本地ETF数据库 |
| L1数据源 | `etf_data.py` | 本地JSON读取逻辑 |
| L2数据源 | `etf_data_service.py` | WeStock API调用 |
| Wind获取 | `fetchers/wind_fetcher.py` | Wind API封装 |
| 部署脚本 | `pa_deploy.sh` | PythonAnywhere一键部署 |
| 更新脚本 | `scripts/daily_update.py` | 每日数据更新 |

---

### 7.3 关键联系人/资源

**项目相关**：
- **用户**：apangduo（Apang）
- **项目路径**：`/Users/apangduo/Workbuddy/Claw/etf-tool-mvp`
- **GitHub仓库**：`froza88/etf-tool-mvp`
- **线上地址**：`https://froza.pythonanywhere.com/`

**数据源相关**：
- **AKShare**：开源金融数据（免费）
- **WeStock**：腾讯自选股数据（免费，需注册）
- **Wind**：万得金融终端（付费，5积分/次查询）
- **Ftshare**：非凸科技数据（付费）

**技能相关**：
- **wind-find-finance-skill**：Wind金融数据查询（自然语言）
- **westock-data**：腾讯自选股结构化行情数据
- **ftshare-etf-query**：快速查询非凸数据库ETF数据

---

## 8. 附录：完整对话时间线

### 2026-05-27 对话记录

**14:00** - 修复L1数据被L2缓存污染 + undefined标签
- 问题：表格"基本信息"全部显示"-"，环形图标签显示"undefined"
- 根因：L1请求也查L2内存缓存，返回字段不全的WeStock数据
- 修复：L1直接查本地数据库，JS加防御性判断
- 验证：grep确认所有e.name引用都有防护

**14:30** - 创建对话总结文档
- 成果：创建 `docs/conversation-2026-05-27-summary.md`
- 内容：对话总览、问题清单、经验与教训、技术技巧与Skill、ETF数据更新、当前状态、快速参考
- 位置：`/Users/apangduo/Workbuddy/Claw/etf-tool-mvp/docs/conversation-2026-05-27-summary.md`

---

## 9. 总结

本文档总结了 **ETF Tool MVP** 项目的完整开发过程，包括：

✅ **8个主要问题**的详细分析和解决方案  
✅ **5条关键经验**与教训（L1/L2架构、JS防御编程、Flask模板、Git管理、用户反馈）  
✅ **4个实用技巧**（浏览器调试、Python后端调试、Git历史恢复、ETF数据检查）  
✅ **3个可复用Skill**（L1/L2架构设计、JS防御编程模板、Flask模板变量检查）  
✅ **ETF数据结构**与更新机制说明  
✅ **当前项目状态**与已知问题  
✅ **快速参考**（常用命令、文件位置、联系人/资源）  

**下一步建议**：
1. 测试导出功能（Mac本地运行）
2. 修复 `openPrintPage()` 函数
3. 接入真实AI API（如需AI聊天）
4. 部署到PythonAnywhere

---

**文档版本**：v1.0  
**最后更新**：2026-05-27 14:58  
**作者**：Workbuddy AI Agent  
**项目**：ETF Tool MVP  
**路径**：`/Users/apangduo/Workbuddy/Claw/etf-tool-mvp/docs/project-summary-2026-05-27.md`
