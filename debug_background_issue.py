#!/usr/bin/env python3
"""
调试背景替换问题
"""
import asyncio
import logging
import os
import sys
import tempfile
from PIL import Image
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

async def create_test_background():
    """创建一个明显的测试背景图片"""
    try:
        # 创建一个红色背景图片
        width, height = 1920, 1080
        image = Image.new('RGB', (width, height), color='red')
        
        # 添加文字标识
        try:
            from PIL import ImageDraw, ImageFont
            draw = ImageDraw.Draw(image)
            
            # 使用默认字体
            try:
                font = ImageFont.truetype("arial.ttf", 80)
            except:
                font = ImageFont.load_default()
            
            text = "TEST BACKGROUND"
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
        image.save(temp_file.name, 'JPEG', quality=95)
        temp_file.close()
        
        logger.info(f"✅ 创建测试背景图片: {temp_file.name}")
        return temp_file.name
        
    except Exception as e:
        logger.error(f"❌ 创建测试背景失败: {e}")
        raise

async def test_background_replacement():
    """测试背景替换功能"""
    try:
        logger.info("🚀 开始测试背景替换功能")
        
        # 查找测试视频
        test_videos = [
            "test_composite_video.mp4",
            "downloaded_video.mp4"
        ]
        
        test_video = None
        for video in test_videos:
            if os.path.exists(video):
                test_video = video
                break
        
        if not test_video:
            logger.error("❌ 未找到测试视频文件")
            return False
        
        logger.info(f"🎥 使用测试视频: {test_video}")
        
        # 创建测试背景
        background_path = await create_test_background()
        
        try:
            # 创建服务实例
            service = TencentVideoService()
            
            # 测试背景替换
            logger.info("🔄 开始测试背景替换...")
            result = await service.remove_background(
                video_file_path=test_video,
                output_dir="outputs",
                quality="medium",
                background_file_path=background_path
            )
            
            logger.info(f"📊 处理结果: {json.dumps(result, indent=2, ensure_ascii=False)}")
            
            if result.get("success"):
                output_path = result.get("output_path")
                background_url = result.get("background_url")
                background_mode = result.get("background_mode")
                
                logger.info(f"✅ 处理成功!")
                logger.info(f"📁 输出文件: {output_path}")
                logger.info(f"🖼️ 背景URL: {background_url}")
                logger.info(f"🎭 背景模式: {background_mode}")
                
                # 检查输出文件
                if os.path.exists(output_path):
                    file_size = os.path.getsize(output_path)
                    logger.info(f"📏 输出文件大小: {file_size / (1024*1024):.2f}MB")
                    
                    if file_size > 0:
                        logger.info("✅ 输出文件生成成功")
                        
                        # 检查是否使用了背景替换模式
                        if background_mode == "Combination" and background_url:
                            logger.info("✅ 确认使用了背景合成模式")
                        else:
                            logger.warning("⚠️ 可能未正确使用背景合成模式")
                        
                        return True
                    else:
                        logger.error("❌ 输出文件为空")
                        return False
                else:
                    logger.error("❌ 输出文件不存在")
                    return False
            else:
                error = result.get("error", "未知错误")
                logger.error(f"❌ 处理失败: {error}")
                return False
                
        finally:
            # 清理临时文件
            try:
                os.unlink(background_path)
                logger.info("🧹 清理临时背景文件")
            except:
                pass
                
    except Exception as e:
        logger.error(f"❌ 测试失败: {e}")
        return False

async def debug_api_parameters():
    """调试API参数配置"""
    try:
        logger.info("🔍 调试API参数配置")
        
        # 创建服务实例
        service = TencentVideoService()
        
        # 创建测试背景
        background_path = await create_test_background()
        
        try:
            # 上传背景图片
            logger.info("📤 测试背景图片上传...")
            background_url = await service.upload_background_image(background_path)
            logger.info(f"🔗 背景URL: {background_url}")
            
            # 模拟API参数构建
            logger.info("⚙️ 模拟API参数构建...")
            
            segment_config = {
                "SegmentType": "HumanSeg",
                "BinaryThreshold": "0.1"
            }
            
            if background_url:
                segment_config["Mode"] = "Combination"
                segment_config["BackgroundLogoUrl"] = background_url
                logger.info(f"🖼️ 使用背景合成模式")
            else:
                segment_config["Mode"] = "Foreground"
                logger.info(f"🎭 使用前景模式")
            
            logger.info(f"📋 segment_config: {json.dumps(segment_config, indent=2, ensure_ascii=False)}")
            
            job_config = {
                "Tag": "SegmentVideoBody",
                "Input": {
                    "Object": "test_input.mp4"
                },
                "Operation": {
                    "SegmentVideoBody": segment_config,
                    "Output": {
                        "Region": service.region,
                        "Bucket": service.bucket_name,
                        "Object": "test_output.mp4",
                        "Format": "mp4"
                    }
                }
            }
            
            logger.info(f"📋 完整job_config: {json.dumps(job_config, indent=2, ensure_ascii=False)}")
            
            return True
            
        finally:
            # 清理临时文件
            try:
                os.unlink(background_path)
            except:
                pass
                
    except Exception as e:
        logger.error(f"❌ 参数调试失败: {e}")
        return False

async def main():
    """主函数"""
    logger.info("=" * 60)
    logger.info("🔧 背景替换问题调试")
    logger.info("=" * 60)
    
    # 测试1: API参数调试
    logger.info("\n📋 测试1: API参数调试")
    logger.info("-" * 40)
    await debug_api_parameters()
    
    # 测试2: 完整背景替换测试
    logger.info("\n📋 测试2: 完整背景替换测试")
    logger.info("-" * 40)
    success = await test_background_replacement()
    
    logger.info("\n" + "=" * 60)
    if success:
        logger.info("🎉 背景替换测试通过!")
    else:
        logger.error("💥 背景替换测试失败!")
    logger.info("=" * 60)
    
    return success

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