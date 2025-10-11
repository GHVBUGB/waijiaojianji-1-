#!/usr/bin/env python3
import requests
import sys
import urllib3
sys.path.append('.')

# 禁用SSL警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

from app.services.tencent_video_service import TencentVideoService

def test_network_simple():
    print("=== 简化网络测试 ===")
    
    # 1. 测试HTTP连接（不用HTTPS）
    print("1. 测试HTTP连接...")
    try:
        response = requests.get("http://httpbin.org/get", timeout=10)
        print(f"✅ HTTP连接正常: {response.status_code}")
    except Exception as e:
        print(f"❌ HTTP连接失败: {e}")
        return
    
    # 2. 测试HTTPS但忽略SSL验证
    print("2. 测试HTTPS（忽略SSL验证）...")
    try:
        response = requests.get("https://httpbin.org/get", timeout=10, verify=False)
        print(f"✅ HTTPS连接正常: {response.status_code}")
    except Exception as e:
        print(f"❌ HTTPS连接失败: {e}")
    
    # 3. 测试腾讯云COS（忽略SSL验证）
    service = TencentVideoService()
    cos_host = f"{service.bucket_name}.cos.{service.region}.myqcloud.com"
    print(f"3. 测试腾讯云COS: {cos_host}")
    
    try:
        response = requests.head(f"https://{cos_host}", timeout=15, verify=False)
        print(f"✅ COS可访问: {response.status_code}")
        
        # 如果COS可访问，尝试小文件上传
        print("4. 尝试小文件上传（忽略SSL验证）...")
        test_content = b"test"
        object_key = "test/network_test.txt"
        uri = f"/{object_key}"
        url = f"https://{cos_host}{uri}"
        
        authorization = service._generate_authorization("PUT", uri)
        headers = {
            'Authorization': authorization,
            'Host': cos_host,
        }
        
        response = requests.put(url, data=test_content, headers=headers, timeout=30, verify=False)
        print(f"   上传响应: {response.status_code}")
        
        if response.status_code in [200, 201]:
            print("✅ 小文件上传成功！网络和权限都正常")
        else:
            print(f"❌ 上传失败: {response.text[:200]}")
            
    except Exception as e:
        print(f"❌ COS访问失败: {e}")
        
    print("\n建议:")
    print("1. 如果是公司网络，可能需要配置代理")
    print("2. 如果是防火墙问题，需要允许HTTPS连接")
    print("3. 可以尝试使用手机热点测试")

if __name__ == "__main__":
    test_network_simple()
