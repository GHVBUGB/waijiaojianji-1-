"""
本地视频处理服务 - 使用FFmpeg进行背景移除和合成
"""
import os
import subprocess
import logging
import tempfile
from typing import Dict, Optional
import uuid

logger = logging.getLogger(__name__)

class LocalVideoProcessor:
    """本地视频处理器"""
    
    def __init__(self):
        logger.info("初始化本地视频处理器")
    
    async def process_video_with_background(
        self, 
        input_video_path: str, 
        background_image_path: str,
        output_path: str
    ) -> Dict:
        """
        使用本地FFmpeg处理视频，添加背景
        
        Args:
            input_video_path: 输入视频路径
            background_image_path: 背景图片路径
            output_path: 输出视频路径
            
        Returns:
            Dict: 处理结果
        """
        try:
            logger.info(f"开始本地视频处理: {input_video_path}")
            
            # 检查输入文件
            if not os.path.exists(input_video_path):
                raise FileNotFoundError(f"输入视频不存在: {input_video_path}")
            
            if not os.path.exists(background_image_path):
                raise FileNotFoundError(f"背景图片不存在: {background_image_path}")
            
            # 创建输出目录
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # FFmpeg命令 - 保持背景图片原始比例
            cmd = [
                "ffmpeg",
                "-i", input_video_path,  # 输入视频
                "-i", background_image_path,  # 背景图片
                "-filter_complex",
                # 保持背景图片原始尺寸，前景视频适应背景
                "[1:v][0:v]scale2ref=w=iw:h=ih[bg][fg];[bg][fg]overlay=(W-w)/2:(H-h)/2",
                "-c:v", "libx264",
                "-crf", "23",
                "-preset", "medium",
                "-c:a", "copy",  # 复制音频
                "-y",  # 覆盖输出文件
                output_path
            ]
            
            logger.info(f"执行FFmpeg命令: {' '.join(cmd)}")
            
            # 执行命令
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5分钟超时
            )
            
            if result.returncode == 0:
                # 检查输出文件
                if os.path.exists(output_path):
                    file_size = os.path.getsize(output_path)
                    logger.info(f"本地视频处理成功: {output_path}, 大小: {file_size/1024/1024:.2f}MB")
                    
                    return {
                        "success": True,
                        "output_path": output_path,
                        "file_size": file_size,
                        "method": "local_ffmpeg"
                    }
                else:
                    raise FileNotFoundError("输出文件未生成")
            else:
                error_msg = f"FFmpeg处理失败: {result.stderr}"
                logger.error(error_msg)
                return {
                    "success": False,
                    "error": error_msg
                }
                
        except subprocess.TimeoutExpired:
            error_msg = "本地视频处理超时"
            logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg
            }
        except Exception as e:
            error_msg = f"本地视频处理异常: {str(e)}"
            logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg
            }
    
    async def remove_background_with_chroma(
        self,
        input_video_path: str,
        output_path: str,
        chroma_color: str = "black",
        threshold: float = 0.3
    ) -> Dict:
        """
        使用色度键移除背景
        
        Args:
            input_video_path: 输入视频路径
            output_path: 输出视频路径
            chroma_color: 要移除的颜色
            threshold: 阈值
            
        Returns:
            Dict: 处理结果
        """
        try:
            logger.info(f"开始色度键背景移除: {input_video_path}")
            
            # 创建输出目录
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # 使用FFmpeg的colorkey滤镜移除背景
            cmd = [
                "ffmpeg",
                "-i", input_video_path,
                "-vf", f"colorkey={chroma_color}:{threshold}:0.1",
                "-c:v", "libx264",
                "-pix_fmt", "yuv420p",
                "-c:a", "copy",
                "-y",
                output_path
            ]
            
            logger.info(f"执行色度键命令: {' '.join(cmd)}")
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300
            )
            
            if result.returncode == 0 and os.path.exists(output_path):
                file_size = os.path.getsize(output_path)
                logger.info(f"色度键处理成功: {output_path}")
                
                return {
                    "success": True,
                    "output_path": output_path,
                    "file_size": file_size,
                    "method": "chroma_key"
                }
            else:
                error_msg = f"色度键处理失败: {result.stderr}"
                logger.error(error_msg)
                return {
                    "success": False,
                    "error": error_msg
                }
                
        except Exception as e:
            error_msg = f"色度键处理异常: {str(e)}"
            logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg
            }