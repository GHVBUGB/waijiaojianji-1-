#!/usr/bin/env python3
"""
测试用户背景图片功能
"""
import requests
import os
import json
from pathlib import Path

def test_background_with_existing_image():
    """使用现有的sitalk_background.png测试背景功能"""
    print("=== 测试现有背景图片功能 ===")
    
    # 检查现有背景图片
    bg_path = "backgrounds/sitalk_background.png"
    if not os.path.exists(bg_path):
        print(f"❌ 背景图片不存在: {bg_path}")
        return False
    
    # 检查测试视频
    video_path = "test_composite_video.mp4"
    if not os.path.exists(video_path):
        print(f"❌ 测试视频不存在: {video_path}")
        return False
    
    url = "http://127.0.0.1:8000/api/v1/video/upload-and-process"
    
    try:
        with open(video_path, 'rb') as video_file, open(bg_path, 'rb') as bg_file:
            files = {
                'file': ('test_video.mp4', video_file, 'video/mp4'),
                'background_image': ('background.png', bg_file, 'image/png')
            }
            
            print(f"📤 上传视频: {video_path}")
            print(f"📤 上传背景: {bg_path}")
            
            response = requests.post(url, files=files, timeout=30)
            
            print(f"📊 响应状态码: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ 请求成功")
                print(f"📋 背景模式: {data.get('background_mode', 'N/A')}")
                print(f"🆔 视频ID: {data.get('job_id', 'N/A')}")
                print(f"📁 背景文件名: {data.get('background_file', 'N/A')}")
                print(f"📊 完整响应数据: {json.dumps(data, indent=2, ensure_ascii=False)}")
                return True
            else:
                print(f"❌ 请求失败: {response.text}")
                return False
                
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        return False

def check_image_properties(image_path):
    """检查图片属性"""
    try:
        from PIL import Image
        
        if not os.path.exists(image_path):
            return {"error": f"文件不存在: {image_path}"}
        
        with Image.open(image_path) as img:
            return {
                "format": img.format,
                "mode": img.mode,
                "size": img.size,
                "file_size": os.path.getsize(image_path),
                "has_transparency": img.mode in ('RGBA', 'LA') or 'transparency' in img.info
            }
    except Exception as e:
        return {"error": str(e)}

def find_user_images():
    """查找用户可能提供的图片"""
    print("\n=== 查找用户图片 ===")
    
    # 常见的图片位置
    search_paths = [
        ".",
        "backgrounds",
        "uploads",
        "temp"
    ]
    
    image_extensions = ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp']
    found_images = []
    
    for search_path in search_paths:
        if os.path.exists(search_path):
            for file in os.listdir(search_path):
                if any(file.lower().endswith(ext) for ext in image_extensions):
                    full_path = os.path.join(search_path, file)
                    if os.path.isfile(full_path):
                        found_images.append(full_path)
    
    print(f"📁 找到 {len(found_images)} 个图片文件:")
    for img in found_images:
        props = check_image_properties(img)
        print(f"  📄 {img}")
        if "error" not in props:
            print(f"     格式: {props['format']}, 尺寸: {props['size']}, 大小: {props['file_size']} bytes")
            print(f"     模式: {props['mode']}, 透明度: {props['has_transparency']}")
        else:
            print(f"     ❌ {props['error']}")
    
    return found_images

def test_image_with_api(image_path):
    """使用API测试特定图片"""
    print(f"\n=== 测试图片: {image_path} ===")
    
    video_path = "test_composite_video.mp4"
    if not os.path.exists(video_path):
        print(f"❌ 测试视频不存在: {video_path}")
        return False
    
    url = "http://127.0.0.1:8000/api/v1/video/upload-and-process"
    
    try:
        with open(video_path, 'rb') as video_file, open(image_path, 'rb') as bg_file:
            files = {
                'file': ('test_video.mp4', video_file, 'video/mp4'),
                'background_image': (os.path.basename(image_path), bg_file, 'image/png')
            }
            
            response = requests.post(url, files=files, timeout=30)
            
            print(f"📊 响应状态码: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ 请求成功")
                print(f"📋 背景模式: {data.get('background_mode', 'N/A')}")
                print(f"📊 完整响应数据: {json.dumps(data, indent=2, ensure_ascii=False)}")
                return True
            else:
                print(f"❌ 请求失败: {response.text}")
                return False
                
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        return False

if __name__ == "__main__":
    print("🔍 开始测试背景图片功能...")
    
    # 1. 测试现有背景图片
    success = test_background_with_existing_image()
    
    # 2. 查找用户图片
    user_images = find_user_images()
    
    # 3. 测试用户图片（如果有的话）
    if user_images:
        print(f"\n=== 测试用户提供的图片 ===")
        for img in user_images[:3]:  # 只测试前3个
            if "sitalk_background" not in img:  # 跳过我们已知的好图片
                test_image_with_api(img)
    
    print("\n🏁 测试完成")