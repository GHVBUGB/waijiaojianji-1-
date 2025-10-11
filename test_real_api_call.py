#!/usr/bin/env python3
"""
测试真实的API调用流程，检查background_file_path传递
"""
import asyncio
import logging
import os
import tempfile
import requests
from PIL import Image
import sys
import json

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def create_test_video(path: str):
    """创建测试视频文件"""
    # 创建一个简单的测试视频文件（实际上是空文件，仅用于测试）
    with open(path, 'wb') as f:
        f.write(b'fake video content for testing')
    logger.info(f"✅ 创建测试视频: {path}")

def create_test_image(path: str):
    """创建测试背景图片"""
    img = Image.new('RGB', (1920, 1080), color='blue')
    img.save(path, 'JPEG')
    logger.info(f"✅ 创建测试图片: {path}")

async def test_api_call():
    """测试API调用"""
    logger.info("🚀 开始测试API调用")
    
    # 创建临时文件
    with tempfile.TemporaryDirectory() as temp_dir:
        # 创建测试文件
        video_path = os.path.join(temp_dir, "test_video.mp4")
        bg_image_path = os.path.join(temp_dir, "test_background.jpg")
        
        create_test_video(video_path)
        create_test_image(bg_image_path)
        
        # API端点
        api_url = "http://localhost:8000/api/v1/video/upload-and-process"
        
        try:
            # 准备文件
            with open(video_path, 'rb') as video_file, open(bg_image_path, 'rb') as bg_file:
                files = {
                    'file': ('test_video.mp4', video_file, 'video/mp4'),
                    'background_file': ('test_background.jpg', bg_file, 'image/jpeg')
                }
                
                data = {
                    'teacher_name': 'Test Teacher',
                    'quality': 'medium',
                    'output_format': 'mp4',
                    'description': 'API测试视频'
                }
                
                logger.info("📤 发送API请求...")
                response = requests.post(api_url, files=files, data=data, timeout=30)
                
                logger.info(f"📡 API响应状态: {response.status_code}")
                logger.info(f"📄 API响应内容: {response.text}")
                
                if response.status_code == 200:
                    result = response.json()
                    job_id = result.get('data', {}).get('job_id')
                    logger.info(f"✅ API调用成功，任务ID: {job_id}")
                    
                    # 等待一段时间让任务开始处理
                    await asyncio.sleep(5)
                    
                    # 检查任务进度
                    progress_url = f"http://localhost:8000/api/v1/video/progress/{job_id}"
                    progress_response = requests.get(progress_url)
                    logger.info(f"📊 任务进度: {progress_response.text}")
                    
                    return job_id
                else:
                    logger.error(f"❌ API调用失败: {response.status_code} - {response.text}")
                    return None
                    
        except Exception as e:
            logger.error(f"💥 API调用异常: {str(e)}")
            return None

async def main():
    """主测试函数"""
    logger.info("🧪 开始测试真实API调用流程")
    
    # 测试API调用
    job_id = await test_api_call()
    
    if job_id:
        logger.info(f"✅ 测试完成，任务ID: {job_id}")
        logger.info("💡 请检查日志文件中的background_file_path传递情况")
    else:
        logger.error("❌ 测试失败")
    
    logger.info("🏁 测试结束")

if __name__ == "__main__":
    asyncio.run(main())