#!/usr/bin/env python3
"""
测试修复后的腾讯云万象API签名生成
"""
import asyncio
import logging
import sys
import requests
import xml.etree.ElementTree as ET
from datetime import datetime
import hashlib
import hmac
import time
import urllib.parse

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

sys.path.append('.')
from app.services.tencent_video_service import TencentVideoService

def generate_correct_authorization(service, method: str, uri: str, body: str = "") -> str:
    """生成正确的腾讯云万象API授权签名"""
    
    # 时间戳
    now = int(time.time())
    expired = now + 3600  # 1小时后过期
    
    # 生成 KeyTime
    key_time = f"{now};{expired}"
    
    # 生成 SignKey
    sign_key = hmac.new(
        service.secret_key.encode('utf-8'),
        key_time.encode('utf-8'),
        hashlib.sha1
    ).hexdigest()
    
    # 对于万象API，需要包含请求体的哈希
    if body:
        body_hash = hashlib.sha1(body.encode('utf-8')).hexdigest()
    else:
        body_hash = hashlib.sha1(b'').hexdigest()
    
    # 生成 HttpString - 万象API格式
    http_string = f"{method.lower()}\n{uri}\n\nhost={service.bucket_name}.ci.{service.region}.myqcloud.com\n"
    
    logger.info(f"🔐 HttpString: {repr(http_string)}")
    
    # 生成 StringToSign
    string_to_sign = f"sha1\n{key_time}\n{hashlib.sha1(http_string.encode('utf-8')).hexdigest()}\n"
    
    logger.info(f"🔐 StringToSign: {repr(string_to_sign)}")
    
    # 生成 Signature
    signature = hmac.new(
        sign_key.encode('utf-8'),
        string_to_sign.encode('utf-8'),
        hashlib.sha1
    ).hexdigest()
    
    # 生成 Authorization - 万象API格式
    authorization = (
        f"q-sign-algorithm=sha1&"
        f"q-ak={service.secret_id}&"
        f"q-sign-time={key_time}&"
        f"q-key-time={key_time}&"
        f"q-header-list=host&"
        f"q-url-param-list=&"
        f"q-signature={signature}"
    )
    
    logger.info(f"🔐 Authorization: {authorization}")
    
    return authorization

async def test_corrected_signature():
    """测试修正后的签名"""
    logger.info("🧪 测试修正后的签名")
    
    service = TencentVideoService()
    
    # 测试简单的队列查询
    ci_host = f"{service.bucket_name}.ci.{service.region}.myqcloud.com"
    url = f"https://{ci_host}/ai_queue"
    uri = "/ai_queue"
    
    # 使用修正的签名方法
    authorization = generate_correct_authorization(service, "GET", uri)
    
    headers = {
        'Authorization': authorization,
        'Host': ci_host,
        'Date': datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S GMT')
    }
    
    logger.info(f"📡 请求头: {headers}")
    
    try:
        response = requests.get(url, headers=headers, timeout=30, verify=True)
        logger.info(f"📡 响应状态: {response.status_code}")
        logger.info(f"📄 响应内容:\n{response.text}")
        
        if response.status_code == 200:
            logger.info("✅ 签名修正成功！")
            return True
        else:
            logger.error(f"❌ 签名仍有问题: {response.status_code}")
            return False
            
    except Exception as e:
        logger.error(f"💥 请求异常: {str(e)}")
        return False

async def test_job_submission_with_fixed_signature():
    """使用修正的签名测试任务提交"""
    logger.info("🧪 使用修正的签名测试任务提交")
    
    service = TencentVideoService()
    
    # 构建简单任务配置
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
    logger.info(f"📄 任务XML:\n{xml_data}")
    
    ci_host = f"{service.bucket_name}.ci.{service.region}.myqcloud.com"
    url = f"https://{ci_host}/jobs"
    uri = "/jobs"
    
    # 使用修正的签名方法
    authorization = generate_correct_authorization(service, "POST", uri, xml_data)
    
    headers = {
        'Authorization': authorization,
        'Host': ci_host,
        'Content-Type': 'application/xml',
        'Date': datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S GMT')
    }
    
    try:
        response = requests.post(url, data=xml_data.encode('utf-8'), headers=headers, timeout=30, verify=True)
        logger.info(f"📡 任务提交响应: {response.status_code}")
        logger.info(f"📄 响应内容:\n{response.text}")
        
        if response.status_code == 200:
            logger.info("✅ 任务提交成功！")
            return True
        else:
            logger.error(f"❌ 任务提交失败: {response.status_code}")
            return False
            
    except Exception as e:
        logger.error(f"💥 任务提交异常: {str(e)}")
        return False

async def main():
    """主函数"""
    logger.info("🚀 开始签名修正测试")
    
    try:
        # 测试队列查询
        queue_success = await test_corrected_signature()
        
        if queue_success:
            # 测试任务提交
            await test_job_submission_with_fixed_signature()
        
    except Exception as e:
        logger.error(f"💥 测试异常: {str(e)}")
        import traceback
        traceback.print_exc()
    
    logger.info("🏁 测试结束")

if __name__ == "__main__":
    asyncio.run(main())