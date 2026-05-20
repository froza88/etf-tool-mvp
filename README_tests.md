# ETF Tool MVP - 测试环境说明

## 测试环境结构

```
etf-tool-mvp/
├── test_data/                    # 测试数据
│   └── sample_etfs.json         # 10 只样本 ETF 数据
├── tests/                      # 测试脚本
│   ├── __init__.py
│   ├── test_services.py        # Service 层测试（9 个）
│   ├── test_repositories.py    # Repository 层测试（8 个）
│   └── test_integration.py    # 集成测试（4 个）
├── conftest.py                # pytest 夹具配置
├── pytest.ini                 # pytest 配置文件
└── README_tests.md           # 本文档
```

## 运行测试

### 运行所有测试
```bash
cd /Users/apangduo/WorkBuddy/Claw/etf-tool-mvp
python3 -m pytest tests/ -v
```

### 运行特定测试文件
```bash
# 运行 Service 层测试
python3 -m pytest tests/test_services.py -v

# 运行 Repository 层测试
python3 -m pytest tests/test_repositories.py -v

# 运行集成测试
python3 -m pytest tests/test_integration.py -v
```

### 运行特定测试类或方法
```bash
# 运行特定类
python3 -m pytest tests/test_services.py::TestETFQueryService -v

# 运行特定方法
python3 -m pytest tests/test_services.py::TestETFQueryService::test_get_etf_list -v
```

## 测试覆盖

### Service 层测试（test_services.py）
- **TestETFQueryService**（5 个测试）
  - `test_get_etf_list` - 测试获取 ETF 列表
  - `test_get_etf_list_with_filter` - 测试带筛选条件获取 ETF 列表
  - `test_get_etf_detail` - 测试获取 ETF 详情
  - `test_get_etf_detail_not_found` - 测试获取不存在的 ETF
  - `test_search_etfs` - 测试搜索 ETF

- **TestETFCompareService**（3 个测试）
  - `test_compare_etfs` - 测试对比 ETF
  - `test_compare_etfs_empty` - 测试对比空列表
  - `test_get_compare_metrics` - 测试获取对比指标

- **TestETFScreeningService**（1 个测试）
  - `test_get_default_screening_criteria` - 测试获取默认筛选条件

### Repository 层测试（test_repositories.py）
- **TestETFRepositoryInterface**（2 个测试）
  - `test_cannot_instantiate_abstract_class` - 测试不能实例化抽象类
  - `test_concrete_class_must_implement_abstract_methods` - 测试具体类必须实现所有抽象方法

- **TestMockRepository**（6 个测试）
  - `test_get_all_etfs` - 测试 get_all_etfs
  - `test_get_etf_by_code` - 测试 get_etf_by_code
  - `test_get_etf_by_code_not_found` - 测试获取不存在的 ETF
  - `test_filter_etfs` - 测试 filter_etfs
  - `test_get_etf_history` - 测试 get_etf_history
  - `test_search_etfs` - 测试 search_etfs

### 集成测试（test_integration.py）
- **TestRepositoryServiceIntegration**（4 个测试）
  - `test_query_service_with_repo` - 测试 QueryService 通过 Repository 获取数据
  - `test_compare_service_with_repo` - 测试 CompareService 通过 Repository 获取对比数据
  - `test_history_service_with_repo` - 测试 HistoryService 通过 Repository 获取历史数据
  - `test_screening_service_with_repo` - 测试 ScreeningService 通过 Repository 执行筛选

## 测试数据

### test_data/sample_etfs.json
包含 10 只不同类型 ETF 的样本数据：
1. **510300** - 沪深300ETF（宽基）
2. **510500** - 中证500ETF（宽基）
3. **512480** - 半导体ETF（行业）
4. **515030** - 新能源汽车ETF（行业）
5. **511010** - 国债ETF（债券）
6. **511260** - 上证10年期国债ETF（债券）
7. **518880** - 黄金ETF（商品）
8. **159915** - 创业板ETF（宽基）
9. **512690** - 酒ETF（行业）
10. **513100** - 纳指ETF（跨境）

## 依赖

测试环境依赖：
- `pytest` - 测试框架
- `pytest-v`（可选）- 详细输出

安装依赖：
```bash
pip3 install pytest
```

## 注意事项

1. **测试使用 Mock Repository**：测试中不依赖真实数据源（如本地 JSON 文件或 NeoData API），而是使用 Mock Repository。这使得测试快速、独立、可重复。

2. **测试不依赖外部服务**：所有测试都是单元测试或集成测试，不依赖外部服务（如数据库、API）。

3. **测试数据独立**：测试数据在 `test_data/` 目录中，与真实数据分离。

## 下一步

1. **添加更多测试**：随着代码开发，需要添加更多测试用例。
2. **测试真实 Repository 实现**：当 `LocalJSONRepo`、`NeoDataRepo` 等真实实现完成后，需要添加针对这些实现的测试。
3. **持续集成**：将测试集成到 CI/CD 流程中，确保每次提交都通过测试。
