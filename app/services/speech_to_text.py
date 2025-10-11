from openai import OpenAI
import os
import logging
import subprocess
import tempfile
import time
from typing import Dict, List
from app.config.settings import settings

logger = logging.getLogger(__name__)

class WhisperService:
    def __init__(self):
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)

    async def extract_audio_from_video(self, video_path: str) -> str:
        """从视频中提取音频"""
        try:
            logger.info(f"开始从视频提取音频: {video_path}")

            # 创建临时音频文件
            with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as temp_audio:
                temp_audio_path = temp_audio.name

            # 使用FFmpeg提取音频
            cmd = [
                'ffmpeg', '-i', video_path,
                '-vn',  # 不要视频流
                '-acodec', 'mp3',  # 音频编码为MP3
                '-ar', str(settings.AUDIO_SAMPLE_RATE),  # 采样率
                '-ac', '1',  # 单声道
                '-y',  # 覆盖输出文件
                temp_audio_path
            ]

            # 运行FFmpeg命令
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5分钟超时
            )

            if result.returncode != 0:
                logger.error(f"FFmpeg错误: {result.stderr}")
                raise Exception(f"音频提取失败: {result.stderr}")

            # 检查输出文件是否存在且有内容
            if not os.path.exists(temp_audio_path) or os.path.getsize(temp_audio_path) == 0:
                raise Exception("提取的音频文件为空")

            logger.info(f"音频提取成功: {temp_audio_path}")
            logger.info(f"音频文件大小: {os.path.getsize(temp_audio_path) / (1024*1024):.2f}MB")

            return temp_audio_path

        except subprocess.TimeoutExpired:
            raise Exception("音频提取超时")
        except Exception as e:
            logger.error(f"音频提取错误: {str(e)}")
            raise

    async def transcribe_video(self, video_path: str, language_hint: str = None) -> Dict:
        """
        转录视频中的语音

        Args:
            video_path: 视频文件路径
            language_hint: 语言提示（如：en, zh, es）

        Returns:
            Dict: 转录结果
        """
        temp_audio_path = None
        start_time = time.time()

        try:
            logger.info(f"开始转录视频: {video_path}")

            # 1. 提取音频
            temp_audio_path = await self.extract_audio_from_video(video_path)

            # 2. 转录音频
            result = await self._transcribe_audio(temp_audio_path, language_hint)

            processing_time = time.time() - start_time
            logger.info(f"转录完成，耗时: {processing_time:.2f}秒")

            result["processing_time"] = processing_time
            return result

        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"视频转录失败: {str(e)}")
            return {
                "success": False,
                "text": "",
                "language": "",
                "duration": 0,
                "segments": [],
                "processing_time": processing_time,
                "error": str(e)
            }
        finally:
            # 清理临时音频文件
            if temp_audio_path and os.path.exists(temp_audio_path):
                try:
                    os.unlink(temp_audio_path)
                    logger.info("临时音频文件已删除")
                except Exception as e:
                    logger.warning(f"删除临时文件失败: {str(e)}")

    async def _transcribe_audio(self, audio_path: str, language_hint: str = None) -> Dict:
        """转录音频文件"""
        try:
            logger.info("正在调用 OpenAI Whisper API...")

            with open(audio_path, "rb") as audio_file:
                # 构建请求参数
                transcribe_params = {
                    "model": "whisper-1",
                    "file": audio_file,
                    "response_format": "verbose_json"
                }

                # 如果提供了语言提示，添加到参数中
                if language_hint:
                    transcribe_params["language"] = language_hint
                    logger.info(f"使用语言提示: {language_hint}")

                # 调用 Whisper API
                transcript = self.client.audio.transcriptions.create(**transcribe_params)

            # 处理返回结果
            segments = []
            if hasattr(transcript, 'segments') and transcript.segments:
                segments = [
                    {
                        "start": segment.start,
                        "end": segment.end,
                        "text": segment.text.strip()
                    }
                    for segment in transcript.segments
                ]

            duration = segments[-1]["end"] if segments else 0

            logger.info(f"转录成功！语言: {transcript.language}, 时长: {duration:.2f}秒")
            logger.info(f"转录文本预览: {transcript.text[:100]}...")

            return {
                "success": True,
                "text": transcript.text.strip(),
                "language": transcript.language,
                "duration": duration,
                "segments": segments
            }

        except Exception as e:
            logger.error(f"Whisper API调用失败: {str(e)}")

            # 根据错误类型提供更具体的错误信息
            if "insufficient_quota" in str(e).lower():
                error_msg = "OpenAI API 余额不足，请充值后重试"
            elif "invalid_api_key" in str(e).lower():
                error_msg = "OpenAI API Key 无效，请检查配置"
            elif "rate_limit" in str(e).lower():
                error_msg = "API 调用频率超限，请稍后重试"
            else:
                error_msg = f"语音转录失败: {str(e)}"

            raise Exception(error_msg)

    async def translate_to_english(self, audio_path: str) -> Dict:
        """将音频翻译成英文"""
        try:
            logger.info("正在将音频翻译成英文...")

            with open(audio_path, "rb") as audio_file:
                translation = self.client.audio.translations.create(
                    model="whisper-1",
                    file=audio_file,
                    response_format="verbose_json"
                )

            segments = []
            if hasattr(translation, 'segments') and translation.segments:
                segments = [
                    {
                        "start": segment.start,
                        "end": segment.end,
                        "text": segment.text.strip()
                    }
                    for segment in translation.segments
                ]

            logger.info(f"翻译成功！原语言: {translation.language}")

            return {
                "success": True,
                "original_language": translation.language,
                "english_text": translation.text.strip(),
                "segments": segments
            }

        except Exception as e:
            logger.error(f"音频翻译失败: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }