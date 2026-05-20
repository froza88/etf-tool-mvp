# 三地数据同步方案 - 设计文档

## 问题描述
当前 `etf_standard_data.json` 在三个位置存储：
1. **本地** (Local) - 开发机器
2. **GitHub** - 远程仓库
3. **PythonAnywhere** - 生产环境

**核心问题：**
- Git pull 可能覆盖本地新数据（回滚）
- 三地数据可能不一致
- 缺少时间戳，无法判断数据新旧

## 解决方案

### 1. 时间戳机制
在 `etf_standard_data.json` 同级目录创建 `data_version.json`：

```json
{
  "version": "2026-05-20T08:42:00+08:00",
  "source": "local",  // local | github | pythonanywhere
  "checksum": "abc123...",
  "etf_count": 1468,
  "fields_coverage": {
    "year_3_return": 1.0
  }
}
```

**规则：**
- 每次数据更新，自动更新 `data_version.json`
- `version` 使用 ISO 8601 格式时间戳
- `source` 标记数据来源
- `checksum` 用于快速验证数据完整性

### 2. 备份优先级与同步流程

```
本地更新 → 立即 commit + push → GitHub 更新
                                    ↓
                            PythonAnywhere 定时 pull (每10分钟)
```

**同步脚本 `sync_data.sh`：**
```bash
#!/bin/bash
# 同步数据到三地

set -e

cd /path/to/etf-tool-mvp

# 1. 更新本地数据 + 版本信息
python3 update_data_version.py

# 2. 提交到 Git
git add etf_standard_data.json data_version.json
git commit -m "data: auto-sync $(date +%Y-%m-%d_%H:%M:%S)"
git push origin main

# 3. 触发 PythonAnywhere 拉取 (通过 webhook 或 API)
curl -X POST https://froza.pythonanywhere.com/api/sync
```

### 3. 防回滚策略

**核心原则：新数据永不覆盖旧数据**

**实现方式：**
1. **Pull 前检查版本**
   ```python
   # 在 git pull 前执行
   local_version = load_version('data_version.json')
   remote_version = get_remote_version()  # 从 Git 或 API
   
   if local_version['version'] > remote_version['version']:
       # 本地更新，先 push 再 pull
       git push origin main
       git pull origin main
   else:
       # 远程更新，直接 pull
       git pull origin main
   ```

2. **PythonAnywhere 拉取策略**
   - 每次 pull 前，备份当前数据
   - 比较版本号，只接受更新的数据
   - 如果本地更新，拒绝 pull（先 push）

3. **Git Hook 保护**
   - Pre-commit: 检查 `data_version.json` 时间戳是否更新
   - Pre-push: 验证数据完整性（checksum）

### 4. 一致性验证

**验证脚本 `verify_sync.py`：**
```python
import json
import hashlib

def verify_consistency():
    """验证三地数据一致性"""
    
    # 1. 检查本地
    local_data = load_data('etf_standard_data.json')
    local_version = load_version('data_version.json')
    
    # 2. 检查 GitHub (通过 Git)
    github_data = get_github_data()
    github_version = get_github_version()
    
    # 3. 检查 PythonAnywhere (通过 API)
    pa_data = get_pa_data()
    pa_version = get_pa_version()
    
    # 4. 对比
    results = {
        'local': {'count': len(local_data), 'version': local_version['version']},
        'github': {'count': len(github_data), 'version': github_version['version']},
        'pythonanywhere': {'count': len(pa_data), 'version': pa_version['version']}
    }
    
    # 5. 输出报告
    print(json.dumps(results, indent=2))
    
    # 6. 检查时间差
    versions = [v['version'] for v in results.values()]
    time_diffs = check_time_diff(versions)
    
    if max(time_diffs) > 10 * 60:  # 10 minutes
        print("WARNING: Data sync delay > 10 minutes!")
    
    return results
```

### 5. 实施步骤

**Phase 1: 基础架构 (今天)**
- [x] 创建 `data_version.json` 结构
- [ ] 编写 `update_data_version.py` 脚本
- [ ] 修改现有脚本，自动更新版本信息

**Phase 2: 同步机制 (明天)**
- [ ] 创建 `sync_data.sh` 同步脚本
- [ ] 配置 PythonAnywhere 定时拉取 (cron)
- [ ] 测试同步流程

**Phase 3: 防回滚 (后天)**
- [ ] 实现版本检查逻辑
- [ ] 添加 Git hooks
- [ ] 测试回滚防护

**Phase 4: 验证与监控 (大后天)**
- [ ] 编写 `verify_sync.py` 验证脚本
- [ ] 添加监控告警 (数据不一致时通知)
- [ ] 文档与培训

## 关键文件

| 文件 | 用途 |
|------|------|
| `data_version.json` | 数据版本元数据 |
| `update_data_version.py` | 更新版本信息脚本 |
| `sync_data.sh` | 三地同步脚本 |
| `verify_sync.py` | 一致性验证脚本 |
| `.git/hooks/pre-commit` | Git 钩子 (保护数据) |
| `api/sync` (PA) | PythonAnywhere 同步接口 |

## 风险与限制

**风险：**
1. 网络中断导致同步失败
2. 冲突解决复杂（本地和远程同时更新）
3. PythonAnywhere 定时任务可能延迟

**限制：**
1. 10分钟同步窗口依赖 PythonAnywhere cron 精度
2. 大文件 (1.3MB) 同步可能慢
3. Git 历史会变大（每次提交数据文件）

**缓解措施：**
1. 添加重试机制
2. 使用 Git LFS 或分片存储
3. 监控告警 + 手动介入流程
