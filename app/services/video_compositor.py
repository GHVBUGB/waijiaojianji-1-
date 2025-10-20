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
            
            # FFmpeg合成命令（显式映射音频，避免丢音频）
            # 保持背景图片原始比例，前景视频适应背景尺寸
            from app.utils.subtitle_burner import get_ffmpeg_path
            ffmpeg = get_ffmpeg_path()
            # 固定比例缩放前景：使“主体”（按alpha包围盒裁剪后）的高度占背景高度的一定比例，并在底部居中叠加
            from app.config.settings import settings
            ratio = getattr(settings, 'FG_SCALE_RATIO', 0.72)
            bottom_margin = getattr(settings, 'FG_BOTTOM_MARGIN', 40)
            top_margin = getattr(settings, 'FG_TOP_MARGIN', 40)
            safe_ratio = getattr(settings, 'FG_SAFE_MARGIN_RATIO', 0.05)

            # 检测前景是否含alpha通道（若有则优先基于alpha求包围盒，否则基于亮度）
            ffprobe = "ffprobe"
            if ffmpeg.lower().endswith("ffmpeg") or ffmpeg.lower().endswith("ffmpeg.exe"):
                ffprobe = ffmpeg.replace("ffmpeg.exe", "ffprobe.exe").replace("ffmpeg", "ffprobe")
            has_alpha = False
            try:
                probe = subprocess.run(
                    [ffprobe, "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=pix_fmt", "-of", "default=nw=1:nk=1", foreground_video_path],
                    capture_output=True, text=True, timeout=10
                )
                pixfmt = (probe.stdout or "").strip().lower()
                has_alpha = "a" in pixfmt  # 粗略判断：rgba、bgra、yuva* 等
                logger.info(f"前景像素格式: {pixfmt} (has_alpha={has_alpha})")
            except Exception as _e:
                logger.warning(f"ffprobe 检测alpha失败，按无alpha处理: {_e}")

            # 使用 ih2(背景高度) 作为参考；并加入左右/上下安全边距限制，避免触边
            # 左右安全边距按背景高度的比例计算（对不同画面一致）
            safe_lr = f"round(ih2*{safe_ratio})"
            # 目标基础尺寸（偶数）
            base_w = f"trunc((ih2*{ratio}*a)/2)*2"
            base_h = f"trunc((ih2*{ratio})/2)*2"
            # 加入 min 约束：不超过 (背景宽度 - 左右安全边距*2) 与 (背景高度 - 上下边距)
            w_expr = f"min({base_w}, iw2-2*{safe_lr})"
            h_expr = f"min({base_h}, ih2-{top_margin}-{bottom_margin})"

            if has_alpha:
                # 基于alpha提取的bbox
                filter_graph = (
                    f"[1:v]split[fa][fb];"
                    f"[fa]alphaextract,bbox[meta];"
                    f"[fb][meta]metadata=mode=copy[fgm];"
                    f"[fgm]crop=w=metadata('lavfi.bbox.w'):h=metadata('lavfi.bbox.h'):x=metadata('lavfi.bbox.x'):y=metadata('lavfi.bbox.y')[fgc];"
                    f"[fgc][0:v]scale2ref=w={w_expr}:h={h_expr}[fgs][bg];"
                    f"[bg][fgs]overlay=(W-w)/2:{top_margin}+((H-{top_margin}-{bottom_margin})-h)/2+({bottom_margin}-{top_margin})/2[vout]"
                )
            else:
                # 基于亮度的bbox（非黑区域），兼容无alpha的前景
                filter_graph = (
                    f"[1:v]split[fx][fb];"
                    f"[fx]format=gray,bbox[meta2];"
                    f"[fb][meta2]metadata=mode=copy[fgm];"
                    f"[fgm]crop=w=metadata('lavfi.bbox.w'):h=metadata('lavfi.bbox.h'):x=metadata('lavfi.bbox.x'):y=metadata('lavfi.bbox.y')[fgc];"
                    f"[fgc][0:v]scale2ref=w={w_expr}:h={h_expr}[fgs][bg];"
                    f"[bg][fgs]overlay=(W-w)/2:{top_margin}+((H-{top_margin}-{bottom_margin})-h)/2+({bottom_margin}-{top_margin})/2[vout]"
                )
            cmd = [
                ffmpeg,
                "-i", background_image_path,  # 背景图片（输入0）
                "-i", foreground_video_path,  # 前景视频（输入1，含音频）
                "-filter_complex", filter_graph,
                "-map", "[vout]",           # 显式选择合成后的视频
                "-map", "1:a:0",            # 显式选择前景视频的音频
                "-c:v", "libx264",
                "-crf", crf,
                "-preset", preset,
                "-c:a", "copy",             # 直接复制音频以避免转码
                "-shortest",                 # 对齐最短流，避免尾部静音/黑场
                "-y",                        # 覆盖输出文件
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