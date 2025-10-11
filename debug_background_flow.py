#!/usr/bin/env python3
"""
调试背景图片处理流程
"""
import asyncio
import logging
import os
import tempfile
from PIL import Image
import sys
import json

# 添加项目路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.tencent_video_service import TencentVideoService

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

def create_test_video(path: str):
    """创建测试视频文件"""
    # 创建一个简单的测试视频文件（实际上是空文件，仅用于测试）
    with open(path, 'wb') as f:
        f.write(b'fake video content for testing')
    logger.info(f"✅ 创建测试视频: {path}")

class DebugTencentVideoService(TencentVideoService):
    """调试版本的TencentVideoService"""
    
    async def debug_remove_background(self, video_file_path: str, output_dir: str, background_file_path: str = None):
        """调试版本的remove_background方法"""
        logger.info("🔍 开始调试背景移除流程")
        
        # 步骤1: 检查背景文件路径
        logger.info(f"📁 背景文件路径: {background_file_path}")
        if background_file_path:
            logger.info(f"📁 背景文件存在: {os.path.exists(background_file_path)}")
        
        # 步骤2: 上传背景图片
        final_background_url = None
        if background_file_path:
            logger.info("🖼️ 开始上传背景图片")
            final_background_url = await self.upload_background_image(background_file_path)
            logger.info(f"🔗 生成的背景URL: {final_background_url}")
        
        # 步骤3: 调试_process_with_ci_api
        logger.info("🎬 开始调试万象API处理")
        return await self.debug_process_with_ci_api(video_file_path, output_dir, final_background_url)
    
    async def debug_process_with_ci_api(self, video_file_path: str, output_dir: str, background_url: str = None):
        """调试版本的_process_with_ci_api方法"""
        logger.info(f"🎬 调试万象API处理: background_url={background_url}")
        
        # 生成唯一的对象键
        import time
        timestamp = int(time.time())
        input_key = f"input/video_{timestamp}.mp4"
        output_key = f"output/processed_{timestamp}.mp4"
        
        # 调试_submit_ci_job
        return await self.debug_submit_ci_job(input_key, output_key, background_url)
    
    async def debug_submit_ci_job(self, input_key: str, output_key: str, background_url: str = None):
        """调试版本的_submit_ci_job方法"""
        logger.info(f"🎬 调试提交万象API任务")
        logger.info(f"📥 输入参数: input_key={input_key}, output_key={output_key}, background_url={background_url}")
        
        # 构建任务配置
        segment_config = {
            "SegmentType": "HumanSeg",
            "BinaryThreshold": "0.1"
        }
        
        # 根据是否提供背景图片选择模式
        if background_url:
            segment_config["Mode"] = "Combination"
            segment_config["BackgroundLogoUrl"] = background_url
            logger.info(f"🖼️ 使用背景合成模式，背景图片: {background_url}")
        else:
            segment_config["Mode"] = "Foreground"
            logger.info("🎭 使用前景模式（无背景替换）")
        
        logger.info(f"⚙️ segment_config: {json.dumps(segment_config, indent=2)}")
        
        job_config = {
            "Tag": "SegmentVideoBody",
            "Input": {
                "Object": input_key
            },
            "Operation": {
                "SegmentVideoBody": segment_config,
                "Output": {
                    "Region": self.region,
                    "Bucket": self.bucket_name,
                    "Object": output_key,
                    "Format": "mp4"
                }
            },
        }
        
        logger.info(f"📋 job_config: {json.dumps(job_config, indent=2)}")
        
        # 转换为XML格式
        xml_data = self._dict_to_xml(job_config, "Request")
        logger.info(f"📄 生成的XML数据:")
        logger.info(xml_data)
        
        # 检查XML中是否包含BackgroundLogoUrl
        if "BackgroundLogoUrl" in xml_data:
            logger.info("✅ XML中包含BackgroundLogoUrl参数")
        else:
            logger.error("❌ XML中缺少BackgroundLogoUrl参数")
        
        return "debug_job_id"

async def main():
    """主测试函数"""
    logger.info("🚀 开始调试背景图片处理流程")
    
    # 创建临时文件
    with tempfile.TemporaryDirectory() as temp_dir:
        # 创建测试文件
        bg_image_path = os.path.join(temp_dir, "test_background.jpg")
        video_path = os.path.join(temp_dir, "test_video.mp4")
        output_dir = os.path.join(temp_dir, "output")
        os.makedirs(output_dir, exist_ok=True)
        
        create_test_image(bg_image_path)
        create_test_video(video_path)
        
        # 创建调试服务实例
        service = DebugTencentVideoService()
        
        # 测试1: 无背景图片
        logger.info("\n" + "="*60)
        logger.info("🧪 测试1: 无背景图片")
        logger.info("="*60)
        await service.debug_remove_background(video_path, output_dir)
        
        # 测试2: 有背景图片
        logger.info("\n" + "="*60)
        logger.info("🧪 测试2: 有背景图片")
        logger.info("="*60)
        await service.debug_remove_background(video_path, output_dir, bg_image_path)
        
    logger.info("🏁 调试完成")

if __name__ == "__main__":
    asyncio.run(main())