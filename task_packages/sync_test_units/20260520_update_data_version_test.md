# 测试单元4：update_data_version.py 功能测试

## 测试目标
测试 `update_data_version.py` 对三个来源（local/github/pythonanywhere）都能正确更新 `data_version.json`

## 测试类型
🤖 **自动化测试**（可重复运行）

## 前置条件
- ✅ `update_data_version.py` 脚本存在
- ✅ `data_version.json` 文件可写

## 测试步骤

### 步骤1：运行测试脚本
```bash
cd /Users/apangduo/WorkBuddy/Claw/etf-tool-mvp/
python3 task_packages/sync_test_units/test_04_update_data_version_test.py
```

### 步骤2：检查输出
**期望结果**：
- ✅ 三个来源（local/github/pythonanywhere）都测试通过
- ✅ `data_version.json` 的 `source` 字段正确
- ✅ 没有错误信息

**失败标志**：
- ❌ 某个来源测试失败
- ❌ `source` 字段不正确
- ❌ 报错信息

### 步骤3：失败处理
如果测试失败：
1. 查看输出，定位哪个来源失败
2. 常见问题：
   - `local` 失败 → 检查本地 `data_version.json` 是否可写
   - `github` 失败 → 检查GitHub API是否可访问
   - `pythonanywhere` 失败 → 检查PA API是否可访问

## 测试交付物
- [ ] 测试输出日志（文本）
- [ ] `data_version.json` 文件（检查source字段）

## 依赖
- 无（可独立运行）

## 后续测试单元
- 测试单元5-8（可并行运行）

## 备注
- 此测试验证 `update_data_version.py` 的核心功能
- 三个来源必须都测试通过，否则同步方案不完整
- 建议每次修改 `update_data_version.py` 后都运行此测试

## 文件清单
- `test_04_update_data_version_test.py` - 自动化测试脚本
- `test_04_update_data_version_test.md` - 本文件（测试说明）

---

**创建时间**：2026-05-20 13:40
**创建人**：AI Assistant
**版本**：v1.0
