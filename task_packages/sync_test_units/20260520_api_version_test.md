# 测试单元7：/api/version 端点测试

## 测试目标
测试 Flask 应用的 `/api/version` 端点是否返回正确的数据（version/source/etf_count/checksum）

## 测试类型
🤖 **自动化测试**（可重复运行）

## 前置条件
- ✅ Flask 应用运行在 https://froza.pythonanywhere.com
- ✅ 或本地Flask应用运行在 http://localhost:5000

## 测试步骤

### 步骤1：运行测试脚本
```bash
cd /Users/apangduo/WorkBuddy/Claw/etf-tool-mvp/
python3 task_packages/sync_test_units/test_07_api_version_test.py
```

### 步骤2：检查输出
**期望结果**：
- ✅ 返回HTTP 200
- ✅ 响应包含 `version`, `source`, `etf_count`, `checksum` 字段
- ✅ 没有错误信息

**失败标志**：
- ❌ 返回不是200（如404/500）
- ❌ 缺少必要字段
- ❌ 连接失败

### 步骤3：失败处理
如果测试失败：
1. 查看输出，定位失败原因
2. 常见问题：
   - 连接失败 → 检查PA是否运行，或修改变量 `BASE_URL` 为 localhost
   - 返回404 → 检查 `/api/version` 端点是否部署
   - 返回500 → 检查PA error log

## 测试交付物
- [ ] 测试输出日志（文本）
- [ ] API响应JSON（截图或文本）

## 依赖
- 测试单元1（PA代码更新）

## 后续测试单元
- 测试单元8（/api/sync端点测试）

## 备注
- 此测试验证API端点的基本功能
- 如果此测试失败，测试单元8也会失败
- 建议每次修改 `app.py` 的 `/api/version` 端点后都运行此测试

## 文件清单
- `test_07_api_version_test.py` - 自动化测试脚本
- `test_07_api_version_test.md` - 本文件（测试说明）

---

**创建时间**：2026-05-20 13:40
**创建人**：AI Assistant
**版本**：v1.0
