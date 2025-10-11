#!/usr/bin/env python3
"""
视频背景分析脚本
用于检查腾讯云万象API处理后的视频是否正确应用了背景替换
"""

import cv2
import numpy as np
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def analyze_video_background(video_path: str):
    """分析视频背景情况"""
    logger.info(f"🔍 开始分析视频: {video_path}")
    
    if not os.path.exists(video_path):
        logger.error(f"❌ 视频文件不存在: {video_path}")
        return
    
    cap = cv2.VideoCapture(video_path)
    
    if not cap.isOpened():
        logger.error("❌ 无法打开视频文件")
        return
    
    # 获取视频信息
    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    duration = frame_count / fps if fps > 0 else 0
    
    logger.info(f"📊 视频信息:")
    logger.info(f"   分辨率: {width}x{height}")
    logger.info(f"   帧率: {fps:.2f} FPS")
    logger.info(f"   总帧数: {frame_count}")
    logger.info(f"   时长: {duration:.2f}秒")
    
    # 分析多帧
    frame_samples = min(10, frame_count)  # 最多分析10帧
    sample_indices = np.linspace(0, frame_count-1, frame_samples, dtype=int)
    
    background_analysis = []
    
    for i, frame_idx in enumerate(sample_indices):
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
        ret, frame = cap.read()
        
        if not ret:
            continue
            
        logger.info(f"🖼️ 分析第 {i+1}/{frame_samples} 帧 (索引: {frame_idx})")
        
        # 检查是否有透明通道
        channels = frame.shape[2] if len(frame.shape) == 3 else 1
        logger.info(f"   通道数: {channels}")
        
        if channels == 4:
            logger.info("✅ 视频包含透明通道（RGBA）")
            alpha_channel = frame[:, :, 3]
            transparent_pixels = np.sum(alpha_channel == 0)
            total_pixels = alpha_channel.size
            transparency_ratio = transparent_pixels / total_pixels
            logger.info(f"   透明像素比例: {transparency_ratio:.2%}")
        else:
            logger.info("⚠️ 视频不包含透明通道（RGB）")
        
        # 分析背景颜色 - 检查边缘区域
        border_width = min(width, height) // 20
        border_pixels = []
        
        # 收集边缘像素
        border_pixels.extend(frame[:border_width, :].reshape(-1, channels))  # 上边缘
        border_pixels.extend(frame[-border_width:, :].reshape(-1, channels))  # 下边缘
        border_pixels.extend(frame[:, :border_width].reshape(-1, channels))  # 左边缘
        border_pixels.extend(frame[:, -border_width:].reshape(-1, channels))  # 右边缘
        
        border_pixels = np.array(border_pixels)
        
        if len(border_pixels) > 0:
            mean_color = np.mean(border_pixels, axis=0)
            if channels >= 3:
                logger.info(f"   边缘区域平均颜色: BGR({mean_color[0]:.1f}, {mean_color[1]:.1f}, {mean_color[2]:.1f})")
                
                # 判断背景类型
                if np.all(mean_color[:3] < 10):
                    background_type = "黑色背景（前景抠图模式）"
                elif np.all(mean_color[:3] > 245):
                    background_type = "白色背景"
                elif np.std(mean_color[:3]) < 20:  # 颜色变化小，可能是纯色背景
                    background_type = f"纯色背景 (BGR: {mean_color[0]:.0f}, {mean_color[1]:.0f}, {mean_color[2]:.0f})"
                else:
                    background_type = "彩色背景（可能是背景替换）"
                
                logger.info(f"   🎭 背景类型: {background_type}")
                background_analysis.append(background_type)
    
    cap.release()
    
    # 总结分析结果
    logger.info("\n📋 分析总结:")
    if background_analysis:
        unique_backgrounds = list(set(background_analysis))
        logger.info(f"   检测到的背景类型: {unique_backgrounds}")
        
        if len(unique_backgrounds) == 1:
            bg_type = unique_backgrounds[0]
            if "黑色背景" in bg_type:
                logger.warning("⚠️ 视频只有前景，没有背景替换！")
                logger.info("💡 建议检查：")
                logger.info("   1. 是否正确传递了背景图片URL")
                logger.info("   2. 万象API是否使用了Combination模式")
                logger.info("   3. BackgroundLogoUrl参数是否正确设置")
            elif "彩色背景" in bg_type:
                logger.info("✅ 检测到彩色背景，背景替换可能成功")
            else:
                logger.info(f"ℹ️ 检测到: {bg_type}")
        else:
            logger.info("ℹ️ 视频中检测到多种背景类型，可能存在场景变化")
    
    logger.info("✅ 视频分析完成")

if __name__ == "__main__":
    # 分析最新的处理后视频
    video_files = []
    outputs_dir = "outputs"
    
    if os.path.exists(outputs_dir):
        for file in os.listdir(outputs_dir):
            if file.endswith('.mp4') and file.startswith('ci_processed_'):
                file_path = os.path.join(outputs_dir, file)
                if os.path.getsize(file_path) > 0:  # 只分析非空文件
                    video_files.append((file_path, os.path.getmtime(file_path)))
    
    if video_files:
        # 按修改时间排序，分析最新的文件
        video_files.sort(key=lambda x: x[1], reverse=True)
        latest_video = video_files[0][0]
        
        logger.info(f"🎯 分析最新的处理后视频: {latest_video}")
        analyze_video_background(latest_video)
    else:
        logger.error("❌ 未找到有效的处理后视频文件")