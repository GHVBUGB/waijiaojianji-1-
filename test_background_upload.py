#!/usr/bin/env python3
"""
测试背景图片上传功能
"""

import asyncio
import os
import sys
import logging
from PIL import Image
import tempfile

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.tencent_video_service import TencentVideoService

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def create_test_background_image():
    """创建一个测试背景图片"""
    try:
        # 创建一个简单的测试图片 (1920x1080, 蓝色背景)
        width, height = 1920, 1080
        image = Image.new('RGB', (width, height), color='blue')
        
        # 添加一些文字
        try:
            from PIL import ImageDraw, ImageFont
            draw = ImageDraw.Draw(image)
            
            # 尝试使用默认字体
            try:
                font = ImageFont.truetype("arial.ttf", 60)
            except:
                font = ImageFont.load_default()
            
            text = "Test Background Image"
            # 获取文字尺寸
            bbox = draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            
            # 居中绘制文字
            x = (width - text_width) // 2
            y = (height - text_height) // 2
            draw.text((x, y), text, fill='white', font=font)
            
        except Exception as e:
            logger.warning(f"添加文字失败: {e}")
        
        # 保存到临时文件
        temp_file = tempfile.NamedTemporaryFile(suffix='.jpg', delete=False)
        image.save(temp_file.name, 'JPEG', quality=85)
        temp_file.close()
        
        logger.info(f"✅ 创建测试背景图片: {temp_file.name}")
        return temp_file.name
        
    except Exception as e:
        logger.error(f"❌ 创建测试图片失败: {e}")
        raise

async def test_background_upload():
    """测试背景图片上传功能"""
    try:
        logger.info("🚀 开始测试背景图片上传功能")
        
        # 创建腾讯云服务实例
        service = TencentVideoService()
        
        # 检查服务配置
        if not service.bucket_name:
            logger.error("❌ 腾讯云COS配置不完整，请检查环境变量")
            return False
        
        logger.info(f"📦 使用COS存储桶: {service.bucket_name}")
        logger.info(f"🌍 区域: {service.region}")
        
        # 创建测试背景图片
        test_image_path = await create_test_background_image()
        
        try:
            # 测试上传背景图片
            logger.info("📤 开始上传背景图片到COS...")
            background_url = await service.upload_background_image(test_image_path)
            
            logger.info(f"✅ 背景图片上传成功!")
            logger.info(f"🔗 背景图片URL: {background_url}")
            
            # 验证URL格式
            expected_prefix = f"https://{service.bucket_name}.cos.{service.region}.myqcloud.com/backgrounds/"
            if background_url.startswith(expected_prefix):
                logger.info("✅ URL格式正确")
            else:
                logger.warning(f"⚠️ URL格式可能不正确，期望前缀: {expected_prefix}")
            
            return True
            
        finally:
            # 清理临时文件
            try:
                os.unlink(test_image_path)
                logger.info("🧹 清理临时文件完成")
            except:
                pass
                
    except Exception as e:
        logger.error(f"❌ 背景图片上传测试失败: {e}")
        return False

async def test_background_processing():
    """测试完整的背景处理流程"""
    try:
        logger.info("🎬 开始测试完整背景处理流程")
        
        # 检查是否有测试视频文件
        test_video_paths = [
            "test_composite_video.mp4",
            "downloaded_video.mp4"
        ]
        
        test_video = None
        for path in test_video_paths:
            if os.path.exists(path):
                test_video = path
                break
        
        if not test_video:
            logger.warning("⚠️ 未找到测试视频文件，跳过完整流程测试")
            return True
        
        logger.info(f"🎥 使用测试视频: {test_video}")
        
        # 创建测试背景图片
        test_image_path = await create_test_background_image()
        
        try:
            # 创建腾讯云服务实例
            service = TencentVideoService()
            
            # 测试完整的背景处理流程
            logger.info("🔄 开始测试背景处理...")
            result = await service.remove_background(
                video_file_path=test_video,
                output_dir="outputs",
                quality="medium",
                background_file_path=test_image_path
            )
            
            if result.get("success"):
                logger.info("✅ 背景处理测试成功!")
                logger.info(f"📁 输出文件: {result.get('output_path')}")
                logger.info(f"🔗 背景URL: {result.get('background_url')}")
                logger.info(f"⏱️ 处理时间: {result.get('processing_time', 0):.2f}秒")
                return True
            else:
                logger.error(f"❌ 背景处理失败: {result.get('error')}")
                return False
                
        finally:
            # 清理临时文件
            try:
                os.unlink(test_image_path)
            except:
                pass
                
    except Exception as e:
        logger.error(f"❌ 背景处理流程测试失败: {e}")
        return False

async def main():
    """主测试函数"""
    logger.info("=" * 60)
    logger.info("🧪 背景图片上传功能测试")
    logger.info("=" * 60)
    
    success_count = 0
    total_tests = 2
    
    # 测试1: 背景图片上传
    logger.info("\n📋 测试1: 背景图片上传到COS")
    logger.info("-" * 40)
    if await test_background_upload():
        success_count += 1
        logger.info("✅ 测试1通过")
    else:
        logger.error("❌ 测试1失败")
    
    # 测试2: 完整背景处理流程
    logger.info("\n📋 测试2: 完整背景处理流程")
    logger.info("-" * 40)
    if await test_background_processing():
        success_count += 1
        logger.info("✅ 测试2通过")
    else:
        logger.error("❌ 测试2失败")
    
    # 总结
    logger.info("\n" + "=" * 60)
    logger.info(f"🏁 测试完成: {success_count}/{total_tests} 通过")
    logger.info("=" * 60)
    
    if success_count == total_tests:
        logger.info("🎉 所有测试通过!")
        return True
    else:
        logger.error("💥 部分测试失败，请检查配置和网络连接")
        return False

if __name__ == "__main__":
    try:
        result = asyncio.run(main())
        sys.exit(0 if result else 1)
    except KeyboardInterrupt:
        logger.info("⏹️ 测试被用户中断")
        sys.exit(1)
    except Exception as e:
        logger.error(f"💥 测试执行失败: {e}")
        sys.exit(1)