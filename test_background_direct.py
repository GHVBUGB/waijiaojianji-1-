#!/usr/bin/env python3
"""
直接测试背景图片上传和视频处理功能
"""

import requests
import os
import time
import json

# 服务器配置
BASE_URL = "http://127.0.0.1:8000"
BACKGROUND_PATH = r"C:\Users\guhongji001\Desktop\44\backgrounds\sitalk_background.svg"
VIDEO_PATH = r"C:\Users\guhongji001\Desktop\44\uploads"

def test_background_upload():
    """测试背景图片上传"""
    print("🔍 测试背景图片上传...")
    
    if not os.path.exists(BACKGROUND_PATH):
        print(f"❌ 背景图片不存在: {BACKGROUND_PATH}")
        return None
    
    # 准备上传数据
    files = {
        'background_image': ('sitalk_background.svg', open(BACKGROUND_PATH, 'rb'), 'image/svg+xml')
    }
    
    try:
        # 发送上传请求
        response = requests.post(f"{BASE_URL}/api/v1/video/process", files=files)
        print(f"📡 响应状态码: {response.status_code}")
        print(f"📄 响应内容: {response.text}")
        
        if response.status_code == 200:
            print("✅ 背景图片上传成功")
            return response.json()
        else:
            print(f"❌ 背景图片上传失败: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"❌ 上传过程中出错: {e}")
        return None
    finally:
        files['background_image'][1].close()

def test_video_with_background():
    """测试带背景的视频处理"""
    print("\n🎬 测试带背景的视频处理...")
    
    # 查找一个测试视频
    video_files = [f for f in os.listdir(VIDEO_PATH) if f.endswith('.mp4')]
    if not video_files:
        print("❌ 没有找到测试视频文件")
        return None
    
    test_video = os.path.join(VIDEO_PATH, video_files[0])
    print(f"📹 使用测试视频: {test_video}")
    
    # 准备上传数据
    files = {
        'file': (video_files[0], open(test_video, 'rb'), 'video/mp4'),
        'background_file': ('sitalk_background.png', open(BACKGROUND_PATH, 'rb'), 'image/png')
    }
    
    data = {
        'teacher_name': '测试外教',
        'quality': 'medium',
        'output_format': 'mp4',
        'description': '背景替换测试'
    }
    
    try:
        print("📤 开始上传视频和背景图片...")
        response = requests.post(f"{BASE_URL}/api/v1/video/upload-and-process", files=files, data=data)
        
        print(f"📡 响应状态码: {response.status_code}")
        print(f"📄 响应内容: {response.text}")
        
        if response.status_code == 200:
            result = response.json()
            job_id = result.get('data', {}).get('job_id')
            print(f"✅ 任务提交成功，任务ID: {job_id}")
            
            # 监控任务进度
            if job_id:
                monitor_task_progress(job_id)
            
            return result
        else:
            print(f"❌ 视频处理失败: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"❌ 处理过程中出错: {e}")
        return None
    finally:
        files['file'][1].close()
        files['background_file'][1].close()

def monitor_task_progress(task_id):
    """监控任务进度"""
    print(f"\n📊 监控任务进度: {task_id}")
    
    max_attempts = 30  # 最多等待5分钟
    attempt = 0
    
    while attempt < max_attempts:
        try:
            response = requests.get(f"{BASE_URL}/api/v1/video/progress/{task_id}")
            
            if response.status_code == 200:
                progress = response.json()
                status = progress.get('status', 'unknown')
                message = progress.get('message', '')
                
                print(f"⏳ 状态: {status} - {message}")
                
                if status == 'completed':
                    print("🎉 任务完成!")
                    result_url = progress.get('result_url')
                    if result_url:
                        print(f"📹 结果视频: {result_url}")
                    break
                elif status == 'failed':
                    print("❌ 任务失败!")
                    error = progress.get('error', '未知错误')
                    print(f"🚫 错误信息: {error}")
                    break
                    
            else:
                print(f"❌ 获取进度失败: {response.status_code}")
                
        except Exception as e:
            print(f"❌ 监控过程中出错: {e}")
            
        attempt += 1
        time.sleep(10)  # 等待10秒后再次检查
    
    if attempt >= max_attempts:
        print("⏰ 监控超时，请手动检查任务状态")

def main():
    """主函数"""
    print("🚀 开始背景图片上传和视频处理测试")
    print("=" * 50)
    
    # 检查服务器是否运行
    try:
        response = requests.get(f"{BASE_URL}/api/v1/health")
        if response.status_code != 200:
            print("❌ 服务器未运行，请先启动服务器")
            return
    except:
        print("❌ 无法连接到服务器，请确认服务器已启动")
        return
    
    print("✅ 服务器连接正常")
    
    # 测试背景图片上传和视频处理
    background_path = r"C:\Users\guhongji001\Desktop\44\backgrounds\sitalk_background.png"
    video_path = r"C:\Users\guhongji001\Desktop\44\test_video.mp4"
    result = test_video_with_background()
    
    if result:
        print("\n🎯 测试总结:")
        print("✅ 背景图片和视频上传成功")
        print("✅ 任务提交成功")
        print("📝 请查看日志文件了解详细处理过程")
    else:
        print("\n❌ 测试失败，请检查错误信息")

if __name__ == "__main__":
    main()