# V2 部署说明

## 架构

```
COS (腾讯云对象存储)
  └─ index.html         ← 静态前端

API 网关
  └─ 云函数 SCF
       └─ function.py   ← 对比接口
            └─ etf_standard_data.json  ← 1490只ETF数据
```

## 本地预览

```bash
cd etf-tool-mvp
python3 app.py
# 打开 http://127.0.0.1:5000/v2
```

## 部署到腾讯云

### 1. COS 静态托管

```bash
# 启动静态网站功能
# 上传 v2/frontend/index.html 到 COS 存储桶
# 设置公共读权限
```

### 2. 云函数 SCF

```bash
# 创建 Python 3.9 云函数
# 上传 v2/backend/function.py + etf_standard_data.json
# 入口函数: function.main_handler
# 绑定 API 网关触发器
# 设置超时 10 秒，内存 256MB
```

### 3. 前端指向云函数

修改 `v2/frontend/index.html` 中：
```js
const API_URL = 'https://your-api-gateway.ap-shanghai.tencentcloudapi.com/your-path';
```

## 数据更新

1. 本地运行数据更新脚本
2. 将新的 `etf_standard_data.json` 更新到云函数
3. 云函数自动热加载（文件变化时重新读取）
