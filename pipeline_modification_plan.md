# Pipeline.py 修改方案：使用新的频率文件结构

生成时间: 2026-05-28 23:50
状态: 设计方案

---

## 一、当前问题

### 现有架构（有问题）
- **单文件存储**: `etf_standard_data.json` (1.7MB~6.6MB)
- **全量重建**: `step_build()` 每次从头构建，导致数据丢失
- **数据丢失**: `year_3_return` 从 79.9% 跌到 49.6%

### 新版架构（目标）
- **5个频率文件**: 按更新频率拆分，增量更新
- **增量合并**: 每次只更新变化的字段，不覆盖已有数据
- **数据完整**: 从备份恢复，保证数据完整性

---

## 二、新文件结构

### 文件列表
1. **etf_static.json** (239KB) - 长期不变数据
   - 字段: code, name, issuer, issue_date, custodian, category, management_fee_rate, custody_fee_rate, fee_rate, track_index_code, track_index_name
   - 更新频率: 手动/年度
   - ETF数量: 1470 (100%)

2. **etf_annual.json** (120KB) - 年度变化数据
   - 字段: code, year_1_return, year_3_return, ytd_return, ytd_max_drawdown, annual_3y, index_1y_return
   - 更新频率: 年度
   - ETF数量: 1470 (100%)

3. **etf_quarterly.json** (596KB) - 季度变化数据
   - 字段: code, top_holdings
   - 更新频率: 季度
   - ETF数量: 1470 (100%)

4. **etf_monthly.json** (2B, 空) - 月度变化数据
   - 字段: code, return_1m, return_3m, return_6m
   - 更新频率: 月度
   - ETF数量: 0 (待补充)

5. **etf_daily.json** (350KB) - 日度变化数据
   - 字段: code, scale, shares, close, prev_close, change_rate, change_pct, max_drawdown, sharpe_ratio, annual_vol, calmar_ratio, max_drawdown_1m, max_drawdown_3m, max_drawdown_6m, max_drawdown_1y, max_drawdown_3y, turnover_rate, turnover_value, discount_ratio, stock_ratio
   - 更新频率: 日度
   - ETF数量: 1470 (100%)

---

## 三、修改方案

### 3.1 数据读取（load_etf_data）
**当前实现**:
```python
def load_etf_data():
    with open('etf_standard_data.json', 'r') as f:
        return json.load(f)
```

**新实现**:
```python
def load_etf_data():
    """从5个频率文件加载数据，合并成完整ETF列表"""
    frequency_files = [
        'etf_static.json',
        'etf_annual.json',
        'etf_quarterly.json',
        'etf_monthly.json',
        'etf_daily.json'
    ]
    
    # 以etf_static.json为基准（包含所有ETF的code）
    with open('etf_static.json', 'r', encoding='utf-8') as f:
        etf_list = json.load(f)
    
    # 创建code->index映射
    code_index = {etf['code']: i for i, etf in enumerate(etf_list)}
    
    # 从其他频率文件合并数据
    for freq_file in frequency_files[1:]:  # 跳过etf_static.json
        if not os.path.exists(freq_file):
            continue
        
        with open(freq_file, 'r', encoding='utf-8') as f:
            freq_data = json.load(f)
        
        # 合并到etf_list
        for freq_etf in freq_data:
            code = freq_etf.get('code')
            if code in code_index:
                idx = code_index[code]
                # 增量合并：只填充缺失字段
                for key, value in freq_etf.items():
                    if key == 'code':
                        continue
                    if key not in etf_list[idx] or etf_list[idx][key] is None or etf_list[idx][key] == '':
                        etf_list[idx][key] = value
    
    return etf_list
```

### 3.2 数据保存（save_etf_data）
**当前实现**:
```python
def save_etf_data(etf_list):
    with open('etf_standard_data.json', 'w') as f:
        json.dump(etf_list, f, ensure_ascii=False, indent=2)
```

**新实现**:
```python
def save_etf_data(etf_list):
    """将ETF数据按频率拆分，保存到5个文件"""
    frequency_files = {
        'etf_static.json': ['code', 'name', 'issuer', 'issue_date', 'custodian', 'category', 'management_fee_rate', 'custody_fee_rate', 'fee_rate', 'track_index_code', 'track_index_name'],
        'etf_annual.json': ['code', 'year_1_return', 'year_3_return', 'ytd_return', 'ytd_max_drawdown', 'annual_3y', 'index_1y_return'],
        'etf_quarterly.json': ['code', 'top_holdings'],
        'etf_monthly.json': ['code', 'return_1m', 'return_3m', 'return_6m'],
        'etf_daily.json': ['code', 'scale', 'shares', 'close', 'prev_close', 'change_rate', 'change_pct', 'max_drawdown', 'sharpe_ratio', 'annual_vol', 'calmar_ratio', 'max_drawdown_1m', 'max_drawdown_3m', 'max_drawdown_6m', 'max_drawdown_1y', 'max_drawdown_3y', 'turnover_rate', 'turnover_value', 'discount_ratio', 'stock_ratio']
    }
    
    for filename, fields in frequency_files.items():
        # 提取对应字段
        freq_data = []
        for etf in etf_list:
            freq_etf = {field: etf.get(field) for field in fields}
            freq_data.append(freq_etf)
        
        # 保存
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(freq_data, f, ensure_ascii=False, indent=2)
        
        print(f"✅ 保存 {filename}: {len(freq_data)} 只ETF")
```

### 3.3 增量更新（update_etf_data）
**新增功能**: 增量更新单个ETF的数据
```python
def update_etf_data(code, new_data, frequency='daily'):
    """增量更新单个ETF的数据到指定频率文件"""
    # 确定文件名
    filename_map = {
        'static': 'etf_static.json',
        'annual': 'etf_annual.json',
        'quarterly': 'etf_quarterly.json',
        'monthly': 'etf_monthly.json',
        'daily': 'etf_daily.json'
    }
    filename = filename_map.get(frequency, 'etf_daily.json')
    
    # 加载频率文件
    with open(filename, 'r', encoding='utf-8') as f:
        freq_data = json.load(f)
    
    # 找到对应的ETF
    etf_index = None
    for i, etf in enumerate(freq_data):
        if etf.get('code') == code:
            etf_index = i
            break
    
    if etf_index is None:
        print(f"⚠️ ETF {code} 不在 {filename} 中")
        return False
    
    # 增量更新：只更新提供的字段
    updated_fields = []
    for key, value in new_data.items():
        if value is not None and value != '' and value != 0:
            if key not in freq_data[etf_index] or freq_data[etf_index][key] is None or freq_data[etf_index][key] == '':
                freq_data[etf_index][key] = value
                updated_fields.append(key)
    
    # 保存
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(freq_data, f, ensure_ascii=False, indent=2)
    
    print(f"✅ 更新 ETF {code} 到 {filename}: {updated_fields}")
    return True
```

---

## 四、修改步骤

### Step 1: 修改 `load_etf_data()` 函数
- 文件: `pipeline.py` (约行460)
- 修改: 从5个频率文件加载，合并数据
- 测试: 运行 `python3 pipeline.py verify` 验证数据加载

### Step 2: 修改 `save_etf_data()` 函数
- 文件: `pipeline.py` (约行480)
- 修改: 按频率拆分，保存到5个文件
- 测试: 运行 `python3 pipeline.py build` 验证数据保存

### Step 3: 修改 `step_build()` 函数
- 文件: `pipeline.py` (约行466-724)
- 修改: 使用增量合并，而不是全量重建
- 测试: 运行 `python3 pipeline.py build` 验证

### Step 4: 添加 `update_etf_data()` 函数
- 文件: `pipeline.py` (新函数)
- 功能: 增量更新单个ETF的数据
- 测试: 运行测试脚本

### Step 5: 修改 Flask 应用
- 文件: `app.py`
- 修改: 使用 `load_etf_data()` 加载数据
- 测试: 本地运行 Flask 应用

---

## 五、风险与应对

### 风险1: 数据丢失
- **风险**: 修改过程中可能丢失数据
- **应对**: 保留备份文件 `etf_standard_data.backup.json`

### 风险2: 性能下降
- **风险**: 从5个文件加载数据可能比从1个文件慢
- **应对**: 使用内存缓存，定期刷新

### 风险3: 代码复杂度增加
- **风险**: 5个文件比1个文件难维护
- **应对**: 封装加载/保存逻辑，提供清晰API

---

## 六、下一步

1. ✅ **创建新文件结构** - 已完成 (etf_static/annual/quarterly/monthly/daily.json)
2. 🔧 **修改 pipeline.py** - 进行中 (按照上述方案)
3. 🧪 **测试验证** - 待办 (运行 pipeline.py verify/build)
4. 🚀 **部署上线** - 待办 (git push + PA部署)

---

**请确认方案，我立即开始修改 pipeline.py**
