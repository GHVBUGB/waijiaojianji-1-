#!/usr/bin/env python3
"""
检查视频背景是否正确应用
"""
import cv2
import numpy as np
import os
import sys

def analyze_video_background(video_path):
    """分析视频背景颜色"""
    try:
        print(f"🎥 分析视频: {video_path}")
        
        # 打开视频
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            print("❌ 无法打开视频文件")
            return False
        
        # 获取视频信息
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        print(f"📊 视频信息: {width}x{height}, {fps}fps, {frame_count}帧")
        
        # 分析几个关键帧
        frame_indices = [0, frame_count//4, frame_count//2, frame_count*3//4, frame_count-1]
        red_pixel_counts = []
        
        for i, frame_idx in enumerate(frame_indices):
            if frame_idx >= frame_count:
                continue
                
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
            ret, frame = cap.read()
            
            if not ret:
                continue
            
            # 转换为RGB
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # 检测红色像素 (R > 200, G < 100, B < 100)
            red_mask = (frame_rgb[:,:,0] > 200) & (frame_rgb[:,:,1] < 100) & (frame_rgb[:,:,2] < 100)
            red_pixels = np.sum(red_mask)
            total_pixels = width * height
            red_percentage = (red_pixels / total_pixels) * 100
            
            red_pixel_counts.append(red_percentage)
            
            print(f"📍 帧 {frame_idx}: 红色像素占比 {red_percentage:.2f}%")
            
            # 分析边缘区域的颜色（背景通常在边缘）
            edge_width = 50
            edges = np.concatenate([
                frame_rgb[:edge_width, :].reshape(-1, 3),  # 上边缘
                frame_rgb[-edge_width:, :].reshape(-1, 3),  # 下边缘
                frame_rgb[:, :edge_width].reshape(-1, 3),  # 左边缘
                frame_rgb[:, -edge_width:].reshape(-1, 3)   # 右边缘
            ])
            
            # 计算边缘区域的平均颜色
            avg_color = np.mean(edges, axis=0)
            print(f"🖼️ 帧 {frame_idx} 边缘平均颜色: R={avg_color[0]:.1f}, G={avg_color[1]:.1f}, B={avg_color[2]:.1f}")
            
            # 检查是否是红色背景
            if avg_color[0] > 150 and avg_color[1] < 100 and avg_color[2] < 100:
                print(f"✅ 帧 {frame_idx}: 检测到红色背景!")
            else:
                print(f"❌ 帧 {frame_idx}: 未检测到红色背景")
        
        cap.release()
        
        # 总结分析结果
        avg_red_percentage = np.mean(red_pixel_counts)
        print(f"\n📊 分析总结:")
        print(f"平均红色像素占比: {avg_red_percentage:.2f}%")
        
        if avg_red_percentage > 10:
            print("✅ 视频中包含大量红色像素，背景替换可能成功!")
            return True
        else:
            print("❌ 视频中红色像素较少，背景替换可能失败")
            return False
            
    except Exception as e:
        print(f"❌ 分析失败: {e}")
        return False

def main():
    """主函数"""
    print("=" * 60)
    print("🔍 视频背景分析工具")
    print("=" * 60)
    
    # 查找最新的处理文件
    outputs_dir = "outputs"
    if not os.path.exists(outputs_dir):
        print("❌ outputs目录不存在")
        return False
    
    # 获取最新的mp4文件
    mp4_files = []
    for file in os.listdir(outputs_dir):
        if file.endswith('.mp4'):
            file_path = os.path.join(outputs_dir, file)
            mp4_files.append((file_path, os.path.getmtime(file_path)))
    
    if not mp4_files:
        print("❌ 未找到任何mp4文件")
        return False
    
    # 按修改时间排序，获取最新的
    mp4_files.sort(key=lambda x: x[1], reverse=True)
    latest_video = mp4_files[0][0]
    
    print(f"🎯 分析最新视频: {latest_video}")
    
    # 分析视频
    success = analyze_video_background(latest_video)
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 背景替换验证成功!")
    else:
        print("💥 背景替换验证失败!")
    print("=" * 60)
    
    return success

if __name__ == "__main__":
    try:
        result = main()
        sys.exit(0 if result else 1)
    except Exception as e:
        print(f"💥 程序执行失败: {e}")
        sys.exit(1)