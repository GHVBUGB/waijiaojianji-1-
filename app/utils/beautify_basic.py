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
        return os.getenv("FFMPEG_PATH") or shutil.which("ffmpeg") or r"C:\\ffmpeg\\bin\\ffmpeg.exe"


def _build_vf(brightness: float, contrast: float, saturation: float, gamma: float, sharpness: float, denoise: float) -> str:
    # 优化美颜：解决泛白问题，增强画质
    return (
        "scale=in_range=full:out_range=full,"
        f"hqdn3d={denoise}:{denoise}:6:6,"  # 自适应降噪
        f"unsharp=luma_msize_x=5:luma_msize_y=5:luma_amount={sharpness},"  # 锐化
        f"eq=brightness={brightness}:contrast={contrast}:saturation={saturation}:gamma={gamma},"  # 色彩调整
        "format=yuv420p"
    )


async def apply_basic_beauty(
    input_video: str,
    brightness: float = 0.03,
    contrast: float = 1.08,
    saturation: float = 1.12,
    gamma: float = 1.05,
    sharpness: float = 0.3,
    denoise: float = 0.8
) -> Optional[str]:
    try:
        if not os.path.exists(input_video):
            logger.error(f"基础美颜输入视频不存在: {input_video}")
            return None

        ffmpeg = _ffmpeg_path()
        base, ext = os.path.splitext(input_video)
        output = f"{base}_beauty{ext}"
        vf = _build_vf(brightness, contrast, saturation, gamma, sharpness, denoise)

        cmd = [
            ffmpeg, "-y",
            "-i", input_video,
            "-vf", vf,
            "-c:v", "libx264", "-preset", "fast", "-crf", "20",
            "-c:a", "copy",
            "-color_range", "2",
            output
        ]
        logger.info(f"执行基础美颜: {' '.join(cmd)}")

        proc = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        _, stderr = await proc.communicate()
        if proc.returncode != 0:
            try:
                err_text = stderr.decode(errors='ignore')
            except Exception:
                err_text = str(stderr)
            logger.error(f"基础美颜失败: {err_text[:500]}")
            return None

        if os.path.exists(output) and os.path.getsize(output) > 0:
            logger.info(f"基础美颜完成: {output}")
            return output
        return None
    except Exception as e:
        logger.error(f"基础美颜异常: {e}")
        return None


