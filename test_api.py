import requests
import time
import json

def test_health_check():
    """测试健康检查接口"""
    try:
        response = requests.get("http://localhost:8000/api/v1/health/", timeout=5)
        print(f"健康检查状态码: {response.status_code}")
        if response.status_code == 200:
            print(f"健康检查结果: {response.json()}")
            return True
        else:
            print(f"健康检查失败: {response.text}")
            return False
    except Exception as e:
        print(f"健康检查异常: {e}")
        return False

def test_root_page():
    """测试根页面"""
    try:
        response = requests.get("http://localhost:8000/", timeout=5)
        print(f"根页面状态码: {response.status_code}")
        if response.status_code == 200:
            print("根页面访问成功")
            return True
        else:
            print(f"根页面访问失败: {response.text}")
            return False
    except Exception as e:
        print(f"根页面访问异常: {e}")
        return False

def test_api_docs():
    """测试API文档"""
    try:
        response = requests.get("http://localhost:8000/docs", timeout=5)
        print(f"API文档状态码: {response.status_code}")
        if response.status_code == 200:
            print("API文档访问成功")
            return True
        else:
            print(f"API文档访问失败: {response.text}")
            return False
    except Exception as e:
        print(f"API文档访问异常: {e}")
        return False

def main():
    print("开始测试外教视频处理系统API...")
    print("=" * 50)

    # 等待服务完全启动
    print("等待服务启动...")
    time.sleep(2)

    tests = [
        ("根页面", test_root_page),
        ("健康检查", test_health_check),
        ("API文档", test_api_docs)
    ]

    results = []
    for test_name, test_func in tests:
        print(f"\n测试 {test_name}...")
        result = test_func()
        results.append((test_name, result))

    print("\n" + "=" * 50)
    print("测试结果汇总:")
    for test_name, result in results:
        status = "PASS" if result else "FAIL"
        print(f"{test_name}: {status}")

    passed = sum(1 for _, result in results if result)
    total = len(results)
    print(f"\n总计: {passed}/{total} 测试通过")

    if passed == total:
        print("所有测试通过！系统运行正常")
    else:
        print("部分测试失败，请检查服务状态")

if __name__ == "__main__":
    main()