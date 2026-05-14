#!/usr/bin/env python3
"""
测试 PythonAnywhere API 连接
"""

import requests

API_TOKEN = "10188c344dc864597808b5744f37f5cb10e380ee"
USERNAME = "froza"

# 正确的 API 端点
API_BASE = f"https://www.pythonanywhere.com/api/v0/user/{USERNAME}"

headers = {
    "Authorization": f"Token {API_TOKEN}"
}

print("=" * 60)
print("🔍 测试 PythonAnywhere API 连接")
print("=" * 60)
print(f"用户名: {USERNAME}")
print(f"API Token: {API_TOKEN[:10]}...{API_TOKEN[-10:]}")
print("=" * 60)

# 测试1: 获取用户信息
print("\n📋 测试1: 获取用户信息")
url = f"{API_BASE}/"
try:
    response = requests.get(url, headers=headers, timeout=10)
    print(f"  状态码: {response.status_code}")
    if response.status_code == 200:
        print(f"  ✅ 成功: {response.json()}")
    else:
        print(f"  ❌ 失败: {response.text[:200]}")
except Exception as e:
    print(f"  ❌ 异常: {e}")

# 测试2: 列出文件（GET 方法）
print("\n📋 测试2: 列出 /home/froza/ 目录")
url = f"{API_BASE}/files/home/{USERNAME}/"
try:
    response = requests.get(url, headers=headers, timeout=10)
    print(f"  状态码: {response.status_code}")
    if response.status_code == 200:
        print(f"  ✅ 成功: {response.json()[:500]}")
    else:
        print(f"  ❌ 失败: {response.text[:200]}")
except Exception as e:
    print(f"  ❌ 异常: {e}")

# 测试3: 上传文件（PUT 方法）
print("\n📋 测试3: 上传测试文件")
url = f"{API_BASE}/files/home/{USERNAME}/test_api.txt"
try:
    response = requests.put(
        url,
        headers=headers,
        data=b"Hello from API!",
        timeout=10
    )
    print(f"  状态码: {response.status_code}")
    if response.status_code in [200, 201, 204]:
        print(f"  ✅ 上传成功!")
    else:
        print(f"  ❌ 失败: {response.text[:200]}")
except Exception as e:
    print(f"  ❌ 异常: {e}")

# 测试4: 删除测试文件
print("\n📋 测试4: 删除测试文件")
try:
    response = requests.delete(
        url,
        headers=headers,
        timeout=10
    )
    print(f"  状态码: {response.status_code}")
    if response.status_code in [200, 204]:
        print(f"  ✅ 删除成功!")
    else:
        print(f"  ❌ 失败: {response.text[:200]}")
except Exception as e:
    print(f"  ❌ 异常: {e}")

print("\n" + "=" * 60)
print("🏁 测试完成")
print("=" * 60)
