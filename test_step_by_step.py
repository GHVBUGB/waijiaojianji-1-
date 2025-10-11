#!/usr/bin/env python3
import asyncio
import sys
import os
import logging
sys.path.append('.')

# 设置详细日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

from app.services.tencent_video_service import TencentVideoService

async def test_step_by_step():
    print("=== 腾讯云万象API逐步测试 ===")
    
    service = TencentVideoService()
    
    # 检查配置
    print(f"配置检查:")
    print(f"  Secret ID: {service.secret_id[:10] if service.secret_id else 'None'}...")
    print(f"  COS Bucket: {service.bucket_name}")
    print(f"  Region: {service.region}")
    
    # 检查测试视频
    test_video = 'uploads/058868c1-61c7-4e74-bec0-380e4898e7f9.mp4'
    if not os.path.exists(test_video):
        print(f"❌ 测试视频不存在: {test_video}")
        return
    
    print(f"✅ 测试视频: {test_video} ({os.path.getsize(test_video) / (1024*1024):.2f}MB)")
    
    # 只测试第一步：上传
    try:
        print("\n🚀 测试步骤1: 上传视频到COS")
        video_filename = os.path.basename(test_video)
        input_object = f"input/{video_filename}"
        
        await service._upload_to_cos(test_video, input_object)
        print("✅ 步骤1成功: 视频上传完成")
        
        # 测试第二步：提交任务
        print("\n🚀 测试步骤2: 提交抠图任务")
        output_object = f"output/ci_no_bg_{video_filename}"
        job_id = await service._submit_segment_job(input_object, output_object)
        print(f"✅ 步骤2成功: 任务提交完成，JobId: {job_id}")
        
        # 测试第三步：检查状态（只检查一次）
        print("\n🚀 测试步骤3: 检查任务状态")
        status = await service._check_job_status(job_id)
        print(f"✅ 步骤3成功: 任务状态 - {status['state']}")
        
        if status['state'] == 'Failed':
            print("⚠️ 任务失败，这可能是正常的（需要检查具体原因）")
        elif status['state'] in ['Submitted', 'Running']:
            print("⏳ 任务正在处理中，这是正常的")
        elif status['state'] == 'Success':
            print("🎉 任务已完成！")
            
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_step_by_step())
