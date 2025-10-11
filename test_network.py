#!/usr/bin/env python3
import requests
import sys
import time
sys.path.append('.')

from app.services.tencent_video_service import TencentVideoService

def test_network():
    print("=== 网络连接测试 ===")
    
    service = TencentVideoService()
    
    # 1. 测试基本网络连接
    print("1. 测试基本网络连接...")
    try:
        response = requests.get("https://www.baidu.com", timeout=10)
        print(f"✅ 基本网络正常: {response.status_code}")
    except Exception as e:
        print(f"❌ 基本网络失败: {e}")
        return
    
    # 2. 测试腾讯云域名解析
    print("2. 测试腾讯云COS域名...")
    cos_host = f"{service.bucket_name}.cos.{service.region}.myqcloud.com"
    try:
        response = requests.head(f"https://{cos_host}", timeout=10)
        print(f"✅ COS域名可访问: {response.status_code}")
    except Exception as e:
        print(f"❌ COS域名访问失败: {e}")
        print(f"   域名: {cos_host}")
    
    # 3. 测试万象域名
    print("3. 测试腾讯云万象域名...")
    ci_host = f"{service.bucket_name}.ci.{service.region}.myqcloud.com"
    try:
        response = requests.head(f"https://{ci_host}", timeout=10)
        print(f"✅ 万象域名可访问: {response.status_code}")
    except Exception as e:
        print(f"❌ 万象域名访问失败: {e}")
        print(f"   域名: {ci_host}")
    
    # 4. 测试小文件上传
    print("4. 测试小文件上传...")
    try:
        # 创建一个小测试文件
        test_content = b"Hello Tencent COS Test"
        test_file = "test_small.txt"
        with open(test_file, 'wb') as f:
            f.write(test_content)
        
        print(f"   创建测试文件: {test_file} ({len(test_content)} bytes)")
        
        # 生成签名和URL
        object_key = "test/small_file.txt"
        host = f"{service.bucket_name}.cos.{service.region}.myqcloud.com"
        uri = f"/{object_key}"
        url = f"https://{host}{uri}"
        
        authorization = service._generate_authorization("PUT", uri)
        
        headers = {
            'Authorization': authorization,
            'Host': host,
        }
        
        print(f"   上传URL: {url}")
        print(f"   开始上传...")
        
        start_time = time.time()
        response = requests.put(url, data=test_content, headers=headers, timeout=30)
        elapsed = time.time() - start_time
        
        print(f"   上传耗时: {elapsed:.2f}秒")
        print(f"   响应状态: {response.status_code}")
        
        if response.status_code in [200, 201]:
            print("✅ 小文件上传成功！")
        else:
            print(f"❌ 小文件上传失败: {response.text}")
            
        # 清理测试文件
        import os
        os.remove(test_file)
        
    except Exception as e:
        print(f"❌ 小文件上传测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_network()
