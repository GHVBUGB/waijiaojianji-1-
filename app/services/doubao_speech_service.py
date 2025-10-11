"""
豆包(Doubao)语音识别服务集成
火山引擎旗下的语音识别服务
"""

import asyncio
import json
import logging
import os
import tempfile
import time
import base64
import hashlib
import hmac
from typing import Dict, List
import subprocess
import websockets
from datetime import datetime
from urllib.parse import urlencode

from app.config.settings import settings

logger = logging.getLogger(__name__)

class DoubaoSpeechService:
    """豆包语音识别服务"""
    
    def __init__(self):
        self.access_key = getattr(settings, 'VOLCENGINE_ACCESS_KEY', None)
        self.secret_key = getattr(settings, 'VOLCENGINE_SECRET_KEY', None)
        
        # 豆包语音识别服务配置
        self.service_name = "doubao-streaming-asr"
        self.ws_url = "wss://openspeech.bytedance.com/api/v1/asr"
        self.region = "cn-north-1"
        
        if not self.access_key or not self.secret_key:
            logger.warning("豆包语音识别服务未配置访问密钥")
    
    def _generate_signature(self, params: dict) -> str:
        """生成火山引擎API签名"""
        try:
            # 按字典序排序参数
            sorted_params = sorted(params.items())
            query_string = urlencode(sorted_params)
            
            # 构建签名字符串
            string_to_sign = f"GET\n/api/v1/asr\n{query_string}"
            
            # 计算HMAC-SHA256签名
            signature = hmac.new(
                self.secret_key.encode('utf-8'),
                string_to_sign.encode('utf-8'),
                hashlib.sha256
            ).digest()
            
            return base64.b64encode(signature).decode('utf-8')
        except Exception as e:
            logger.error(f"签名生成失败: {e}")
            raise
    
    async def extract_audio_from_video(self, video_path: str) -> str:
        """从视频中提取音频"""
        try:
            logger.info(f"开始从视频提取音频: {video_path}")

            # 创建临时音频文件
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_audio:
                temp_audio_path = temp_audio.name

            # 使用FFmpeg提取音频 - 豆包推荐格式
            cmd = [
                'ffmpeg', '-i', video_path,
                '-vn',  # 不要视频流
                '-acodec', 'pcm_s16le',  # PCM 16位编码
                '-ar', '16000',  # 采样率 16kHz
                '-ac', '1',  # 单声道
                '-y',  # 覆盖输出文件
                temp_audio_path
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300
            )

            if result.returncode != 0:
                logger.error(f"FFmpeg错误: {result.stderr}")
                raise Exception(f"音频提取失败: {result.stderr}")

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

    async def transcribe_video(self, video_path: str, language_hint: str = "zh-CN") -> Dict:
        """
        转录视频中的语音
        
        Args:
            video_path: 视频文件路径
            language_hint: 语言提示（zh-CN, en-US等）
            
        Returns:
            Dict: 转录结果
        """
        temp_audio_path = None
        start_time = time.time()

        try:
            logger.info(f"开始使用豆包服务转录视频: {video_path}")

            # 1. 提取音频
            temp_audio_path = await self.extract_audio_from_video(video_path)

            # 2. 转录音频
            result = await self._transcribe_audio_websocket(temp_audio_path, language_hint)

            processing_time = time.time() - start_time
            logger.info(f"豆包转录完成，耗时: {processing_time:.2f}秒")

            result["processing_time"] = processing_time
            result["service"] = "doubao"
            return result

        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"豆包视频转录失败: {str(e)}")
            return {
                "success": False,
                "text": "",
                "language": language_hint,
                "duration": 0,
                "segments": [],
                "processing_time": processing_time,
                "service": "doubao",
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

    async def _transcribe_audio_websocket(self, audio_path: str, language: str = "zh-CN") -> Dict:
        """使用豆包WebSocket API进行音频转录"""
        try:
            logger.info("正在调用豆包语音识别 WebSocket API...")
            
            # 准备认证参数
            timestamp = str(int(time.time()))
            params = {
                'appid': self.service_name,
                'timestamp': timestamp,
                'signature_method': 'HMAC-SHA256',
                'signature_version': '1.0',
                'access_key': self.access_key
            }
            
            # 生成签名
            signature = self._generate_signature(params)
            params['signature'] = signature
            
            # 构建WebSocket URL
            query_string = urlencode(params)
            ws_url = f"{self.ws_url}?{query_string}"
            
            # 读取音频文件
            with open(audio_path, 'rb') as f:
                audio_data = f.read()
            
            logger.info(f"音频数据大小: {len(audio_data)} 字节")
            
            # WebSocket连接和转录
            segments = []
            full_text = ""
            
            try:
                async with websockets.connect(
                    ws_url, 
                    ping_interval=30,
                    ping_timeout=10,
                    close_timeout=10
                ) as websocket:
                    
                    # 发送开始信号
                    start_msg = {
                        "type": "start",
                        "data": {
                            "language": language,
                            "format": "wav",
                            "rate": 16000,
                            "bits": 16,
                            "channel": 1,
                            "codec": "pcm",
                            "vad_enable": True,  # 启用语音活动检测
                            "show_punctuation": True,  # 显示标点符号
                            "show_sentence_end": True  # 显示句子结束
                        }
                    }
                    
                    await websocket.send(json.dumps(start_msg))
                    logger.info("已发送开始信号")
                    
                    # 分块发送音频数据
                    chunk_size = 8000  # 8KB per chunk
                    total_chunks = (len(audio_data) + chunk_size - 1) // chunk_size
                    
                    for i in range(0, len(audio_data), chunk_size):
                        chunk = audio_data[i:i + chunk_size]
                        chunk_index = i // chunk_size + 1
                        
                        audio_msg = {
                            "type": "audio",
                            "data": base64.b64encode(chunk).decode('utf-8')
                        }
                        
                        await websocket.send(json.dumps(audio_msg))
                        
                        if chunk_index % 10 == 0:
                            logger.info(f"已发送 {chunk_index}/{total_chunks} 音频块")
                        
                        # 接收部分结果
                        try:
                            response = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                            await self._process_response(response, segments, full_text)
                        except asyncio.TimeoutError:
                            continue
                    
                    # 发送结束信号
                    end_msg = {"type": "end"}
                    await websocket.send(json.dumps(end_msg))
                    logger.info("已发送结束信号")
                    
                    # 接收最终结果
                    final_timeout = 10  # 10秒超时
                    end_time = time.time() + final_timeout
                    
                    while time.time() < end_time:
                        try:
                            response = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                            is_final = await self._process_response(response, segments, full_text)
                            if is_final:
                                break
                        except asyncio.TimeoutError:
                            continue
                        except websockets.exceptions.ConnectionClosed:
                            logger.info("WebSocket连接已关闭")
                            break
                    
            except websockets.exceptions.WebSocketException as e:
                logger.error(f"WebSocket连接错误: {e}")
                raise Exception(f"豆包语音识别连接失败: {e}")
            
            # 处理转录结果
            full_text = full_text.strip()
            duration = segments[-1]["end"] if segments else 0
            
            logger.info(f"豆包转录成功！语言: {language}, 时长: {duration:.2f}秒")
            logger.info(f"转录文本预览: {full_text[:100]}...")
            logger.info(f"共识别到 {len(segments)} 个语音段")

            return {
                "success": True,
                "text": full_text,
                "language": language,
                "duration": duration,
                "segments": segments,
                "service": "doubao"
            }

        except Exception as e:
            logger.error(f"豆包语音识别API调用失败: {str(e)}")
            
            # 根据错误类型提供更具体的错误信息
            if "authentication" in str(e).lower() or "unauthorized" in str(e).lower():
                error_msg = "豆包API认证失败，请检查Access Key和Secret Key"
            elif "quota" in str(e).lower() or "limit" in str(e).lower():
                error_msg = "豆包API配额不足或超出并发限制，请检查账户余额"
            elif "websocket" in str(e).lower():
                error_msg = "豆包WebSocket连接失败，请检查网络连接"
            else:
                error_msg = f"豆包语音转录失败: {str(e)}"
            
            raise Exception(error_msg)

    async def _process_response(self, response: str, segments: List[Dict], full_text: str) -> bool:
        """处理WebSocket响应"""
        try:
            result_data = json.loads(response)
            
            if result_data.get("type") == "result":
                result_info = result_data.get("data", {})
                
                if result_info.get("result"):
                    text = result_info["result"]
                    start_time = result_info.get("start_time", 0) / 1000.0
                    end_time = result_info.get("end_time", 0) / 1000.0
                    is_final = result_info.get("is_final", False)
                    
                    # 添加到segments
                    segment = {
                        "start": start_time,
                        "end": end_time,
                        "text": text.strip(),
                        "is_final": is_final
                    }
                    
                    segments.append(segment)
                    
                    if is_final:
                        full_text += text + " "
                        return True
                        
            elif result_data.get("type") == "error":
                error_info = result_data.get("data", {})
                error_msg = error_info.get("message", "未知错误")
                logger.error(f"豆包API返回错误: {error_msg}")
                raise Exception(f"豆包API错误: {error_msg}")
                
        except json.JSONDecodeError as e:
            logger.warning(f"解析WebSocket响应失败: {e}")
        
        return False

    async def get_supported_languages(self) -> List[Dict]:
        """获取豆包支持的语言列表"""
        return [
            {"code": "zh-CN", "name": "中文（普通话）", "recommended": True},
            {"code": "en-US", "name": "英语（美式）", "recommended": True},
            {"code": "en-GB", "name": "英语（英式）"},
            {"code": "ja-JP", "name": "日语"},
            {"code": "ko-KR", "name": "韩语"},
            {"code": "fr-FR", "name": "法语"},
            {"code": "de-DE", "name": "德语"},
            {"code": "es-ES", "name": "西班牙语"},
            {"code": "ru-RU", "name": "俄语"},
            {"code": "it-IT", "name": "意大利语"},
            {"code": "pt-BR", "name": "葡萄牙语（巴西）"},
            {"code": "ar-SA", "name": "阿拉伯语"}
        ]

    async def get_service_info(self) -> Dict:
        """获取服务信息"""
        return {
            "service_name": "豆包(Doubao)语音识别",
            "provider": "火山引擎",
            "pricing": "4.5元/小时",
            "concurrent_limit": "10 QPS",
            "supported_formats": ["WAV", "MP3", "AAC", "FLAC"],
            "sample_rate": "16kHz",
            "channel": "单声道",
            "max_duration": "60分钟",
            "features": [
                "实时流式识别",
                "语音活动检测",
                "标点符号识别",
                "多语言支持",
                "高准确率识别"
            ]
        }
