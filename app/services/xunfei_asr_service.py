"""
讯飞语音识别服务
支持实时语音识别和文件转写
"""

import os
import json
import time
import hmac
import base64
import hashlib
import urllib.parse
import websocket
import threading
from datetime import datetime
from typing import List, Dict, Optional, Tuple
import requests
import wave
import audioop
from app.utils.logger import logger


class XunfeiASRService:
    """讯飞语音识别服务类"""
    
    def __init__(self):
        """初始化讯飞ASR服务"""
        self.app_id = os.getenv('XUNFEI_APP_ID')
        self.api_key = os.getenv('XUNFEI_API_KEY') 
        self.api_secret = os.getenv('XUNFEI_API_SECRET')
        
        if not all([self.app_id, self.api_key, self.api_secret]):
            raise ValueError("请设置讯飞API密钥: XUNFEI_APP_ID, XUNFEI_API_KEY, XUNFEI_API_SECRET")
        
        # 讯飞语音识别API配置
        self.host = "iat-api.xfyun.cn"
        self.path = "/v2/iat"
        self.url = f"wss://{self.host}{self.path}"
        
        # 音频参数
        self.chunk_duration = 2  # 再缩短到2秒片段，降低单次发送大小，提升稳定性
        self.sample_rate = 16000
        self.channels = 1
        
        logger.info("讯飞ASR服务初始化成功")
    
    def _create_auth_url(self) -> str:
        """创建认证URL"""
        # 生成RFC1123格式的时间戳
        now = datetime.now()
        date = now.strftime('%a, %d %b %Y %H:%M:%S GMT')
        
        # 拼接字符串
        signature_origin = f"host: {self.host}\ndate: {date}\nGET {self.path} HTTP/1.1"
        
        # 进行hmac-sha256加密
        signature_sha = hmac.new(
            self.api_secret.encode('utf-8'),
            signature_origin.encode('utf-8'),
            digestmod=hashlib.sha256
        ).digest()
        
        signature_sha_base64 = base64.b64encode(signature_sha).decode(encoding='utf-8')
        
        authorization_origin = f'api_key="{self.api_key}", algorithm="hmac-sha256", headers="host date request-line", signature="{signature_sha_base64}"'
        
        authorization = base64.b64encode(authorization_origin.encode('utf-8')).decode(encoding='utf-8')
        
        # 将请求的鉴权参数组合为字典
        v = {
            "authorization": authorization,
            "date": date,
            "host": self.host
        }
        
        # 拼接鉴权参数，生成url
        url = self.url + '?' + urllib.parse.urlencode(v)
        return url
    
    def _split_audio_by_duration(self, audio_path: str) -> List[Tuple[str, float, float]]:
        """按时长分割音频文件"""
        try:
            import subprocess
            
            # 设置ffmpeg和ffprobe路径
            ffmpeg_path = r"C:\ffmpeg\bin\ffmpeg.exe"
            ffprobe_path = r"C:\ffmpeg\bin\ffprobe.exe"
            
            if not os.path.exists(ffmpeg_path):
                ffmpeg_path = "ffmpeg"
            if not os.path.exists(ffprobe_path):
                ffprobe_path = "ffprobe"
            
            # 获取音频总时长
            result = subprocess.run([
                ffprobe_path, '-v', 'quiet', '-show_entries', 'format=duration',
                '-of', 'csv=p=0', audio_path
            ], capture_output=True, text=True, check=True)
            
            total_duration = float(result.stdout.strip())
            logger.info(f"音频总时长: {total_duration:.2f}秒")
            
            chunks = []
            start_time = 0
            chunk_index = 0
            
            while start_time < total_duration:
                end_time = min(start_time + self.chunk_duration, total_duration)
                
                # 生成分片文件名
                chunk_filename = f"temp_chunk_{chunk_index}_{int(start_time)}_{int(end_time)}.wav"
                chunk_path = os.path.join(os.path.dirname(audio_path), chunk_filename)
                
                # 使用ffmpeg提取音频片段
                subprocess.run([
                    ffmpeg_path, '-i', audio_path, '-ss', str(start_time),
                    '-t', str(end_time - start_time), '-ar', str(self.sample_rate),
                    '-ac', str(self.channels), '-y', chunk_path
                ], check=True, capture_output=True)
                
                chunks.append((chunk_path, start_time, end_time))
                logger.info(f"创建音频片段 {chunk_index + 1}: {start_time:.2f}s - {end_time:.2f}s")
                
                start_time = end_time
                chunk_index += 1
            
            return chunks
            
        except Exception as e:
            logger.error(f"分割音频失败: {str(e)}")
            raise
    
    def _recognize_audio_chunk(self, audio_path: str, max_retries: int = 3) -> str:
        """识别单个音频片段，添加重试机制"""
        for attempt in range(max_retries):
            try:
                logger.info(f"尝试识别音频片段 (第{attempt + 1}次)")
                
                # 读取音频文件
                with wave.open(audio_path, 'rb') as wf:
                    audio_data = wf.readframes(wf.getnframes())
                
                # WebSocket连接参数
                result_text = ""
                error_msg = ""
                connection_closed = False
                recognition_complete = False
                
                def on_message(ws, message):
                    nonlocal result_text, error_msg, recognition_complete
                    try:
                        data = json.loads(message)
                        code = data['code']
                        
                        logger.info(f"收到消息: code={code}")
                        
                        if code != 0:
                            error_msg = f"识别错误: {data.get('message', '未知错误')}"
                            ws.close()
                            return
                        
                        results = data.get('data', {}).get('result', {}).get('ws', [])
                        for result in results:
                            for cw in result.get('cw', []):
                                result_text += cw.get('w', '')
                        
                        # 检查是否识别完成
                        if data.get('data', {}).get('status') == 2:
                            recognition_complete = True
                            logger.info("识别完成")
                            ws.close()
                                
                    except Exception as e:
                        error_msg = f"解析响应失败: {str(e)}"
                        ws.close()
                
                def on_error(ws, error):
                    nonlocal error_msg
                    error_msg = f"WebSocket错误: {str(error)}"
                    logger.error(f"WebSocket错误: {error}")
                
                def on_close(ws, close_status_code, close_msg):
                    nonlocal connection_closed
                    connection_closed = True
                    logger.info(f"WebSocket连接关闭: {close_status_code}, {close_msg}")
                
                def on_open(ws):
                    logger.info("WebSocket连接已建立")
                    def run():
                        try:
                            # 发送音频数据
                            frame_size = 960  # 每次发送的字节数（更小的帧降低丢包概率）
                            
                            # 发送开始帧
                            params = {
                                "common": {
                                    "app_id": self.app_id
                                },
                                "business": {
                                    "language": "zh_cn",
                                    "domain": "iat",
                                    "accent": "mandarin",
                                    "vinfo": 1,
                                    "vad_eos": 2000,  # 允许更长静音，避免被截断
                                    # 关闭动态修正，直接拿最终结果
                                    # "dwa": "wpgs",
                                    "ptt": 1,         # 开启标点符号
                                    "pcm": 1,         # 标点返回位置控制
                                    "nunum": 1        # 数字格式规则
                                },
                                "data": {
                                    "status": 0,
                                    "format": "audio/L16;rate=16000",
                                    "audio": "",
                                    "encoding": "raw"
                                }
                            }
                            logger.info("发送开始帧")
                            ws.send(json.dumps(params))
                            time.sleep(0.1)  # 等待服务器准备
                            
                            # 分帧发送音频数据
                            logger.info(f"开始发送音频数据，总长度: {len(audio_data)} 字节")
                            for i in range(0, len(audio_data), frame_size):
                                chunk = audio_data[i:i + frame_size]
                                params["data"]["status"] = 1
                                params["data"]["audio"] = base64.b64encode(chunk).decode()
                                ws.send(json.dumps(params))
                                time.sleep(0.04)  # 按官方建议40ms间隔
                            
                            # 发送结束帧
                            logger.info("发送结束帧")
                            params["data"]["status"] = 2
                            params["data"]["audio"] = ""
                            ws.send(json.dumps(params))
                            
                        except Exception as e:
                            nonlocal error_msg
                            error_msg = f"发送音频数据失败: {str(e)}"
                            logger.error(f"发送音频数据失败: {e}")
                            ws.close()
                    
                    threading.Thread(target=run).start()
                
                # 创建WebSocket连接
                auth_url = self._create_auth_url()
                ws = websocket.WebSocketApp(
                    auth_url,
                    on_message=on_message,
                    on_error=on_error,
                    on_close=on_close,
                    on_open=on_open
                )
                
                # 使用线程运行WebSocket，添加超时控制
                import threading
                import time
                
                def run_websocket():
                    ws.run_forever(ping_interval=10, ping_timeout=5)
                
                ws_thread = threading.Thread(target=run_websocket)
                ws_thread.daemon = True
                ws_thread.start()
                
                # 等待识别完成或超时
                timeout_seconds = 25  # 适当增加超时
                start_time = time.time()
                
                while ws_thread.is_alive() and not recognition_complete and not error_msg:
                    if time.time() - start_time > timeout_seconds:
                        logger.warning("识别超时")
                        ws.close()
                        break
                    time.sleep(0.1)
                
                # 等待线程结束
                ws_thread.join(timeout=2)
                
                if error_msg:
                    if "timeout" in error_msg.lower() and attempt < max_retries - 1:
                        logger.warning(f"第{attempt + 1}次尝试超时，准备重试...")
                        time.sleep(2)  # 重试前等待2秒
                        continue
                    raise Exception(error_msg)
                
                if result_text.strip():
                    logger.info(f"识别成功: {result_text.strip()}")
                    return result_text.strip()
                elif attempt < max_retries - 1:
                    logger.warning(f"第{attempt + 1}次尝试结果为空，准备重试...")
                    time.sleep(1 * (2 ** attempt))
                    continue
                else:
                    logger.warning("所有重试都失败，返回空结果")
                    return ""
                
            except Exception as e:
                if attempt < max_retries - 1:
                    logger.warning(f"第{attempt + 1}次尝试失败: {str(e)}，准备重试...")
                    time.sleep(1 * (2 ** attempt))
                    continue
                else:
                    logger.error(f"识别音频片段失败: {str(e)}")
                    return ""
        
        return ""
    
    def _clean_recognition_text(self, text: str) -> str:
        """
        清理识别文本中的重复词汇和错误
        
        Args:
            text: 原始识别文本
            
        Returns:
            清理后的文本
        """
        if not text or not text.strip():
            return ""
        
        import re
        
        # 移除多余的空格
        text = re.sub(r'\s+', ' ', text.strip())
        
        # 移除单独的字母或数字（通常是识别错误）
        text = re.sub(r'\b[a-zA-Z0-9]\b', '', text)
        
        # 移除重复的词汇（更智能的重复检测）
        words = text.split()
        cleaned_words = []
        
        i = 0
        while i < len(words):
            current_word = words[i]
            
            # 检查是否有连续重复的词汇
            repeat_count = 1
            j = i + 1
            while j < len(words) and words[j].lower() == current_word.lower():
                repeat_count += 1
                j += 1
            
            # 只保留一个重复的词汇
            if current_word.strip():  # 确保不是空字符串
                cleaned_words.append(current_word)
            
            # 跳过重复的词汇
            i = j
        
        # 进一步清理：移除部分重复的短语
        if len(cleaned_words) > 3:
            final_words = []
            for k in range(len(cleaned_words)):
                word = cleaned_words[k]
                
                # 检查是否是重复短语的一部分
                is_duplicate_phrase = False
                
                # 检查前面是否有相同的2-3词组合
                if k >= 2:
                    current_bigram = f"{cleaned_words[k-1]} {word}".lower()
                    for prev_idx in range(max(0, k-10), k-1):
                        if prev_idx + 1 < len(cleaned_words):
                            prev_bigram = f"{cleaned_words[prev_idx]} {cleaned_words[prev_idx+1]}".lower()
                            if current_bigram == prev_bigram:
                                is_duplicate_phrase = True
                                break
                
                if not is_duplicate_phrase:
                    final_words.append(word)
            
            cleaned_words = final_words
        
        # 重新组合文本
        cleaned_text = ' '.join(cleaned_words)
        
        # 移除多余的标点符号
        cleaned_text = re.sub(r'[,，]{2,}', ',', cleaned_text)
        cleaned_text = re.sub(r'[.。]{2,}', '.', cleaned_text)
        
        # 移除常见的识别错误模式
        cleaned_text = re.sub(r'\b(and\s+){2,}', 'and ', cleaned_text, flags=re.IGNORECASE)
        cleaned_text = re.sub(r'\b(the\s+){2,}', 'the ', cleaned_text, flags=re.IGNORECASE)
        cleaned_text = re.sub(r'\b(to\s+){2,}', 'to ', cleaned_text, flags=re.IGNORECASE)
        
        return cleaned_text.strip()
    
    def _split_long_sentence(self, text: str, start_time: float, end_time: float) -> List[Dict]:
        """智能分割长句子，提高时间戳精度"""
        if not text.strip():
            return []
        
        # 先清理文本
        cleaned_text = self._clean_recognition_text(text)
        if not cleaned_text:
            return []
        
        # 按标点符号和语义分割
        import re
        
        # 更智能的句子分割，考虑英文语法
        # 按句号、问号、感叹号分割主要句子
        major_sentences = re.split(r'[.!?]+', cleaned_text)
        
        results = []
        duration = end_time - start_time
        
        # 如果只有一个句子或句子很短，不分割
        if len(major_sentences) <= 1 or len(cleaned_text) < 50:
            return [{
                "text": cleaned_text,
                "start_time": round(start_time, 1),
                "end_time": round(end_time, 1)
            }]
        
        # 计算每个句子的时间分配
        valid_sentences = [s.strip() for s in major_sentences if s.strip()]
        if not valid_sentences:
            return [{
                "text": cleaned_text,
                "start_time": round(start_time, 1),
                "end_time": round(end_time, 1)
            }]
        
        total_chars = sum(len(s) for s in valid_sentences)
        current_time = start_time
        
        for i, sentence in enumerate(valid_sentences):
            if not sentence:
                continue
            
            # 按字符比例分配时间，但确保最小时长
            char_ratio = len(sentence) / total_chars if total_chars > 0 else 1.0 / len(valid_sentences)
            sentence_duration = max(duration * char_ratio, 1.0)  # 最小1秒
            
            # 最后一个句子使用剩余时间
            if i == len(valid_sentences) - 1:
                sentence_end_time = end_time
            else:
                sentence_end_time = min(current_time + sentence_duration, end_time)
            
            results.append({
                "text": sentence.strip(),
                "start_time": round(current_time, 1),
                "end_time": round(sentence_end_time, 1)
            })
            
            current_time = sentence_end_time
        
        return results
    
    def transcribe_audio(self, audio_path: str) -> List[Dict]:
        """转录音频文件为带时间戳的文本"""
        try:
            logger.info(f"开始转录音频: {audio_path}")
            
            # 分割音频
            chunks = self._split_audio_by_duration(audio_path)
            logger.info(f"音频分割为 {len(chunks)} 个片段")
            
            all_results = []
            
            consecutive_empty = 0
            for i, (chunk_path, start_time, end_time) in enumerate(chunks):
                try:
                    logger.info(f"识别片段 {i+1}/{len(chunks)}: {start_time:.1f}s - {end_time:.1f}s")
                    
                    # 识别音频片段
                    text = self._recognize_audio_chunk(chunk_path)
                    
                    if text:
                        consecutive_empty = 0
                        # 清理识别文本
                        cleaned_text = self._clean_recognition_text(text)
                        if cleaned_text:
                            # 智能分割长句子
                            sentences = self._split_long_sentence(cleaned_text, start_time, end_time)
                            all_results.extend(sentences)
                            logger.info(f"片段 {i+1} 识别结果: {cleaned_text}")
                        else:
                            logger.warning(f"片段 {i+1} 清理后文本为空")
                    else:
                        logger.warning(f"片段 {i+1} 识别结果为空")
                        consecutive_empty += 1
                        # 连续空结果过多，短暂退避，避免WS限流
                        if consecutive_empty >= 3:
                            logger.warning("连续3个片段为空，退避2秒后继续...")
                            time.sleep(2)
                            consecutive_empty = 0
                    
                    # 清理临时文件
                    if os.path.exists(chunk_path):
                        os.remove(chunk_path)
                    # 片段间增加轻微间隔，减小被限流概率
                    time.sleep(0.2)
                        
                except Exception as e:
                    logger.error(f"识别片段 {i+1} 失败: {str(e)}")
                    # 清理临时文件
                    if os.path.exists(chunk_path):
                        os.remove(chunk_path)
                    continue
            
            logger.info(f"转录完成，共生成 {len(all_results)} 个文本片段")
            return all_results
            
        except Exception as e:
            logger.error(f"转录音频失败: {str(e)}")
            raise
    
    def generate_srt_content(self, transcription_results: List[Dict]) -> str:
        """生成SRT字幕内容"""
        try:
            srt_content = ""
            
            for i, result in enumerate(transcription_results, 1):
                start_time = result['start_time']
                end_time = result['end_time']
                text = result['text']
                
                # 转换为SRT时间格式
                start_srt = self._seconds_to_srt_time(start_time)
                end_srt = self._seconds_to_srt_time(end_time)
                
                srt_content += f"{i}\n"
                srt_content += f"{start_srt} --> {end_srt}\n"
                srt_content += f"{text}\n\n"
            
            return srt_content
            
        except Exception as e:
            logger.error(f"生成SRT内容失败: {str(e)}")
            raise
    
    def _seconds_to_srt_time(self, seconds: float) -> str:
        """将秒数转换为SRT时间格式"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millisecs = int((seconds % 1) * 1000)
        
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millisecs:03d}"


# 创建全局服务实例
try:
    xunfei_asr_service = XunfeiASRService()
    logger.info("讯飞ASR服务全局实例创建成功")
except Exception as e:
    logger.error(f"讯飞ASR服务初始化失败: {str(e)}")
    xunfei_asr_service = None