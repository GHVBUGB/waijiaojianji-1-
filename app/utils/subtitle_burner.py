import os
import shutil
import subprocess
from pathlib import Path
from typing import Optional, List


def get_ffmpeg_path() -> str:
    """Resolve ffmpeg binary path with environment, PATH, or Windows default."""
    env_path = os.getenv("FFMPEG_PATH")
    if env_path and os.path.exists(env_path):
        return env_path
    detected = shutil.which("ffmpeg")
    if detected:
        return detected
    win_default = r"C:\\ffmpeg\\bin\\ffmpeg.exe"
    return win_default if os.path.exists(win_default) else "ffmpeg"


def escape_path_for_subtitles_filter(file_path: str) -> str:
    """Convert path to a form acceptable by ffmpeg subtitles filter on Windows.
    Uses forward slashes and escapes the drive colon.
    """
    p = str(Path(file_path).resolve())
    p = p.replace("\\", "/")
    if ":" in p:
        drive, rest = p.split(":", 1)
        p = f"{drive}\\:{rest}"
    return p


def build_subtitles_cmd(
    input_video: str,
    srt_file: str,
    output_video: str,
    font_name: str = "Microsoft YaHei Bold",
    font_size: int = 24,
    margin_v: int = 20,
    alignment: int = 2,
) -> List[str]:
    """Build a robust ffmpeg command to burn SRT subtitles with visible style."""
    ffmpeg = get_ffmpeg_path()
    srt_escaped = escape_path_for_subtitles_filter(srt_file)

    # libass color format is &HAABBGGRR; 00 = fully opaque
    # 用户需求：黑色文字、更小字号、位置更靠下（更接近底部）
    primary = "&H00000000"  # black text
    outline_colour = "&H00FFFFFF"  # white outline to keep readability on dark backgrounds

    # 使用描边样式而非不透明底框，避免遮挡画面：BorderStyle=1 + Outline>0
    # Alignment: 2 = bottom-center（用户期望）
    force_style_raw = (
        f"FontName={font_name},FontSize={font_size},PrimaryColour={primary},OutlineColour={outline_colour},"
        f"BorderStyle=1,Outline=3,Shadow=0,Alignment={alignment},MarginV={margin_v},Bold=1"
    )
    force_style_escaped = force_style_raw.replace("\\", r"\\").replace(",", r"\,")

    # Quote the value so commas are treated as part of the string
    filter_arg = f"subtitles=filename='{srt_escaped}':charenc=UTF-8:force_style='{force_style_escaped}'"

    cmd = [
        ffmpeg,
        "-loglevel",
        "info",
        "-i",
        input_video,
        "-vf",
        filter_arg,
        "-c:v",
        "libx264",
        "-crf",
        "18",
        "-preset",
        "medium",
        "-c:a",
        "copy",
        "-y",
        output_video,
    ]
    return cmd


async def burn_subtitles(
    input_video: str,
    srt_file: str,
    output_video: Optional[str] = None,
    font_name: str = "Microsoft YaHei Bold",
    font_size: int = 24,
    margin_v: int = 20,
    timeout_sec: int = 600,
) -> Optional[str]:
    """Run ffmpeg to burn subtitles and write a side log file. Returns output path on success."""
    in_path = str(Path(input_video))
    if output_video is None:
        base = str(Path(input_video).with_suffix(""))
        output_video = f"{base}_with_subtitles.mp4"

    cmd = build_subtitles_cmd(
        in_path, srt_file, output_video, font_name=font_name, font_size=font_size, margin_v=margin_v
    )

    log_file = Path(in_path).with_suffix("")
    log_path = f"{log_file}_subtitle_log.txt"

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_sec)
    with open(log_path, "w", encoding="utf-8") as f:
        f.write("Command: " + " ".join(cmd) + "\n")
        f.write(f"Return code: {result.returncode}\n")
        f.write("STDERR:\n" + result.stderr + "\n")
        f.write("STDOUT:\n" + result.stdout + "\n")

    if result.returncode == 0 and Path(output_video).exists():
        return output_video
    return None


