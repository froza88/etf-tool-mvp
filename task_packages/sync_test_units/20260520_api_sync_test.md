# 测试单元8：/api/sync 端点测试

## 测试目标
测试 Flask 应用的 `/api/sync` 端点是否能正确触发 PA 数据同步（git pull）

## 测试类型
🤖 **自动化测试**（可重复运行，但会触发实际同步）

## 前置条件
- ✅ PA 应用运行在 https://froza.pythonanywhere.com
- ✅ `/api/sync` 端点已部署
- ✅ GitHub Webhook已配置（可选，用于验证）

## 测试步骤

### 步骤1：运行测试脚本
```bash
cd /Users/apangduo/WorkBuddy/Claw/etf-tool-mvp/
python3 task_packages/sync_test_units/test_08_api_sync_test.py
```

### 步骤2：检查输出
**期望结果**：
- ✅ 返回HTTP 200
- ✅ 响应中 `status` 为 `"success"`
- ✅ 没有错误信息

**失败标志**：
- ❌ 返回不是200（如500）
- ❌ `status` 不是 `"success"`
- ❌ 连接失败

### 步骤3：失败处理
如果测试失败：
1. 查看输出，定位失败原因
2. 常见问题：
   - 连接失败 → 检查PA是否运行
   - 返回500 → 检查PA error log，可能是 `/api/sync` 端点有bug
   - `status` 不是success → 检查PA的git配置和网络

## 测试交付物
- [ ] 测试输出日志（文本）
- [ ] API响应JSON（截图或文本）
- [ ] PA的git log（验证是否成功pull）

## 依赖
- 测试单元1（PA代码更新）

## 后续测试单元
- 无（这是最后一个测试单元）

## 备注
- ⚠️ 此测试会触发实际的git pull操作，可能修改PA的代码
- ⚠️ 建议先在测试环境运行，确认无误后再在生产环境运行
- 建议每次修改 `app.py` 的 `/api/sync` 端点后都运行此测试

## 文件清单
- `test_08_api_sync_test.py` - 自动化测试脚本
- `test_08_api_sync_test.md` - 本文件（测试说明）

---

**创建时间**：2026-05-20 13:40
**创建人**：AI Assistant
**版本**：v1.0
