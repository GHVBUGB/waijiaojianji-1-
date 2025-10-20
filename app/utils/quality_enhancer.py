import os
import asyncio
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def _ffmpeg_path() -> str:
    try:
        from app.utils.subtitle_burner import get_ffmpeg_path
        return get_ffmpeg_path()
    except Exception:
        import shutil
        return os.getenv("FFMPEG_PATH") or shutil.which("ffmpeg") or r"C:\ffmpeg\bin\ffmpeg.exe"


def _build_quality_vf() -> str:
    # 画质优化：色彩增强 + 细节锐化 + 降噪 + 色彩空间优化
    return (
        "scale=in_range=full:out_range=full,"
        "hqdn3d=0.5:0.5:3:3,"  # 轻降噪
        "unsharp=luma_msize_x=3:luma_msize_y=3:luma_amount=0.5,"  # 细节锐化
        "eq=contrast=1.02:saturation=1.05:gamma=1.01,"  # 轻微色彩增强
        "format=yuv420p"
    )


async def enhance_video_quality(input_video: str, preset: str = "medium", crf: str = "20") -> Optional[str]:
    """
    画质优化：增强视频质量，提升细节和色彩
    """
    try:
        if not os.path.exists(input_video):
            logger.error(f"画质优化输入视频不存在: {input_video}")
            return None

        ffmpeg = _ffmpeg_path()
        base, ext = os.path.splitext(input_video)
        output = f"{base}_enhanced{ext}"
        vf = _build_quality_vf()

        cmd = [
            ffmpeg, "-y",
            "-i", input_video,
            "-vf", vf,
            "-c:v", "libx264", "-preset", preset, "-crf", crf,
            "-c:a", "copy",
            "-color_range", "2",  # 标记为full range
            "-movflags", "+faststart",  # 优化流媒体播放
            output
        ]
        logger.info(f"执行画质优化: {' '.join(cmd)}")

        proc = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        _, stderr = await proc.communicate()
        if proc.returncode != 0:
            try:
                err_text = stderr.decode(errors='ignore')
            except Exception:
                err_text = str(stderr)
            logger.error(f"画质优化失败: {err_text[:500]}")
            return None

        if os.path.exists(output) and os.path.getsize(output) > 0:
            logger.info(f"画质优化完成: {output}")
            return output
        return None
    except Exception as e:
        logger.error(f"画质优化异常: {e}")
        return None
