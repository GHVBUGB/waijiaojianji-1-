#!/usr/bin/env python3
import asyncio
import sys
import os
sys.path.append('.')

from app.services.tencent_video_service import TencentVideoService

async def test_ci_video_processing():
    print("=== 腾讯云万象视频抠图测试 ===")
    
    service = TencentVideoService()
    
    # 检查测试视频文件
    test_video = 'uploads/058868c1-61c7-4e74-bec0-380e4898e7f9.mp4'
    if not os.path.exists(test_video):
        print(f"❌ 测试视频不存在: {test_video}")
        return
    
    print(f"✅ 找到测试视频: {test_video}")
    print(f"📁 文件大小: {os.path.getsize(test_video) / (1024*1024):.2f}MB")
    
    try:
        print("\n🚀 开始处理视频...")
        result = await service.remove_background(test_video, 'outputs')
        
        print(f"\n📊 处理结果:")
        print(f"  成功: {result['success']}")
        print(f"  服务: {result['service']}")
        print(f"  输出路径: {result['output_path']}")
        print(f"  处理时间: {result['processing_time']:.2f}秒")
        print(f"  原始大小: {result['original_size'] / (1024*1024):.2f}MB")
        print(f"  处理后大小: {result['processed_size'] / (1024*1024):.2f}MB")
        print(f"  成本估算: {result['cost_estimate']}")
        
        if result['success'] and os.path.exists(result['output_path']):
            print(f"✅ 视频处理成功！输出文件: {result['output_path']}")
        else:
            print(f"❌ 视频处理失败: {result.get('error', '未知错误')}")
            
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_ci_video_processing())
