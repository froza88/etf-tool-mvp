# 代码审查报告 — ETF Tool MVP

审查日期：2026-05-25 | 审查范围：app.py / etf_data.py / templates/compare_v3.html

---

## 一、🔴 Critical（必须修）

### C1. app.py `get_etf_history`：模拟数据不稳定
**位置**：app.py 第 437-441 行
```python
for i in range(limit):
    volatility = 0.02
    randomReturn = (math.sin(i * 0.1) * 0.01) + daily_return + (math.cos(i * 0.3) * 0.005)
```
**问题**：用 `math.sin/cos` 伪随机有周期性，多次访问不同 ETF 会得到相同的"伪走势"。
**建议**：用 `random.seed(code)` 让每只 ETF 的走势不同，或直接返回明确标明"模拟数据"的错误码。

### C2. app.py `sync_data`：shell 命令注入风险
**位置**：app.py 第 499 行
```python
cmd = f'{cli} mcp call GetBatchFundPerformance --input \'{{"fundCodes":["{code}"]}}\' 2>/dev/null'
```
**问题**：`{code}` 直接拼接到 shell 命令中。虽然当前 code 来自 URL 路由（已验证格式），但这种模式不安全。
**建议**：用 `subprocess.run([cli, "mcp", "call", ...])` 数组形式避免 shell 注入，或对 code 做格式校验。

### C3. `print(file=sys.stderr)` 仍有残留
**位置**：etf_data.py 第 55、75、78、87、101、106 行
**问题**：第 49-52 行我加了 try/except，但其他 print 还是裸调用，Flask reloader 下同样会 BrokenPipeError。
**建议**：统一替换为 logging，或全局加一层 safe_stderr。

---

## 二、🟡 Warning（建议修）

### W1. app.py：路由重复
**位置**：第 131、155 行
```python
@app.route('/compare')       # 分发到 compare_v3.html
@app.route('/compare/v3')    # 也分发到 compare_v3.html
```
**问题**：两个路由用同一个模板，代码完全相同。容易被误认为不同功能。
**建议**：一个路由 redirect 到另一个，或删除 `/compare/v3`。

### W2. etf_data.py：筛选函数逐层 if 可读性差
**位置**：第 157-180 行
**问题**：`filter_etfs()` 用 8 个 if/continue 串联，随着筛选条件增加会越来越乱。
**建议**：用 filter 函数列表模式：
```python
filters_handlers = {
    "type": lambda e: e.get("type") == filters["type"],
    "scale_min": lambda e: (e.get("scale") or 0) >= float(filters["scale_min"]),
    ...
}
for etf in etfs:
    if all(handler(etf) for key, handler in filters_handlers.items() if key in filters):
        result.append(etf)
```

### W3. compare_v3.html：双重 renderHero 历史遗留
**位置**：第 ~540 行（loadData）和第 ~560 行（updateWithL2Data）
**背景**：初始数据来一次 → L2 来一次。虽然现在 L2 改为直接改 DOM，但代码路径中还有 `renderHero()` 的守卫逻辑。
**建议**：确认 L2 不再走 `renderHero()` 路径后，删掉 `renderHero(false)` 分支。

### W4. 前端数据状态管理
**问题**：`etfs` 是全局变量，`updateWithL2Data` 直接修改它，但代码中多处使用了 `etfs[idx]` 引用，如果 idx 错位会数据混乱。
**建议**：用 `data-code` 属性在 JS 中通过 code 查找，不用索引匹配。

### W5. GSAP CDN 单点故障
**位置**：compare_v3.html `<head>` 中 CDN 引入
**问题**：CDN 挂了动画就没了。虽然有降级逻辑（`typeof gsap === 'undefined'`），但降级直接用 setAttribute 没有过渡。
**建议**：把 GSAP 的 `from`→`to` 逻辑封装成独立函数，降级时用 CSS transition 替代完全无动画。

---

## 三、💭 Nit（可优化）

### N1. app.py `get_risk_api` 嵌套太深
第 470-486 行两层遍历 + 四层字典嵌套 + 多级 try/except。建议抽出子函数。

### N2. 魔数 "200000000000"
compare_v3.html 中 `RING_TOTAL = 200000000000`（2000亿）出现多次且硬编码。如果未来调整这个基准值，要改 6-7 处。建议定义为常量。

### N3. etf_data.py `_normalize_units` 的 magic number
`< 10000` 的判断假设 scale 不可能小于 1万元。但微型 ETF 规模可能真小于 1亿（比如新成立 ETF 0.5亿）。
**建议**：`< 10000` 改为 `< 100000`（10万）更安全，避免误判。

---

## 四、✅ 做得好的

1. **etf_data.py**：多级加载策略（快照→标准→过期→回退），防崩溃
2. **app.py**：`get_default_service()` 缓存 + mtime 校验，避免重复创建服务
3. **app.py**：API 降级链路清晰（westock → local → fallback）
4. **compare_v3.html**：`data-*` 属性选择器 + GSAP 动画，DOM 操作精准
5. **updateWithL2Data**：直接改 DOM 属性避免闪屏的设计方向正确（比重新渲染强多了）

---

## 五、优先级建议

| 优先级 | 编号 | 预计耗时 |
|--------|------|----------|
| 🔴 立即修 | C1 | 5分钟 |
| 🔴 立即修 | C2 | 5分钟 |
| 🔴 本周修 | C3 | 10分钟 |
| 🟡 本周修 | W1, W4 | 10分钟 |
| 🟡 有空修 | W2, W3, W5 | 20分钟 |
| 💭 随缘 | N1, N2, N3 | 10分钟 |
