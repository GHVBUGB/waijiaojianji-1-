#!/usr/bin/env python3
"""
测试修复后的万象API调用
"""
import os
import sys
import requests
import json
import time
from datetime import datetime
import tempfile
from PIL import Image

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def create_test_video():
    """创建一个简单的测试视频文件"""
    import cv2
    import numpy as np
    
    # 创建临时视频文件
    temp_video = tempfile.NamedTemporaryFile(suffix='.mp4', delete=False)
    temp_video.close()
    
    # 创建一个简单的视频（红色背景，白色方块移动）
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(temp_video.name, fourcc, 10.0, (640, 480))
    
    for i in range(30):  # 3秒视频
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        frame[:, :] = [0, 0, 255]  # 红色背景
        
        # 添加一个移动的白色方块
        x = (i * 20) % 600
        cv2.rectangle(frame, (x, 200), (x+40, 240), (255, 255, 255), -1)
        
        out.write(frame)
    
    out.release()
    return temp_video.name

def create_test_background():
    """创建一个测试背景图片"""
    temp_bg = tempfile.NamedTemporaryFile(suffix='.jpg', delete=False)
    temp_bg.close()
    
    # 创建蓝色背景图片
    img = Image.new('RGB', (640, 480), color='blue')
    img.save(temp_bg.name, 'JPEG')
    
    return temp_bg.name

def test_api_call():
    """测试API调用"""
    print("🎬 开始测试修复后的万象API调用")
    
    # 创建测试文件
    print("📹 创建测试视频...")
    video_path = create_test_video()
    
    print("🖼️ 创建测试背景图片...")
    bg_path = create_test_background()
    
    try:
        # 准备文件
        with open(video_path, 'rb') as vf, open(bg_path, 'rb') as bf:
            files = {
                'video': ('test_video.mp4', vf, 'video/mp4'),
                'background': ('test_bg.jpg', bf, 'image/jpeg')
            }
            
            data = {
                'mode': 'combination',
                'threshold': '0.3'
            }
            
            print("📡 发送API请求...")
            response = requests.post(
                'http://localhost:8000/api/v1/video/upload-and-process',
                files={
                    'file': ('test_video.mp4', vf, 'video/mp4'),
                    'background_file': ('test_bg.jpg', bf, 'image/jpeg')
                },
                data={
                    'teacher_name': 'Test Teacher',
                    'quality': 'medium'
                },
                timeout=60
            )
            
            print(f"📊 响应状态码: {response.status_code}")
            print(f"📄 响应内容: {response.text}")
            
            if response.status_code == 200:
                result = response.json()
                job_id = result.get('data', {}).get('job_id')  # 修正JSON结构
                
                if job_id:
                    print(f"✅ 任务提交成功，Job ID: {job_id}")
                    
                    # 监控任务状态
                    print("⏳ 监控任务状态...")
                    for i in range(30):  # 最多等待5分钟
                        time.sleep(10)
                        
                        status_response = requests.get(
                            f'http://localhost:8000/api/v1/video/progress/{job_id}',
                            timeout=30
                        )
                        
                        if status_response.status_code == 200:
                            status_data = status_response.json()
                            progress_data = status_data.get('data', {})
                            status = progress_data.get('status')
                            print(f"📊 任务状态 ({i+1}/30): {status}")
                            
                            if status == 'completed':
                                print("🎉 任务处理成功！")
                                # 尝试获取下载链接
                                results_response = requests.get(
                                    f'http://localhost:8000/api/v1/video/results/{job_id}',
                                    timeout=30
                                )
                                if results_response.status_code == 200:
                                    results_data = results_response.json()
                                    output_path = results_data.get('data', {}).get('output_path')
                                    if output_path:
                                        print(f"📥 输出文件: {output_path}")
                                break
                            elif status == 'failed':
                                error_msg = progress_data.get('error', '未知错误')
                                print(f"❌ 任务处理失败: {error_msg}")
                                break
                        else:
                            print(f"⚠️ 状态查询失败: {status_response.status_code}")
                    else:
                        print("⏰ 任务监控超时")
                else:
                    print("❌ 未获取到Job ID")
            else:
                print(f"❌ API调用失败: {response.status_code}")
                print(f"错误信息: {response.text}")
                
    except Exception as e:
        print(f"💥 测试过程中发生异常: {str(e)}")
    
    finally:
        # 清理临时文件
        try:
            os.unlink(video_path)
            os.unlink(bg_path)
            print("🧹 临时文件已清理")
        except:
            pass

if __name__ == "__main__":
    test_api_call()