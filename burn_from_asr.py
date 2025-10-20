import os
import sys
import json
from pathlib import Path
from typing import Optional

from app.utils.subtitle_burner import burn_subtitles


def generate_srt_via_asr(video_path: str, service: str = "tencent") -> Optional[str]:
    """Generate SRT by calling an available ASR implementation in repo.
    Returns path to generated SRT or None on failure.
    """
    try:
        # Prefer existing services in codebase
        if service.lower() == "xunfei":
            from app.services.xunfei_asr_service import xunfei_asr_service
            if not xunfei_asr_service:
                print("讯飞ASR不可用")
                return None
            # Extract audio using ffmpeg via video_processor convention
            import subprocess
            audio_path = str(Path(video_path).with_suffix("_audio.wav"))
            subprocess.run([
                os.getenv('FFMPEG_PATH', 'ffmpeg'), '-i', video_path, '-vn', '-acodec', 'pcm_s16le',
                '-ar', '16000', '-ac', '1', '-y', audio_path
            ], check=True, capture_output=True)

            segments = xunfei_asr_service.transcribe_audio(audio_path)
            if Path(audio_path).exists():
                Path(audio_path).unlink(missing_ok=True)
            if not segments:
                return None
            # Normalize to SRT
            base = str(Path(video_path).with_suffix(""))
            srt_path = f"{base}.srt"
            with open(srt_path, "w", encoding="utf-8") as f:
                for i, seg in enumerate(segments, 1):
                    start = _to_srt_time(seg.get("start_time", seg.get("start", 0)))
                    end = _to_srt_time(seg.get("end_time", seg.get("end", 0)))
                    text = (seg.get("text") or "").strip()
                    f.write(f"{i}\n{start} --> {end}\n{text}\n\n")
            return srt_path
        else:
            # Tencent SDK service used by current repo
            from app.services.tencent_asr_sdk import TencentASRSDKService
            svc = TencentASRSDKService()
            result = svc.transcribe_video(video_path, language_hint=os.getenv("LANG_HINT", "zh-CN"))
            if not result.get("success") or not result.get("segments"):
                return None
            base = str(Path(video_path).with_suffix(""))
            srt_path = f"{base}.srt"
            with open(srt_path, "w", encoding="utf-8") as f:
                for i, seg in enumerate(result["segments"], 1):
                    start = _to_srt_time(seg.get("start", 0))
                    end = _to_srt_time(seg.get("end", 0))
                    text = (seg.get("text") or "").strip()
                    f.write(f"{i}\n{start} --> {end}\n{text}\n\n")
            return srt_path
    except Exception as e:
        print("ASR失败:", e)
        return None


def _to_srt_time(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds % 1) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def main():
    if len(sys.argv) < 2:
        print("用法: python burn_from_asr.py <video_path> [srt_path] [font_size]")
        sys.exit(1)

    video = Path(sys.argv[1]).resolve()
    srt = Path(sys.argv[2]).resolve() if len(sys.argv) >= 3 else None
    font_size = int(sys.argv[3]) if len(sys.argv) >= 4 else 40

    if not video.exists():
        print("❌ 视频不存在:", video)
        sys.exit(2)

    # If no SRT provided, try ASR
    if srt is None:
        service = os.getenv("ASR_SERVICE", "tencent")
        print("未提供SRT，使用ASR生成... 服务:", service)
        gen = generate_srt_via_asr(str(video), service=service)
        if not gen:
            print("❌ 无法生成SRT")
            sys.exit(3)
        srt = Path(gen)

    if not srt.exists():
        print("❌ 字幕文件不存在:", srt)
        sys.exit(4)

    out = burn_subtitles(
        input_video=str(video),
        srt_file=str(srt),
        font_name=os.getenv("SUBTITLE_FONT_NAME", "Microsoft YaHei"),
        font_size=font_size,
        margin_v=int(os.getenv("SUBTITLE_MARGIN_V", "60")),
    )

    manifest = {
        "video": str(video),
        "srt": str(srt),
        "output": out,
    }
    print(json.dumps(manifest, ensure_ascii=False, indent=2))

    if not out:
        sys.exit(5)


if __name__ == "__main__":
    main()


