#!/usr/bin/env python3
"""
检查最新生成的视频文件
"""

import os
import cv2
import numpy as np
from datetime import datetime

def check_latest_video():
    """检查最新的视频文件"""
    outputs_dir = "outputs"
    
    if not os.path.exists(outputs_dir):
        print("❌ outputs目录不存在")
        return False
    
    # 获取所有mp4文件
    mp4_files = []
    for file in os.listdir(outputs_dir):
        if file.endswith('.mp4'):
            file_path = os.path.join(outputs_dir, file)
            mtime = os.path.getmtime(file_path)
            mp4_files.append((file_path, mtime, file))
    
    if not mp4_files:
        print("❌ 未找到任何mp4文件")
        return False
    
    # 按修改时间排序，获取最新的
    mp4_files.sort(key=lambda x: x[1], reverse=True)
    latest_video_path, mtime, filename = mp4_files[0]
    
    print(f"🎯 最新视频文件: {filename}")
    print(f"📅 修改时间: {datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📏 文件大小: {os.path.getsize(latest_video_path) / (1024*1024):.2f}MB")
    
    # 检查视频属性
    try:
        cap = cv2.VideoCapture(latest_video_path)
        if not cap.isOpened():
            print("❌ 无法打开视频文件")
            return False
        
        # 获取视频信息
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        duration = frame_count / fps if fps > 0 else 0
        
        print(f"📊 视频信息:")
        print(f"   分辨率: {width}x{height}")
        print(f"   帧率: {fps:.2f} FPS")
        print(f"   总帧数: {frame_count}")
        print(f"   时长: {duration:.2f}秒")
        
        # 检查几个关键帧
        print(f"\n🔍 检查关键帧:")
        
        # 检查第一帧
        ret, frame = cap.read()
        if ret:
            print(f"   第1帧: ✅ 正常")
            # 分析颜色分布
            avg_color = np.mean(frame, axis=(0, 1))
            print(f"   平均颜色 (BGR): {avg_color}")
            
            # 检查是否有黄色背景（我们的测试背景是黄色）
            # 黄色在BGR中大致是 (0, 255, 255)
            if avg_color[1] > 150 and avg_color[2] > 150:  # G和R通道都比较高
                print(f"   🟡 检测到黄色背景特征")
            else:
                print(f"   🔵 未检测到明显的黄色背景")
        else:
            print(f"   第1帧: ❌ 读取失败")
        
        # 检查中间帧
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_count // 2)
        ret, frame = cap.read()
        if ret:
            print(f"   中间帧: ✅ 正常")
            avg_color = np.mean(frame, axis=(0, 1))
            print(f"   平均颜色 (BGR): {avg_color}")
            
            if avg_color[1] > 150 and avg_color[2] > 150:
                print(f"   🟡 检测到黄色背景特征")
            else:
                print(f"   🔵 未检测到明显的黄色背景")
        else:
            print(f"   中间帧: ❌ 读取失败")
        
        # 检查最后一帧
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_count - 1)
        ret, frame = cap.read()
        if ret:
            print(f"   最后帧: ✅ 正常")
            avg_color = np.mean(frame, axis=(0, 1))
            print(f"   平均颜色 (BGR): {avg_color}")
            
            if avg_color[1] > 150 and avg_color[2] > 150:
                print(f"   🟡 检测到黄色背景特征")
            else:
                print(f"   🔵 未检测到明显的黄色背景")
        else:
            print(f"   最后帧: ❌ 读取失败")
        
        cap.release()
        
        print(f"\n✅ 视频文件检查完成")
        return True
        
    except Exception as e:
        print(f"❌ 检查视频时出错: {e}")
        return False

def main():
    """主函数"""
    print("🎬 检查最新生成的视频文件")
    print("=" * 60)
    
    success = check_latest_video()
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 视频检查成功!")
    else:
        print("💥 视频检查失败!")

if __name__ == "__main__":
    main()