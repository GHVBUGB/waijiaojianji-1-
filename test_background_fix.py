#!/usr/bin/env python3
"""
测试背景替换功能修复
"""

import asyncio
import logging
import os
import tempfile
from PIL import Image
from app.services.tencent_video_service import TencentVideoService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def create_test_background():
    """创建测试背景图片"""
    # 创建一个明显的彩色背景图片
    width, height = 640, 480
    
    # 创建渐变背景：从蓝色到绿色
    img = Image.new('RGB', (width, height))
    pixels = img.load()
    
    for y in range(height):
        for x in range(width):
            # 创建从蓝色到绿色的渐变
            blue_ratio = 1 - (x / width)
            green_ratio = x / width
            
            r = int(50 * (1 - y / height))  # 少量红色
            g = int(255 * green_ratio)      # 绿色渐变
            b = int(255 * blue_ratio)       # 蓝色渐变
            
            pixels[x, y] = (r, g, b)
    
    # 保存临时背景图片
    temp_bg = tempfile.NamedTemporaryFile(suffix='.jpg', delete=False)
    img.save(temp_bg.name, 'JPEG', quality=95)
    temp_bg.close()
    
    logger.info(f"🖼️ 创建测试背景图片: {temp_bg.name}")
    return temp_bg.name

async def create_test_video():
    """创建测试视频"""
    import cv2
    import numpy as np
    
    # 创建一个简单的测试视频
    temp_video = tempfile.NamedTemporaryFile(suffix='.mp4', delete=False)
    temp_video.close()
    
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(temp_video.name, fourcc, 10.0, (640, 480))
    
    # 创建30帧的视频，中间有一个移动的白色圆圈（模拟人物）
    for frame_num in range(30):
        # 黑色背景
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        
        # 移动的白色圆圈
        center_x = int(320 + 100 * np.sin(frame_num * 0.2))
        center_y = int(240 + 50 * np.cos(frame_num * 0.2))
        
        cv2.circle(frame, (center_x, center_y), 50, (255, 255, 255), -1)
        
        out.write(frame)
    
    out.release()
    logger.info(f"🎬 创建测试视频: {temp_video.name}")
    return temp_video.name

async def test_background_replacement():
    """测试背景替换功能"""
    logger.info("🧪 开始测试背景替换功能")
    
    try:
        # 创建测试文件
        test_video = await create_test_video()
        test_background = await create_test_background()
        
        # 创建服务实例
        service = TencentVideoService()
        
        # 测试背景替换
        logger.info("🎬 开始背景替换处理...")
        result = await service.remove_background(
            video_file_path=test_video,
            output_dir="outputs",
            quality="medium",
            background_file_path=test_background  # 传递背景图片文件路径
        )
        
        logger.info(f"📊 处理结果: {result}")
        
        if result.get("success"):
            output_path = result.get("output_path")
            background_mode = result.get("background_mode", "Unknown")
            background_url = result.get("background_url")
            
            logger.info(f"✅ 背景替换成功!")
            logger.info(f"   输出文件: {output_path}")
            logger.info(f"   背景模式: {background_mode}")
            logger.info(f"   背景URL: {background_url}")
            
            # 检查输出文件
            if os.path.exists(output_path):
                file_size = os.path.getsize(output_path)
                logger.info(f"   文件大小: {file_size / (1024*1024):.2f}MB")
                
                if file_size > 0:
                    logger.info("🎉 背景替换测试成功！")
                    return True
                else:
                    logger.error("❌ 输出文件为空")
            else:
                logger.error("❌ 输出文件不存在")
        else:
            logger.error(f"❌ 背景替换失败: {result.get('error')}")
        
        return False
        
    except Exception as e:
        logger.error(f"❌ 测试异常: {str(e)}")
        return False
    
    finally:
        # 清理临时文件
        try:
            if 'test_video' in locals():
                os.unlink(test_video)
            if 'test_background' in locals():
                os.unlink(test_background)
        except:
            pass

if __name__ == "__main__":
    asyncio.run(test_background_replacement())