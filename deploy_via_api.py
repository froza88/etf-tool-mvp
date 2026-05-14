#!/usr/bin/env python3
"""
PythonAnywhere 自动化部署脚本 (API 版本)
使用 PythonAnywhere Files API 上传文件
"""

import os
import sys
import requests
from pathlib import Path

# ========== 配置区 ==========
API_TOKEN = "10188c344dc864597808b5744f37f5cb10e380ee"
USERNAME = "froza"
DOMAIN = f"{USERNAME}.pythonanywhere.com"
API_BASE = f"https://www.pythonanywhere.com/api/v0/user/{USERNAME}"

LOCAL_DIR = Path("/Users/apangduo/WorkBuddy/Claw/etf-tool-mvp")

# 要上传的关键文件（避免上传多余文件）
INCLUDE_EXTENSIONS = {
    ".py", ".json", ".html", ".txt", ".md", ".css", ".js", ".png", ".jpg", ".gif"
}

EXCLUDE_DIRS = {"__pycache__", "venv", ".venv", ".git", "node_modules", "tests"}
# =============================


def get_headers():
    """获取 API 请求头"""
    return {
        "Authorization": f"Token {API_TOKEN}",
        "Content-Type": "application/octet-stream"
    }


def upload_file(local_path: Path, remote_path: str):
    """上传单个文件到 PythonAnywhere"""
    url = f"{API_BASE}/files/{remote_path}"
    
    try:
        with open(local_path, "rb") as f:
            content = f.read()
        
        headers = {
            "Authorization": f"Token {API_TOKEN}",
            "Content-Type": "application/octet-stream"
        }
        
        # 使用 PUT 方法上传文件
        response = requests.put(url, headers=headers, data=content, timeout=30)
        
        if response.status_code in [200, 201, 204]:
            print(f"  ✅ {remote_path}")
            return True
        else:
            print(f"  ❌ {remote_path} ({response.status_code})")
            print(f"     {response.text[:100]}")
            return False
    
    except Exception as e:
        print(f"  ❌ {remote_path}: {e}")
        return False


def upload_key_files():
    """上传关键文件"""
    print("📤 开始上传文件...\n")
    
    uploaded = 0
    failed = 0
    
    # 1. 上传根目录的 Python 文件
    print("📦 核心 Python 文件:")
    for py_file in LOCAL_DIR.glob("*.py"):
        if py_file.name.startswith("test_") or py_file.name.startswith("auto_update"):
            continue
        remote_path = f"/home/{USERNAME}/mysite/{py_file.name}"
        if upload_file(py_file, remote_path):
            uploaded += 1
        else:
            failed += 1
    
    # 2. 上传 JSON 数据文件
    print("\n📊 数据文件:")
    for json_file in LOCAL_DIR.glob("*.json"):
        remote_path = f"/home/{USERNAME}/mysite/{json_file.name}"
        if upload_file(json_file, remote_path):
            uploaded += 1
        else:
            failed += 1
    
    # 3. 上传 HTML 文件
    print("\n🌐 模板文件:")
    templates_dir = LOCAL_DIR / "templates"
    if templates_dir.exists():
        for html_file in templates_dir.rglob("*.html"):
            relative_path = html_file.relative_to(LOCAL_DIR)
            remote_path = f"/home/{USERNAME}/mysite/{relative_path}"
            if upload_file(html_file, remote_path):
                uploaded += 1
            else:
                failed += 1
    
    # 4. 上传 requirements.txt
    print("\n📦 依赖文件:")
    req_file = LOCAL_DIR / "requirements.txt"
    if req_file.exists():
        remote_path = f"/home/{USERNAME}/mysite/requirements.txt"
        if upload_file(req_file, remote_path):
            uploaded += 1
        else:
            failed += 1
    
    return uploaded, failed


def reload_webapp():
    """重新加载 Web 应用"""
    url = f"{API_BASE}/webapps/{DOMAIN}/reload/"
    
    print(f"\n🔄 重新加载 Web 应用...")
    response = requests.post(url, headers={
        "Authorization": f"Token {API_TOKEN}"
    }, timeout=30)
    
    if response.status_code == 200:
        print("✅ Web 应用已重新加载")
        return True
    else:
        print(f"❌ 重新加载失败 ({response.status_code})")
        print(f"   {response.text[:200]}")
        return False


def main():
    print("=" * 60)
    print("🚀 PythonAnywhere 自动化部署 (API 版本)")
    print("=" * 60)
    print(f"用户: {USERNAME}")
    print(f"域名: {DOMAIN}")
    print("=" * 60)
    
    # 检查 API Token
    print("\n🔍 验证 API Token...")
    response = requests.get(f"{API_BASE}/", headers={
        "Authorization": f"Token {API_TOKEN}"
    })
    
    if response.status_code != 200:
        print(f"❌ API Token 无效 ({response.status_code})")
        print(f"   {response.text[:200]}")
        sys.exit(1)
    
    print("✅ API Token 有效\n")
    
    # 上传文件
    uploaded, failed = upload_key_files()
    
    print("\n" + "=" * 60)
    print(f"📊 上传完成: 成功 {uploaded} 个, 失败 {failed} 个")
    print("=" * 60)
    
    if failed > 0:
        print("\n⚠️  部分文件上传失败，请检查错误信息")
        choice = input("是否继续重新加载 Web 应用？(y/n): ")
        if choice.lower() != 'y':
            sys.exit(1)
    
    # 重新加载 Web 应用
    if reload_webapp():
        print("\n" + "=" * 60)
        print("✅ 部署完成！")
        print(f"🌐 访问: https://{DOMAIN}")
        print("=" * 60)
    else:
        print("\n⚠️  文件已上传，但 Web 应用重新加载失败")
        print("请手动在 PythonAnywhere 控制台点击 'Reload'")


if __name__ == "__main__":
    try:
        # 安装依赖
        import requests
    except ImportError:
        print("❌ 缺少 requests 库，正在安装...")
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "requests"])
        import requests
    
    main()
