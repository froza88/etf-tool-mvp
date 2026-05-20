#!/usr/bin/env python3
"""
测试单元8：/api/sync 端点测试

测试目标：
  测试 Flask 应用的 /api/sync 端点是否能正确触发 PA 数据同步

测试类型：
  🤖 自动化测试（可重复运行）

前置条件：
  - PA 应用运行在 https://froza.pythonanywhere.com
  - /api/sync 端点已部署

运行方式：
  cd /Users/apangduo/WorkBuddy/Claw/etf-tool-mvp/
  python3 task_packages/sync_test_units/test_08_api_sync.py
"""

import requests
import json
import sys
import time

BASE_URL = "https://froza.pythonanywhere.com"

def test_api_sync():
    """测试 /api/sync 端点"""
    print("=" * 60)
    print("测试单元8：/api/sync 端点测试")
    print("=" * 60)
    
    url = f"{BASE_URL}/api/sync"
    print(f"\nPOST 请求: {url}")
    
    try:
        resp = requests.post(url, timeout=30)
        print(f"状态码: {resp.status_code}")
        
        if resp.status_code != 200:
            print(f"❌ 期望 200，实际 {resp.status_code}")
            print(f"响应: {resp.text[:500]}")
            return False
        
        data = resp.json()
        print(f"\n响应数据:")
        print(json.dumps(data, indent=2, ensure_ascii=False))
        
        # 验证必要字段
        if data.get("status") != "success":
            print(f"\n❌ status 不是 'success': {data.get('status')}")
            return False
        
        print(f"\n✅ /api/sync 执行成功")
        print(f"  git_output: {data.get('git_output', '')[:100]}...")
        print(f"  version_output: {data.get('version_output', '')[:100]}...")
        
        return True
        
    except requests.exceptions.ConnectionError as e:
        print(f"❌ 连接失败: {e}")
        return False
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False

def main():
    success = test_api_sync()
    
    print("\n" + "=" * 60)
    print("测试单元8 报告")
    print("=" * 60)
    if success:
        print("✅ 通过")
        print("\n后续: 所有核心测试已完成")
        print("  建议: 运行 test_03_verify_sync.py 做端到端验证")
    else:
        print("❌ 失败")
        print("\n后续: 检查 PA 部署状态 (测试单元1)")
        print("  可能原因: /api/sync 端点有 bug")
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
