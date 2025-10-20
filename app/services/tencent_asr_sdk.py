"""
腾讯云ASR服务 - 使用官方SDK实现
"""
import os
import json
import base64
import logging
import subprocess
import time
from typing import Dict, List, Optional, Tuple
from tencentcloud.common import credential
from tencentcloud.common.profile.client_profile import ClientProfile
from tencentcloud.common.profile.http_profile import HttpProfile
from tencentcloud.asr.v20190614 import asr_client, models
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException

logger = logging.getLogger(__name__)

class TencentASRSDKService:
    """腾讯云ASR服务 - 使用官方SDK"""
    
    def __init__(self):
        """初始化腾讯云ASR客户端"""
        self.secret_id = os.getenv('TENCENT_ASR_SECRET_ID')
        self.secret_key = os.getenv('TENCENT_ASR_SECRET_KEY')
        self.region = os.getenv('TENCENT_ASR_REGION', 'ap-beijing')
        
        if not self.secret_id or not self.secret_key:
            raise ValueError("腾讯云ASR密钥未配置")
        
        # 创建认证对象
        cred = credential.Credential(self.secret_id, self.secret_key)
        
        # 实例化一个http选项，可选的，没有特殊需求可以跳过
        httpProfile = HttpProfile()
        httpProfile.endpoint = "asr.tencentcloudapi.com"
        
        # 实例化一个client选项，可选的，没有特殊需求可以跳过
        clientProfile = ClientProfile()
        clientProfile.httpProfile = httpProfile
        
        # 实例化要请求产品的client对象
        self.client = asr_client.AsrClient(cred, self.region, clientProfile)
        
        logger.info(f"腾讯云ASR SDK服务初始化成功，区域: {self.region}")
    
    def extract_audio(self, video_path: str, audio_path: str) -> bool:
        """从视频中提取音频"""
        try:
            ffmpeg_path = os.getenv('FFMPEG_PATH', 'ffmpeg')
            
            # 使用FFmpeg提取音频为WAV格式
            cmd = [
                ffmpeg_path,
                '-i', video_path,
                '-vn',  # 不处理视频
                '-acodec', 'pcm_s16le',  # 16位PCM编码
                '-ar', '16000',  # 采样率16kHz
                '-ac', '1',  # 单声道
                '-y',  # 覆盖输出文件
                audio_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                logger.error(f"音频提取失败: {result.stderr}")
                return False
            
            logger.info(f"音频提取成功: {audio_path}")
            return True
            
        except Exception as e:
            logger.error(f"音频提取异常: {str(e)}")
            return False
    
    def recognize_audio_chunk(self, audio_data: bytes, language_hint: str = "zh-CN") -> Dict:
        """识别音频片段 - 使用官方文档推荐的参数"""
        try:
            # 将音频数据转换为base64
            audio_base64 = base64.b64encode(audio_data).decode('utf-8')
            
            # 实例化一个请求对象
            req = models.SentenceRecognitionRequest()
            
            # 根据官方文档设置完整参数
            req.ProjectId = 0  # 项目ID，默认为0
            req.SubServiceType = 2  # 子服务类型，2表示一句话识别
            
            # 根据语言提示设置引擎类型
            if language_hint.startswith('en'):
                req.EngSerViceType = "16k_en"  # 英文
            elif language_hint.startswith('zh'):
                req.EngSerViceType = "16k_zh"  # 中文普通话
            else:
                req.EngSerViceType = "16k_zh"  # 默认中文
            
            req.SourceType = 1  # 语音数据来源，1：语音数据（post body）
            req.VoiceFormat = "wav"  # 语音格式
            req.UsrAudioKey = f"chunk_{int(time.time() * 1000)}"  # 用户音频数据唯一标识
            req.Data = audio_base64  # 语音数据base64编码
            
            # 可选参数 - 根据官方文档添加
            req.FilterDirty = 1  # 是否过滤脏词
            req.FilterModal = 1  # 是否过滤语气词
            req.ConvertNumMode = 1  # 是否进行阿拉伯数字智能转换
            
            logger.info(f"发送识别请求，引擎类型: {req.EngSerViceType}, 数据大小: {len(audio_data)} bytes")
            
            # 发起请求
            resp = self.client.SentenceRecognition(req)
            
            # 解析响应 - 根据官方文档的返回格式
            result_text = ""
            confidence = 1.0
            
            if hasattr(resp, 'Result'):
                result_text = resp.Result
            
            # 检查是否有详细的识别结果
            if hasattr(resp, 'AudioDuration'):
                logger.info(f"音频时长: {resp.AudioDuration}ms")
            
            if hasattr(resp, 'WordList') and resp.WordList:
                # 如果有词级别的结果，提取置信度
                total_confidence = 0
                word_count = 0
                for word_info in resp.WordList:
                    if hasattr(word_info, 'Confidence'):
                        total_confidence += word_info.Confidence
                        word_count += 1
                
                if word_count > 0:
                    confidence = total_confidence / word_count / 100.0  # 转换为0-1范围
            
            result = {
                'text': result_text,
                'confidence': confidence,
                'language': language_hint,
                'request_id': resp.RequestId if hasattr(resp, 'RequestId') else None
            }
            
            logger.info(f"识别结果: {result['text']} (置信度: {confidence:.2f})")
            return result
            
        except Exception as e:
            logger.error(f"音频识别失败: {str(e)}")
            return {
                'text': '',
                'confidence': 0.0,
                'language': language_hint,
                'error': str(e)
            }
    
    def split_audio(self, audio_path: str, chunk_duration: int = 60) -> List[str]:
        """将音频文件分割成小片段"""
        try:
            ffmpeg_path = os.getenv('FFMPEG_PATH', 'ffmpeg')
            
            # 获取音频时长
            probe_cmd = [
                ffmpeg_path,
                '-i', audio_path,
                '-f', 'null', '-'
            ]
            
            result = subprocess.run(probe_cmd, capture_output=True, text=True)
            
            # 从stderr中提取时长信息
            duration_line = None
            for line in result.stderr.split('\n'):
                if 'Duration:' in line:
                    duration_line = line
                    break
            
            if not duration_line:
                logger.error("无法获取音频时长")
                return []
            
            # 解析时长
            duration_str = duration_line.split('Duration:')[1].split(',')[0].strip()
            time_parts = duration_str.split(':')
            total_seconds = int(float(time_parts[0]) * 3600 + float(time_parts[1]) * 60 + float(time_parts[2]))
            
            logger.info(f"音频总时长: {total_seconds}秒")
            
            # 分割音频
            chunk_files = []
            base_name = os.path.splitext(audio_path)[0]
            
            for i in range(0, total_seconds, chunk_duration):
                chunk_file = f"{base_name}_chunk_{i//chunk_duration}.wav"
                
                cmd = [
                    ffmpeg_path,
                    '-i', audio_path,
                    '-ss', str(i),
                    '-t', str(chunk_duration),
                    '-acodec', 'pcm_s16le',
                    '-ar', '16000',
                    '-ac', '1',
                    '-y',
                    chunk_file
                ]
                
                result = subprocess.run(cmd, capture_output=True, text=True)
                
                if result.returncode == 0:
                    chunk_files.append(chunk_file)
                    logger.info(f"创建音频片段: {chunk_file}")
                else:
                    logger.error(f"创建音频片段失败: {result.stderr}")
            
            return chunk_files
            
        except Exception as e:
            logger.error(f"音频分割失败: {str(e)}")
            return []
    
    def transcribe_audio(self, audio_path: str, language_hint: str = "zh-CN") -> List[Dict]:
        """转录音频文件 - 返回标准格式的片段列表"""
        try:
            logger.info(f"开始转录音频: {audio_path}")
            
            # 检查音频文件是否存在
            if not os.path.exists(audio_path):
                logger.error(f"音频文件不存在: {audio_path}")
                return []
            
            # 获取音频文件大小
            file_size = os.path.getsize(audio_path)
            logger.info(f"音频文件大小: {file_size} 字节")
            
            # 腾讯云一句话识别有大小限制（5MB），如果文件太大需要分片
            max_chunk_size = 4 * 1024 * 1024  # 4MB
            
            segments = []
            
            if file_size <= max_chunk_size:
                # 文件不大，直接识别
                with open(audio_path, 'rb') as f:
                    audio_data = f.read()
                
                result = self.recognize_audio_chunk(audio_data, language_hint)
                if result.get('success') and result.get('text'):
                    # 转换为标准格式
                    segments.append({
                        'start_time': 0.0,
                        'end_time': result.get('duration', 10.0),  # 默认10秒
                        'text': result['text']
                    })
            else:
                # 文件太大，需要分片处理
                logger.info("音频文件较大，进行分片处理")
                
                # 按时间分片
                chunk_duration = 30  # 每片30秒
                chunk_files = self.split_audio(audio_path, chunk_duration)
                
                for i, chunk_path in enumerate(chunk_files):
                    try:
                        with open(chunk_path, 'rb') as f:
                            chunk_data = f.read()
                        
                        result = self.recognize_audio_chunk(chunk_data, language_hint)
                        
                        if result.get('success') and result.get('text'):
                            start_time = i * chunk_duration
                            end_time = start_time + chunk_duration
                            
                            segments.append({
                                'start_time': start_time,
                                'end_time': end_time,
                                'text': result['text']
                            })
                        
                        # 清理临时文件
                        if os.path.exists(chunk_path):
                            os.remove(chunk_path)
                            
                    except Exception as e:
                        logger.error(f"处理音频片段 {i+1} 失败: {str(e)}")
                        continue
            
            logger.info(f"音频转录完成，获得 {len(segments)} 个片段")
            return segments
            
        except Exception as e:
            logger.error(f"音频转录失败: {str(e)}")
            return []

    def generate_srt_content(self, segments: List[Dict]) -> str:
        """生成SRT字幕内容"""
        if not segments:
            return ""
        
        srt_content = []
        
        for i, segment in enumerate(segments):
            start_time = segment.get('start_time', 0)
            end_time = segment.get('end_time', 0)
            text = segment.get('text', '').strip()
            
            if not text:
                continue
            
            # 转换时间格式为SRT格式 (HH:MM:SS,mmm)
            start_srt = self._seconds_to_srt_time(start_time)
            end_srt = self._seconds_to_srt_time(end_time)
            
            srt_content.append(f"{i + 1}")
            srt_content.append(f"{start_srt} --> {end_srt}")
            srt_content.append(text)
            srt_content.append("")  # 空行分隔
        
        return "\n".join(srt_content)
    
    def _seconds_to_srt_time(self, seconds: float) -> str:
        """将秒数转换为SRT时间格式"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millisecs = int((seconds % 1) * 1000)
        
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millisecs:03d}"
    
    def transcribe_video(self, video_path: str, language_hint: str = "zh-CN") -> Dict:
        """转录视频文件 - 高精度时间戳对齐"""
        try:
            logger.info(f"开始转录视频: {video_path}")
            
            # 提取音频
            audio_path = video_path.replace('.mp4', '_audio.wav')
            if not self.extract_audio(video_path, audio_path):
                return {
                    'success': False,
                    'text': '',
                    'language': language_hint,
                    'duration': 0,
                    'segments': [],
                    'error': '音频提取失败'
                }
            
            # 获取实际音频时长（精确到毫秒）
            try:
                ffmpeg_path = os.getenv('FFMPEG_PATH', 'ffmpeg')
                cmd = [ffmpeg_path, '-i', audio_path, '-f', 'null', '-']
                result = subprocess.run(cmd, capture_output=True, text=True)
                
                # 从FFmpeg输出中解析实际时长（精确到毫秒）
                actual_duration = 0.0
                for line in result.stderr.split('\n'):
                    if 'Duration:' in line:
                        duration_str = line.split('Duration:')[1].split(',')[0].strip()
                        time_parts = duration_str.split(':')
                        # 精确计算到毫秒
                        hours = float(time_parts[0])
                        minutes = float(time_parts[1])
                        seconds = float(time_parts[2])
                        actual_duration = hours * 3600 + minutes * 60 + seconds
                        break
                
                logger.info(f"音频实际时长: {actual_duration:.3f}秒")
            except Exception as e:
                logger.warning(f"无法获取音频时长: {e}")
                actual_duration = 120.0  # 默认值
            
            # 使用更短的片段以提高时间戳精度 - 改为15秒
            chunk_duration = 15  # 15秒片段，提供更精确的时间戳
            chunk_files = self.split_audio(audio_path, chunk_duration=chunk_duration)
            if not chunk_files:
                return {
                    'success': False,
                    'text': '',
                    'language': language_hint,
                    'duration': 0,
                    'segments': [],
                    'error': '音频分割失败'
                }
            
            # 识别每个音频片段
            all_text = []
            segments = []
            
            for i, chunk_file in enumerate(chunk_files):
                try:
                    # 读取音频数据
                    with open(chunk_file, 'rb') as f:
                        audio_data = f.read()
                    
                    # 识别音频
                    result = self.recognize_audio_chunk(audio_data, language_hint)
                    
                    if result['text']:
                        # 计算精确的时间戳（精确到0.1秒）
                        start_time = round(i * chunk_duration, 1)
                        end_time = round(min((i + 1) * chunk_duration, actual_duration), 1)
                        
                        # 进一步细分长句子的时间戳
                        text = result['text'].strip()
                        words = text.split()
                        
                        # 如果句子较长，尝试按标点符号或长度分割
                        if len(words) > 10:  # 超过10个词的长句子
                            sub_segments = self._split_long_sentence(text, start_time, end_time)
                            segments.extend(sub_segments)
                            all_text.append(text)
                        else:
                            all_text.append(text)
                            segments.append({
                                'start': start_time,
                                'end': end_time,
                                'text': text
                            })
                        
                        logger.info(f"片段 {i+1}: {start_time:.1f}s-{end_time:.1f}s -> {text[:50]}...")
                    
                    # 清理临时文件
                    if os.path.exists(chunk_file):
                        os.remove(chunk_file)
                        
                except Exception as e:
                    logger.error(f"处理音频片段 {chunk_file} 失败: {str(e)}")
                    continue
            
            # 清理临时音频文件
            if os.path.exists(audio_path):
                os.remove(audio_path)
            
            # 合并结果
            full_text = ' '.join(all_text)
            
            result = {
                'success': True,
                'text': full_text,
                'language': language_hint,
                'duration': actual_duration,
                'segments': segments
            }
            
            logger.info(f"视频转录完成，识别文本长度: {len(full_text)}, 片段数: {len(segments)}")
            return result
            
        except Exception as e:
            logger.error(f"视频转录失败: {str(e)}")
            return {
                'success': False,
                'text': '',
                'language': language_hint,
                'duration': 0,
                'segments': [],
                'error': str(e)
            }
    
    def _split_long_sentence(self, text: str, start_time: float, end_time: float) -> list:
        """将长句子按标点符号分割为更精确的时间段"""
        import re
        
        # 按标点符号分割
        sentences = re.split(r'[.!?。！？,，;；]', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        if len(sentences) <= 1:
            return [{
                'start': start_time,
                'end': end_time,
                'text': text
            }]
        
        # 计算每个子句的时间分配
        total_chars = sum(len(s) for s in sentences)
        duration = end_time - start_time
        
        segments = []
        current_time = start_time
        
        for i, sentence in enumerate(sentences):
            # 按字符数比例分配时间
            sentence_duration = (len(sentence) / total_chars) * duration
            sentence_end = round(current_time + sentence_duration, 1)
            
            # 确保最后一个片段的结束时间正确
            if i == len(sentences) - 1:
                sentence_end = end_time
            
            segments.append({
                'start': round(current_time, 1),
                'end': sentence_end,
                'text': sentence.strip()
            })
            
            current_time = sentence_end
        
        return segments