# 任务：用 WeStock Data 填补 ETF 缺失数据

## 任务背景

我们有一个 ETF 工具 MVP 项目，包含 1473 个 ETF 的标准数据文件 `etf_standard_data.json`。

**问题**：该文件中部分字段完整度很低（0-50%），需要从 WeStock Data 查询并填补这些缺失数据。

**目标**：使用 WeStock Data CLI 工具，查询 1473 个 ETF 的缺失字段，并填补到 `etf_standard_data.json` 中。

---

## 一、缺失字段清单（按优先级排序）

### 🔴 高优先级（完整度 0-1%，必须填补）

| 字段名 | 中文 | 完整度 | WeStock 来源 | WeStock 字段 |
|--------|------|--------|------------|------------|
| `custodian` | 托管人 | 0% | `etf` 命令 | `trusteeInstitution` |
| `tracking_error` | 跟踪误差% | 0% | 需计算或查其他源 | - |
| `valuation_percentile` | 估值分位数% | 0% | 需计算 | - |
| `fee_rate` | 总费率% | 0.1% | `etf` 命令 | 需计算(managementFee+custodyFee+serviceFee) |
| `net_inflow_5d` | 5日净流入亿元 | 0.1% | 需计算 | - |
| `net_inflow_ratio` | 净流入比例% | 0.1% | `etf` 命令 | `sharesChgRatio` |
| `net_inflow_shares` | 净份额流入亿份 | 0.1% | `etf` 命令 | `sharesChg` |
| `premium_discount` | 溢价折价% | 0.1% | `etf` 命令 | `disc` |
| `fee_rate_custody` | 托管费率% | 0.1% | `etf` 命令 | `custodyFee` |
| `fee_rate_management` | 管理费率% | 0.1% | `etf` 命令 | `managementFee` |
| `fee_rate_service` | 服务费率% | 0.1% | `etf` 命令 | `serviceFee` |

### 🟡 中优先级（完整度 6.7-49.8%，部分填补）

| 字段名 | 中文 | 完整度 | WeStock 来源 | WeStock 字段 |
|--------|------|--------|------------|------------|
| `benchmark` | 业绩基准 | 6.7% | `etf` 命令 | `trackIndexName` |
| `annual_3y` | 3年年化回报% | 49.8% | `etf` 命令 | `return3Y` |
| `year_3_return` | 3年回报率% | 49.8% | `etf` 命令 | `return3Y` |

### 🟢 低优先级（完整度 96.8-100%，可选填补）

| 字段名 | 中文 | 完整度 | WeStock 来源 | WeStock 字段 |
|--------|------|--------|------------|------------|
| `calmar_ratio` | 卡玛比率 | 96.8% | 需计算 | - |
| `sharpe_ratio` | 夏普比率 | 100% | 需计算 | - |
| `max_drawdown` | 最大回撤% | 100% | `etf` 命令 | `maxDrawdown1Y` |
| `annual_vol` | 年化波动率% | 100% | 需计算 | - |

---

## 二、WeStock Data 工具使用说明

### 1. 环境要求
- **Node.js**: >= v18
- **CLI 路径**: `/Users/apangduo/.workbuddy/plugins/marketplaces/cb_teams_marketplace/plugins/finance-data/skills/westock-data/scripts/index.js`
- **运行方式**: `node <CLI路径> <命令> <参数>`

### 2. 核心命令：`etf`（ETF 详情）

**命令格式**：
```bash
node /Users/apangduo/.workbuddy/plugins/marketplaces/cb_teams_marketplace/plugins/finance-data/skills/westock-data/scripts/index.js etf <ETF代码>
```

**批量查询**（最多10个代码，逗号分隔)：
```bash
node <CLI路径> etf sh510300,sh510500,sz159915
```

**返回格式**：Markdown 表格，包含以下字段（部分）：

| WeStock 字段 | 说明 | 对应我们的字段 |
|-------------|------|---------------|
| `trusteeInstitution` | 托管人 | `custodian` |
| `managementFee` | 管理费率(%) | `fee_rate_management` / `management_fee_rate` |
| `custodyFee` | 托管费率(%) | `fee_rate_custody` / `custody_fee_rate` |
| `serviceFee` | 销售服务费率(%) | `fee_rate_service` |
| `disc` | 溢折率(%) | `premium_discount` |
| `sharesChg` | 净申购份额 | `net_inflow_shares` |
| `sharesChgRatio` | 净申购比例(%) | `net_inflow_ratio` |
| `return1Y` | 近1年收益率(%) | `year_1_return` |
| `return3Y` | 近3年收益率(%) | `year_3_return` / `annual_3y` |
| `maxDrawdown1Y` | 近1年最大回撤(%) | `max_drawdown` |
| `trackIndexCode` | 跟踪指数代码 | - |
| `trackIndexName` | 跟踪指数名称 | `benchmark` |
| `establishDate` | 成立日期 | `issue_date` |
| `manageInstitution` | 管理人 | `issuer` |

### 3. 其他有用命令

#### `etf-holdings`（ETF 持仓明细）
```bash
node <CLI路径> etf-holdings sh510300
```
返回：前十大持仓股票列表（代码、名称、占比%）

#### `etf-nav`（ETF 净值历史）
```bash
node <CLI路径> etf-nav sh510300 --start 2026-01-01 --end 2026-05-23
```
返回：历史净值数据（日期、净值、涨跌幅%）

#### `etf-company`（ETF 公司信息）
```bash
node <CLI路径> etf-company sh510300
```
返回：基金公司详细信息

#### `etf-holders`（ETF 持有人结构）
```bash
node <CLI路径> etf-holders sh510300
```
返回：持有人结构（机构持有%、个人持有%等）

#### `etf-financial`（ETF 财务指标）
```bash
node <CLI路径> etf-financial sh510300
```
返回：财务指标（ROE、毛利率等）

---

## 三、执行步骤

### 步骤 1：准备 ETF 代码列表

1. 读取 `/Users/apangduo/WorkBuddy/Claw/etf-tool-mvp/etf_standard_data.json`
2. 提取所有 ETF 的代码（code 字段）
3. 转换为 WeStock 格式（沪市：`sh` + 6位数字，如 `sh510300`；深市：`sz` + 6位数字，如 `sz159915`）

**代码示例**（Python）：
```python
import json

with open('etf_standard_data.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# 假设数据是 [{"code": "510300", "market": "sh"}, ...]
etf_list = data if isinstance(data, list) else data.get('etfs', [])

# 转换为 WeStock 代码格式
westock_codes = []
for etf in etf_list:
    code = etf['code']
    market = etf.get('market', 'sh')  # 默认沪市
    westock_code = f"{market}{code}"
    westock_codes.append(westock_code)

print(f"总计 {len(westock_codes)} 个 ETF")
print(f"示例：{westock_codes[:5]}")
```

### 步骤 2：批量查询 WeStock Data

**策略**：每次查询 10 个 ETF（WeStock 批量查询上限），循环处理全部 1473 个。

**伪代码**：
```python
import subprocess
import json
import time

BATCH_SIZE = 10
CLI_PATH = "/Users/apangduo/.workbuddy/plugins/marketplaces/cb_teams_marketplace/plugins/finance-data/skills/westock-data/scripts/index.js"

results = []
for i in range(0, len(westock_codes), BATCH_SIZE):
    batch = westock_codes[i:i+BATCH_SIZE]
    batch_str = ",".join(batch)
    
    # 调用 WeStock CLI
    cmd = ["node", CLI_PATH, "etf", batch_str]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    
    if result.returncode == 0:
        # 解析 Markdown 表格输出
        parsed = parse_markdown_table(result.stdout)
        results.extend(parsed)
    else:
        print(f"❌ 批次 {i//BATCH_SIZE + 1} 失败: {result.stderr}")
    
    # 避免请求过快，暂停 1 秒
    time.sleep(1)
    
    print(f"进度: {min(i+BATCH_SIZE, len(westock_codes))}/{len(westock_codes)}")

print(f"✅ 查询完成，成功 {len(results)} 个 ETF")
```

### 步骤 3：解析 WeStock 返回数据

WeStock CLI 返回 Markdown 表格，需要解析并映射到我们的字段。

**解析示例**（Python，使用 `pandas` 或手动解析）：

```python
import re

def parse_markdown_table(markdown_text):
    """解析 WeStock CLI 返回的 Markdown 表格"""
    lines = markdown_text.strip().split('\n')
    
    # 找到表格开始（第一个 | 行）
    table_start = -1
    for i, line in enumerate(lines):
        if line.startswith('|') and 'code' in line.lower():
            table_start = i
            break
    
    if table_start == -1:
        return []
    
    # 解析表头
    headers = [h.strip() for h in lines[table_start].split('|')[1:-1]]
    
    # 解析数据行
    rows = []
    for line in lines[table_start+2:]:  # 跳过分隔线
        if not line.startswith('|'):
            break
        values = [v.strip() for v in line.split('|')[1:-1]]
        row = dict(zip(headers, values))
        rows.append(row)
    
    return rows
```

### 步骤 4：字段映射（WeStock → 我们的格式）

```python
def map_westock_to_our(westock_data):
    """将 WeStock 数据映射到我们的字段格式"""
    our_data = {}
    
    # 直接映射
    if 'trusteeInstitution' in westock_data:
        our_data['custodian'] = westock_data['trusteeInstitution']
    
    if 'managementFee' in westock_data:
        our_data['fee_rate_management'] = float(westock_data['managementFee'])
    
    if 'custodyFee' in westock_data:
        our_data['fee_rate_custody'] = float(westock_data['custodyFee'])
    
    if 'serviceFee' in westock_data:
        our_data['fee_rate_service'] = float(westock_data['serviceFee'])
    
    if 'disc' in westock_data:
        our_data['premium_discount'] = float(westock_data['disc'])
    
    if 'sharesChg' in westock_data:
        our_data['net_inflow_shares'] = float(westock_data['sharesChg'])
    
    if 'sharesChgRatio' in westock_data:
        our_data['net_inflow_ratio'] = float(westock_data['sharesChgRatio'])
    
    if 'return3Y' in westock_data:
        our_data['year_3_return'] = float(westock_data['return3Y'])
        our_data['annual_3y'] = float(westock_data['return3Y'])
    
    if 'trackIndexName' in westock_data:
        our_data['benchmark'] = westock_data['trackIndexName']
    
    # 计算总费率
    mgmt = float(westock_data.get('managementFee', 0))
    custody = float(westock_data.get('custodyFee', 0))
    service = float(westock_data.get('serviceFee', 0))
    our_data['fee_rate'] = mgmt + custody + service
    
    return our_data
```

### 步骤 5：填补到 `etf_standard_data.json`

```python
def fill_missing_data(original_data, westock_results):
    """将 WeStock 查询结果填补到原始数据"""
    # 建立 code → WeStock 数据的映射
    westock_map = {item['code']: item for item in westock_results}
    
    filled_count = 0
    for etf in original_data:
        code = etf['code']
        if code in westock_map:
            westock_data = westock_map[code]
            our_data = map_westock_to_our(westock_data)
            
            # 填补缺失字段
            for key, value in our_data.items():
                if key not in etf or etf[key] is None or etf[key] == '':
                    etf[key] = value
                    filled_count += 1
    
    print(f"✅ 填补完成，共填补 {filled_count} 个字段")
    return original_data
```

### 步骤 6：保存并验证

```python
# 保存填补后的数据
with open('etf_standard_data_filled.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

# 验证完整度
print("验证完整度...")
for field in ['custodian', 'fee_rate', 'benchmark', 'tracking_error']:
    non_empty = sum(1 for etf in data if etf.get(field))
    completeness = non_empty / len(data) * 100
    print(f"  {field}: {non_empty}/{len(data)} ({completeness:.1f}%)")
```

---

## 四、注意事项

### 1. API 限制
- **批量查询上限**：每次最多 10 个 ETF 代码
- **请求频率**：建议每次请求后暂停 1-2 秒，避免被限流
- **超时设置**：单个请求超时设为 30 秒

### 2. 数据质量
- **字段缺失**：WeStock 可能不返回某些字段（该 ETF 无数据），需检查并处理
- **数据格式**：WeStock 返回的是字符串，需转换为数值类型
- **异常值**：注意 `-`、`N/A`、空字符串等异常情况

### 3. 计算字段（暂时无法从 WeStock 获取）
以下字段需要复杂计算或其他数据源，本次任务**暂不处理**：
- `tracking_error`（跟踪误差）：需要历史净值数据 + 基准数据计算
- `valuation_percentile`（估值分位数）：需要历史净值 + 统计计算
- `sharpe_ratio`（夏普比率）：需要无风险利率 + 收益率计算
- `calmar_ratio`（卡玛比率）：需要最大回撤 + 年化回报计算
- `annual_vol`（年化波动率）：需要日收益率序列计算
- `net_inflow_5d`（5日净流入）：需要份额变动数据计算

### 4. 代码格式转换
- 沪市 ETF：`sh` + 6位数字（如 `sh510300`）
- 深市 ETF：`sz` + 6位数字（如 `sz159915`）
- **注意**：原始数据中的 `code` 字段可能不带市场前缀，需根据 `market` 字段或猜测添加

---

## 五、验收标准

完成任务后，需满足以下标准：

### 1. 数据完整度提升

| 字段 | 填补前完整度 | 目标完整度 | 验收标准 |
|------|--------------|------------|----------|
| `custodian` | 0% | ≥90% | 至少 1325/1473 个 ETF 有数据 |
| `fee_rate` | 0.1% | ≥80% | 至少 1178/1473 个 ETF 有数据 |
| `benchmark` | 6.7% | ≥80% | 至少 1178/1473 个 ETF 有数据 |
| `annual_3y` | 49.8% | ≥80% | 至少 1178/1473 个 ETF 有数据 |
| `year_3_return` | 49.8% | ≥80% | 至少 1178/1473 个 ETF 有数据 |
| `premium_discount` | 0.1% | ≥70% | 至少 1031/1473 个 ETF 有数据 |
| `net_inflow_shares` | 0.1% | ≥70% | 至少 1031/1473 个 ETF 有数据 |
| `net_inflow_ratio` | 0.1% | ≥70% | 至少 1031/1473 个 ETF 有数据 |

### 2. 数据格式正确
- 数值字段为 `float` 类型（不是字符串）
- 百分比字段为小数形式（如 `0.95` 表示 0.95%，不是 `0.95%`）
- 文本字段为 `str` 类型，空值用 `""` 而不是 `None`

### 3. 输出文件
- 填补后的数据保存为：`etf_standard_data_filled.json`
- 数据格式与原始文件兼容（相同的结构）
- 文件大小合理（不应比原始文件大太多）

### 4. 日志记录
- 记录查询进度（已查询 X/1473 个 ETF）
- 记录失败批次（哪些 ETF 查询失败）
- 记录填补统计（共填补 Y 个字段）

---

## 六、交付物

完成任务后，需交付以下文件：

1. **`etf_standard_data_filled.json`**：填补后的完整数据文件
2. **`fill_report.md`**：填补报告，包含：
   - 查询耗时
   - 成功/失败统计
   - 完整度对比（填补前 vs 填补后）
   - 遇到的问题及解决方案
3. **`fill_script.py`**（可选）：填补脚本，方便后续重新运行

---

## 七、常见问题

### Q1: WeStock CLI 查询失败怎么办？
**A**: 记录失败的 ETF 代码，稍后重试。可能是网络问题或 API 限流。

### Q2: 某些 ETF 在 WeStock 中查不到数据？
**A**: 可能是 ETF 代码格式错误（如市场前缀错误），或该 ETF 不在 WeStock 数据库中。记录这些 ETF，后续人工检查。

### Q3: 填补后的数据有问题（如费率=0）？
**A**: 检查 WeStock 原始返回数据。如果 WeStock 返回的就是 0，可能是该 ETF 确实费率为 0，或是数据质量问题。记录并标记这些异常值。

### Q4: 运行时间太长（1473 个 ETF × 每批 10 个 = 148 批次 × 1秒/批 = 约 2.5 分钟）？
**A**: 可以接受。如果想加速，可以增加并发（但注意 API 限流）。或者先用小样本测试（如前 100 个 ETF）。

---

## 八、联系信息

如有疑问，联系项目维护者：
- **项目路径**：`/Users/apangduo/WorkBuddy/Claw/etf-tool-mvp/`
- **数据文件**：`etf_standard_data.json`
- **WeStock CLI**：`/Users/apangduo/.workbuddy/plugins/marketplaces/cb_teams_marketplace/plugins/finance-data/skills/westock-data/scripts/index.js`

---

**祝任务顺利！🚀**
