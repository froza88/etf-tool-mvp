#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自动化版本追踪脚本 - 扫描git历史并生成完整版本清单
每次运行都会重新生成最新的版本清单
"""

import sys
import io
import subprocess
import re
from datetime import datetime

# 修复中文输出乱码
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

class VersionTracker:
    def __init__(self, repo_path='/Users/apangduo/WorkBuddy/Claw/etf-tool-mvp'):
        self.repo_path = repo_path
        self.output_file = f'{repo_path}/ETF_工具MVP_完整版本清单.md'
    
    def get_git_log(self):
        """获取所有git提交记录"""
        try:
            # 获取完整git log：哈希|日期|提交信息
            result = subprocess.run(
                ['git', 'log', '--pretty=format:%H|%ai|%s'],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True
            )
            
            commits = []
            for line in result.stdout.strip().split('\n'):
                if not line:
                    continue
                
                parts = line.split('|', 2)
                if len(parts) >= 3:
                    commit_hash = parts[0][:7]  # 短哈希
                    date_str = parts[1].split()[0]  # 只取日期部分
                    message = parts[2]
                    
                    # 解析提交信息，提取备注
                    remark = self._extract_remark(message)
                    
                    commits.append({
                        'hash': commit_hash,
                        'date': date_str,
                        'message': message,
                        'remark': remark
                    })
            
            return commits
        except subprocess.CalledProcessError as e:
            print(f"❌ 获取git log失败: {e}")
            return []
    
    def _extract_remark(self, message):
        """从提交信息中提取备注"""
        remark = []
        
        # 检测关键词
        if 'fix' in message.lower():
            remark.append('修复Bug')
        if 'feat' in message.lower():
            remark.append('新功能')
        if 'deploy' in message.lower():
            remark.append('部署相关')
        if 'data' in message.lower():
            remark.append('数据相关')
        if 'refactor' in message.lower():
            remark.append('重构')
        if 'chore' in message.lower():
            remark.append('杂项')
        if 'test' in message.lower():
            remark.append('测试')
        if 'doc' in message.lower():
            remark.append('文档')
        
        # 如果没有匹配，返回空
        if not remark:
            return ''
        
        return ', '.join(remark)
    
    def analyze_version_stages(self, commits):
        """分析版本演进阶段"""
        stages = []
        current_stage = None
        stage_commits = []
        
        for i, commit in enumerate(commits):
            # 判断阶段切换
            if 'Initial commit' in commit['message']:
                if current_stage:
                    stages.append({'name': current_stage, 'commits': stage_commits})
                current_stage = '阶段1: MVP初始版本'
                stage_commits = [commit]
            elif 'deploy' in commit['message'].lower() or 'deployment' in commit['message'].lower():
                if current_stage and '部署' not in current_stage:
                    if current_stage:
                        stages.append({'name': current_stage, 'commits': stage_commits})
                    current_stage = '阶段2: 部署配置'
                    stage_commits = [commit]
                else:
                    stage_commits.append(commit)
            elif 'data' in commit['message'].lower() or 'etf' in commit['message'].lower():
                if current_stage and '数据' not in current_stage:
                    if current_stage:
                        stages.append({'name': current_stage, 'commits': stage_commits})
                    current_stage = '阶段3: 数据质量提升'
                    stage_commits = [commit]
                else:
                    stage_commits.append(commit)
            elif 'enrich' in commit['message'].lower() or 'indicator' in commit['message'].lower():
                if current_stage and '指标' not in current_stage:
                    if current_stage:
                        stages.append({'name': current_stage, 'commits': stage_commits})
                    current_stage = '阶段4: 风险指标完善'
                    stage_commits = [commit]
                else:
                    stage_commits.append(commit)
            else:
                stage_commits.append(commit)
        
        # 添加最后一个阶段
        if current_stage:
            stages.append({'name': current_stage, 'commits': stage_commits})
        
        return stages
    
    def generate_markdown(self, commits):
        """生成Markdown版本清单"""
        now = datetime.now().strftime('%Y-%m-%d %H:%M')
        
        md = f"""# ETF工具MVP - 完整版本清单

**统计时间**: {now}
**总版本数**: {len(commits)} 个
**时间范围**: {commits[-1]['date']} 至 {commits[0]['date']}

---

## 版本清单（按时间编号）

| 编号 | 日期 | 提交哈希 | 版本描述 | 备注 |
|------|------|----------|----------|------|
"""
        
        # 倒序排列（最新的在前面）
        for i, commit in enumerate(commits, 1):
            md += f"| {i:3d} | {commit['date']} | {commit['hash']} | {commit['message']} | {commit['remark']} |\n"
        
        md += "\n---\n\n## 版本演进分析\n\n"
        
        # 版本演进阶段
        stages = self.analyze_version_stages(commits)
        for stage in stages:
            md += f"### {stage['name']}\n\n"
            md += f"**提交数**: {len(stage['commits'])} 个\n\n"
            for commit in stage['commits'][:5]:  # 只显示前5个
                md += f"- `{commit['hash']}` {commit['date']} - {commit['message']}\n"
            if len(stage['commits']) > 5:
                md += f"- ... 还有 {len(stage['commits']) - 5} 个提交\n"
            md += "\n"
        
        md += """---

## 重要版本标记

### 稳定版本（推荐回退）
- **版本97** (`4f3c505`): 数据质量相对稳定
- **版本113** (`latest`): 当前最新版本

### 问题版本（谨慎使用）
- **版本65** (`ce4d17a`): 删除了88个文件，可能导致功能缺失

---

## 缓存文件删除记录

以下缓存文件在版本65被删除（可从git历史恢复）：
- `etf_data_130.json`
- `etf_data_1461.json`
- `etf_risk_indicators.json`
- `etf_top_holdings.json`
- `etf_data_with_returns.json`
- ... 等共28个文件

**恢复命令**：
```bash
cd /Users/apangduo/WorkBuddy/Claw/etf-tool-mvp
git checkout ce4d17a~1 -- data_generated/
```

---

## 当前文件清单

### 核心文件（22个）
- `app.py` - Flask主应用
- `etf_data.py` - 数据加载模块
- `data_fetcher.py` - 数据获取
- `data_processor.py` - 数据处理
- `calc_metrics.py` - 指标计算
- `enrich_prices.py` - 价格补充
- `enrich_holdings.py` - 持仓补充
- `templates/index.html` - 列表页
- `templates/detail.html` - 详情页
- `templates/risk.html` - 风险页
- `data_generated/etf_data.json` - 核心数据(1463只)
- `data_generated/etf_prices.json` - 价格数据
- `data_generated/etf_holdings.json` - 持仓数据

### 文档文件
- `README.md`
- `deploy.py`
- `deploy.sh`
- `ETF_工具MVP_完整版本清单.md`
- `ETF_data_indicators_analysis.md`
- `distributed_cache_architecture.md`

---

## 使用建议

1. **保留所有版本**：git历史完整，随时可回退
2. **恢复被删文件**：从版本64恢复缓存文件
3. **版本对比**：使用 `git diff` 对比不同版本
4. **稳定版本**：版本97或版本113

---

**自动生成时间**: {now}
**脚本路径**: `version_tracker.py`
**运行命令**: `python3 version_tracker.py`
"""
        
        return md
    
    def save_markdown(self, content):
        """保存Markdown文件"""
        try:
            with open(self.output_file, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✅ 版本清单已保存: {self.output_file}")
            return True
        except Exception as e:
            print(f"❌ 保存失败: {e}")
            return False
    
    def run(self):
        """执行版本追踪"""
        print("="*60)
        print("📊 开始扫描git历史...")
        print("="*60)
        
        # 1. 获取git log
        commits = self.get_git_log()
        if not commits:
            print("❌ 没有找到任何提交记录")
            return
        
        print(f"✅ 找到 {len(commits)} 个版本")
        
        # 2. 生成Markdown
        print("\n📝 生成Markdown版本清单...")
        md_content = self.generate_markdown(commits)
        
        # 3. 保存文件
        print("\n💾 保存版本清单...")
        self.save_markdown(md_content)
        
        print("\n" + "="*60)
        print("✅ 版本追踪完成")
        print("="*60)
        print(f"\n📄 版本清单: {self.output_file}")
        print(f"📊 总版本数: {len(commits)}")
        print(f"📅 时间范围: {commits[-1]['date']} 至 {commits[0]['date']}")

if __name__ == '__main__':
    tracker = VersionTracker()
    tracker.run()
