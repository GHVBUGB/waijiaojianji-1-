#!/usr/bin/env python3
import requests
import os

def test_upload():
    print("=== 测试文件上传API ===")
    
    # 测试文件路径
    test_file = "uploads/058868c1-61c7-4e74-bec0-380e4898e7f9.mp4"
    
    if not os.path.exists(test_file):
        print(f"❌ 测试文件不存在: {test_file}")
        return
    
    print(f"✅ 测试文件: {test_file}")
    print(f"📁 文件大小: {os.path.getsize(test_file) / (1024*1024):.2f}MB")
    
    # 准备上传数据
    files = {
        'file': ('test_video.mp4', open(test_file, 'rb'), 'video/mp4')
    }
    
    data = {
        'teacher_name': '测试外教',
        'language_hint': 'zh-CN',
        'description': '测试上传'
    }
    
    try:
        print("📤 开始上传...")
        response = requests.post(
            'http://localhost:8000/api/v1/video/upload-and-process',
            files=files,
            data=data,
            timeout=30
        )
        
        print(f"📡 响应状态: {response.status_code}")
        print(f"📄 响应内容: {response.text}")
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                print("✅ 上传成功！")
                print(f"🆔 任务ID: {result['data']['job_id']}")
            else:
                print(f"❌ 上传失败: {result.get('message')}")
        else:
            print(f"❌ HTTP错误: {response.status_code}")
            
    except Exception as e:
        print(f"❌ 上传异常: {e}")
    finally:
        files['file'][1].close()

if __name__ == "__main__":
    test_upload()
