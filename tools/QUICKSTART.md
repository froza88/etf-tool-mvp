# 对比小工具 - 快速套用指南

## 🎯 目标

快速创建新的数据源对比工具，无需从零开始。

## 📁 文件结构

```
tools/
├── template_compare_tool.html   # 通用模板（套用时复制此文件）
├── akshare_etf_compare.html   # AKShare工具（示例1）
├── wind_etf_compare.html      # Wind工具（示例2）
├── westock_etf_compare.html   # WeStock工具（示例3）
├── baostock_etf_compare.html  # Baostock工具（示例4）
├── tushare_etf_compare.html   # Tushare工具（示例5）
├── adata_etf_compare.html     # adata工具（示例6）
└── README.md                  # 使用文档
```

## 🚀 套用步骤（3分钟搞定）

### 步骤1：复制模板

```bash
cp template_compare_tool.html {new_source}_etf_compare.html
```

**示例**：创建"Yahoo Finance"对比工具
```bash
cp template_compare_tool.html yahoo_etf_compare.html
```

### 步骤2：修改3个地方

用文本编辑器打开新文件，修改以下3处：

#### 2.1 修改标题和描述（第5-11行）

```html
<title>{DATA_SOURCE} ETF对比工具</title>  <!-- 改这里 -->
...
<h1>{DATA_SOURCE} ETF 对比工具</h1>  <!-- 改这里 -->
<div class="subtitle">数据源：{DATA_SOURCE_DESCRIPTION}</div>  <!-- 改这里 -->
```

**示例**（Yahoo Finance）：
```html
<title>Yahoo Finance ETF对比工具</title>
...
<h1>Yahoo Finance ETF 对比工具</h1>
<div class="subtitle">数据源：Yahoo Finance - 全球ETF数据、免费、实时</div>
```

#### 2.2 修改模拟数据（第75-120行）

找到 `MOCK_DATA` 对象，修改：
- `data` 数组：改成你的数据源实际字段
- `fields` 数组：列名列表

**示例**（Yahoo Finance）：
```javascript
const MOCK_DATA = {
    "success": true,
    "count": 2,
    "data": [
        {
            "代码": "SPY",
            "名称": "S&P 500 ETF",
            "最新价": 450.5,
            "涨跌幅": 1.2,
            "成交量": 89000000,
            "市盈率": 22.5,
            "股息率": 1.5
        },
        // ... 更多模拟数据
    ],
    "fields": ["代码", "名称", "最新价", "涨跌幅", "成交量", "市盈率", "股息率"],
    "update_time": new Date().toISOString()
};
```

#### 2.3 修改API端点（第60行）

```javascript
const API_ENDPOINT = "{API_ENDPOINT}";  // 改成你的真实API地址
```

**示例**（Yahoo Finance）：
```javascript
const API_ENDPOINT = "/api/yahoo/etf/compare";
```

### 步骤3：测试

用浏览器打开HTML文件，输入测试代码，点击"对比"按钮。

**如果看到表格**：✅ 成功！
**如果报错**：检查浏览器控制台（F12），确认模拟数据格式正确。

## 🔧 进阶定制（可选）

### 定制字段格式化

修改 `formatCellValue()` 函数（第180行），添加你的字段格式化逻辑。

**示例**：Yahoo Finance使用美元，需要显示"$"符号
```javascript
function formatCellValue(field, value) {
    if (field === '最新价' || field === '市值') {
        return '$' + value.toFixed(2);  // 添加$符号
    }
    // ... 其他格式化逻辑
}
```

### 定制单元格样式

修改 `getCellClass()` 函数（第165行），添加你的样式逻辑。

**示例**：Yahoo Finance涨跌幅使用美国惯例（绿涨红跌）
```javascript
function getCellClass(field, value) {
    if (field.includes('涨') || field.includes('跌')) {
        return value > 0 ? 'negative' : 'positive';  // 美国惯例：绿涨红跌
    }
    return '';
}
```

### 连接真实API

修改 `USE_MOCK` 变量（第61行）为 `false`，然后实现 `fetchRealData()` 函数（第130行）。

**示例**：
```javascript
const USE_MOCK = false;  // 改为false，使用真实API

async function fetchRealData(codes) {
    const response = await fetch(`/api/yahoo/etf/compare?codes=${codes.join(',')}`);
    if (!response.ok) throw new Error('API请求失败');
    return await response.json();
}
```

## 📊 字段设计建议

### 好的字段设计原则

1. **对比维度清晰**：用户能一眼看出差异
2. **数据类型丰富**：价格、涨跌、估值、风险都要有
3. **数据真实可获取**：不要设计无法获取的字段
4. **格式化友好**：数字、百分比、日期要正确格式化

### 常见ETF对比维度

| 维度 | 字段示例 | 数据来源 |
|------|----------|----------|
| **价格交易** | 最新价、涨跌幅、成交量、成交额、换手率 | AKShare、WeStock、Baostock |
| **估值指标** | 市盈率PE、市净率PB、股息率、净资产 | Tushare、Wind |
| **风险指标** | 波动率、夏普比率、最大回撤、卡玛比率 | Wind、盈米 |
| **资金流向** | 净流入额、净流入比例、大单净流入 | WeStock、东方财富 |
| **持仓结构** | 前十大持仓、行业分布、个股占比 | Wind、AKShare |
| **基金信息** | 管理费、托管费、跟踪误差、基金规模 | Tushare、Wind |

## 🎨 样式定制（可选）

### 修改主题色

修改CSS中的 `background` 颜色（第16行）：

```css
button { 
    background: #1890ff;  /* 蓝色主题 */
    /* 改成你的品牌色，例如：#ff6b6b（红色）、#51cf66（绿色）*/
}
```

### 修改表格样式

修改 `th`、`td` 的样式（第16-17行）：

```css
th {
    background: #fafafa;  /* 表头背景 */
    color: #333;          /* 表头文字颜色 */
}
td {
    padding: 8px 12px;  /* 单元格内边距 */
    font-size: 13px;     /* 字体大小 */
}
```

## ❓ 常见问题

### Q1：如何添加排序功能？

A：修改 `sortTable()` 函数（第195行），实现数组排序逻辑。参考代码：

```javascript
let sortField = null;
let sortAsc = true;

function sortTable(field) {
    if (sortField === field) {
        sortAsc = !sortAsc;  // 切换升序/降序
    } else {
        sortField = field;
        sortAsc = true;
    }
    
    // 对data数组排序
    comparisonData.data.sort((a, b) => {
        const valA = a[field];
        const valB = b[field];
        if (sortAsc) {
            return valA > valB ? 1 : -1;
        } else {
            return valA < valB ? 1 : -1;
        }
    });
    
    renderTable(comparisonData);  // 重新渲染
}
```

### Q2：如何添加筛选功能？

A：在表格上方添加筛选输入框，修改 `renderTable()` 函数，只渲染符合条件的行。

### Q3：如何导出Excel？

A：使用 `SheetJS` 库，或调用后端API生成Excel文件。参考代码：

```javascript
function exportExcel() {
    // 需要使用SheetJS库（xlsx.full.min.js）
    const ws = XLSX.utils.table_to_sheet(document.getElementById('comparisonTable'));
    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, "ETF对比");
    XLSX.writeFile(wb, "etf_compare.xlsx");
}
```

## 📞 联系支持

遇到问题？联系：apangduo

---

**快速套用，3分钟创建新工具！** 🚀
