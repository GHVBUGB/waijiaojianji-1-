#!/usr/bin/env python3
import asyncio
import sys
import os
sys.path.append('.')

from app.services.tencent_video_service import TencentVideoService

async def test_ci_connection():
    print("=== 腾讯云万象API连接测试 ===")
    
    service = TencentVideoService()
    
    print(f"配置信息:")
    print(f"  Secret ID: {service.secret_id[:10]}...")
    print(f"  COS Bucket: {service.bucket_name}")
    print(f"  Region: {service.region}")
    
    # 测试签名生成
    try:
        print("\n🔐 测试签名生成...")
        auth = service._generate_authorization("GET", "/test")
        print(f"✅ 签名生成成功: {auth[:50]}...")
    except Exception as e:
        print(f"❌ 签名生成失败: {e}")
        return
    
    # 测试简单的任务提交（不实际处理）
    try:
        print("\n📤 测试任务提交...")
        # 使用一个小的测试对象
        job_id = await service._submit_segment_job("test/input.mp4", "test/output.mp4")
        print(f"✅ 任务提交成功，JobId: {job_id}")
        
        # 检查任务状态
        print(f"\n📊 检查任务状态...")
        status = await service._check_job_status(job_id)
        print(f"任务状态: {status['state']}")
        
        if status['state'] == 'Failed':
            print("⚠️ 任务失败，可能是因为输入文件不存在（这是预期的）")
        else:
            print(f"✅ API连接正常，任务状态: {status['state']}")
            
    except Exception as e:
        print(f"❌ API调用失败: {e}")
        print("可能的原因:")
        print("  1. 存储桶不存在或无权限")
        print("  2. 万象服务未开通")
        print("  3. 密钥权限不足")

if __name__ == "__main__":
    asyncio.run(test_ci_connection())
