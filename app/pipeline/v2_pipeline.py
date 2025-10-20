import os
import shutil
import subprocess
from pathlib import Path
from typing import Optional, Dict

from app.utils.subtitle_burner import burn_subtitles


def _get_ffmpeg() -> str:
    return os.getenv("FFMPEG_PATH") or shutil.which("ffmpeg") or r"C:\\ffmpeg\\bin\\ffmpeg.exe"


def composite_with_background_local(input_video: str, background_image: str, output_video: str, size: Optional[str] = None) -> Dict:
    ffmpeg = _get_ffmpeg()
    filters = []
    if size:
        filters.append(f"scale={size}")
    # 背景铺满，前景居中
    # 使用 scale2ref 将背景缩放到与前景视频一致尺寸
    filter_complex = (
        f"[1:v][0:v]scale2ref=w=iw:h=ih[bg][fg];"
        f"[bg][fg]overlay=0:0:format=auto"
    )
    cmd = [
        ffmpeg,
        "-i", input_video,
        "-loop", "1", "-i", background_image,
        "-filter_complex", filter_complex,
        "-c:v", "libx264", "-preset", "medium", "-crf", "20",
        "-c:a", "copy", "-shortest",
        "-y", output_video,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return {"success": result.returncode == 0, "cmd": " ".join(cmd), "stderr": result.stderr, "output": output_video}


def extract_frames(input_video: str, at_seconds: list[int], out_dir: str) -> list[str]:
    ffmpeg = _get_ffmpeg()
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    outputs = []
    for s in at_seconds:
        out = Path(out_dir) / f"frame_{s}s.png"
        cmd = [ffmpeg, "-y", "-ss", str(s), "-i", input_video, "-frames:v", "1", str(out)]
        subprocess.run(cmd, capture_output=True)
        if out.exists():
            outputs.append(str(out))
    return outputs


def run_pipeline_v2(
    source_video: str,
    background_image: Optional[str],
    output_dir: str = "outputs",
    srt_file: Optional[str] = None,
) -> Dict:
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    base = Path(output_dir) / f"v2_{Path(source_video).stem}.mp4"
    if background_image:
        comp = composite_with_background_local(source_video, background_image, str(base))
        if not comp.get("success"):
            return {"success": False, "error": "composite_failed", "detail": comp}
    else:
        shutil.copy2(source_video, base)

    burned: Optional[str] = None
    if srt_file:
        burned = __import__(__name__)
        # use async burner in sync by running a subprocess within the utility; fallback to direct ffmpeg if needed
    
    # 直接调用字幕工具（同步等待）
    from asyncio import run as asyncio_run
    if srt_file:
        burned_path = asyncio_run(burn_subtitles(str(base), srt_file))
        if burned_path:
            burned = burned_path

    final_video = burned or str(base)
    frames = extract_frames(final_video, [2, 4], output_dir)
    manifest = {
        "source": str(source_video),
        "background": str(background_image) if background_image else None,
        "composited": str(base),
        "subtitle": srt_file,
        "final": final_video,
        "frames": frames,
    }
    (Path(output_dir) / "v2_manifest.json").write_text(__import__("json").dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"success": True, "manifest": manifest}


