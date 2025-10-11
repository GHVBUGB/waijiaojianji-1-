import os
import subprocess
import json
from typing import Optional, Dict
from app.config.settings import settings

def get_video_info(file_path: str) -> Dict:
    """
    获取视频文件信息
    """
    try:
        # 使用 ffprobe 获取视频信息
        cmd = [
            'ffprobe', '-v', 'quiet', '-print_format', 'json',
            '-show_format', '-show_streams', file_path
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            return {
                "filename": os.path.basename(file_path),
                "size": os.path.getsize(file_path),
                "format": os.path.splitext(file_path)[1].lower(),
                "duration": None,
                "resolution": None
            }

        data = json.loads(result.stdout)

        # 提取视频流信息
        video_stream = None
        for stream in data.get('streams', []):
            if stream.get('codec_type') == 'video':
                video_stream = stream
                break

        format_info = data.get('format', {})

        duration = float(format_info.get('duration', 0)) if format_info.get('duration') else None

        resolution = None
        if video_stream:
            width = video_stream.get('width')
            height = video_stream.get('height')
            if width and height:
                resolution = f"{width}x{height}"

        return {
            "filename": os.path.basename(file_path),
            "size": int(format_info.get('size', os.path.getsize(file_path))),
            "format": format_info.get('format_name', os.path.splitext(file_path)[1]).lower(),
            "duration": duration,
            "resolution": resolution
        }

    except Exception as e:
        # 如果 ffprobe 失败，返回基本信息
        return {
            "filename": os.path.basename(file_path),
            "size": os.path.getsize(file_path),
            "format": os.path.splitext(file_path)[1].lower(),
            "duration": None,
            "resolution": None
        }

def validate_video_file(file_path: str) -> bool:
    """
    验证视频文件格式和大小
    """
    try:
        # 检查文件是否存在
        if not os.path.exists(file_path):
            return False

        # 检查文件大小
        file_size = os.path.getsize(file_path)
        if file_size > settings.MAX_VIDEO_SIZE:
            return False

        # 检查文件扩展名
        file_extension = os.path.splitext(file_path)[1].lower()
        if file_extension not in settings.SUPPORTED_VIDEO_FORMATS:
            return False

        return True

    except Exception:
        return False

def cleanup_temp_files():
    """
    清理临时文件
    """
    try:
        temp_dir = settings.TEMP_DIR
        if os.path.exists(temp_dir):
            for filename in os.listdir(temp_dir):
                file_path = os.path.join(temp_dir, filename)
                try:
                    if os.path.isfile(file_path):
                        os.unlink(file_path)
                except Exception as e:
                    print(f"清理临时文件失败 {file_path}: {e}")
    except Exception as e:
        print(f"清理临时目录失败: {e}")