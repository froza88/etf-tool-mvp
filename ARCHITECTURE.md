# ETF Tool MVP - 架构设计 v3

> 最后更新：2026-05-21

## 核心原则

**本地 JSON = Single Source of Truth (SST)，外部 API = 临时数据提供者**

- 每次外部 API 调用都立即持久化到本地文件
- 外部数据源失效时，本地数据仍可提供服务
- Pipeline 只操作本地文件，不直接调用外部 API

## 数据流架构

```
┌─────────────────────────────────────────────┐
│               外部数据源（临时，可失效）               │
│  AKShare │ 非凸 │ 盈米 │ NeoData │ Wind │ ...        │
└────────────────────┬────────────────────────┘
                     │ query & store（查询即存储）
                     ▼
┌─────────────────────────────────────────────┐
│               本地存储层（永久，SST）                 │
│  data/etf_standard_data.json  (主数据文件)          │
│  data/history/{code}.json       (历史K线)           │
│  data/cache/akshare/{code}.json (AKShare缓存)      │
│  data/cache/wind/{code}.json    (Wind缓存)          │
│  data/snapshots/              (版本快照)             │
└────────────────────┬────────────────────────┘
                     │ build（合并生成）
                     ▼
┌─────────────────────────────────────────────┐
│             Flask App（只读，0 外部API调用）          │
│  app.py → templates/*.html → 用户浏览器             │
└─────────────────────────────────────────────┘
```

## 目录结构

```
etf-tool-mvp/
├── fetchers/              # 外部数据源封装（查询即存储）
│   ├── __init__.py
│   ├── base_fetcher.py   # 基类：缓存检查 + 查询 + 存储
│   ├── akshare_fetcher.py
│   ├── westock_fetcher.py
│   ├── yingmi_fetcher.py
│   ├── neodata_fetcher.py
│   └── wind_fetcher.py   # ⭐ 新增：Wind数据源
├── pipeline.py            # 数据管道（操作本地文件）
├── app.py                # Flask应用（只读本地文件）
├── data/
│   ├── etf_standard_data.json   # SST主文件
│   ├── history/{code}.json      # 历史K线缓存
│   ├── cache/                  # 外部API响应缓存
│   └── snapshots/             # 版本快照
└── scripts/                # 一次性脚本（不参与管道）
```

## Pipeline 步骤（v3）

| 步骤 | 名称 | 功能 | 数据源 |
|------|------|------|--------|
| 1 | `sync` | 同步ETF列表 | AKShare → local |
| 2 | `enrich` | 补充价格/持仓 | 非凸 → local |
| 3 | `enrich_wind` | ⭐ 新增：补充Wind数据 | Wind → local |
| 4 | `calc` | 计算风险指标 | local history → local |
| 5 | `build` | 生成标准化数据 | local → etf_standard_data.json |
| 6 | `deploy` | 部署 | git push |

## Wind 集成方案

### WindFetcher 设计

```python
class WindFetcher(BaseFetcher):
    """Wind API 数据获取器（查询即存储）"""
    
    def fetch_etf_info(self, code: str, name: str) -> dict:
        """获取ETF基础信息（基金管理人/成立日/费率/基准等）"""
        # 1. 检查本地缓存
        cache = self._load_cache(code, "etf_info")
        if cache and self._is_cache_valid(cache):
            return cache['data']
        
        # 2. 调用 Wind API
        data = self._call_wind_api("get_fund_info", f"{code}{name}基金档案")
        
        # 3. 立即存储到本地
        self._save_cache(code, "etf_info", data)
        
        return data
```

### 集成到 Pipeline

在 `pipeline.py` 中新增 `step_enrich_wind()` 步骤：

```python
def step_enrich_wind():
    """从 Wind 补充ETF基础信息（基金管理人/费率/基准等）"""
    log("Step 3: 从 Wind 补充数据")
    
    from fetchers.wind_fetcher import WindFetcher
    fetcher = WindFetcher()
    
    # 加载当前数据
    standard_data = load_json(LEGACY_FILES["standard"])
    
    # 找出需要补充的 ETF
    need_wind = [e for e in standard_data 
                 if not e.get('custodian') or not e.get('benchmark')]
    
    log(f"  需补充Wind数据: {len(need_wind)} 只")
    
    # 逐个获取（带缓存）
    for etf in need_wind[:10]:  # 先测试10只
        code = etf['code']
        name = etf['name']
        
        try:
            wind_data = fetcher.fetch_etf_info(code, name)
            # 更新本地数据
            etf.update(wind_data)
        except Exception as e:
            log(f"  {code} 失败: {e}")
        
        time.sleep(1)  # 避免QPS限制
    
    # 保存
    save_json(LEGACY_FILES["standard"], standard_data)
    create_snapshot("enrich_wind")
```

## 数据冗余保障

### 当前问题
- `step_enrich` 直接写 `etf_generated_data.json`，没有按ETF拆分缓存
- 如果非凸API失效，无法重新获取

### 改造方案
1. **每个ETF独立缓存文件** `data/cache/{source}/{code}.json`
2. **Pipeline每一步都从缓存读取**，不直接调用API
3. **定时任务**：每天重新fetch一次，更新缓存

### 缓存文件格式

```json
{
  "code": "511670",
  "source": "wind",
  "endpoint": "get_fund_info",
  "fetched_at": "2026-05-21T13:00:00",
  "data": {
    "issuer": "华宝基金管理有限公司",
    "issue_date": "2017-08-11",
    "custodian": "中国工商银行股份有限公司",
    "management_fee_rate": 0.15,
    "custody_fee_rate": 0.05,
    "benchmark": "创业板指数",
    "fund_manager": "成曦,刘树荣"
  },
  "ttl_days": 7
}
```

## 下一步优化点（2026-05-21 更新）

### ✅ 已完成
- [x] 创建 `fetchers/` 模块和 `WindFetcher`
- [x] 修改 `pipeline.py` 集成 Wind（step_enrich_wind → step_build 合并）
- [x] `etf_standard_data.json` 包含 benchmark / management_fee_rate / custody_fee_rate 字段

### P0（当前最紧急）
- [ ] **运行 `python pipeline.py enrich_wind`** 填充 custodian/benchmark/费率（需Wind积分）
- [ ] year_3_return 79.9% — 需更多K线数据积累
- [ ] annual_vol 94.6% — calc_risk_metrics 有 bug 待修

### P1（重要）
- [ ] 将 `step_enrich` 中的 AKShare 调用改为使用 `fetchers/akshare_fetcher.py`
- [ ] 添加缓存清理脚本（清理过期 Wind 缓存）
- [ ] 补充 Wind 剩余数据（~11天分批次）

### P2（可选）
- [ ] 添加数据质量监控仪表盘
- [ ] 支持多数据源优先级可视化配置
- [ ] 前端展示 benchmark / management_fee_rate / custodian 等新字段

## Wind API 积分规划

- 每日免费：1000 积分
- 单次调用：~6.67 积分
- 每日可调用：~150 次
- 全部1470只ETF：需约10天

### 分天下载计划

| 天数 | 调用次数 | 消耗积分 | 说明 |
|------|----------|----------|------|
| 今天 | 140 | 934 | 剩余积分 |
| 第2-11天 | 150/天 | 1000/天 | 每日免费额度 |
| 第12天 | 109 | 727 | 最后一批 |

**总计：12天，~9800积分**
