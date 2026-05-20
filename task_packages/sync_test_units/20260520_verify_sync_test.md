# 测试单元3：三地同步验证测试

## 测试目标
运行 `verify_sync.py`，验证本地/GitHub/PA三地数据一致，时间差 < 10分钟

## 测试类型
🤖 **自动化测试**（可重复运行）

## 前置条件
- ✅ 测试单元2已完成（GitHub Webhook触发成功）
- ✅ PA可访问（https://froza.pythonanywhere.com）
- ✅ `verify_sync.py` 脚本存在

## 测试步骤

### 步骤1：运行测试脚本
```bash
cd /Users/apangduo/WorkBuddy/Claw/etf-tool-mvp/
python3 task_packages/sync_test_units/test_03_verify_sync.py
```

### 步骤2：检查输出
**期望结果**：
- ✅ 输出中没有 `❌` 符号
- ✅ 所有时间差 < 10分钟
- ✅ 三地数据一致（checksum相同）

**失败标志**：
- ❌ 输出中有 `❌` 符号
- ❌ 时间差 > 10分钟
- ❌ checksum不一致

### 步骤3：失败处理
如果测试失败：
1. 查看输出中的 `❌` 行，定位问题
2. 常见问题：
   - PA不可访问 → 检查测试单元1（PA代码更新）
   - GitHub不可访问 → 检查网络连接
   - 时间差过大 → 检查测试单元2（Webhook触发）

## 测试交付物
- [ ] 测试输出日志（文本）
- [ ] 三地同步状态报告

## 依赖
- 测试单元2（GitHub Webhook触发测试）

## 后续测试单元
- 无（这是端到端验证测试）

## 备注
- 此测试是**端到端验证**，确保整个同步方案工作正常
- 如果此测试通过，说明三地同步方案基本可用
- 建议每次修改同步相关代码后都运行此测试

## 文件清单
- `test_03_verify_sync.py` - 自动化测试脚本
- `test_03_verify_sync.md` - 本文件（测试说明）

---

**创建时间**：2026-05-20 13:40
**创建人**：AI Assistant
**版本**：v1.0
