#!/usr/bin/env python3
"""
pa_auto_pull_setup.py - PythonAnywhere 自动拉取配置助手

功能：
1. 打印 PythonAnywhere 配置自动拉取的步骤
2. 生成 crontab 配置命令
3. 测试当前配置是否工作

使用方式：
    # 在本地运行，查看配置说明
    python3 pa_auto_pull_setup.py
    
    # 在 PythonAnywhere 上运行，执行配置
    python3 pa_auto_pull_setup.py --run
"""

import os
import sys
import argparse
from pathlib import Path

def print_setup_guide():
    """打印配置指南"""
    print("=" * 70)
    print("PythonAnywhere 自动拉取配置指南")
    print("=" * 70)
    print()
    print("📋 配置目标：")
    print("   - 每 10 分钟自动从 GitHub 拉取最新数据")
    print("   - 确保本地、GitHub、PythonAnywhere 三地数据同步")
    print("   - 同步窗口：不超过 10 分钟")
    print()
    print("🔧 配置步骤：")
    print()
    print("步骤 1: 登录 PythonAnywhere")
    print("   - 访问 https://www.pythonanywhere.com/")
    print("   - 登录你的账号")
    print()
    print("步骤 2: 打开 Console (控制台)")
    print("   - 点击 'Consoles' 标签")
    print("   - 打开一个 Bash console")
    print()
    print("步骤 3: 进入项目目录")
    print("   输入命令：")
    print("   cd /path/to/your/etf-tool-mvp")
    print("   (默认路径可能是 ~/ETF-tool-MVP 或类似)")
    print()
    print("步骤 4: 编辑 crontab")
    print("   输入命令：")
    print("   crontab -e")
    print()
    print("步骤 5: 添加定时任务")
    print("   在打开的编辑器中，添加以下行：")
    print()
    
    # 生成 cron 命令
    repo_path = os.environ.get('PA_PROJECT_PATH', '/home/froza/ETF-tool-MVP')
    log_path = f"{repo_path}/logs/auto_pull.log"
    cron_cmd = f"*/10 * * * * cd {repo_path} && git pull origin main >> {log_path} 2>&1"
    
    print(f"   {cron_cmd}")
    print()
    print("   说明：")
    print("   - */10 * * * * : 每 10 分钟执行一次")
    print(f"   - cd {repo_path} : 进入项目目录")
    print("   - git pull origin main : 从 GitHub 拉取最新代码")
    print(f"   - >> {log_path} 2>&1 : 记录日志")
    print()
    print("步骤 6: 保存并退出")
    print("   - 按 ESC，然后输入 :wq 保存退出")
    print()
    print("步骤 7: 验证配置")
    print("   输入命令：")
    print("   crontab -l")
    print("   应该能看到刚才添加的任务")
    print()
    print("=" * 70)
    print("✅ 配置完成！PythonAnywhere 将每 10 分钟自动同步数据")
    print("=" * 70)
    print()
    print("💡 提示：")
    print("   - 如果想立即测试，可以手动运行：")
    print(f"     cd {repo_path} && git pull origin main")
    print("   - 查看日志：")
    print(f"     tail -f {log_path}")
    print()

def generate_cron_command():
    """生成 crontab 命令"""
    repo_path = os.environ.get('PA_PROJECT_PATH', '/home/froza/ETF-tool-MVP')
    log_path = f"{repo_path}/logs/auto_pull.log"
    
    cron_cmd = f"*/10 * * * * cd {repo_path} && git pull origin main >> {log_path} 2>&1"
    
    print("Crontab 命令：")
    print("-" * 70)
    print(cron_cmd)
    print("-" * 70)
    print()
    print("复制上面的命令，然后运行: crontab -e")
    print("在编辑器中粘贴这一行，保存退出")
    print()
    
    return cron_cmd

def test_pull():
    """测试 git pull 是否工作"""
    print("测试 git pull...")
    print("-" * 70)
    
    # 检查当前目录
    cwd = os.getcwd()
    print(f"当前目录: {cwd}")
    
    # 检查是否是 git 仓库
    if not Path(".git").exists():
        print("❌ 当前目录不是 Git 仓库")
        return False
    
    # 测试 git pull
    import subprocess
    try:
        result = subprocess.run(
            ['git', 'pull', 'origin', 'main'],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        print(f"退出码: {result.returncode}")
        print(f"输出: {result.stdout}")
        
        if result.returncode == 0:
            print("✅ Git pull 成功")
            return True
        else:
            print(f"❌ Git pull 失败: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description='PythonAnywhere 自动拉取配置助手')
    parser.add_argument('--run', action='store_true', help='执行配置（在 PA 上运行）')
    parser.add_argument('--test', action='store_true', help='测试 git pull')
    parser.add_argument('--cron', action='store_true', help='仅生成 crontab 命令')
    
    args = parser.parse_args()
    
    if args.cron:
        generate_cron_command()
    elif args.test:
        test_pull()
    elif args.run:
        print("在 PythonAnywhere 上执行配置...")
        print()
        print("步骤 1: 生成 crontab 命令")
        cron_cmd = generate_cron_command()
        
        print()
        print("步骤 2: 请手动执行以下命令：")
        print("   crontab -e")
        print("   然后粘贴上面的命令，保存退出")
        print()
        print("步骤 3: 验证配置")
        print("   crontab -l")
    else:
        print_setup_guide()

if __name__ == '__main__':
    main()
