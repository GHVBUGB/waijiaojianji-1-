#!/usr/bin/env python3
"""
使用真实视频文件测试背景替换功能
"""
import asyncio
import logging
import os
import tempfile
import requests
from PIL import Image
import sys
import json
import shutil

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def create_test_image(path: str):
    """创建测试背景图片"""
    img = Image.new('RGB', (1920, 1080), color='blue')
    img.save(path, 'JPEG')
    logger.info(f"✅ 创建测试图片: {path}")

async def test_with_real_video():
    """使用真实视频文件测试"""
    logger.info("🚀 开始使用真实视频文件测试")
    
    # 查找现有的视频文件
    uploads_dir = "uploads"
    video_files = [f for f in os.listdir(uploads_dir) if f.endswith('.mp4')]
    
    if not video_files:
        logger.error("❌ 未找到可用的视频文件")
        return None
    
    # 使用第一个找到的视频文件
    source_video = os.path.join(uploads_dir, video_files[0])
    logger.info(f"📹 使用视频文件: {source_video}")
    
    # 创建临时文件
    with tempfile.TemporaryDirectory() as temp_dir:
        # 复制视频文件到临时目录
        temp_video = os.path.join(temp_dir, "test_video.mp4")
        shutil.copy2(source_video, temp_video)
        
        # 创建背景图片
        bg_image_path = os.path.join(temp_dir, "test_background.jpg")
        create_test_image(bg_image_path)
        
        # API端点
        api_url = "http://localhost:8000/api/v1/video/upload-and-process"
        
        try:
            # 准备文件
            with open(temp_video, 'rb') as video_file, open(bg_image_path, 'rb') as bg_file:
                files = {
                    'file': ('test_video.mp4', video_file, 'video/mp4'),
                    'background_file': ('test_background.jpg', bg_file, 'image/jpeg')
                }
                
                data = {
                    'teacher_name': 'Test Teacher',
                    'quality': 'medium',
                    'output_format': 'mp4',
                    'description': '真实视频背景替换测试'
                }
                
                logger.info("📤 发送API请求...")
                response = requests.post(api_url, files=files, data=data, timeout=60)
                
                logger.info(f"📡 API响应状态: {response.status_code}")
                logger.info(f"📄 API响应内容: {response.text}")
                
                if response.status_code == 200:
                    result = response.json()
                    job_id = result.get('data', {}).get('job_id')
                    logger.info(f"✅ API调用成功，任务ID: {job_id}")
                    
                    # 等待处理完成
                    await monitor_job_progress(job_id)
                    
                    return job_id
                else:
                    logger.error(f"❌ API调用失败: {response.status_code} - {response.text}")
                    return None
                    
        except Exception as e:
            logger.error(f"💥 API调用异常: {str(e)}")
            return None

async def monitor_job_progress(job_id: str, max_wait_time: int = 300):
    """监控任务进度"""
    logger.info(f"📊 开始监控任务进度: {job_id}")
    
    progress_url = f"http://localhost:8000/api/v1/video/progress/{job_id}"
    start_time = asyncio.get_event_loop().time()
    
    while True:
        try:
            response = requests.get(progress_url, timeout=10)
            if response.status_code == 200:
                result = response.json()
                data = result.get('data', {})
                status = data.get('status', 'unknown')
                progress = data.get('progress', 0)
                current_step = data.get('current_step', '')
                
                logger.info(f"📈 任务状态: {status}, 进度: {progress}%, 当前步骤: {current_step}")
                
                if status in ['completed', 'failed']:
                    if status == 'completed':
                        logger.info("✅ 任务完成成功")
                    else:
                        error = data.get('error', '未知错误')
                        logger.error(f"❌ 任务失败: {error}")
                    break
                
                # 检查超时
                if asyncio.get_event_loop().time() - start_time > max_wait_time:
                    logger.warning("⏰ 监控超时")
                    break
                
                await asyncio.sleep(5)  # 等待5秒后再次检查
            else:
                logger.error(f"❌ 获取进度失败: {response.status_code}")
                break
                
        except Exception as e:
            logger.error(f"💥 监控异常: {str(e)}")
            break

async def main():
    """主测试函数"""
    logger.info("🧪 开始真实视频背景替换测试")
    
    # 测试API调用
    job_id = await test_with_real_video()
    
    if job_id:
        logger.info(f"✅ 测试完成，任务ID: {job_id}")
    else:
        logger.error("❌ 测试失败")
    
    logger.info("🏁 测试结束")

if __name__ == "__main__":
    asyncio.run(main())