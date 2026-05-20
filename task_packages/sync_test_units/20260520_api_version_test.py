#!/usr/bin/env python3
"""
测试单元7：/api/version 端点测试

测试目标：
  测试 Flask 应用的 /api/version 端点是否返回正确的数据

测试类型：
  🤖 自动化测试（可重复运行）

前置条件：
  - Flask 应用运行在 https://froza.pythonanywhere.com
  - 或直接运行本地 Flask 应用

运行方式：
  cd /Users/apangduo/WorkBuddy/Claw/etf-tool-mvp/
  python3 task_packages/sync_test_units/test_07_api_version.py
"""

import requests
import json
import sys

BASE_URL = "https://froza.pythonanywhere.com"

def test_api_version():
    """测试 /api/version 端点"""
    print("=" * 60)
    print("测试单元7：/api/version 端点测试")
    print("=" * 60)
    
    url = f"{BASE_URL}/api/version"
    print(f"\n请求: {url}")
    
    try:
        resp = requests.get(url, timeout=10)
        print(f"状态码: {resp.status_code}")
        
        if resp.status_code != 200:
            print(f"❌ 期望 200，实际 {resp.status_code}")
            print(f"响应: {resp.text[:500]}")
            return False
        
        data = resp.json()
        print(f"\n响应数据:")
        print(json.dumps(data, indent=2, ensure_ascii=False))
        
        # 验证必要字段
        required_fields = ["version", "source", "etf_count", "checksum"]
        missing = [f for f in required_fields if f not in data]
        if missing:
            print(f"\n❌ 缺少字段: {missing}")
            return False
        
        print(f"\n✅ 所有必要字段存在")
        print(f"  version: {data['version']}")
        print(f"  source: {data['source']}")
        print(f"  etf_count: {data['etf_count']}")
        
        return True
        
    except requests.exceptions.ConnectionError as e:
        print(f"❌ 连接失败: {e}")
        print(f"\n提示: 如果测试本地应用，修改 BASE_URL 为 http://localhost:5000")
        return False
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False

def main():
    success = test_api_version()
    
    print("\n" + "=" * 60)
    print("测试单元7 报告")
    print("=" * 60)
    if success:
        print("✅ 通过")
        print("\n后续: 可以继续测试单元8 (/api/sync)")
    else:
        print("❌ 失败")
        print("\n后续: 检查 PA 部署状态 (测试单元1)")
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
