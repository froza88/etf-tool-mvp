# 测试单元2：GitHub Webhook触发测试

## 测试目标
验证GitHub Webhook能否成功触发PA的 `/api/sync` 端点

## 测试类型
🔶 **半自动**（需要人工检查GitHub Webhook页面）

## 前置条件
- ✅ 测试单元1已完成（PA代码已更新）
- ✅ GitHub Webhook已配置（Payload URL: `https://froza.pythonanywhere.com/api/sync`）

## 测试步骤

### 步骤1：本地推送测试提交
```bash
cd /Users/apangduo/WorkBuddy/Claw/etf-tool-mvp/
echo "# webhook test $(date)" >> README.md
git add README.md
git commit -m "test: webhook trigger test"
git push origin main
```

### 步骤2：等待Webhook触发（10秒）

### 步骤3：检查GitHub Webhook Delivery
1. 浏览器打开：`https://github.com/froza88/etf-tool-mvp/settings/hooks`
2. 点击你的Webhook（进入详情页）
3. 滚动到页面底部，找到 **"Recent deliveries"** 区域
4. 找到刚才push对应的记录（几分钟前）
5. 点击该记录，展开详情
6. 切换到 **"Response"** 标签页

**期望结果**：
```
Status: 200
Body: {
  "status": "success",
  "git_output": "...",
  "version_output": "...",
  "version_error": ""
}
```

**成功标志**：
- ✅ Status code = 200
- ✅ Response body包含 `"status": "success"`

**失败处理**：
- 如果Recent deliveries为空 → Webhook未配置push事件，检查Webhook设置
- 如果Status = 500 → PA的 `/api/sync` 执行失败，查看Response body的错误信息

### 步骤4：验证PA已同步
浏览器访问：`https://froza.pythonanywhere.com/api/version`

**期望结果**：
- `version` 时间戳是最近的（几分钟前）
- `source` = `"pythonanywhere"`

## 测试交付物
- [ ] GitHub Webhook Delivery截图（显示Status 200）
- [ ] PA的 `/api/version` 响应（JSON文本）

## 依赖
- 测试单元1（PA代码更新）

## 后续测试单元
- 测试单元3：三地同步验证测试（依赖本测试成功）
