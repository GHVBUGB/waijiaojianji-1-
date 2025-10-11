#!/usr/bin/env python3
"""
测试BackgroundLogoUrl参数传递
"""

import asyncio
import os
import sys
import logging
import tempfile
from PIL import Image

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.tencent_video_service import TencentVideoService

# 配置日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def create_test_image():
    """创建测试图片"""
    width, height = 1920, 1080
    image = Image.new('RGB', (width, height), color='green')
    
    temp_file = tempfile.NamedTemporaryFile(suffix='.jpg', delete=False)
    image.save(temp_file.name, 'JPEG', quality=85)
    temp_file.close()
    
    return temp_file.name

async def test_background_url_generation():
    """测试背景URL生成和参数传递"""
    try:
        logger.info("🧪 开始测试BackgroundLogoUrl参数传递")
        
        # 创建服务实例
        service = TencentVideoService()
        
        # 创建测试图片
        test_image = await create_test_image()
        logger.info(f"📷 创建测试图片: {test_image}")
        
        try:
            # 测试上传背景图片
            logger.info("📤 测试背景图片上传...")
            background_url = await service.upload_background_image(test_image)
            logger.info(f"✅ 背景URL生成成功: {background_url}")
            
            # 验证URL格式
            if "backgrounds/bg_" in background_url:
                logger.info("✅ URL包含正确的路径前缀")
            else:
                logger.warning("⚠️ URL路径格式可能不正确")
            
            # 测试XML生成（模拟API调用）
            logger.info("🔧 测试XML配置生成...")
            
            # 模拟segment_config的生成逻辑
            segment_config = {
                "SegmentType": "HumanSeg",
                "BinaryThreshold": "0.1",
                "Mode": "Combination",
                "BackgroundLogoUrl": background_url
            }
            
            logger.info("📋 生成的segment_config:")
            for key, value in segment_config.items():
                logger.info(f"  {key}: {value}")
            
            # 测试XML转换
            xml_data = service._dict_to_xml(segment_config)
            logger.info(f"📄 生成的XML片段:\n{xml_data}")
            
            # 验证XML中是否包含BackgroundLogoUrl
            if "BackgroundLogoUrl" in xml_data and background_url in xml_data:
                logger.info("✅ XML中正确包含BackgroundLogoUrl参数")
                return True
            else:
                logger.error("❌ XML中缺少BackgroundLogoUrl参数或值不正确")
                return False
                
        finally:
            # 清理临时文件
            try:
                os.unlink(test_image)
            except:
                pass
                
    except Exception as e:
        logger.error(f"❌ 测试失败: {e}")
        return False

async def test_api_call_with_background():
    """测试完整的API调用流程"""
    try:
        logger.info("🚀 测试完整API调用流程")
        
        # 检查测试视频
        test_video = "test_composite_video.mp4"
        if not os.path.exists(test_video):
            logger.warning("⚠️ 测试视频不存在，跳过完整API测试")
            return True
        
        # 创建服务实例
        service = TencentVideoService()
        
        # 创建测试背景图片
        test_image = await create_test_image()
        
        try:
            # 重写_submit_ci_job方法来捕获XML数据
            original_submit = service._submit_ci_job
            captured_xml = None
            
            async def capture_xml_submit(video_key, output_key, segment_config):
                nonlocal captured_xml
                # 生成XML数据
                operation_config = {
                    "SegmentVideoBody": segment_config,
                    "Output": {
                        "Region": service.region,
                        "Bucket": service.bucket_name,
                        "Object": output_key,
                        "Format": "mp4"
                    }
                }
                
                request_config = {
                    "Tag": "SegmentVideoBody",
                    "Input": {"Object": video_key},
                    "Operation": operation_config
                }
                
                captured_xml = service._dict_to_xml(request_config)
                logger.info(f"🔍 捕获的完整XML数据:\n{captured_xml}")
                
                # 调用原始方法
                return await original_submit(video_key, output_key, segment_config)
            
            # 临时替换方法
            service._submit_ci_job = capture_xml_submit
            
            # 执行API调用
            logger.info("📞 执行API调用...")
            result = await service.remove_background(
                video_file_path=test_video,
                output_dir="outputs",
                quality="medium",
                background_file_path=test_image
            )
            
            # 分析捕获的XML
            if captured_xml:
                logger.info("📊 分析XML数据:")
                if "BackgroundLogoUrl" in captured_xml:
                    if "backgrounds/bg_" in captured_xml:
                        logger.info("✅ XML包含正确的BackgroundLogoUrl参数")
                        return True
                    else:
                        logger.warning("⚠️ XML包含BackgroundLogoUrl但值可能为空")
                        return False
                else:
                    logger.error("❌ XML中缺少BackgroundLogoUrl参数")
                    return False
            else:
                logger.error("❌ 未能捕获XML数据")
                return False
                
        finally:
            # 清理临时文件
            try:
                os.unlink(test_image)
            except:
                pass
                
    except Exception as e:
        logger.error(f"❌ API调用测试失败: {e}")
        return False

async def main():
    """主测试函数"""
    logger.info("=" * 60)
    logger.info("🧪 BackgroundLogoUrl参数传递测试")
    logger.info("=" * 60)
    
    success_count = 0
    total_tests = 2
    
    # 测试1: URL生成和XML配置
    logger.info("\n📋 测试1: 背景URL生成和XML配置")
    logger.info("-" * 40)
    if await test_background_url_generation():
        success_count += 1
        logger.info("✅ 测试1通过")
    else:
        logger.error("❌ 测试1失败")
    
    # 测试2: 完整API调用流程
    logger.info("\n📋 测试2: 完整API调用流程")
    logger.info("-" * 40)
    if await test_api_call_with_background():
        success_count += 1
        logger.info("✅ 测试2通过")
    else:
        logger.error("❌ 测试2失败")
    
    # 总结
    logger.info("\n" + "=" * 60)
    logger.info(f"🏁 测试完成: {success_count}/{total_tests} 通过")
    logger.info("=" * 60)
    
    if success_count == total_tests:
        logger.info("🎉 BackgroundLogoUrl参数传递正常!")
        return True
    else:
        logger.error("💥 BackgroundLogoUrl参数传递存在问题")
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