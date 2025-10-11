"""
视频合成服务 - 将抠图后的前景视频与背景图片合成
"""

import os
import subprocess
import logging
import tempfile
from typing import Dict, Optional
import time

logger = logging.getLogger(__name__)

class VideoCompositorService:
    """视频合成服务"""
    
    def __init__(self):
        self.name = "Video Compositor Service"
        logger.info("初始化视频合成服务")
    
    async def composite_with_background(
        self, 
        foreground_video_path: str, 
        background_image_path: str, 
        output_path: str,
        quality: str = "medium"
    ) -> Dict:
        """
        将前景视频与背景图片合成
        
        Args:
            foreground_video_path: 前景视频路径（透明背景）
            background_image_path: 背景图片路径
            output_path: 输出视频路径
            quality: 处理质量
            
        Returns:
            Dict: 合成结果
        """
        start_time = time.time()
        
        try:
            logger.info(f"开始视频合成: {foreground_video_path} + {background_image_path}")
            
            # 检查输入文件
            if not os.path.exists(foreground_video_path):
                raise FileNotFoundError(f"前景视频不存在: {foreground_video_path}")
            
            if not os.path.exists(background_image_path):
                raise FileNotFoundError(f"背景图片不存在: {background_image_path}")
            
            # 根据质量设置参数
            if quality == "high":
                crf = "18"
                preset = "slow"
            elif quality == "fast":
                crf = "28"
                preset = "ultrafast"
            else:  # medium
                crf = "23"
                preset = "medium"
            
            # FFmpeg合成命令
            # 使用overlay滤镜将前景视频叠加到背景图片上
            cmd = [
                "ffmpeg",
                "-i", background_image_path,  # 背景图片
                "-i", foreground_video_path,  # 前景视频
                "-filter_complex", 
                "[0:v]scale=1920:1080[bg];[1:v]scale=1920:1080[fg];[bg][fg]overlay=0:0",
                "-c:v", "libx264",
                "-crf", crf,
                "-preset", preset,
                "-c:a", "aac",
                "-b:a", "128k",
                "-y",  # 覆盖输出文件
                output_path
            ]
            
            logger.info(f"执行FFmpeg命令: {' '.join(cmd)}")
            
            # 执行合成
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5分钟超时
            )
            
            if result.returncode == 0:
                processing_time = time.time() - start_time
                output_size = os.path.getsize(output_path) if os.path.exists(output_path) else 0
                
                logger.info(f"视频合成完成: {output_path}")
                logger.info(f"处理耗时: {processing_time:.2f}秒")
                logger.info(f"输出文件大小: {output_size / (1024*1024):.2f}MB")
                
                return {
                    'success': True,
                    'output_path': output_path,
                    'processing_time': processing_time,
                    'output_size': output_size,
                    'method': 'ffmpeg_composite'
                }
            else:
                error_msg = f"FFmpeg合成失败: {result.stderr}"
                logger.error(error_msg)
                raise Exception(error_msg)
                
        except subprocess.TimeoutExpired:
            error_msg = "视频合成超时"
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg,
                'processing_time': time.time() - start_time
            }
        except Exception as e:
            error_msg = str(e)
            logger.error(f"视频合成失败: {error_msg}")
            return {
                'success': False,
                'error': error_msg,
                'processing_time': time.time() - start_time
            }
    
    def create_default_background(self, width: int = 1920, height: int = 1080) -> str:
        """
        创建默认背景图片
        
        Args:
            width: 背景宽度
            height: 背景高度
            
        Returns:
            str: 背景图片路径
        """
        try:
            # 首先尝试使用项目中的背景图片（随机选择）
            backgrounds_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "backgrounds")
            
            if os.path.exists(backgrounds_dir):
                # 获取所有背景图片
                background_files = []
                for file in os.listdir(backgrounds_dir):
                    if file.lower().endswith(('.png', '.jpg', '.jpeg')):
                        background_files.append(os.path.join(backgrounds_dir, file))
                
                if background_files:
                    # 随机选择一张背景图片
                    import random
                    selected_bg = random.choice(background_files)
                    logger.info(f"随机选择背景图片: {selected_bg}")
                    return selected_bg
            
            # 如果项目背景不存在，创建临时背景图片
            temp_bg_path = os.path.join(tempfile.gettempdir(), "default_background.png")
            
            # 使用FFmpeg创建渐变背景
            cmd = [
                "ffmpeg",
                "-f", "lavfi",
                "-i", f"color=c=0x4a90e2:size={width}x{height}:duration=1",
                "-vframes", "1",
                "-y",
                temp_bg_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0 and os.path.exists(temp_bg_path):
                logger.info(f"创建临时背景: {temp_bg_path}")
                return temp_bg_path
            else:
                logger.error(f"创建临时背景失败: {result.stderr}")
                return None
                
        except Exception as e:
            logger.error(f"创建默认背景异常: {str(e)}")
            return None