#!/usr/bin/env python3
"""
测试单元3：三地同步验证测试

测试目标：
  运行 verify_sync.py，验证本地/GitHub/PA三地数据一致

测试类型：
  🤖 自动化测试（可重复运行）

前置条件：
  - 测试单元2已完成（GitHub Webhook触发成功）
  - PA可访问（https://froza.pythonanywhere.com）

运行方式：
  cd /Users/apangduo/WorkBuddy/Claw/etf-tool-mvp/
  python3 task_packages/sync_test_units/test_03_verify_sync.py
"""

import subprocess
import sys
import json
import time

def run_verify_sync():
    """运行 verify_sync.py 并解析输出"""
    print("=" * 60)
    print("测试单元3：运行 verify_sync.py")
    print("=" * 60)
    
    result = subprocess.run(
        [sys.executable, "verify_sync.py"],
        capture_output=True,
        text=True,
        cwd="/Users/apangduo/WorkBuddy/Claw/etf-tool-mvp"
    )
    
    output = result.stdout
    print(output)
    
    # 解析输出，检查是否有 ❌
    if "❌" in output:
        print("\n❌ 测试失败：verify_sync.py 检测到问题")
        print("\n问题详情：")
        for line in output.split("\n"):
            if "❌" in line:
                print(f"  {line.strip()}")
        return False
    else:
        print("\n✅ 测试通过：三地同步一致")
        return True

def check_pa_api_version():
    """检查PA的 /api/version 端点是否可访问"""
    print("\n--- 检查 PA /api/version ---")
    try:
        import requests
        resp = requests.get("https://froza.pythonanywhere.com/api/version", timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            print(f"✅ PA /api/version 可访问")
            print(f"   Version: {data.get('version')}")
            print(f"   Source: {data.get('source')}")
            return True
        else:
            print(f"❌ PA /api/version 返回 {resp.status_code}")
            return False
    except Exception as e:
        print(f"❌ PA /api/version 无法访问: {e}")
        return False

def main():
    # 1. 检查PA API
    if not check_pa_api_version():
        print("\n⚠️  PA API不可访问，测试终止")
        print("请先完成测试单元1和2")
        sys.exit(1)
    
    # 2. 运行 verify_sync.py
    success = run_verify_sync()
    
    # 3. 输出测试报告
    print("\n" + "=" * 60)
    print("测试单元3 报告")
    print("=" * 60)
    if success:
        print("✅ 通过")
        print("\n后续：所有测试单元已完成，三地同步方案可用")
    else:
        print("❌ 失败")
        print("\n后续：需要修复问题后重新测试")
        print("建议：检查 test_01 和 test_02 是否成功")
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
