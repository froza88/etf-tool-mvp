# ETF Tool MVP 代码审查标准与流程

## 一、审查原则

1. **每次 PR/修改必须审查** — 无论改的人是谁
2. **审查代码，不审查人** — 对代码不对人
3. **先功能后质量** — 先看逻辑是否正确，再看代码是否优雅
4. **One review, complete** — 一次性给出完整反馈，不要挤牙膏式评论

---

## 二、审查优先级标记

| 标记 | 含义 | 处理方式 |
|------|------|----------|
| 🔴 **Critical** | 必修 | Bug、安全漏洞、数据错误、500错误 |
| 🟡 **Warning** | 建议修 | 可维护性问题、性能隐患、边界情况 |
| 💭 **Nit** | 可忽略 | 风格、命名、格式（有 lint 的除外） |

---

## 三、审查 Checklist（按代码层次）

### 3.1 后端 Python（app.py / etf_data.py / services/*）

#### 🔴 Critical
- [ ] **SQL 注入 / 命令注入** — 用户输入是否拼接到了 SQL/shell 命令？参数化查询？
- [ ] **500 错误** — try/except 是否覆盖了所有外部调用？异常被吞了还是返回了 HTTP 500？
- [ ] **数据一致性** — JSON 写入前是否有备份？更新是否幂等？
- [ ] **文件路径** — 使用了 Path() 而非字符串拼接？跨平台兼容？

#### 🟡 Warning
- [ ] **模块导入** — 避免 `from X import *`，按需导入
- [ ] **函数复杂度** — 一个函数超过 60 行？拆！
- [ ] **None 安全** — `data.get("key")` 而非 `data["key"]`，例如：
  ```python
  # ❌ 会崩
  val = obj["scale"] / 100000000
  # ✅ 安全
  val = obj.get("scale", 0) / 100000000 if obj.get("scale") else 0
  ```
- [ ] **文件编码** — `open()` 默认缺 encoding，JSON 文件用 `encoding="utf-8"`
- [ ] **配置硬编码** — API key / 端口 / 路径是否可配置？`os.environ.get()` 优先
- [ ] **print 不用于生产** — `print(file=sys.stderr)` 在 reloader 下会 BrokenPipeError，用 logging

#### 💭 Nit
- [ ] **类型提示** — 函数签名加类型标注有助于理解
- [ ] **f-string 优先** — 少用 `%` 或 `.format()`
- [ ] **注释** — 不要写"改了什么"，写"为什么要这么改"

---

### 3.2 前端 HTML/JS（templates/*.html）

#### 🔴 Critical
- [ ] **XSS** — 用户数据内插到 HTML 时是否 `textContent`/转义？内联 JS 是否拼接了不可信输入？
  ```javascript
  // ❌ 危险
  container.innerHTML = '<div>' + userInput + '</div>';
  // ✅ 安全
  container.textContent = userInput;
  ```
- [ ] **API 错误处理** — fetch 失败/超时/非 200 有没有兜底 UI？
- [ ] **空数据** — 列表/表格在没有数据时是否显示了占位？

#### 🟡 Warning
- [ ] **双重渲染** — `renderHero()` 是否被调了两次？检查 setTimeout/fetch 回调
- [ ] **DOM 查询精度** — `querySelector('g')` 可能返回错误元素，用 `[data-xxx]` 属性选择器
- [ ] **SVG animate 时序** — `begin="0s"` 从页面加载开始计时，不是 JS 调用时。用 `begin="indefinite"` + `beginElement()`
- [ ] **GSAP 安全** — `typeof gsap !== 'undefined'` 检查 CDN 是否加载成功
- [ ] **CSS 变量兜底** — 用了 `var(--xxx)` 的确认后备值（`var(--xxx, fallback)`）

#### 💭 Nit
- [ ] **内联样式 vs CSS class** — 重复的 inline style 抽成 class
- [ ] **语义化 class** — `.hero-ring-card` > `.card1`
- [ ] **动画 ease** — 统一缓出函数，不要混用 ease-out / cubic-bezier / linear

---

### 3.3 数据层（fetchers/* / etf_data.py）

#### 🔴 Critical
- [ ] **单位假设** — scale/amount 是"元"还是"亿"？是否有转换检查（`val < 10000` 判断）？
- [ ] **外部 API 超时** — `requests.get()` 必须设 `timeout`，否则可能卡死
- [ ] **缓存穿透** — 缓存失效时是否直接调外部 API？是否有降级数据？

#### 🟡 Warning
- [ ] **文件格式兼容** — 数据文件可能是 list 或 `{"etfs": []}`，两种都要兼容
- [ ] **快照回落** — 主数据文件坏了有没有 backup 路径？
- [ ] **字段映射** — WeStock/Wind/AKShare 字段名是否统一映射了？

---

## 四、审查流程

### 4.1 日常开发流程

```
修改代码 → git add → git commit → 自测（本地跑一次）
                               ↓
                        提交 PR / 请求审查
                               ↓
                          审查通过？
                         ↙         ↘
                       是           否
                        ↓           ↓
                    合并/部署      修改后重新审查
```

### 4.2 自测清单（提交前必做）

```bash
# 1. Python 代码是否可导入
python3 -c "import app; print('OK')"

# 2. 服务能否启动
python3 app.py &  # 启动后 curl localhost:5000/api/version

# 3. API 是否返回
curl -s http://localhost:5000/api/etfs?limit=1 | head -5

# 4. 对比页渲染
curl -s -o /dev/null -w "%{http_code}" "http://localhost:5000/compare?codes=510300,510500,159915"

# 5. 前端模板没有 Jinja2 语法错误（Flask 启动即检查）
```

### 4.3 典型 Bug 模式（历史教训）

| 模式 | 已发生次数 | 预防方法 |
|------|-----------|----------|
| SVG circle 缺 cx/cy | 1次 | 审查 SVG 元素必须显式指定圆心 |
| print(file=sys.stderr) BrokenPipeError | 1次 | 用 logging 或 try/except |
| 双重 renderHero() | 1次 | 检查 `setTimeout` + fetch 回调链 |
| 单位假设错误（万/亿/元混用） | 2次 | 统一在 `_normalize_units()` 处理 |
| 前端数字格式化溢出 | 1次 | review 表格列的 `fmtFn` |

---

## 五、Git 提交规范

```
格式: <类型>: <简短描述>

类型:
  feat    — 新功能
  fix     — 修 Bug
  refactor— 重构
  style   — 仅样式/格式
  docs    — 文档
  perf    — 性能优化
  chore   — 构建/工具

示例:
  feat: 对比页环形图改融合设计
  fix: circle 元素缺少 cx/cy 导致圆心偏移
  refactor: 统一数据单位标准化逻辑
```

---

## 六、如何执行审查

### 方式 A：手动审查（推荐当前阶段）

1. 修改完成后，Merge Request 中贴上 Checklist（复制第三节）
2. 逐项打勾检查
3. 标注 🔴/🟡/💭 问题
4. 修复后重新验证

### 方式 B：自动化辅助（后续可加）

- `pytest` — 后端单元测试（已有 `conftest.py`）
- 后续可引入 `flake8` / `black` 做风格检查

---

## 七、本文件的使用

- 每次 Review 前打开此文件，逐项过 Checklist
- 发现新的 Bug 模式，追加到"典型 Bug 模式"表中
- 审查者需在 PR 评论区贴上 Checklist 结果
