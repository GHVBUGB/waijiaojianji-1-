#!/usr/bin/env python3
"""
测试真实的视频处理功能
包括OpenAI Whisper语音转文字和腾讯云背景移除
"""

import asyncio
import os
import sys
import logging
from pathlib import Path

# 添加项目路径
sys.path.append(str(Path(__file__).parent))

from app.config.settings import settings
from app.services.speech_to_text import WhisperService
from app.services.tencent_video_service import TencentVideoService

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_speech_to_text(video_path: str):
    """测试OpenAI Whisper语音转文字"""
    print("\n[语音转文字] 测试 OpenAI Whisper...")
    print(f"视频文件: {video_path}")
    
    try:
        whisper = WhisperService()
        result = await whisper.transcribe_video(video_path, language_hint="en")
        
        if result.get("success"):
            print("[SUCCESS] 语音转文字成功!")
            print(f"检测语言: {result.get('language')}")
            print(f"音频时长: {result.get('duration'):.2f}秒")
            print(f"处理时间: {result.get('processing_time'):.2f}秒")
            print(f"转录文本: {result.get('text')[:200]}...")
            return result
        else:
            print("[ERROR] 语音转文字失败!")
            print(f"错误: {result.get('error')}")
            return None
            
    except Exception as e:
        print(f"[EXCEPTION] 语音转文字异常: {str(e)}")
        return None

async def test_background_removal(video_path: str):
    """测试腾讯云背景移除"""
    print("\n[背景移除] 测试腾讯云背景移除...")
    print(f"视频文件: {video_path}")
    
    try:
        tencent = TencentVideoService()
        result = await tencent.remove_background(video_path, settings.OUTPUT_DIR)
        
        if result.get("success"):
            print("[SUCCESS] 背景移除成功!")
            print(f"输出文件: {result.get('output_path')}")
            print(f"原始大小: {result.get('original_size') / (1024*1024):.2f}MB")
            print(f"处理后大小: {result.get('processed_size') / (1024*1024):.2f}MB")
            print(f"处理时间: {result.get('processing_time'):.2f}秒")
            return result
        else:
            print("[ERROR] 背景移除失败!")
            print(f"错误: {result.get('error')}")
            return None
            
    except Exception as e:
        print(f"[EXCEPTION] 背景移除异常: {str(e)}")
        return None

async def test_full_processing(video_path: str):
    """测试完整的视频处理流程"""
    print("[开始测试] 完整视频处理流程...")
    print("="*50)
    
    # 检查视频文件
    if not os.path.exists(video_path):
        print(f"[ERROR] 视频文件不存在: {video_path}")
        return
    
    file_size = os.path.getsize(video_path) / (1024*1024)
    print(f"[文件信息] 视频文件: {os.path.basename(video_path)}")
    print(f"[文件信息] 文件大小: {file_size:.2f}MB")
    
    # 测试语音转文字
    speech_result = await test_speech_to_text(video_path)
    
    # 测试背景移除
    video_result = await test_background_removal(video_path)
    
    # 总结结果
    print("\n[测试总结] 结果:")
    print("="*30)
    if speech_result and speech_result.get("success"):
        print("[OK] 语音转文字: 成功")
    else:
        print("[FAIL] 语音转文字: 失败")
        
    if video_result and video_result.get("success"):
        print("[OK] 背景移除: 成功")
    else:
        print("[FAIL] 背景移除: 失败")
    
    if speech_result and video_result and speech_result.get("success") and video_result.get("success"):
        print("\n[完成] 完整处理流程测试成功!")
        print(f"[转录] 转录文本: {speech_result.get('text')[:100]}...")
        print(f"[视频] 处理后视频: {video_result.get('output_path')}")
    else:
        print("\n[警告] 部分功能测试失败，请检查配置")

def main():
    """主函数"""
    print("外教视频处理系统 - 功能测试")
    print("="*50)
    
    # 查找测试视频
    uploads_dir = Path("uploads")
    if not uploads_dir.exists():
        print("[ERROR] uploads目录不存在")
        return
    
    video_files = list(uploads_dir.glob("*.mp4"))
    if not video_files:
        print("[ERROR] uploads目录中没有找到mp4文件")
        return
    
    # 使用第一个视频文件进行测试
    test_video = str(video_files[0])
    print(f"[测试文件] 使用视频: {test_video}")
    
    # 运行测试
    asyncio.run(test_full_processing(test_video))

if __name__ == "__main__":
    main()