# ETF对比工具集 - Tools/

## 📊 工具列表

| 工具 | 文件 | 数据源 | 对比维度 | 状态 |
|------|------|--------|----------|------|
| **AKShare ETF对比** | `akshare_etf_compare.html` | AKShare（免费开源） | 37个实时行情字段（价格、涨跌、成交、市值、资金流） | ✅ Demo |
| **Wind ETF对比** | `wind_etf_compare.html` | Wind（付费终端） | 13个深度指标（夏普、波动率、最大回撤、资金流、持有人结构） | ✅ Demo |
| **WeStock ETF对比** | `westock_etf_compare.html` | WeStock Data（腾讯自选股） | 20个字段（行情、估值、风险、费率） | ✅ Demo |
| **Baostock ETF对比** | `baostock_etf_compare.html` | Baostock（开源API+本地存储） | 18个字段（日线、财务、市值、盈利能力） | ✅ Demo |
| **Tushare ETF对比** | `tushare_etf_compare.html` | Tushare（需Token） | 19个字段（净值、增长率、份额、费率） | ✅ Demo |
| **adata ETF对比** | `adata_etf_compare.html` | adata（多源融合） | 18个字段（行情、估值、风险、数据来源） | ✅ Demo |

## 🎯 设计理念

**核心原则**：每个数据源独立对比，不融合、不增强、只客观展示该数据源能提供的对比维度。

**优势**：
1. **开发快**：每个工具独立，无需复杂的数据融合逻辑
2. **客观**：用户能看到每个数据源的真实能力边界
3. **可组合**：用户想要全面对比，可以自己打开多个工具横向参考
4. **不阻塞**：不需要等"所有数据源融合完成"才能发布

## 🚀 如何使用

### 演示模式（立即体验）

1. 用浏览器打开任意 `tools/*_etf_compare.html` 文件
2. 输入ETF代码（如 `510300, 510500`），点击"对比"
3. 查看对比结果（当前为模拟数据）

### 连接真实API（需要部署后端）

每个工具都有 `USE_MOCK` 变量（第61行）：
- `true` = 使用模拟数据（默认，可立即演示）
- `false` = 调用真实API（需要后端支持）

**后端部署示例**（以AKShare为例）：
```bash
# 1. 安装依赖
pip install akshare flask

# 2. 启动后端
python3 tools/akshare_backend.py

# 3. 访问前端
open http://localhost:8888
```

## 📁 文件结构

```
etf-tool-mvp/tools/
├── template_compare_tool.html   # 通用模板（快速套用）
├── akshare_etf_compare.html   # AKShare前端（可独立打开）
├── akshare_backend.py          # AKShare后端（Flask）
├── wind_etf_compare.html      # Wind前端（可独立打开）
├── westock_etf_compare.html   # WeStock前端（可独立打开）
├── baostock_etf_compare.html  # Baostock前端（可独立打开）
├── tushare_etf_compare.html   # Tushare前端（可独立打开）
├── adata_etf_compare.html     # adata前端（可独立打开）
├── QUICKSTART.md              # 快速套用指南（3分钟创建新工具）
└── README.md                  # 本文档
```

## 🔧 快速套用（创建新工具）

**场景**：你想添加一个新的数据源对比工具（如Yahoo Finance、Alpha Vantage等）。

**时间**：3分钟

**步骤**：
1. 复制 `template_compare_tool.html` 为新文件
2. 修改3个地方：标题描述、模拟数据、API端点
3. 测试：用浏览器打开，输入测试代码

**详细指南**：阅读 `QUICKSTART.md`

## 📊 数据源对比

| 数据源 | 免费/付费 | 实时/延时 | 字段丰富度 | 本地存储 | 推荐场景 |
|--------|------------|-------------|------------|----------|----------|
| **AKShare** | 免费 | 实时 | ⭐⭐⭐⭐⭐ | ❌ | 快速原型、公开数据 |
| **Wind** | 付费 | 实时 | ⭐⭐⭐⭐⭐ | ✅ | 专业分析、深度指标 |
| **WeStock** | 免费 | 实时 | ⭐⭐⭐⭐ | ❌ | 腾讯生态、行情数据 |
| **Baostock** | 免费 | 日线 | ⭐⭐⭐ | ✅ (Parquet) | 历史回测、本地分析 |
| **Tushare** | 付费 | 实时 | ⭐⭐⭐⭐ | ❌ (需自建) | 量化研究、财务数据 |
| **adata** | 免费 | 实时 | ⭐⭐⭐ | ❌ | 多源融合、代理支持 |

## 🎨 UI定制

### 修改主题色

编辑HTML文件，修改CSS中的 `background` 颜色：

```css
button { 
    background: #1890ff;  /* 改成你的品牌色 */
}
```

### 修改表格字段

编辑HTML文件，修改 `MOCK_DATA.fields` 数组（第85行）：

```javascript
"fields": ["代码", "名称", "最新价", "涨跌幅"],  // 改成你想要的字段
```

### 修改模拟数据

编辑HTML文件，修改 `MOCK_DATA.data` 数组（第75行）：

```javascript
"data": [
    {
        "代码": "510300",
        "名称": "沪深300ETF",
        "最新价": 4.05,
        // ... 添加更多字段
    }
]
```

## 🔗 集成到主应用

**方式1：iframe嵌入**

在主应用（Flask）中添加路由：

```python
@app.route('/tools/akshare')
def tools_akshare():
    return render_template('tools/akshare_etf_compare.html')
```

**方式2：独立部署**

将 `tools/` 目录部署到静态服务器（如PythonAnywhere、Netlify、Vercel）。

**方式3：本地打开**

直接用浏览器打开HTML文件（`file://` 协议），无需服务器。

## ❓ 常见问题

### Q1：为什么表格没有数据？

A：检查浏览器控制台（F12），确认：
- `USE_MOCK` 是否为 `true`（使用模拟数据）
- 模拟数据格式是否正确（`MOCK_DATA` 对象结构）

### Q2：如何连接真实API？

A：修改 `USE_MOCK` 为 `false`，然后实现 `fetchRealData()` 函数（第130行）。

### Q3：如何添加排序/筛选/导出功能？

A：参考 `QUICKSTART.md` 的"进阶定制"章节。

## 📞 联系支持

遇到问题？联系：apangduo

---

**6个对比工具，随时套用，3分钟创建新工具！** 🚀
