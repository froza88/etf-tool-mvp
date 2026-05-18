# 分布式数据缓存架构设计
# 多地点存储 + 智能调用策略

## 架构概览

```
┌─────────────────────────────────────────────────────────────┐
│              数据获取/更新（单一入口）                         │
│  enrich_*.py / API调用 / 手动更新                            │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ↓
┌─────────────────────────────────────────────────────────────┐
│              同步写入三个地点（原子性保证）                      │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐             │
│  │ 本地缓存  │    │  GitHub  │    │  Python  │             │
│  │(最快访问) │    │(版本控制)│    │ Anywhere │             │
│  └──────────┘    └──────────┘    └──────────┘             │
└─────────────────────────────────────────────────────────────┘
                 │
                 ↓
┌─────────────────────────────────────────────────────────────┐
│              工具使用 - 智能调用策略                           │
│  环境检测 → 选择最佳数据源 → 降级策略 → 数据恢复               │
└─────────────────────────────────────────────────────────────┘
```

## 三个存储地点详情

### 1. 本地缓存（Local Cache）
**路径**：`/Users/apangduo/WorkBuddy/Claw/etf-tool-mvp/data_generated/`

**特点**：
- ✅ 访问速度最快（本地文件系统）
- ✅ 适合开发调试
- ✅ 可以离线工作
- ❌ 只存在于本地机器

**数据**：
- `etf_data.json`（核心数据，1463只ETF）
- `etf_prices.json`（价格数据）
- `etf_holdings.json`（持仓数据）
- `etf_nav_history_*.json`（历史净值）

---

### 2. GitHub仓库（版本控制 + 备份）
**仓库**：`https://github.com/apangduo/etf-tool-mvp`

**特点**：
- ✅ 版本控制（可以回滚到任意历史版本）
- ✅ 数据备份（防止本地数据丢失）
- ✅ 协作友好（团队可以pull最新数据）
- ✅ 数据溯源（每次更新都有commit记录）
- ❌ 访问需要网络
- ❌ 大文件存储有限制（<100MB）

**同步策略**：
```bash
# 每次数据更新后自动执行
git add data_generated/
git commit -m "data: Update ETF data (YYYY-MM-DD, 1463 funds)"
git push origin main
```

**数据结构**：
```
etf-tool-mvp/
├── data_generated/          # 与本地缓存同步
│   ├── etf_data.json
│   ├── etf_prices.json
│   └── etf_holdings.json
└── data_backup/             # 历史版本存档（可选）
    ├── 2026-05-12/
    ├── 2026-05-13/
    └── ...
```

---

### 3. PythonAnywhere（线上服务）
**URL**：`https://froza.pythonanywhere.com`

**特点**：
- ✅ 线上环境直接访问
- ✅ 无需跨网络传输数据
- ✅ 适合API服务
- ❌ 需要手动/自动同步

**同步方式**：

**方式A：Git Pull（推荐）**
```bash
# PythonAnywhere上执行
cd ~/etf-tool-mvp
git pull origin main
touch /var/www/froza_pythonanywhere_com_wsgi.py  # 重启Web服务
```

**方式B：API上传（备选）**
```python
# 本地执行：上传数据到PythonAnywhere
import requests
with open('data_generated/etf_data.json', 'rb') as f:
    requests.post(
        'https://froza.pythonanywhere.com/api/upload_data',
        files={'file': f},
        auth=('username', 'password')
    )
```

**方式C：定时任务（自动化）**
```bash
# PythonAnywhere Scheduled Tasks
# 每天凌晨3点自动git pull
0 3 * * * cd ~/etf-tool-mvp && git pull origin main
```

---

## 智能调用策略

### 环境检测
```python
import os

def detect_environment():
    """检测当前运行环境"""
    if 'PYTHONANYWHERE_DOMAIN' in os.environ:
        return 'pythonanywhere'
    elif os.path.exists('/Users/apangduo/WorkBuddy/Claw/etf-tool-mvp'):
        return 'local'
    else:
        return 'unknown'

current_env = detect_environment()
```

### 数据源选择逻辑
```python
def get_data_source(data_type='etf_data'):
    """根据环境和可用性选择最佳数据源"""
    
    if current_env == 'local':
        # 本地环境：优先本地缓存
        local_path = f'data_generated/{data_type}.json'
        if os.path.exists(local_path):
            return 'local', local_path
        
        # 降级：从GitHub拉取
        print("⚠️ 本地缓存缺失，从GitHub拉取...")
        os.system('git pull origin main')
        if os.path.exists(local_path):
            return 'local', local_path
        
        # 降级：从PythonAnywhere下载
        print("⚠️ GitHub拉取失败，从PythonAnywhere下载...")
        download_from_pythonanywhere(data_type)
        return 'local', local_path
    
    elif current_env == 'pythonanywhere':
        # 线上环境：优先PythonAnywhere本地文件
        local_path = f'~/etf-tool-mvp/data_generated/{data_type}.json'
        if os.path.exists(local_path):
            return 'pythonanywhere', local_path
        
        # 降级：从GitHub拉取
        print("⚠️ 本地文件缺失，从GitHub拉取...")
        os.system('cd ~/etf-tool-mvp && git pull origin main')
        if os.path.exists(local_path):
            return 'pythonanywhere', local_path
        
        # 降级：从本地上传（需要API）
        print("⚠️ GitHub拉取失败，请从本地上传数据...")
        return None, None
    
    return None, None
```

### 降级策略流程图
```
本地环境：
  1. 本地缓存（最快）
     ↓ (缺失)
  2. Git Pull（从GitHub恢复）
     ↓ (失败)
  3. 从PythonAnywhere下载
     ↓ (失败)
  4. 报错：无法获取数据

线上环境：
  1. PythonAnywhere本地文件（最快）
     ↓ (缺失)
  2. Git Pull（从GitHub恢复）
     ↓ (失败)
  3. 提示用户从本地上传
     ↓ (失败)
  4. 报错：无法获取数据
```

---

## 数据同步实施方案

### Phase 1：自动化同步脚本
创建 `sync_data.py`：

```python
#!/usr/bin/env python3
"""
数据同步脚本 - 同步到本地、GitHub、PythonAnywhere
"""

import os
import sys
import subprocess
import requests
from datetime import datetime

class DataSyncer:
    def __init__(self):
        self.project_root = '/Users/apangduo/WorkBuddy/Claw/etf-tool-mvp'
        self.data_dir = os.path.join(self.project_root, 'data_generated')
        
    def sync_to_github(self):
        """同步到GitHub"""
        try:
            # Git add
            subprocess.run(['git', 'add', 'data_generated/'], 
                         cwd=self.project_root, check=True)
            
            # Git commit
            date_str = datetime.now().strftime('%Y-%m-%d')
            commit_msg = f"data: Update ETF data ({date_str})"
            subprocess.run(['git', 'commit', '-m', commit_msg], 
                         cwd=self.project_root, check=True)
            
            # Git push
            subprocess.run(['git', 'push', 'origin', 'main'], 
                         cwd=self.project_root, check=True)
            
            print("✅ GitHub同步成功")
            return True
        except subprocess.CalledProcessError as e:
            print(f"⚠️ GitHub同步失败: {e}")
            return False
    
    def sync_to_pythonanywhere(self):
        """同步到PythonAnywhere（通过Git Pull）"""
        print("📝 PythonAnywhere同步说明：")
        print("   请在PythonAnywhere Bash中执行：")
        print("   cd ~/etf-tool-mvp && git pull origin main")
        print("   touch /var/www/froza_pythonanywhere_com_wsgi.py")
        return True
    
    def run(self):
        """执行完整同步流程"""
        print("="*60)
        print("🔄 开始数据同步")
        print("="*60)
        
        # 1. 同步到GitHub
        print("\n[1/2] 同步到GitHub...")
        self.sync_to_github()
        
        # 2. 同步到PythonAnywhere
        print("\n[2/2] 同步到PythonAnywhere...")
        self.sync_to_pythonanywhere()
        
        print("\n" + "="*60)
        print("✅ 数据同步流程完成")
        print("="*60)

if __name__ == '__main__':
    syncer = DataSyncer()
    syncer.run()
```

---

### Phase 2：集成到数据更新脚本
修改 `enrich_prices.py` 和 `enrich_holdings.py`：

```python
# 在文件末尾添加：
if __name__ == '__main__':
    # 原有逻辑...
    enrich_prices()
    
    # 同步到多地
    from sync_data import DataSyncer
    syncer = DataSyncer()
    syncer.sync_to_github()
    syncer.sync_to_pythonanywhere()
```

---

### Phase 3：PythonAnywhere定时任务
在PythonAnywhere设置Scheduled Tasks：

```bash
# 每天凌晨3点自动同步
0 3 * * * cd ~/etf-tool-mvp && git pull origin main && touch /var/www/froza_pythonanywhere_com_wsgi.py
```

---

## 故障恢复方案

### 场景1：本地缓存丢失
**症状**：`data_generated/` 目录被误删

**恢复步骤**：
```bash
# 从GitHub恢复
cd /Users/apangduo/WorkBuddy/Claw/etf-tool-mvp
git checkout HEAD -- data_generated/

# 验证
ls -lh data_generated/etf_data.json
```

---

### 场景2：GitHub仓库损坏
**症状**：Git仓库损坏或数据被误提交覆盖

**恢复步骤**：
```bash
# 从本地缓存恢复GitHub
cd /Users/apangduo/WorkBuddy/Claw/etf-tool-mvp
git add data_generated/
git commit -m "Recovery: Restore data from local cache"
git push origin main
```

---

### 场景3：PythonAnywhere数据缺失
**症状**：线上服务报错"数据文件不存在"

**恢复步骤**：
```bash
# 登录PythonAnywhere Bash
cd ~/etf-tool-mvp
git pull origin main
touch /var/www/froza_pythonanywhere_com_wsgi.py
```

---

### 场景4：三个地点数据不一致
**症状**：本地、GitHub、PythonAnywhere数据版本不同

**解决步骤**：
```bash
# 1. 以本地为权威源（因为本地通常是最新）
cd /Users/apangduo/WorkBuddy/Claw/etf-tool-mvp

# 2. 强制同步到GitHub
git add data_generated/
git commit -m "fix: Force sync data to GitHub"
git push origin main --force

# 3. 在PythonAnywhere上强制同步
cd ~/etf-tool-mvp
git fetch origin
git reset --hard origin/main
touch /var/www/froza_pythonanywhere_com_wsgi.py
```

---

## 数据结构设计

### 统一数据格式
确保所有地点的数据格式完全一致：

```json
{
  "metadata": {
    "version": "2026.05.18",
    "update_time": "2026-05-18 23:00:00",
    "source": "enrich_prices.py + enrich_holdings.py",
    "record_count": 1463
  },
  "data": [
    {
      "code": "510300",
      "name": "沪深300ETF",
      "category": "宽基指数",
      "manager": "华泰柏瑞",
      "return_1y": 8.5,
      "return_3y": 25.3,
      "max_drawdown": -15.2,
      "sharpe_ratio": 0.85,
      "close_price": 4.12,
      "change_pct": 1.2,
      "holdings": [...],
      "update_time": "2026-05-18 23:00:00"
    }
  ]
}
```

---

## 性能优化

### 1. 增量同步
只同步变更的文件，而非全量：

```bash
# Git会自动处理增量
git add data_generated/etf_data.json  # 只添加变更的文件
git commit -m "data: Update etf_data.json"
```

### 2. 压缩传输
大文件（如历史净值）使用压缩：

```python
import gzip
import json

# 压缩
with gzip.open('etf_nav_history.json.gz', 'wt') as f:
    json.dump(data, f)

# 解压
with gzip.open('etf_nav_history.json.gz', 'rt') as f:
    data = json.load(f)
```

### 3. 并行同步
同时同步到GitHub和PythonAnywhere：

```python
from concurrent.futures import ThreadPoolExecutor

def sync_parallel():
    with ThreadPoolExecutor(max_workers=2) as executor:
        future1 = executor.submit(sync_to_github)
        future2 = executor.submit(sync_to_pythonanywhere)
        
        result1 = future1.result()
        result2 = future2.result()
    
    return result1 and result2
```

---

## 监控和告警

### 数据一致性检查
创建 `check_data_consistency.py`：

```python
#!/usr/bin/env python3
"""
数据一致性检查 - 对比本地、GitHub、PythonAnywhere的数据
"""

import json
import requests

def check_consistency():
    """检查三个地点的数据一致性"""
    
    # 1. 本地数据
    with open('data_generated/etf_data.json', 'r') as f:
        local_data = json.load(f)
    local_count = len(local_data['data'])
    
    # 2. GitHub数据（通过GitHub API）
    github_url = 'https://raw.githubusercontent.com/apangduo/etf-tool-mvp/main/data_generated/etf_data.json'
    response = requests.get(github_url)
    github_data = response.json()
    github_count = len(github_data['data'])
    
    # 3. PythonAnywhere数据
    pa_url = 'https://froza.pythonanywhere.com/api/etf_data'
    response = requests.get(pa_url)
    pa_data = response.json()
    pa_count = len(pa_data['data'])
    
    # 对比
    print("="*60)
    print("📊 数据一致性检查")
    print("="*60)
    print(f"本地数据: {local_count} 条")
    print(f"GitHub数据: {github_count} 条")
    print(f"PythonAnywhere数据: {pa_count} 条")
    
    if local_count == github_count == pa_count:
        print("✅ 三个地点数据一致")
    else:
        print("⚠️ 数据不一致，请执行同步")
    print("="*60)

if __name__ == '__main__':
    check_consistency()
```

---

## 总结

**架构优势**：
1. ✅ **高可用**：任一地点故障，其他地点可以继续服务
2. ✅ **负载均衡**：根据环境智能选择最佳数据源
3. ✅ **数据冗余**：防止数据丢失
4. ✅ **版本控制**：GitHub提供完整的数据版本历史
5. ✅ **快速访问**：本地环境用本地缓存，线上环境用PythonAnywhere

**下一步实施**：
1. 创建 `sync_data.py` 同步脚本
2. 集成到现有数据更新脚本
3. 设置PythonAnywhere定时任务
4. 创建数据一致性检查脚本

需要我立即开始实施吗？
