#!/usr/bin/env python3
"""
检查腾讯云万象队列状态并尝试创建队列
"""
import asyncio
import logging
import sys
import requests
import xml.etree.ElementTree as ET
from datetime import datetime

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

sys.path.append('.')
from app.services.tencent_video_service import TencentVideoService

async def check_and_create_queue():
    """检查队列状态并尝试创建队列"""
    logger.info("🔍 检查腾讯云万象队列状态")
    
    service = TencentVideoService()
    
    # 1. 检查现有队列
    await check_existing_queues(service)
    
    # 2. 尝试创建AIProcess队列
    await create_ai_process_queue(service)
    
    # 3. 再次检查队列
    await check_existing_queues(service)

async def check_existing_queues(service):
    """检查现有队列"""
    logger.info("📋 检查现有队列...")
    
    ci_host = f"{service.bucket_name}.ci.{service.region}.myqcloud.com"
    url = f"https://{ci_host}/ai_queue"
    
    authorization = service._generate_authorization("GET", "/ai_queue")
    headers = {
        'Authorization': authorization,
        'Host': ci_host,
        'Date': datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S GMT')
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=30, verify=True)
        logger.info(f"📡 队列查询响应: {response.status_code}")
        logger.info(f"📄 响应内容:\n{response.text}")
        
        if response.status_code == 200:
            root = ET.fromstring(response.content)
            queue_list = root.find('.//QueueList')
            
            if queue_list is not None:
                queues = queue_list.findall('Queue')
                logger.info(f"📊 找到 {len(queues)} 个队列:")
                
                for i, queue in enumerate(queues):
                    queue_id = queue.find('QueueId')
                    name = queue.find('Name')
                    state = queue.find('State')
                    
                    logger.info(f"  队列 {i+1}:")
                    logger.info(f"    ID: {queue_id.text if queue_id is not None else 'N/A'}")
                    logger.info(f"    名称: {name.text if name is not None else 'N/A'}")
                    logger.info(f"    状态: {state.text if state is not None else 'N/A'}")
            else:
                logger.warning("⚠️ 未找到队列列表")
        else:
            logger.error(f"❌ 队列查询失败: {response.status_code}")
            
    except Exception as e:
        logger.error(f"💥 队列查询异常: {str(e)}")

async def create_ai_process_queue(service):
    """创建AIProcess队列"""
    logger.info("🏗️ 尝试创建AIProcess队列...")
    
    ci_host = f"{service.bucket_name}.ci.{service.region}.myqcloud.com"
    url = f"https://{ci_host}/ai_queue"
    
    # 队列配置
    queue_config = {
        "Name": "AIProcess-Queue",
        "QueueID": "",
        "State": "Active",
        "MaxSize": "10000",
        "MaxConcurrent": "10",
        "UpdateTime": datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S+0800'),
        "CreateTime": datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S+0800'),
        "NotifyConfig": {
            "State": "Off"
        }
    }
    
    xml_data = service._dict_to_xml(queue_config, "Request")
    logger.info(f"📄 队列创建XML:\n{xml_data}")
    
    authorization = service._generate_authorization("POST", "/ai_queue", xml_data)
    headers = {
        'Authorization': authorization,
        'Host': ci_host,
        'Content-Type': 'application/xml',
        'Date': datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S GMT')
    }
    
    try:
        response = requests.post(url, data=xml_data.encode('utf-8'), headers=headers, timeout=30, verify=True)
        logger.info(f"📡 队列创建响应: {response.status_code}")
        logger.info(f"📄 响应内容:\n{response.text}")
        
        if response.status_code == 200:
            logger.info("✅ 队列创建成功")
        else:
            logger.error(f"❌ 队列创建失败: {response.status_code}")
            
    except Exception as e:
        logger.error(f"💥 队列创建异常: {str(e)}")

async def test_simple_job_without_queue():
    """测试不使用队列ID的简单任务"""
    logger.info("🧪 测试不使用队列ID的简单任务")
    
    service = TencentVideoService()
    
    # 构建最简单的任务配置
    job_config = {
        "Tag": "SegmentVideoBody",
        "Input": {
            "Object": "test/simple_input.mp4"
        },
        "Operation": {
            "SegmentVideoBody": {
                "SegmentType": "HumanSeg",
                "Mode": "Foreground"
            },
            "Output": {
                "Region": service.region,
                "Bucket": service.bucket_name,
                "Object": "test/simple_output.mp4"
            }
        }
    }
    
    xml_data = service._dict_to_xml(job_config)
    logger.info(f"📄 简单任务XML:\n{xml_data}")
    
    ci_host = f"{service.bucket_name}.ci.{service.region}.myqcloud.com"
    url = f"https://{ci_host}/jobs"
    
    authorization = service._generate_authorization("POST", "/jobs", xml_data)
    headers = {
        'Authorization': authorization,
        'Host': ci_host,
        'Content-Type': 'application/xml',
        'Date': datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S GMT')
    }
    
    try:
        response = requests.post(url, data=xml_data.encode('utf-8'), headers=headers, timeout=30, verify=True)
        logger.info(f"📡 简单任务提交响应: {response.status_code}")
        logger.info(f"📄 响应内容:\n{response.text}")
        
        if response.status_code == 200:
            logger.info("✅ 简单任务提交成功")
        else:
            logger.error(f"❌ 简单任务提交失败: {response.status_code}")
            
    except Exception as e:
        logger.error(f"💥 简单任务提交异常: {str(e)}")

async def main():
    """主函数"""
    logger.info("🚀 开始队列状态检查")
    
    try:
        await check_and_create_queue()
        await test_simple_job_without_queue()
    except Exception as e:
        logger.error(f"💥 检查异常: {str(e)}")
        import traceback
        traceback.print_exc()
    
    logger.info("🏁 检查结束")

if __name__ == "__main__":
    asyncio.run(main())