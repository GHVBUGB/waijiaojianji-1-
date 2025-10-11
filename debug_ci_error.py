#!/usr/bin/env python3
"""
调试腾讯云万象API "Invalid data found when processing input" 错误
"""
import asyncio
import logging
import os
import tempfile
import requests
from PIL import Image
import sys
import json
import xml.etree.ElementTree as ET

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

sys.path.append('.')
from app.services.tencent_video_service import TencentVideoService

def create_minimal_video(path: str):
    """创建一个最小的测试视频文件"""
    # 使用ffmpeg创建一个简单的测试视频
    import subprocess
    try:
        cmd = [
            'ffmpeg', '-y',
            '-f', 'lavfi',
            '-i', 'testsrc=duration=3:size=320x240:rate=1',
            '-c:v', 'libx264',
            '-pix_fmt', 'yuv420p',
            path
        ]
        subprocess.run(cmd, check=True, capture_output=True)
        logger.info(f"✅ 创建测试视频: {path}")
        return True
    except Exception as e:
        logger.error(f"❌ 创建测试视频失败: {e}")
        return False

def create_simple_background(path: str):
    """创建一个简单的背景图片"""
    img = Image.new('RGB', (320, 240), color='green')
    img.save(path, 'JPEG', quality=95)
    logger.info(f"✅ 创建背景图片: {path}")

async def test_minimal_ci_job():
    """测试最小的万象API任务"""
    logger.info("🧪 开始最小万象API任务测试")
    
    service = TencentVideoService()
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # 创建最小测试文件
        video_path = os.path.join(temp_dir, "test_video.mp4")
        bg_path = os.path.join(temp_dir, "test_bg.jpg")
        
        if not create_minimal_video(video_path):
            logger.error("❌ 无法创建测试视频")
            return
        
        create_simple_background(bg_path)
        
        try:
            # 1. 上传背景图片
            logger.info("📤 上传背景图片...")
            bg_url = await service.upload_background_image(bg_path)
            logger.info(f"✅ 背景图片上传成功: {bg_url}")
            
            # 2. 测试不同的任务配置
            await test_different_configs(service, video_path, bg_url)
            
        except Exception as e:
            logger.error(f"💥 测试异常: {str(e)}")

async def test_different_configs(service, video_path, bg_url):
    """测试不同的任务配置"""
    
    configs = [
        {
            "name": "仅前景模式",
            "background_url": None,
            "segment_config": {
                "SegmentType": "HumanSeg",
                "Mode": "Foreground"
            }
        },
        {
            "name": "背景合成模式 - 基础配置",
            "background_url": bg_url,
            "segment_config": {
                "SegmentType": "HumanSeg",
                "Mode": "Combination",
                "BackgroundLogoUrl": bg_url
            }
        },
        {
            "name": "背景合成模式 - 调整阈值",
            "background_url": bg_url,
            "segment_config": {
                "SegmentType": "HumanSeg",
                "Mode": "Combination",
                "BackgroundLogoUrl": bg_url,
                "BinaryThreshold": "0.5"
            }
        }
    ]
    
    for i, config in enumerate(configs):
        logger.info(f"\n🧪 测试配置 {i+1}: {config['name']}")
        
        try:
            # 上传视频
            import time
            timestamp = int(time.time()) + i
            input_key = f"debug/input_{timestamp}.mp4"
            output_key = f"debug/output_{timestamp}.mp4"
            
            await service._upload_to_cos(video_path, input_key)
            logger.info(f"✅ 视频上传成功: {input_key}")
            
            # 提交任务
            job_id = await submit_custom_job(service, input_key, output_key, config["segment_config"])
            logger.info(f"✅ 任务提交成功: {job_id}")
            
            # 检查任务状态
            await check_job_detailed_status(service, job_id)
            
        except Exception as e:
            logger.error(f"❌ 配置 {config['name']} 测试失败: {str(e)}")

async def submit_custom_job(service, input_key, output_key, segment_config):
    """提交自定义配置的任务"""
    
    # 获取队列ID
    queue_id = await service._get_queue_id()
    
    # 构建任务配置
    job_config = {
        "Tag": "SegmentVideoBody",
        "Input": {
            "Object": input_key
        },
        "Operation": {
            "SegmentVideoBody": segment_config,
            "Output": {
                "Region": service.region,
                "Bucket": service.bucket_name,
                "Object": output_key
            }
        }
    }
    
    # 如果有队列ID，添加到配置中
    if queue_id:
        job_config["QueueId"] = queue_id
    
    # 转换为XML
    xml_data = service._dict_to_xml(job_config)
    logger.info(f"📄 任务XML配置:\n{xml_data}")
    
    # 提交任务
    ci_host = f"{service.bucket_name}.ci.{service.region}.myqcloud.com"
    url = f"https://{ci_host}/jobs"
    
    authorization = service._generate_authorization("POST", "/jobs", xml_data)
    from datetime import datetime
    headers = {
        'Authorization': authorization,
        'Host': ci_host,
        'Content-Type': 'application/xml',
        'Date': datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S GMT')
    }
    
    response = requests.post(url, data=xml_data.encode('utf-8'), headers=headers, timeout=30, verify=True)
    
    logger.info(f"📡 任务提交响应: {response.status_code}")
    logger.info(f"📄 响应内容: {response.text}")
    
    if response.status_code == 200:
        root = ET.fromstring(response.content)
        job_id = root.find('.//JobId').text if root.find('.//JobId') is not None else None
        return job_id
    else:
        raise Exception(f"任务提交失败: {response.status_code} - {response.text}")

async def check_job_detailed_status(service, job_id):
    """详细检查任务状态"""
    logger.info(f"📊 详细检查任务状态: {job_id}")
    
    ci_host = f"{service.bucket_name}.ci.{service.region}.myqcloud.com"
    url = f"https://{ci_host}/jobs/{job_id}"
    
    authorization = service._generate_authorization("GET", f"/jobs/{job_id}")
    from datetime import datetime
    headers = {
        'Authorization': authorization,
        'Host': ci_host,
        'Date': datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S GMT')
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=30, verify=True)
        logger.info(f"📡 状态查询响应: {response.status_code}")
        logger.info(f"📄 完整响应内容:\n{response.text}")
        
        if response.status_code == 200:
            root = ET.fromstring(response.content)
            
            # 提取关键信息
            state = root.find('.//State')
            code = root.find('.//Code')
            message = root.find('.//Message')
            
            logger.info(f"📊 任务状态详情:")
            logger.info(f"  State: {state.text if state is not None else 'N/A'}")
            logger.info(f"  Code: {code.text if code is not None else 'N/A'}")
            logger.info(f"  Message: {message.text if message is not None else 'N/A'}")
            
            # 如果失败，尝试获取更多错误信息
            if state is not None and state.text == "Failed":
                logger.error("❌ 任务失败，分析错误原因...")
                analyze_failure_reason(root)
        
    except Exception as e:
        logger.error(f"💥 状态查询异常: {str(e)}")

def analyze_failure_reason(root):
    """分析任务失败原因"""
    logger.info("🔍 分析任务失败原因...")
    
    # 查找所有可能的错误信息字段
    error_fields = ['Message', 'ErrorMessage', 'ErrorCode', 'ErrorDetails']
    
    for field in error_fields:
        element = root.find(f'.//{field}')
        if element is not None and element.text:
            logger.error(f"  {field}: {element.text}")
    
    # 检查操作相关的错误
    operation = root.find('.//Operation')
    if operation is not None:
        logger.info("🔧 操作配置:")
        for child in operation:
            logger.info(f"  {child.tag}: {child.text if child.text else 'N/A'}")

async def main():
    """主测试函数"""
    logger.info("🚀 开始腾讯云万象API错误调试")
    
    try:
        await test_minimal_ci_job()
    except Exception as e:
        logger.error(f"💥 调试异常: {str(e)}")
        import traceback
        traceback.print_exc()
    
    logger.info("🏁 调试结束")

if __name__ == "__main__":
    asyncio.run(main())