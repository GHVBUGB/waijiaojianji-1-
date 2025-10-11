#!/usr/bin/env python3
import asyncio
import sys
sys.path.append('.')

from app.services.tencent_video_service import TencentVideoService

async def check_job():
    service = TencentVideoService()
    job_id = "909faaac-df5a-4de5-bfbb-36fc4da1f767"  # 刚才提交的任务ID
    
    print(f"检查任务状态: {job_id}")
    
    try:
        status = await service._check_job_status(job_id)
        print(f"任务状态: {status['state']}")
        
        if status['state'] == 'Success':
            print("🎉 任务完成！开始下载结果...")
            
            # 下载结果
            output_object = "output/ci_no_bg_058868c1-61c7-4e74-bec0-380e4898e7f9.mp4"
            output_path = "outputs/ci_processed_video.mp4"
            
            await service._download_from_cos(output_object, output_path)
            print(f"✅ 视频下载完成: {output_path}")
            
        elif status['state'] == 'Failed':
            print("❌ 任务失败")
            print(f"响应: {status['response']}")
        else:
            print(f"⏳ 任务还在处理中: {status['state']}")
            
    except Exception as e:
        print(f"检查失败: {e}")

if __name__ == "__main__":
    asyncio.run(check_job())
