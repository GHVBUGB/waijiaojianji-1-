import os
import re
import logging
from typing import Optional, Tuple
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)

class NameOverlayService:
    """
    名字提取和视频文本叠加服务
    """
    
    def __init__(self):
        self.font_path = self._get_font_path()
        logger.info(f"名字叠加服务初始化完成，字体路径: {self.font_path}")
    
    def _get_font_path(self) -> str:
        """
        获取系统字体路径
        """
        # Windows系统字体路径
        windows_fonts = [
            "C:/Windows/Fonts/msyh.ttc",  # 微软雅黑
            "C:/Windows/Fonts/simhei.ttf",  # 黑体
            "C:/Windows/Fonts/simsun.ttc",  # 宋体
            "C:/Windows/Fonts/arial.ttf",   # Arial
        ]
        
        for font_path in windows_fonts:
            if os.path.exists(font_path):
                return font_path
        
        # 如果没有找到字体，使用默认字体
        logger.warning("未找到系统字体，将使用FFmpeg默认字体")
        return ""
    
    def extract_name_from_filename(self, filename: str) -> Optional[str]:
        """
        从文件名中提取名字
        
        Args:
            filename: 原始文件名
            
        Returns:
            提取的名字，如果无法提取则返回None
        """
        try:
            # 移除文件扩展名
            name_part = os.path.splitext(filename)[0]
            
            # 常见的名字提取模式
            patterns = [
                # 匹配中文姓名（2-4个中文字符）
                r'([\u4e00-\u9fff]{2,4})',
                # 匹配英文姓名（首字母大写的单词组合）
                r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
                # 匹配包含"老师"的模式
                r'([\u4e00-\u9fff]{2,4})老师',
                # 匹配"teacher_"开头的模式
                r'teacher[_\s]*([\u4e00-\u9fff]{2,4}|[A-Z][a-z]+)',
                # 匹配数字后的名字
                r'\d+[_\s]*([\u4e00-\u9fff]{2,4}|[A-Z][a-z]+)',
            ]
            
            for pattern in patterns:
                match = re.search(pattern, name_part, re.IGNORECASE)
                if match:
                    extracted_name = match.group(1).strip()
                    logger.info(f"从文件名 '{filename}' 中提取到名字: '{extracted_name}'")
                    return extracted_name
            
            # 如果没有匹配到特定模式，尝试提取第一个看起来像名字的部分
            # 分割文件名并查找可能的名字
            parts = re.split(r'[_\s\-\.]+', name_part)
            for part in parts:
                # 检查是否是中文名字（2-4个中文字符）
                if re.match(r'^[\u4e00-\u9fff]{2,4}$', part):
                    logger.info(f"从文件名 '{filename}' 中提取到中文名字: '{part}'")
                    return part
                # 检查是否是英文名字（首字母大写，至少2个字符）
                if re.match(r'^[A-Z][a-z]{1,}$', part) and len(part) >= 2:
                    logger.info(f"从文件名 '{filename}' 中提取到英文名字: '{part}'")
                    return part
            
            logger.warning(f"无法从文件名 '{filename}' 中提取名字")
            return None
            
        except Exception as e:
            logger.error(f"提取名字时发生错误: {str(e)}")
            return None
    
    def add_name_overlay_to_video(
        self, 
        input_video_path: str, 
        output_video_path: str, 
        name: str,
        position: str = "center_right",
        font_size: int = 48,
        font_color: str = "white",
        background_color: str = "black@0.5"
    ) -> bool:
        """
        在视频上添加名字文本叠加
        
        Args:
            input_video_path: 输入视频路径
            output_video_path: 输出视频路径
            name: 要显示的名字
            position: 文本位置 (center_right, top_right, bottom_right等)
            font_size: 字体大小
            font_color: 字体颜色
            background_color: 背景颜色（可选）
            
        Returns:
            是否成功添加文本叠加
        """
        try:
            logger.info(f"开始为视频添加名字叠加: {name}")
            
            # 获取视频尺寸
            width, height = self._get_video_dimensions(input_video_path)
            if not width or not height:
                logger.error("无法获取视频尺寸")
                return False
            
            # 计算文本位置
            x_pos, y_pos = self._calculate_text_position(position, width, height, font_size)
            
            # 构建FFmpeg命令
            cmd = [
                "ffmpeg",
                "-i", input_video_path,
                "-vf"
            ]
            
            # 构建文本滤镜
            if self.font_path:
                text_filter = f"drawtext=fontfile='{self.font_path}':text='{name}':fontsize={font_size}:fontcolor={font_color}:x={x_pos}:y={y_pos}:box=1:boxcolor={background_color}:boxborderw=5"
            else:
                text_filter = f"drawtext=text='{name}':fontsize={font_size}:fontcolor={font_color}:x={x_pos}:y={y_pos}:box=1:boxcolor={background_color}:boxborderw=5"
            
            cmd.extend([text_filter, "-c:a", "copy", "-y", output_video_path])
            
            logger.info(f"执行FFmpeg命令: {' '.join(cmd)}")
            
            # 执行FFmpeg命令
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5分钟超时
            )
            
            if result.returncode == 0:
                logger.info(f"成功添加名字叠加到视频: {output_video_path}")
                return True
            else:
                logger.error(f"FFmpeg执行失败: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            logger.error("FFmpeg执行超时")
            return False
        except Exception as e:
            logger.error(f"添加名字叠加时发生错误: {str(e)}")
            return False
    
    def _get_video_dimensions(self, video_path: str) -> Tuple[Optional[int], Optional[int]]:
        """
        获取视频尺寸
        """
        try:
            cmd = [
                "ffprobe",
                "-v", "quiet",
                "-print_format", "json",
                "-show_streams",
                video_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                logger.error(f"获取视频信息失败: {result.stderr}")
                return None, None
            
            import json
            data = json.loads(result.stdout)
            
            for stream in data.get('streams', []):
                if stream.get('codec_type') == 'video':
                    width = stream.get('width')
                    height = stream.get('height')
                    if width and height:
                        return int(width), int(height)
            
            return None, None
            
        except Exception as e:
            logger.error(f"获取视频尺寸时发生错误: {str(e)}")
            return None, None
    
    def _calculate_text_position(self, position: str, width: int, height: int, font_size: int) -> Tuple[str, str]:
        """
        计算文本位置
        """
        positions = {
            "center_right": (f"w-tw-{font_size}", "(h-th)/2"),
            "top_right": (f"w-tw-{font_size//2}", str(font_size//2)),
            "bottom_right": (f"w-tw-{font_size//2}", f"h-th-{font_size//2}"),
            "center": ("(w-tw)/2", "(h-th)/2"),
            "top_center": ("(w-tw)/2", str(font_size//2)),
            "bottom_center": ("(w-tw)/2", f"h-th-{font_size//2}"),
            "center_left": (str(font_size//2), "(h-th)/2"),
            "top_left": (str(font_size//2), str(font_size//2)),
            "bottom_left": (str(font_size//2), f"h-th-{font_size//2}")
        }
        
        return positions.get(position, positions["center_right"])