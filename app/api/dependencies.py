from fastapi import HTTPException, UploadFile
from typing import Optional
import os
from app.config.settings import settings

async def validate_video_file(file: UploadFile) -> None:
    """
    验证上传的视频文件
    """
    # 检查文件大小
    if file.size and file.size > settings.MAX_VIDEO_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"文件大小超过限制 ({settings.MAX_VIDEO_SIZE // (1024*1024)}MB)"
        )

    # 检查文件扩展名
    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="文件名不能为空"
        )
        
    file_extension = os.path.splitext(file.filename)[1].lower()
    if file_extension not in settings.SUPPORTED_VIDEO_FORMATS:
        raise HTTPException(
            status_code=415,
            detail=f"不支持的文件格式。支持的格式: {', '.join(settings.SUPPORTED_VIDEO_FORMATS)}"
        )

    # 基本的文件内容类型检查（不依赖 libmagic）
    if not file.content_type or not file.content_type.startswith('video/'):
        # 如果没有正确的 content_type，基于扩展名进行宽松检查
        video_extensions = ['.mp4', '.mov', '.avi', '.mkv']
        if file_extension not in video_extensions:
            raise HTTPException(
                status_code=415,
                detail="文件可能不是有效的视频格式"
            )

def get_video_info(file_path: str) -> dict:
    """
    获取视频文件信息
    """
    try:
        import subprocess
        import json

        # 使用 ffprobe 获取视频信息
        cmd = [
            'ffprobe', '-v', 'quiet', '-print_format', 'json',
            '-show_format', '-show_streams', file_path
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

        if result.returncode != 0:
            return {
                "filename": os.path.basename(file_path),
                "size": os.path.getsize(file_path),
                "format": os.path.splitext(file_path)[1],
                "duration": None,
                "resolution": None,
                "error": "无法获取详细视频信息"
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
            "format": format_info.get('format_name', os.path.splitext(file_path)[1]),
            "duration": duration,
            "resolution": resolution,
            "codec": video_stream.get('codec_name') if video_stream else None
        }

    except subprocess.TimeoutExpired:
        return {
            "filename": os.path.basename(file_path),
            "size": os.path.getsize(file_path),
            "format": os.path.splitext(file_path)[1],
            "duration": None,
            "resolution": None,
            "error": "视频信息获取超时"
        }
    except Exception as e:
        # 如果 ffprobe 失败，返回基本信息
        return {
            "filename": os.path.basename(file_path),
            "size": os.path.getsize(file_path) if os.path.exists(file_path) else 0,
            "format": os.path.splitext(file_path)[1],
            "duration": None,
            "resolution": None,
            "error": f"获取视频信息失败: {str(e)}"
        }