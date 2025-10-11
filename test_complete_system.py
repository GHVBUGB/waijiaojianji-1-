#!/usr/bin/env python3
"""
完整系统测试脚本
测试视频处理系统的所有功能
"""

import asyncio
import json
import os
import sys
import time
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

from app.config.settings import settings
from app.services.video_processor import video_processor

async def test_system_status():
    """测试系统状态"""
    print("🔍 检查系统状态...")
    
    try:
        status = await video_processor.get_service_status()
        print(f"✅ 系统状态: {json.dumps(status, indent=2, ensure_ascii=False)}")
        return True
    except Exception as e:
        print(f"❌ 系统状态检查失败: {e}")
        return False

async def test_video_processing():
    """测试视频处理功能"""
    print("\n🎬 测试视频处理功能...")
    
    # 检查是否有测试视频文件
    test_video_path = None
    for ext in ['.mp4', '.mov', '.avi']:
        for name in ['test', 'sample', 'demo']:
            path = f"{name}{ext}"
            if os.path.exists(path):
                test_video_path = path
                break
        if test_video_path:
            break
    
    if not test_video_path:
        print("⚠️  未找到测试视频文件，跳过视频处理测试")
        print("   请在项目根目录放置名为 test.mp4 的测试视频文件")
        return True
    
    try:
        print(f"📁 使用测试视频: {test_video_path}")
        
        # 创建测试任务
        job_id = "test_job_" + str(int(time.time()))
        
        print(f"🚀 开始处理任务: {job_id}")
        
        # 启动后台处理
        task = asyncio.create_task(
            video_processor.process_teacher_video_background(
                job_id=job_id,
                video_path=test_video_path,
                teacher_name="测试外教",
                language_hint="zh-CN",
                quality="fast",  # 使用快速模式进行测试
                output_format="mp4"
            )
        )
        
        # 监控处理进度
        max_wait_time = 300  # 最多等待5分钟
        start_time = time.time()
        
        while not task.done() and (time.time() - start_time) < max_wait_time:
            progress = video_processor.get_job_progress(job_id)
            if progress:
                status = progress.get('status', 'unknown')
                current_progress = progress.get('progress', 0)
                step = progress.get('current_step', 'unknown')
                
                print(f"📊 进度: {current_progress}% - {step} (状态: {status})")
                
                if status in ['completed', 'failed']:
                    break
            
            await asyncio.sleep(2)
        
        # 等待任务完成
        await task
        
        # 检查最终结果
        final_progress = video_processor.get_job_progress(job_id)
        if final_progress:
            if final_progress.get('status') == 'completed':
                print("✅ 视频处理完成!")
                result = final_progress.get('result', {})
                print(f"   处理时间: {result.get('processing_time', 0):.2f}秒")
                print(f"   输出视频: {result.get('processed_video', 'N/A')}")
                print(f"   转录文本: {result.get('transcript', 'N/A')[:100]}...")
                return True
            else:
                error = final_progress.get('error', 'Unknown error')
                print(f"❌ 视频处理失败: {error}")
                return False
        else:
            print("❌ 无法获取处理结果")
            return False
            
    except Exception as e:
        print(f"❌ 视频处理测试失败: {e}")
        return False

def test_configuration():
    """测试配置"""
    print("⚙️  检查配置...")
    
    config_items = [
        ("语音服务", settings.SPEECH_SERVICE),
        ("视频服务", settings.VIDEO_SERVICE),
        ("腾讯云密钥ID", "已配置" if settings.TENCENT_SECRET_ID else "未配置"),
        ("腾讯云存储桶", settings.TENCENT_COS_BUCKET or "未配置"),
        ("最大并发任务", settings.MAX_CONCURRENT_JOBS),
        ("上传目录", settings.UPLOAD_DIR),
        ("输出目录", settings.OUTPUT_DIR),
    ]
    
    all_good = True
    for name, value in config_items:
        status = "✅" if value and value != "未配置" else "⚠️ "
        print(f"   {status} {name}: {value}")
        if value == "未配置" or not value:
            all_good = False
    
    return all_good

def test_directories():
    """测试目录结构"""
    print("\n📁 检查目录结构...")
    
    directories = [
        settings.UPLOAD_DIR,
        settings.OUTPUT_DIR,
        "app/static",
        "app/api",
        "app/services"
    ]
    
    all_good = True
    for directory in directories:
        if os.path.exists(directory):
            print(f"   ✅ {directory}")
        else:
            print(f"   ❌ {directory} (不存在)")
            all_good = False
            # 尝试创建目录
            try:
                os.makedirs(directory, exist_ok=True)
                print(f"   ✅ 已创建 {directory}")
            except Exception as e:
                print(f"   ❌ 无法创建 {directory}: {e}")
    
    return all_good

async def main():
    """主测试函数"""
    print("🎯 外教视频处理系统 - 完整功能测试")
    print("=" * 50)
    
    # 测试项目列表
    tests = [
        ("配置检查", test_configuration),
        ("目录结构", test_directories),
        ("系统状态", test_system_status),
        ("视频处理", test_video_processing),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n🧪 {test_name}测试...")
        try:
            if asyncio.iscoroutinefunction(test_func):
                result = await test_func()
            else:
                result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name}测试异常: {e}")
            results.append((test_name, False))
    
    # 汇总结果
    print("\n" + "=" * 50)
    print("📋 测试结果汇总:")
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"   {test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\n🎯 总体结果: {passed}/{total} 项测试通过")
    
    if passed == total:
        print("🎉 所有测试通过！系统运行正常。")
        print("\n🚀 您现在可以:")
        print("   1. 运行 'python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload' 启动服务")
        print("   2. 打开浏览器访问 http://localhost:8000")
        print("   3. 上传视频文件进行处理")
    else:
        print("⚠️  部分测试失败，请检查配置和依赖。")
    
    return passed == total

if __name__ == "__main__":
    try:
        result = asyncio.run(main())
        sys.exit(0 if result else 1)
    except KeyboardInterrupt:
        print("\n⏹️  测试被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 测试过程中发生异常: {e}")
        sys.exit(1)

