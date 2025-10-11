#!/usr/bin/env python3
"""
测试透明背景功能的API脚本
"""
import requests
import json
import time
import os

def test_transparent_background():
    """测试透明背景功能"""
    
    # API基础URL
    base_url = "http://localhost:8000/api/v1/video"
    
    # 测试参数
    test_data = {
        'foreground_video': 'uploads/058868c1-61c7-4e74-bec0-380e4898e7f9.mp4',
        'name_text': '测试透明背景',
        'name_position': 'bottom-right',
        'font_size': 24,
        'font_color': 'white',
        'background_color': 'black@0.5',
        'use_tencent_matting': True
    }
    
    print("🎬 开始测试透明背景功能...")
    print(f"📁 前景视频: {test_data['foreground_video']}")
    
    # 检查视频文件是否存在
    if not os.path.exists(test_data['foreground_video']):
        print(f"❌ 视频文件不存在: {test_data['foreground_video']}")
        return False
    
    try:
        # 发送合成请求
        print("📤 发送视频合成请求...")
        response = requests.post(
            f"{base_url}/composite",
            data=test_data,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                job_id = result.get('data', {}).get('job_id')
                print(f"✅ 任务创建成功，Job ID: {job_id}")
                
                # 等待处理完成
                print("⏳ 等待处理完成...")
                time.sleep(20)
                
                # 检查处理结果
                progress_response = requests.get(f"{base_url}/progress/{job_id}")
                if progress_response.status_code == 200:
                    progress_data = progress_response.json()
                    print(f"📊 处理状态: {progress_data}")
                    
                    if progress_data.get('data', {}).get('status') == 'completed':
                        output_file = progress_data.get('data', {}).get('output_path')
                        print(f"🎉 处理完成！输出文件: {output_file}")
                        
                        # 检查输出文件
                        if output_file and os.path.exists(output_file):
                            file_size = os.path.getsize(output_file)
                            print(f"📁 文件大小: {file_size / 1024 / 1024:.2f} MB")
                            
                            # 提取一帧查看效果
                            test_frame = "outputs/api_test_frame.png"
                            os.system(f'ffmpeg -y -i "{output_file}" -vframes 1 "{test_frame}"')
                            
                            if os.path.exists(test_frame):
                                print(f"🖼️ 测试帧已保存: {test_frame}")
                                os.system(f'start "{test_frame}"')
                            
                            return True
                        else:
                            print(f"❌ 输出文件不存在: {output_file}")
                    else:
                        print(f"⚠️ 处理未完成，状态: {progress_data.get('data', {}).get('status')}")
                else:
                    print(f"❌ 获取进度失败: {progress_response.status_code}")
            else:
                print(f"❌ 任务创建失败: {result.get('message')}")
        else:
            print(f"❌ 请求失败: {response.status_code}")
            print(f"错误信息: {response.text}")
            
    except Exception as e:
        print(f"💥 测试异常: {str(e)}")
        return False
    
    return False

if __name__ == "__main__":
    print("=" * 50)
    print("🎯 透明背景功能测试")
    print("=" * 50)
    
    success = test_transparent_background()
    
    print("=" * 50)
    if success:
        print("✅ 测试成功！透明背景功能正常工作")
    else:
        print("❌ 测试失败，请检查日志")
    print("=" * 50)