#!/usr/bin/env python3
import asyncio
import sys
import time
sys.path.append('.')

from app.services.tencent_video_service import TencentVideoService

async def monitor_job():
    service = TencentVideoService()
    job_id = "ab11f32d6a4d511f0b65ddf415e607aff"  # 刚才提交的任务ID
    
    print(f"🔍 监控任务: {job_id}")
    print("每30秒检查一次状态...")
    
    max_checks = 20  # 最多检查20次（10分钟）
    check_count = 0
    
    while check_count < max_checks:
        check_count += 1
        try:
            status = await service._check_job_status(job_id)
            current_time = time.strftime("%H:%M:%S")
            print(f"[{current_time}] 检查 #{check_count}: {status['state']}")
            
            if status['state'] == 'Success':
                print("🎉 任务完成！开始下载结果...")
                
                # 下载结果
                output_object = "output/ci_no_bg_058868c1-61c7-4e74-bec0-380e4898e7f9.mp4"
                output_path = "outputs/ci_processed_video.mp4"
                
                await service._download_from_cos(output_object, output_path)
                print(f"✅ 视频下载完成: {output_path}")
                
                # 检查文件大小
                import os
                if os.path.exists(output_path):
                    size = os.path.getsize(output_path)
                    print(f"📁 处理后文件大小: {size / (1024*1024):.2f}MB")
                
                break
                
            elif status['state'] == 'Failed':
                print("❌ 任务失败")
                print(f"响应: {status['response']}")
                break
            else:
                print(f"⏳ 任务还在处理中...")
                
        except Exception as e:
            print(f"❌ 检查失败: {e}")
        
        if check_count < max_checks:
            await asyncio.sleep(30)  # 等待30秒
    
    if check_count >= max_checks:
        print("⏰ 监控超时，任务可能需要更长时间")

if __name__ == "__main__":
    asyncio.run(monitor_job())
