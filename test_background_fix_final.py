#!/usr/bin/env python3
"""
测试背景应用修复效果
验证前后端参数匹配和背景图片处理流程
"""

import requests
import os
import time
import json

def test_background_upload():
    """测试背景图片上传和处理"""
    
    # API端点
    upload_url = "http://127.0.0.1:8000/api/v1/video/upload-and-process"
    
    # 测试文件路径
    video_file = "./uploads/6cc4fd5b-4483-4572-a66f-932b642e9b85.mp4"  # 使用之前的测试视频
    background_file = "./backgrounds/sitalk_background.png"  # 黄色背景图片
    
    if not os.path.exists(video_file):
        print(f"❌ 测试视频文件不存在: {video_file}")
        return False
        
    if not os.path.exists(background_file):
        print(f"❌ 背景图片文件不存在: {background_file}")
        return False
    
    print("🧪 开始测试背景应用修复...")
    print(f"📹 视频文件: {video_file}")
    print(f"🖼️ 背景图片: {background_file}")
    
    try:
        # 准备文件上传
        with open(video_file, 'rb') as vf, open(background_file, 'rb') as bf:
            files = {
                'file': ('test_video.mp4', vf, 'video/mp4'),
                'background_image': ('background.png', bf, 'image/png')  # 使用修复后的参数名
            }
            
            data = {
                'teacher_name': 'Test Teacher',
                'quality': 'medium',
                'output_format': 'mp4',
                'description': '测试背景应用修复'
            }
            
            print("📤 发送上传请求...")
            response = requests.post(upload_url, files=files, data=data, timeout=30)
            
        print(f"📊 响应状态码: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ 上传成功!")
            print(f"📋 响应数据: {json.dumps(result, indent=2, ensure_ascii=False)}")
            
            # 检查背景模式
            if result.get('data', {}).get('background_mode') == 'Combination':
                print("🎯 背景模式正确: Combination")
                return True
            else:
                print(f"❌ 背景模式错误: {result.get('data', {}).get('background_mode')}")
                return False
        else:
            print(f"❌ 上传失败: {response.status_code}")
            print(f"错误信息: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ 测试过程中出现错误: {str(e)}")
        return False

def main():
    """主测试函数"""
    print("=" * 50)
    print("🔧 背景应用修复测试")
    print("=" * 50)
    
    # 测试背景上传
    success = test_background_upload()
    
    print("\n" + "=" * 50)
    if success:
        print("✅ 测试通过! 背景应用修复成功")
        print("🎉 前后端参数匹配正常，应该能正确应用背景图片")
    else:
        print("❌ 测试失败! 需要进一步检查")
    print("=" * 50)

if __name__ == "__main__":
    main()