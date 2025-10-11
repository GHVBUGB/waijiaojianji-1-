#!/usr/bin/env python3
"""
简单检查视频处理任务状态
"""

import requests
import json

BASE_URL = "http://127.0.0.1:8000"
JOB_ID = "909faaac-df5a-4de5-bfbb-36fc4da1f767"

def check_job_status():
    """检查任务状态"""
    print(f"🔍 检查任务状态: {JOB_ID}")
    print("=" * 60)
    
    try:
        # 检查任务进度
        print("📊 检查任务进度...")
        response = requests.get(f"{BASE_URL}/api/v1/video/progress/{JOB_ID}")
        print(f"📡 进度状态码: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"📄 进度内容: {json.dumps(data, indent=2, ensure_ascii=False)}")
        else:
            print(f"❌ 获取进度失败: {response.text}")
        
        print("\n" + "-" * 40)
        
        # 检查任务结果
        print("📋 检查任务结果...")
        response = requests.get(f"{BASE_URL}/api/v1/video/results/{JOB_ID}")
        print(f"📡 结果状态码: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"📄 结果内容: {json.dumps(data, indent=2, ensure_ascii=False)}")
            
            # 检查是否有下载链接
            if data.get('success') and data.get('data'):
                result_data = data['data']
                if 'download_url' in result_data:
                    print(f"🔗 下载链接: {result_data['download_url']}")
                if 'background_url' in result_data:
                    print(f"🖼️ 背景URL: {result_data['background_url']}")
                if 'status' in result_data:
                    print(f"📊 任务状态: {result_data['status']}")
        else:
            print(f"❌ 获取结果失败: {response.text}")
            
    except Exception as e:
        print(f"❌ 检查失败: {e}")
    
    print("\n" + "=" * 60)
    print("✅ 检查完成")

if __name__ == "__main__":
    check_job_status()