#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
腾讯云语音识别服务
使用腾讯云ASR API进行语音转文字
"""

import os
import json
import time
import hmac
import hashlib
import base64
import asyncio
import logging
import tempfile
import subprocess
from typing import Dict, List, Optional
from datetime import datetime
import requests

logger = logging.getLogger(__name__)

class TencentASRService:
    """腾讯云语音识别服务"""
    
    def __init__(self):
        # 从环境变量获取配置
        self.secret_id = os.getenv('TENCENT_ASR_SECRET_ID') or os.getenv('TENCENT_SECRET_ID')
        self.secret_key = os.getenv('TENCENT_ASR_SECRET_KEY') or os.getenv('TENCENT_SECRET_KEY')
        self.region = os.getenv('TENCENT_ASR_REGION', 'ap-beijing')
        
        # API配置
        self.service = "asr"
        self.version = "2019-06-14"
        self.action = "SentenceRecognition"
        self.endpoint = "asr.tencentcloudapi.com"
        
        if not self.secret_id or not self.secret_key:
            raise ValueError("腾讯云ASR密钥未配置，请设置 TENCENT_ASR_SECRET_ID 和 TENCENT_ASR_SECRET_KEY")
        
        logger.info(f"腾讯云ASR服务初始化成功，区域: {self.region}")
    
    def _sign(self, key: bytes, msg: str) -> bytes:
        """HMAC-SHA256签名"""
        return hmac.new(key, msg.encode('utf-8'), hashlib.sha256).digest()
    
    def _get_signature_key(self, key: str, date_stamp: str, region_name: str, service_name: str) -> bytes:
        """获取签名密钥"""
        k_date = self._sign(('TC3' + key).encode('utf-8'), date_stamp)
        k_region = self._sign(k_date, region_name)
        k_service = self._sign(k_region, service_name)
        k_signing = self._sign(k_service, 'tc3_request')
        return k_signing
    
    def _create_authorization_header(self, payload: str, timestamp: int) -> Dict[str, str]:
        """创建授权头"""
        # 时间戳
        t = timestamp
        date = datetime.utcfromtimestamp(t).strftime('%Y-%m-%d')
        
        # 步骤 1：拼接规范请求串
        http_request_method = "POST"
        canonical_uri = "/"
        canonical_querystring = ""
        canonical_headers = f"content-type:application/json; charset=utf-8\nhost:{self.endpoint}\n"
        signed_headers = "content-type;host"
        hashed_request_payload = hashlib.sha256(payload.encode('utf-8')).hexdigest()
        canonical_request = f"{http_request_method}\n{canonical_uri}\n{canonical_querystring}\n{canonical_headers}\n{signed_headers}\n{hashed_request_payload}"
        
        # 步骤 2：拼接待签名字符串
        algorithm = "TC3-HMAC-SHA256"
        credential_scope = f"{date}/{self.region}/{self.service}/tc3_request"
        hashed_canonical_request = hashlib.sha256(canonical_request.encode('utf-8')).hexdigest()
        string_to_sign = f"{algorithm}\n{t}\n{credential_scope}\n{hashed_canonical_request}"
        
        # 步骤 3：计算签名
        signature_key = self._get_signature_key(self.secret_key, date, self.region, self.service)
        signature = hmac.new(signature_key, string_to_sign.encode('utf-8'), hashlib.sha256).hexdigest()
        
        # 步骤 4：拼接 Authorization
        authorization = f"{algorithm} Credential={self.secret_id}/{credential_scope}, SignedHeaders={signed_headers}, Signature={signature}"
        
        return {
            "Authorization": authorization,
            "Content-Type": "application/json; charset=utf-8",
            "Host": self.endpoint,
            "X-TC-Action": self.action,
            "X-TC-Timestamp": str(t),
            "X-TC-Version": self.version,
            "X-TC-Region": self.region
        }
    
    async def _extract_audio_from_video(self, video_path: str) -> str:
        """从视频中提取音频"""
        try:
            # 创建临时音频文件
            temp_audio = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
            temp_audio.close()
            
            # 使用FFmpeg提取音频
            cmd = [
                'ffmpeg', '-i', video_path,
                '-vn',  # 不处理视频
                '-acodec', 'pcm_s16le',  # 16位PCM编码
                '-ar', '16000',  # 16kHz采样率
                '-ac', '1',  # 单声道
                '-y',  # 覆盖输出文件
                temp_audio.name
            ]
            
            logger.info(f"提取音频: {' '.join(cmd)}")
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                logger.error(f"FFmpeg错误: {stderr.decode()}")
                raise Exception(f"音频提取失败: {stderr.decode()}")
            
            logger.info(f"音频提取成功: {temp_audio.name}")
            return temp_audio.name
            
        except Exception as e:
            logger.error(f"音频提取失败: {e}")
            raise
    
    async def _recognize_audio_chunk(self, audio_data: bytes, chunk_index: int = 0) -> Dict:
        """识别音频片段"""
        try:
            # 将音频数据编码为base64
            audio_base64 = base64.b64encode(audio_data).decode('utf-8')
            
            # 构建请求参数 - 使用腾讯云ASR标准格式
            timestamp = int(time.time())
            payload = {
                "ProjectId": 0,
                "SubServiceType": 2,  # 一句话识别
                "EngSerViceType": "16k_zh",  # 中文普通话
                "SourceType": 1,  # 语音数据来源，1：语音数据（post body）
                "VoiceFormat": "wav",  # 语音格式
                "UsrAudioKey": f"chunk_{chunk_index}_{timestamp}",
                "Data": audio_base64
            }
            
            payload_json = json.dumps(payload)
            
            # 创建授权头
            headers = self._create_authorization_header(payload_json, timestamp)
            
            # 发送请求
            url = f"https://{self.endpoint}"
            
            logger.info(f"发送ASR请求，音频大小: {len(audio_data)} 字节")
            
            response = requests.post(url, headers=headers, data=payload_json, timeout=30)
            
            if response.status_code != 200:
                logger.error(f"ASR请求失败: {response.status_code} - {response.text}")
                raise Exception(f"ASR请求失败: {response.status_code}")
            
            result = response.json()
            
            if 'Response' not in result:
                logger.error(f"ASR响应格式错误: {result}")
                raise Exception(f"ASR响应格式错误")
            
            response_data = result['Response']
            
            if 'Error' in response_data:
                error = response_data['Error']
                logger.error(f"ASR API错误: {error['Code']} - {error['Message']}")
                raise Exception(f"ASR API错误: {error['Code']} - {error['Message']}")
            
            return response_data
            
        except Exception as e:
            logger.error(f"音频识别失败: {e}")
            raise
    
    async def transcribe_audio(self, audio_path: str) -> List[Dict]:
        """转录音频文件"""
        try:
            logger.info(f"开始转录音频: {audio_path}")
            
            # 读取音频文件
            with open(audio_path, 'rb') as f:
                audio_data = f.read()
            
            logger.info(f"音频文件大小: {len(audio_data)} 字节")
            
            # 腾讯云一句话识别有大小限制（通常是5MB），如果文件太大需要分片
            max_chunk_size = 4 * 1024 * 1024  # 4MB
            
            segments = []
            
            if len(audio_data) <= max_chunk_size:
                # 文件不大，直接识别
                result = await self._recognize_audio_chunk(audio_data, 0)
                segments.extend(self._parse_recognition_result(result, 0))
            else:
                # 文件太大，需要分片处理
                logger.info("音频文件较大，进行分片处理")
                
                # 简单的分片策略：按时间分片
                # 这里需要使用FFmpeg进行音频分片
                chunk_duration = 30  # 每片30秒
                chunk_segments = await self._split_audio_by_time(audio_path, chunk_duration)
                
                for i, chunk_path in enumerate(chunk_segments):
                    try:
                        with open(chunk_path, 'rb') as f:
                            chunk_data = f.read()
                        
                        result = await self._recognize_audio_chunk(chunk_data, i)
                        chunk_segments_result = self._parse_recognition_result(result, i * chunk_duration)
                        segments.extend(chunk_segments_result)
                        
                        # 清理临时文件
                        os.unlink(chunk_path)
                        
                    except Exception as e:
                        logger.error(f"处理音频片段 {i} 失败: {e}")
                        continue
            
            logger.info(f"转录完成，共 {len(segments)} 个片段")
            return segments
            
        except Exception as e:
            logger.error(f"音频转录失败: {e}")
            raise
    
    def _parse_recognition_result(self, result: Dict, time_offset: float = 0) -> List[Dict]:
        """解析识别结果"""
        segments = []
        
        try:
            # 获取识别文本
            text = result.get('Result', '')
            if not text:
                return segments
            
            # 获取词级别时间戳
            word_list = result.get('WordList', [])
            
            if word_list:
                # 有详细的词级别时间戳
                current_segment = {
                    'start': time_offset,
                    'end': time_offset,
                    'text': ''
                }
                
                for word_info in word_list:
                    word = word_info.get('Word', '')
                    start_time = word_info.get('StartTime', 0) / 1000.0 + time_offset  # 毫秒转秒
                    end_time = word_info.get('EndTime', 0) / 1000.0 + time_offset
                    
                    if current_segment['text'] == '':
                        current_segment['start'] = start_time
                    
                    current_segment['text'] += word
                    current_segment['end'] = end_time
                
                if current_segment['text']:
                    segments.append(current_segment)
            else:
                # 没有详细时间戳，创建一个基本片段
                segments.append({
                    'start': time_offset,
                    'end': time_offset + 5.0,  # 假设5秒长度
                    'text': text
                })
            
        except Exception as e:
            logger.error(f"解析识别结果失败: {e}")
            # 创建一个基本片段
            text = result.get('Result', '')
            if text:
                segments.append({
                    'start': time_offset,
                    'end': time_offset + 5.0,
                    'text': text
                })
        
        return segments
    
    async def _split_audio_by_time(self, audio_path: str, chunk_duration: int) -> List[str]:
        """按时间分割音频"""
        chunk_files = []
        
        try:
            # 获取音频时长
            cmd = ['ffprobe', '-v', 'quiet', '-show_entries', 'format=duration', 
                   '-of', 'csv=p=0', audio_path]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                raise Exception(f"获取音频时长失败: {stderr.decode()}")
            
            duration = float(stdout.decode().strip())
            logger.info(f"音频总时长: {duration:.2f}秒")
            
            # 分割音频
            chunk_count = int(duration / chunk_duration) + 1
            
            for i in range(chunk_count):
                start_time = i * chunk_duration
                
                # 创建临时文件
                temp_chunk = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
                temp_chunk.close()
                
                # FFmpeg分割命令
                cmd = [
                    'ffmpeg', '-i', audio_path,
                    '-ss', str(start_time),
                    '-t', str(chunk_duration),
                    '-acodec', 'pcm_s16le',
                    '-ar', '16000',
                    '-ac', '1',
                    '-y',
                    temp_chunk.name
                ]
                
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                
                stdout, stderr = await process.communicate()
                
                if process.returncode == 0:
                    chunk_files.append(temp_chunk.name)
                    logger.info(f"创建音频片段 {i+1}/{chunk_count}: {temp_chunk.name}")
                else:
                    logger.error(f"创建音频片段 {i+1} 失败: {stderr.decode()}")
                    os.unlink(temp_chunk.name)
            
            return chunk_files
            
        except Exception as e:
            logger.error(f"音频分割失败: {e}")
            # 清理已创建的文件
            for chunk_file in chunk_files:
                if os.path.exists(chunk_file):
                    os.unlink(chunk_file)
            raise
    
    async def transcribe_video(self, video_path: str, language_hint: str = "zh-CN") -> Dict:
        """转录视频文件"""
        temp_audio = None
        
        try:
            logger.info(f"开始转录视频: {video_path}")
            
            # 从视频提取音频
            temp_audio = await self._extract_audio_from_video(video_path)
            
            # 转录音频
            segments = await self.transcribe_audio(temp_audio)
            
            # 合并所有文本
            full_text = ' '.join([seg['text'] for seg in segments])
            
            # 计算总时长
            duration = segments[-1]['end'] if segments else 0
            
            result = {
                'success': True,
                'text': full_text,
                'segments': segments,
                'language': language_hint,
                'duration': duration,
                'service': 'tencent_asr'
            }
            
            logger.info(f"视频转录完成: {len(segments)} 个片段, 总时长 {duration:.2f}秒")
            return result
            
        except Exception as e:
            logger.error(f"视频转录失败: {e}")
            return {
                'success': False,
                'error': str(e),
                'text': '',
                'segments': [],
                'language': language_hint,
                'duration': 0,
                'service': 'tencent_asr'
            }
        
        finally:
            # 清理临时音频文件
            if temp_audio and os.path.exists(temp_audio):
                os.unlink(temp_audio)
                logger.info("清理临时音频文件")