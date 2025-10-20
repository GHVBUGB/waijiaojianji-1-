"""
OpenCV视频处理服务 - 使用OpenCV进行智能背景分割和替换
"""
import os
import cv2
import numpy as np
import logging
import tempfile
from typing import Dict, Optional, Tuple
import uuid
from PIL import Image

logger = logging.getLogger(__name__)

class OpenCVVideoProcessor:
    """OpenCV视频处理器 - 智能背景分割"""
    
    def __init__(self):
        logger.info("初始化OpenCV视频处理器")
        
    def extract_foreground_with_grabcut(
        self, 
        image: np.ndarray, 
        iterations: int = 5
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        使用GrabCut算法提取前景
        
        Args:
            image: 输入图像 (BGR格式)
            iterations: GrabCut迭代次数
            
        Returns:
            Tuple[np.ndarray, np.ndarray]: (前景掩码, 分割后的图像)
        """
        try:
            height, width = image.shape[:2]
            
            # 创建掩码
            mask = np.zeros((height, width), np.uint8)
            
            # 定义前景和背景区域
            # 假设人物在中央区域，边缘为背景
            border = min(width, height) // 10
            rect = (border, border, width - 2*border, height - 2*border)
            
            # 初始化前景和背景模型
            bgd_model = np.zeros((1, 65), np.float64)
            fgd_model = np.zeros((1, 65), np.float64)
            
            # 应用GrabCut算法
            cv2.grabCut(image, mask, rect, bgd_model, fgd_model, iterations, cv2.GC_INIT_WITH_RECT)
            
            # 创建最终掩码 (前景和可能前景)
            mask2 = np.where((mask == 2) | (mask == 0), 0, 1).astype('uint8')
            
            # 应用形态学操作来平滑掩码
            kernel = np.ones((3, 3), np.uint8)
            mask2 = cv2.morphologyEx(mask2, cv2.MORPH_CLOSE, kernel)
            mask2 = cv2.morphologyEx(mask2, cv2.MORPH_OPEN, kernel)
            
            # 应用高斯模糊来软化边缘
            mask2 = cv2.GaussianBlur(mask2, (5, 5), 0)
            
            # 创建3通道掩码
            mask3 = np.repeat(mask2[:, :, np.newaxis], 3, axis=2)
            
            # 提取前景
            foreground = image * mask3
            
            return mask2, foreground
            
        except Exception as e:
            logger.error(f"GrabCut前景提取失败: {str(e)}")
            # 返回原图作为前景
            return np.ones((height, width), dtype=np.uint8), image
    
    def enhance_foreground_detection(self, image: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        增强前景检测 - 结合多种方法
        
        Args:
            image: 输入图像
            
        Returns:
            Tuple[np.ndarray, np.ndarray]: (掩码, 前景图像)
        """
        try:
            # 方法1: GrabCut
            mask_grabcut, fg_grabcut = self.extract_foreground_with_grabcut(image)
            
            # 方法2: 边缘检测辅助
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            edges = cv2.Canny(gray, 50, 150)
            
            # 方法3: 颜色分割 (假设背景颜色相对单一)
            hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
            
            # 检测背景主要颜色 (边缘区域)
            h, w = image.shape[:2]
            border_mask = np.zeros((h, w), dtype=np.uint8)
            border_width = min(h, w) // 20
            border_mask[:border_width, :] = 1
            border_mask[-border_width:, :] = 1
            border_mask[:, :border_width] = 1
            border_mask[:, -border_width:] = 1
            
            # 获取边缘区域的颜色统计
            border_pixels = hsv[border_mask == 1]
            if len(border_pixels) > 0:
                # 计算边缘区域的主要颜色
                h_mean = np.mean(border_pixels[:, 0])
                s_mean = np.mean(border_pixels[:, 1])
                v_mean = np.mean(border_pixels[:, 2])
                
                # 创建颜色范围
                h_range = 20
                s_range = 50
                v_range = 50
                
                lower = np.array([max(0, h_mean - h_range), max(0, s_mean - s_range), max(0, v_mean - v_range)])
                upper = np.array([min(179, h_mean + h_range), min(255, s_mean + s_range), min(255, v_mean + v_range)])
                
                # 创建颜色掩码 (背景区域)
                color_mask = cv2.inRange(hsv, lower, upper)
                # 反转得到前景掩码
                color_fg_mask = cv2.bitwise_not(color_mask)
                color_fg_mask = color_fg_mask.astype(np.float32) / 255.0
            else:
                color_fg_mask = np.ones((h, w), dtype=np.float32)
            
            # 结合多种方法
            combined_mask = mask_grabcut.astype(np.float32) * color_fg_mask
            combined_mask = (combined_mask * 255).astype(np.uint8)
            
            # 应用形态学操作
            kernel = np.ones((5, 5), np.uint8)
            combined_mask = cv2.morphologyEx(combined_mask, cv2.MORPH_CLOSE, kernel)
            combined_mask = cv2.morphologyEx(combined_mask, cv2.MORPH_OPEN, kernel)
            
            # 高斯模糊软化边缘
            combined_mask = cv2.GaussianBlur(combined_mask, (7, 7), 0)
            
            # 创建3通道掩码
            mask3 = np.repeat(combined_mask[:, :, np.newaxis], 3, axis=2) / 255.0
            
            # 提取前景
            enhanced_foreground = (image * mask3).astype(np.uint8)
            
            return combined_mask, enhanced_foreground
            
        except Exception as e:
            logger.error(f"增强前景检测失败: {str(e)}")
            return self.extract_foreground_with_grabcut(image)
    
    def composite_with_background(
        self, 
        foreground: np.ndarray, 
        mask: np.ndarray, 
        background: np.ndarray
    ) -> np.ndarray:
        """
        将前景与背景合成
        
        Args:
            foreground: 前景图像
            mask: 前景掩码
            background: 背景图像
            
        Returns:
            np.ndarray: 合成后的图像
        """
        try:
            # 确保所有图像尺寸一致，但保持背景图片原始比例
            bg_h, bg_w = background.shape[:2]
            fg_h, fg_w = foreground.shape[:2]
            
            # 如果前景和背景尺寸不同，将前景缩放到背景尺寸
            if fg_h != bg_h or fg_w != bg_w:
                foreground = cv2.resize(foreground, (bg_w, bg_h))
                if mask.shape[:2] != (bg_h, bg_w):
                    mask = cv2.resize(mask, (bg_w, bg_h))
                
            # 归一化掩码
            if mask.dtype != np.float32:
                mask = mask.astype(np.float32) / 255.0
            
            # 创建3通道掩码
            if len(mask.shape) == 2:
                mask3 = np.repeat(mask[:, :, np.newaxis], 3, axis=2)
            else:
                mask3 = mask
            
            # 合成图像
            composite = foreground * mask3 + background * (1 - mask3)
            
            return composite.astype(np.uint8)
            
        except Exception as e:
            logger.error(f"图像合成失败: {str(e)}")
            return foreground
    
    async def process_video_with_opencv(
        self, 
        input_video_path: str, 
        background_image_path: str,
        output_path: str,
        sample_frames: int = 5,
        fast_mode: bool = True,  # 新增：快速模式
        max_resolution: int = 720,  # 新增：最大分辨率
        target_fps: int = 15  # 新增：目标帧率
    ) -> Dict:
        """
        使用OpenCV处理视频，智能背景替换
        
        Args:
            input_video_path: 输入视频路径
            background_image_path: 背景图片路径
            output_path: 输出视频路径
            sample_frames: 用于背景学习的采样帧数
            fast_mode: 快速模式（简化算法）
            max_resolution: 最大分辨率（720p或480p）
            target_fps: 目标帧率
            
        Returns:
            Dict: 处理结果
        """
        try:
            logger.info(f"开始OpenCV视频处理: {input_video_path}")
            logger.info(f"处理模式: {'快速模式' if fast_mode else '高质量模式'}, 最大分辨率: {max_resolution}p, 目标帧率: {target_fps}fps")
            
            # 检查输入文件
            if not os.path.exists(input_video_path):
                raise FileNotFoundError(f"输入视频不存在: {input_video_path}")
            
            if not os.path.exists(background_image_path):
                raise FileNotFoundError(f"背景图片不存在: {background_image_path}")
            
            # 创建输出目录
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # 打开视频
            cap = cv2.VideoCapture(input_video_path)
            if not cap.isOpened():
                raise ValueError("无法打开输入视频")
            
            # 获取视频属性
            original_fps = int(cap.get(cv2.CAP_PROP_FPS))
            original_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            original_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            
            # 计算优化后的尺寸和帧率
            if original_height > max_resolution:
                scale_factor = max_resolution / original_height
                width = int(original_width * scale_factor)
                height = max_resolution
                logger.info(f"分辨率降采样: {original_width}x{original_height} -> {width}x{height}")
            else:
                width = original_width
                height = original_height
                
            # 帧率降采样
            fps = min(target_fps, original_fps)
            frame_skip = max(1, original_fps // fps)
            
            logger.info(f"视频属性: {width}x{height}, {fps}fps, {total_frames}帧")
            logger.info(f"帧率优化: {original_fps}fps -> {fps}fps (每{frame_skip}帧取1帧)")
            
            # 估算处理时间
            estimated_time = (total_frames // frame_skip) * (0.1 if fast_mode else 0.5)
            logger.info(f"预计处理时间: {estimated_time:.1f}秒")
            
            # 读取背景图片
            background_img = cv2.imread(background_image_path)
            if background_img is None:
                raise ValueError("无法读取背景图片")
            
            # 保持背景图片原始比例，调整视频尺寸以适应背景
            bg_height, bg_width = background_img.shape[:2]
            
            # 如果背景图片太大，按比例缩小但保持比例
            if bg_height > max_resolution:
                scale_factor = max_resolution / bg_height
                bg_width = int(bg_width * scale_factor)
                bg_height = max_resolution
                background_img = cv2.resize(background_img, (bg_width, bg_height))
                logger.info(f"背景图片按比例缩放: {bg_width}x{bg_height}")
            
            # 使用背景图片的尺寸作为输出尺寸
            width = bg_width
            height = bg_height
            
            # 设置视频编码器
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
            
            if not out.isOpened():
                raise ValueError("无法创建输出视频")
            
            processed_frames = 0
            frame_count = 0
            
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                
                frame_count += 1
                
                # 帧率降采样 - 跳过不需要的帧
                if frame_count % frame_skip != 0:
                    continue
                
                try:
                    # 分辨率降采样
                    if width != original_width or height != original_height:
                        frame = cv2.resize(frame, (width, height))
                    
                    # 根据模式选择处理方法
                    if fast_mode:
                        # 快速模式：使用简化的GrabCut算法（减少迭代次数）
                        mask, foreground = self.extract_foreground_with_grabcut(frame, iterations=1)
                    else:
                        # 高质量模式：使用增强的前景检测
                        mask, foreground = self.enhance_foreground_detection(frame)
                    
                    # 与背景合成
                    composite_frame = self.composite_with_background(
                        foreground, mask, background_img
                    )
                    
                    # 写入输出视频
                    out.write(composite_frame)
                    processed_frames += 1
                    
                    # 进度日志 - 更频繁的进度更新
                    if processed_frames % 10 == 0 or processed_frames == 1:
                        progress = (processed_frames / (total_frames // frame_skip)) * 100
                        logger.info(f"OpenCV处理进度: {progress:.1f}% ({processed_frames}/{total_frames // frame_skip}帧)")
                        
                except Exception as e:
                    logger.warning(f"处理第{processed_frames}帧时出错: {str(e)}, 使用原帧")
                    if width != original_width or height != original_height:
                        frame = cv2.resize(frame, (width, height))
                    out.write(frame)
                    processed_frames += 1
            
            # 释放资源
            cap.release()
            out.release()
            
            # 检查输出文件
            if os.path.exists(output_path):
                file_size = os.path.getsize(output_path)
                logger.info(f"OpenCV视频处理成功: {output_path}, 大小: {file_size/1024/1024:.2f}MB")
                
                return {
                    "success": True,
                    "output_path": output_path,
                    "file_size": file_size,
                    "processed_frames": processed_frames,
                    "method": "opencv_grabcut"
                }
            else:
                raise FileNotFoundError("输出文件未生成")
                
        except (cv2.error, ValueError, OSError) as e:
            error_msg = f"OpenCV视频处理失败: {str(e)}"
            logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg
            }
        finally:
            # 确保资源释放
            try:
                cap.release()
                out.release()
            except (AttributeError, cv2.error):
                pass