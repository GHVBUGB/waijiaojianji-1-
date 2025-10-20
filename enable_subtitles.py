#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
启用字幕功能的简单脚本
"""

import os
import sys

def enable_subtitles():
    """启用字幕功能"""
    print("🎬 启用字幕功能...")
    
    # 设置环境变量
    os.environ['SUBTITLE_ENABLED'] = 'true'
    os.environ['BURN_SUBTITLES_TO_VIDEO'] = 'true'
    
    print("✅ 字幕功能已启用")
    print("📝 配置:")
    print(f"  SUBTITLE_ENABLED: {os.getenv('SUBTITLE_ENABLED')}")
    print(f"  BURN_SUBTITLES_TO_VIDEO: {os.getenv('BURN_SUBTITLES_TO_VIDEO')}")
    
    # 检查OpenAI API密钥
    if os.getenv('OPENAI_API_KEY'):
        print("✅ OpenAI API密钥已配置")
    else:
        print("⚠️ 请设置OPENAI_API_KEY环境变量")
    
    return True

if __name__ == "__main__":
    enable_subtitles()