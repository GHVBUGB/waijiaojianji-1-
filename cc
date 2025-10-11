# 外教视频处理系统开发文档

## 项目概述

基于 FastAPI 的外教自我介绍视频处理系统，集成 **OpenAI Whisper API**（语音转文字）和 **Unscreen API**（视频人像抠像）功能。

### 核心功能
- 🎥 视频人像背景移除（透明背景）
- 🎤 多语言语音转文字识别
- 📝 自动生成字幕和时间戳
- 🔄 异步处理，支持批量操作
- 📊 处理进度跟踪

---

## 项目结构

```
teacher_video_processor/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI 应用入口
│   ├── config/
│   │   ├── __init__.py
│   │   └── settings.py         # 配置文件
│   ├── models/
│   │   ├── __init__.py
│   │   ├── video.py           # 视频相关模型
│   │   └── response.py        # API响应模型
│   ├── services/
│   │   ├── __init__.py
│   │   ├── video_processor.py  # 主处理服务
│   │   ├── background_removal.py  # 背景移除服务
│   │   └── speech_to_text.py   # 语音转文字服务
│   ├── api/
│   │   ├── __init__.py
│   │   ├── routes/
│   │   │   ├── __init__.py
│   │   │   ├── video.py       # 视频处理路由
│   │   │   └── health.py      # 健康检查
│   │   └── dependencies.py    # 依赖注入
│   └── utils/
│       ├── __init__.py
│       ├── file_handler.py    # 文件处理工具
│       └── logger.py          # 日志配置
├── uploads/                   # 上传目录
├── outputs/                   # 输出目录
├── temp/                      # 临时文件目录
├── logs/                      # 日志目录
├── requirements.txt           # Python依赖
├── .env                       # 环境变量
├── .env.example              # 环境变量示例
├── docker-compose.yml        # Docker配置
├── Dockerfile               # Docker镜像
└── README.md               # 项目说明
```

---

## 安装和配置

### 1. 环境要求

```bash
Python >= 3.9
FFmpeg >= 4.0
```

### 2. 克隆项目

```bash
git clone <repository-url>
cd teacher_video_processor
```

### 3. 创建虚拟环境

```bash
python -m venv venv

# Linux/macOS
source venv/bin/activate

# Windows
venv\Scripts\activate
```

### 4. 安装依赖

```bash
# Python依赖
pip install -r requirements.txt

# 系统依赖
# Ubuntu/Debian
sudo apt update && sudo apt install ffmpeg

# macOS
brew install ffmpeg

# Windows
# 下载 FFmpeg 并添加到 PATH
```

### 5. 环境变量配置

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑 .env 文件
nano .env
```

**.env 文件内容：**
```bash
# ===================
# API 配置
# ===================
# OpenAI API Key (语音转文字)
OPENAI_API_KEY=sk-your-openai-api-key-here

# Unscreen API Key (视频抠像)
UNSCREEN_API_KEY=your-unscreen-api-key-here

# ===================
# 应用配置
# ===================
# 环境
ENVIRONMENT=development

# 服务器配置
HOST=0.0.0.0
PORT=8000

# 日志级别
LOG_LEVEL=INFO

# ===================
# 文件存储配置
# ===================
UPLOAD_DIR=./uploads
OUTPUT_DIR=./outputs
TEMP_DIR=./temp

# 文件限制
MAX_VIDEO_SIZE=104857600  # 100MB
MAX_CONCURRENT_JOBS=3

# ===================
# 数据库配置 (可选)
# ===================
# DATABASE_URL=sqlite:///./teacher_videos.db
```

### 6. 获取 API Keys

#### OpenAI API Key
1. 访问 [OpenAI Platform](https://platform.openai.com/api-keys)
2. 登录并创建新的 API Key
3. 充值账户余额（最低 $5）

#### Unscreen API Key
1. 访问 [Unscreen API](https://www.unscreen.com/api)
2. 注册账号并进入 Dashboard
3. 获取 API Key
4. 购买 Credits（最低 $10）

---

## 核心代码文件

### 1. 配置文件 (`app/config/settings.py`)

```python
from pydantic import BaseSettings, validator
from typing import List, Optional
import os

class Settings(BaseSettings):
    # API 配置
    OPENAI_API_KEY: Optional[str] = None
    UNSCREEN_API_KEY: Optional[str] = None
  
    # 应用配置
    ENVIRONMENT: str = "development"
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    LOG_LEVEL: str = "INFO"
  
    # 文件配置
    UPLOAD_DIR: str = "./uploads"
    OUTPUT_DIR: str = "./outputs"
    TEMP_DIR: str = "./temp"
  
    # 文件限制
    MAX_VIDEO_SIZE: int = 100 * 1024 * 1024  # 100MB
    MAX_CONCURRENT_JOBS: int = 3
    SUPPORTED_VIDEO_FORMATS: List[str] = [".mp4", ".mov", ".avi", ".mkv"]
  
    # 处理配置
    AUDIO_SAMPLE_RATE: int = 16000
    VIDEO_OUTPUT_FORMAT: str = "mp4"
  
    @validator("OPENAI_API_KEY")
    def validate_openai_key(cls, v):
        if not v:
            raise ValueError("OPENAI_API_KEY is required")
        return v
  
    @validator("UNSCREEN_API_KEY")
    def validate_unscreen_key(cls, v):
        if not v:
            raise ValueError("UNSCREEN_API_KEY is required")
        return v
  
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # 创建必要的目录
        for directory in [self.UPLOAD_DIR, self.OUTPUT_DIR, self.TEMP_DIR]:
            os.makedirs(directory, exist_ok=True)
  
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
```

### 2. 响应模型 (`app/models/response.py`)

```python
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum

class ProcessingStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class TranscriptionSegment(BaseModel):
    start: float = Field(..., description="开始时间（秒）")
    end: float = Field(..., description="结束时间（秒）")
    text: str = Field(..., description="文本内容")

class TranscriptionResult(BaseModel):
    success: bool = Field(..., description="是否成功")
    text: str = Field("", description="完整转录文本")
    language: str = Field("", description="检测到的语言")
    duration: float = Field(0, description="音频总时长（秒）")
    segments: List[TranscriptionSegment] = Field([], description="分段转录结果")
    error: Optional[str] = Field(None, description="错误信息")

class BackgroundRemovalResult(BaseModel):
    success: bool = Field(..., description="是否成功")
    output_path: str = Field("", description="输出文件路径")
    original_size: int = Field(0, description="原始文件大小（字节）")
    processed_size: int = Field(0, description="处理后文件大小（字节）")
    processing_time: float = Field(0, description="处理耗时（秒）")
    error: Optional[str] = Field(None, description="错误信息")

class VideoProcessResult(BaseModel):
    success: bool = Field(..., description="是否成功")
    job_id: str = Field(..., description="任务ID")
    teacher_name: Optional[str] = Field(None, description="外教姓名")
    original_video: str = Field("", description="原始视频路径")
    processed_video: str = Field("", description="处理后视频路径")
    transcription: TranscriptionResult = Field(..., description="转录结果")
    background_removal: BackgroundRemovalResult = Field(..., description="背景移除结果")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    completed_at: Optional[datetime] = Field(None, description="完成时间")
    status: ProcessingStatus = Field(ProcessingStatus.PENDING, description="处理状态")
    error: Optional[str] = Field(None, description="错误信息")

class ProcessingProgress(BaseModel):
    job_id: str = Field(..., description="任务ID")
    status: ProcessingStatus = Field(..., description="处理状态")
    progress: float = Field(0, ge=0, le=100, description="进度百分比")
    current_step: str = Field("", description="当前步骤")
    estimated_completion: Optional[datetime] = Field(None, description="预计完成时间")
    error: Optional[str] = Field(None, description="错误信息")

class ApiResponse(BaseModel):
    success: bool = Field(..., description="请求是否成功")
    message: str = Field("", description="响应消息")
    data: Optional[Any] = Field(None, description="响应数据")
    error: Optional[str] = Field(None, description="错误信息")
    timestamp: datetime = Field(default_factory=datetime.now, description="响应时间")
```

### 3. 视频模型 (`app/models/video.py`)

```python
from pydantic import BaseModel, Field, validator
from typing import Optional
import os

class VideoUploadRequest(BaseModel):
    teacher_name: str = Field(..., min_length=1, max_length=100, description="外教姓名")
    description: Optional[str] = Field(None, max_length=500, description="视频描述")
    language_hint: Optional[str] = Field(None, description="语言提示（如：en, zh, es）")
  
    @validator("teacher_name")
    def validate_teacher_name(cls, v):
        if not v.strip():
            raise ValueError("外教姓名不能为空")
        return v.strip()

class VideoInfo(BaseModel):
    filename: str = Field(..., description="文件名")
    size: int = Field(..., description="文件大小（字节）")
    duration: Optional[float] = Field(None, description="视频时长（秒）")
    format: str = Field(..., description="视频格式")
    resolution: Optional[str] = Field(None, description="分辨率")
  
    @validator("size")
    def validate_size(cls, v):
        max_size = 100 * 1024 * 1024  # 100MB
        if v > max_size:
            raise ValueError(f"文件大小不能超过 {max_size // (1024*1024)}MB")
        return v
  
    @validator("format")
    def validate_format(cls, v):
        allowed_formats = [".mp4", ".mov", ".avi", ".mkv"]
        if v.lower() not in allowed_formats:
            raise ValueError(f"不支持的视频格式，支持的格式：{', '.join(allowed_formats)}")
        return v.lower()
```

### 4. 背景移除服务 (`app/services/background_removal.py`)

```python
import requests
import asyncio
import os
import time
import logging
from typing import Dict
from app.config.settings import settings

logger = logging.getLogger(__name__)

class UnscreenService:
    def __init__(self):
        self.api_key = settings.UNSCREEN_API_KEY
        self.base_url = "https://api.unscreen.com/v1.0"
      
    async def remove_background(self, video_file_path: str, output_dir: str) -> Dict:
        """
        移除视频背景
      
        Args:
            video_file_path: 输入视频路径
            output_dir: 输出目录
          
        Returns:
            Dict: 处理结果
        """
        start_time = time.time()
      
        try:
            logger.info(f"开始处理视频背景移除: {video_file_path}")
          
            # 检查文件是否存在
            if not os.path.exists(video_file_path):
                raise FileNotFoundError(f"视频文件不存在: {video_file_path}")
          
            original_size = os.path.getsize(video_file_path)
            logger.info(f"原始文件大小: {original_size / (1024*1024):.2f}MB")
          
            # 1. 上传并处理视频
            clip_url = await self._process_video(video_file_path)
          
            # 2. 下载处理后的视频
            output_filename = f"no_bg_{os.path.basename(video_file_path)}"
            output_path = os.path.join(output_dir, output_filename)
          
            await self._download_video(clip_url, output_path)
          
            processed_size = os.path.getsize(output_path)
            processing_time = time.time() - start_time
          
            logger.info(f"背景移除完成: {output_path}")
            logger.info(f"处理耗时: {processing_time:.2f}秒")
            logger.info(f"处理后大小: {processed_size / (1024*1024):.2f}MB")
          
            return {
                "success": True,
                "output_path": output_path,
                "original_size": original_size,
                "processed_size": processed_size,
                "processing_time": processing_time
            }
          
        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"背景移除失败: {str(e)}")
            return {
                "success": False,
                "output_path": "",
                "original_size": 0,
                "processed_size": 0,
                "processing_time": processing_time,
                "error": str(e)
            }
  
    async def _process_video(self, video_file_path: str) -> str:
        """上传并处理视频"""
        headers = {"Authorization": f"Bearer {self.api_key}"}
      
        try:
            with open(video_file_path, 'rb') as f:
                files = {"clip_file": f}
                data = {
                    "output_format": settings.VIDEO_OUTPUT_FORMAT,
                    "enhance": "true",       # 边缘增强
                    "matting": "alpha"       # 透明通道处理
                }
              
                logger.info("正在上传视频到 Unscreen...")
                response = requests.post(
                    f"{self.base_url}/account/credits/v1.0/process",
                    headers=headers,
                    files=files,
                    data=data,
                    timeout=300  # 5分钟超时
                )
          
            if response.status_code == 200:
                result = response.json()
                clip_url = result["clip_url"]
                logger.info("视频处理成功，获取到下载链接")
                return clip_url
            else:
                error_msg = f"Unscreen API错误: {response.status_code} - {response.text}"
                logger.error(error_msg)
                raise Exception(error_msg)
              
        except requests.exceptions.Timeout:
            raise Exception("上传视频超时，请检查网络连接")
        except requests.exceptions.RequestException as e:
            raise Exception(f"网络请求失败: {str(e)}")
  
    async def _download_video(self, clip_url: str, output_path: str):
        """下载处理后的视频"""
        try:
            logger.info("正在下载处理后的视频...")
          
            # 确保输出目录存在
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
          
            response = requests.get(clip_url, stream=True, timeout=300)
            response.raise_for_status()
          
            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
          
            logger.info(f"视频下载完成: {output_path}")
          
        except requests.exceptions.RequestException as e:
            raise Exception(f"下载视频失败: {str(e)}")
  
    async def get_account_credits(self) -> Dict:
        """查询账户余额"""
        headers = {"Authorization": f"Bearer {self.api_key}"}
      
        try:
            response = requests.get(
                f"{self.base_url}/account/credits",
                headers=headers,
                timeout=30
            )
          
            if response.status_code == 200:
                return response.json()
            else:
                raise Exception(f"获取余额失败: {response.status_code} - {response.text}")
              
        except requests.exceptions.RequestException as e:
            raise Exception(f"查询余额失败: {str(e)}")
```

### 5. 语音转文字服务 (`app/services/speech_to_text.py`)

```python
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
                    "response_format": "verbose_json",
                    "timestamp_granularities": ["segment"]
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
```

### 6. 主处理服务 (`app/services/video_processor.py`)

```python
import os
import uuid
import asyncio
import logging
from datetime import datetime
from typing import Dict, Optional
from concurrent.futures import ThreadPoolExecutor

from app.config.settings import settings
from app.models.response import VideoProcessResult, ProcessingStatus
from .background_removal import UnscreenService
from .speech_to_text import WhisperService

logger = logging.getLogger(__name__)

class VideoProcessorService:
    def __init__(self):
        self.bg_removal_service = UnscreenService()
        self.speech_service = WhisperService()
        self.executor = ThreadPoolExecutor(max_workers=settings.MAX_CONCURRENT_JOBS)
      
        # 存储处理进度的字典
        self.job_progress = {}
  
    async def process_teacher_video(
        self, 
        video_path: str, 
        teacher_name: str,
        language_hint: Optional[str] = None
    ) -> Dict:
        """
        处理外教自我介绍视频的完整流程
      
        Args:
            video_path: 视频文件路径
            teacher_name: 外教姓名
            language_hint: 语言提示
          
        Returns:
            Dict: 处理结果
        """
        job_id = str(uuid.uuid4())
        start_time = datetime.now()
      
        # 初始化任务进度
        self.job_progress[job_id] = {
            "status": ProcessingStatus.PROCESSING,
            "progress": 0,
            "current_step": "开始处理",
            "created_at": start_time
        }
      
        try:
            logger.info(f"开始处理外教视频 - 任务ID: {job_id}, 外教: {teacher_name}")
          
            # 验证输入文件
            if not os.path.exists(video_path):
                raise FileNotFoundError(f"视频文件不存在: {video_path}")
          
            # 步骤1: 语音转文字 (0-50%)
            logger.info(f"[{job_id}] 步骤1: 语音转文字")
            self._update_progress(job_id, 10, "正在提取音频...")
          
            speech_result = await self.speech_service.transcribe_video(
                video_path, 
                language_hint
            )
          
            if not speech_result.get("success"):
                raise Exception(f"语音转文字失败: {speech_result.get('error')}")
          
            self._update_progress(job_id, 50, "语音转文字完成")
          
            # 步骤2: 人像抠像 (50-90%)
            logger.info(f"[{job_id}] 步骤2: 视频背景移除")
            self._update_progress(job_id, 60, "正在移除背景...")
          
            bg_removal_result = await self.bg_removal_service.remove_background(
                video_path, 
                settings.OUTPUT_DIR
            )
          
            if not bg_removal_result.get("success"):
                raise Exception(f"背景移除失败: {bg_removal_result.get('error')}")
          
            self._update_progress(job_id, 90, "背景移除完成")
          
            # 步骤3: 生成最终结果 (90-100%)
            self._update_progress(job_id, 95, "生成处理结果...")
          
            completed_at = datetime.now()
            processing_duration = (completed_at - start_time).total_seconds()
          
            # 构建完整结果
            result = {
                "success": True,
                "job_id": job_id,
                "teacher_name": teacher_name,
                "original_video": video_path,
                "processed_video": bg_removal_result["output_path"],
                "transcription": speech_result,
                "background_removal": bg_removal_result,
                "created_at": start_time,
                "completed_at": completed_at,
                "processing_duration": processing_duration,
                "status": ProcessingStatus.COMPLETED
            }
          
            # 更新最终进度
            self.job_progress[job_id].update({
                "status": ProcessingStatus.COMPLETED,
                "progress": 100,
                "current_step": "处理完成",
                "completed_at": completed_at,
                "result": result
            })
          
            logger.info(f"[{job_id}] 视频处理完成，总耗时: {processing_duration:.2f}秒")
          
            return result
          
        except Exception as e:
            error_msg = str(e)
            completed_at = datetime.now()
            processing_duration = (completed_at - start_time).total_seconds()
          
            logger.error(f"[{job_id}] 视频处理失败: {error_msg}")
          
            # 更新失败状态
            self.job_progress[job_id].update({
                "status": ProcessingStatus.FAILED,
                "current_step": "处理失败",
                "error": error_msg,
                "completed_at": completed_at
            })
          
            return {
                "success": False,
                "job_id": job_id,
                "teacher_name": teacher_name,
                "original_video": video_path,
                "error": error_msg,
                "created_at": start_time,
                "completed_at": completed_at,
                "processing_duration": processing_duration,
                "status": ProcessingStatus.FAILED
            }
  
    def _update_progress(self, job_id: str, progress: float, step: str):
        """更新任务进度"""
        if job_id in self.job_progress:
            self.job_progress[job_id].update({
                "progress": progress,
                "current_step": step,
                "updated_at": datetime.now()
            })
            logger.info(f"[{job_id}] {progress}% - {step}")
  
    def get_job_progress(self, job_id: str) -> Optional[Dict]:
        """获取任务进度"""
        return self.job_progress.get(job_id)
  
    def get_all_jobs(self) -> Dict:
        """获取所有任务状态"""
        return self.job_progress.copy()
  
    async def cleanup_old_jobs(self, hours: int = 24):
        """清理旧的任务记录"""
        current_time = datetime.now()
        jobs_to_remove = []
      
        for job_id, job_info in self.job_progress.items():
            created_at = job_info.get("created_at", current_time)
            age_hours = (current_time - created_at).total_seconds() / 3600
          
            if age_hours > hours:
                jobs_to_remove.append(job_id)
      
        for job_id in jobs_to_remove:
            del self.job_progress[job_id]
            logger.info(f"清理旧任务: {job_id}")
  
    async def get_service_status(self) -> Dict:
        """获取服务状态"""
        try:
            # 检查 Unscreen 账户余额
            unscreen_credits = await self.bg_removal_service.get_account_credits()
          
            return {
                "success": True,
                "services": {
                    "background_removal": {
                        "provider": "Unscreen",
                        "status": "healthy",
                        "credits": unscreen_credits
                    },
                    "speech_to_text": {
                        "provider": "OpenAI Whisper",
                        "status": "healthy"
                    }
                },
                "active_jobs": len([
                    job for job in self.job_progress.values() 
                    if job.get("status") == ProcessingStatus.PROCESSING
                ]),
                "total_jobs": len(self.job_progress)
            }
          
        except Exception as e:
            logger.error(f"获取服务状态失败: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

# 创建全局实例
video_processor = VideoProcessorService()
```

### 7. API 路由 (`app/api/routes/video.py`)

```python
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from typing import Optional
import os
import shutil
import uuid
from datetime import datetime

from app.models.response import ApiResponse, VideoProcessResult, ProcessingProgress
from app.models.video import VideoUploadRequest, VideoInfo
from app.services.video_processor import video_processor
from app.config.settings import settings
from app.utils.file_handler import validate_video_file, get_video_info

router = APIRouter(prefix="/api/v1/video", tags=["视频处理"])

@router.post("/upload-and-process", response_model=ApiResponse)
async def upload_and_process_video(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="视频文件"),
    teacher_name: str = Form(..., description="外教姓名"),
    description: Optional[str] = Form(None, description="视频描述"),
    language_hint: Optional[str] = Form(None, description="语言提示（如：en, zh, es）")
):
    """
    上传并处理外教视频
  
    支持的格式：MP4, MOV, AVI, MKV
    最大文件大小：100MB
    """
    try:
        # 1. 验证文件
        if not file.filename:
            raise HTTPException(status_code=400, detail="请选择文件")
      
        file_extension = os.path.splitext(file.filename)[1].lower()
        if file_extension not in settings.SUPPORTED_VIDEO_FORMATS:
            raise HTTPException(
                status_code=400, 
                detail=f"不支持的文件格式。支持的格式：{', '.join(settings.SUPPORTED_VIDEO_FORMATS)}"
            )
      
        # 2. 检查文件大小
        file_size = 0
        content = await file.read()
        file_size = len(content)
      
        if file_size > settings.MAX_VIDEO_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"文件大小不能超过 {settings.MAX_VIDEO_SIZE // (1024*1024)}MB"
            )
      
        # 3. 保存上传的文件
        upload_id = str(uuid.uuid4())
        filename = f"{upload_id}_{file.filename}"
        file_path = os.path.join(settings.UPLOAD_DIR, filename)
      
        with open(file_path, "wb") as buffer:
            buffer.write(content)
      
        # 4. 开始异步处理
        background_tasks.add_task(
            process_video_background,
            file_path,
            teacher_name,
            language_hint
        )
      
        return ApiResponse(
            success=True,
            message="视频上传成功，正在后台处理",
            data={
                "upload_id": upload_id,
                "filename": file.filename,
                "size": file_size,
                "teacher_name": teacher_name,
                "status": "processing"
            }
        )
      
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"上传失败: {str(e)}")

@router.post("/process", response_model=ApiResponse)
async def process_existing_video(
    background_tasks: BackgroundTasks,
    video_path: str = Form(..., description="视频文件路径"),
    teacher_name: str = Form(..., description="外教姓名"),
    language_hint: Optional[str] = Form(None, description="语言提示")
):
    """
    处理已存在的视频文件
    """
    try:
        if not os.path.exists(video_path):
            raise HTTPException(status_code=404, detail="视频文件不存在")
      
        # 开始异步处理
        background_tasks.add_task(
            process_video_background,
            video_path,
            teacher_name,
            language_hint
        )
      
        return ApiResponse(
            success=True,
            message="开始处理视频",
            data={
                "video_path": video_path,
                "teacher_name": teacher_name,
                "status": "processing"
            }
        )
      
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"处理失败: {str(e)}")

@router.get("/progress/{job_id}", response_model=ApiResponse)
async def get_processing_progress(job_id: str):
    """
    获取处理进度
    """
    try:
        progress = video_processor.get_job_progress(job_id)
      
        if not progress:
            raise HTTPException(status_code=404, detail="任务不存在")
      
        return ApiResponse(
            success=True,
            message="获取进度成功",
            data=progress
        )
      
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取进度失败: {str(e)}")

@router.get("/jobs", response_model=ApiResponse)
async def get_all_jobs():
    """
    获取所有任务状态
    """
    try:
        jobs = video_processor.get_all_jobs()
      
        return ApiResponse(
            success=True,
            message="获取任务列表成功",
            data={
                "jobs": jobs,
                "total": len(jobs)
            }
        )
      
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取任务列表失败: {str(e)}")

@router.get("/download/{job_id}")
async def download_processed_video(job_id: str):
    """
    下载处理后的视频
    """
    try:
        progress = video_processor.get_job_progress(job_id)
      
        if not progress:
            raise HTTPException(status_code=404, detail="任务不存在")
      
        if progress["status"] != "completed":
            raise HTTPException(status_code=400, detail="视频尚未处理完成")
      
        result = progress.get("result", {})
        processed_video = result.get("processed_video")
      
        if not processed_video or not os.path.exists(processed_video):
            raise HTTPException(status_code=404, detail="处理后的视频文件不存在")
      
        filename = os.path.basename(processed_video)
      
        return FileResponse(
            path=processed_video,
            filename=filename,
            media_type="video/mp4"
        )
      
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"下载失败: {str(e)}")

@router.get("/status", response_model=ApiResponse)
async def get_service_status():
    """
    获取服务状态
    """
    try:
        status = await video_processor.get_service_status()
      
        return ApiResponse(
            success=True,
            message="获取服务状态成功",
            data=status
        )
      
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取服务状态失败: {str(e)}")

async def process_video_background(
    video_path: str, 
    teacher_name: str, 
    language_hint: Optional[str] = None
):
    """
    后台处理视频的任务
    """
    try:
        result = await video_processor.process_teacher_video(
            video_path, 
            teacher_name, 
            language_hint
        )
      
        # 这里可以添加处理完成后的通知逻辑
        # 例如发送邮件、Webhook 等
      
    except Exception as e:
        # 记录错误日志
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"后台视频处理失败: {str(e)}")
```

### 8. 健康检查路由 (`app/api/routes/health.py`)

```python
from fastapi import APIRouter, HTTPException
from app.models.response import ApiResponse
from app.config.settings import settings
import os
import subprocess

router = APIRouter(prefix="/api/v1/health", tags=["健康检查"])

@router.get("/", response_model=ApiResponse)
async def health_check():
    """
    基本健康检查
    """
    return ApiResponse(
        success=True,
        message="服务运行正常",
        data={
            "status": "healthy",
            "environment": settings.ENVIRONMENT
        }
    )

@router.get("/detailed", response_model=ApiResponse)
async def detailed_health_check():
    """
    详细健康检查
    """
    try:
        checks = {}
      
        # 检查 API Keys
        checks["api_keys"] = {
            "openai": bool(settings.OPENAI_API_KEY),
            "unscreen": bool(settings.UNSCREEN_API_KEY)
        }
      
        # 检查目录权限
        checks["directories"] = {}
        for dir_name, dir_path in [
            ("upload", settings.UPLOAD_DIR),
            ("output", settings.OUTPUT_DIR),
            ("temp", settings.TEMP_DIR)
        ]:
            checks["directories"][dir_name] = {
                "exists": os.path.exists(dir_path),
                "writable": os.access(dir_path, os.W_OK) if os.path.exists(dir_path) else False
            }
      
        # 检查 FFmpeg
        try:
            result = subprocess.run(['ffmpeg', '-version'], capture_output=True, timeout=10)
            checks["ffmpeg"] = {
                "available": result.returncode == 0,
                "version": result.stdout.decode().split('\n')[0] if result.returncode == 0 else None
            }
        except Exception:
            checks["ffmpeg"] = {"available": False, "version": None}
      
        # 检查磁盘空间
        try:
            statvfs = os.statvfs(settings.OUTPUT_DIR)
            free_space = statvfs.f_frsize * statvfs.f_bavail
            checks["disk_space"] = {
                "free_bytes": free_space,
                "free_gb": round(free_space / (1024**3), 2)
            }
        except Exception:
            checks["disk_space"] = {"error": "无法获取磁盘空间信息"}
      
        return ApiResponse(
            success=True,
            message="详细健康检查完成",
            data=checks
        )
      
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"健康检查失败: {str(e)}")
```

### 9. 主应用文件 (`app/main.py`)

```python
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import os
import logging
from contextlib import asynccontextmanager

from app.config.settings import settings
from app.api.routes import video, health
from app.utils.logger import setup_logging

# 设置日志
setup_logging()
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时执行
    logger.info("外教视频处理系统启动")
    logger.info(f"环境: {settings.ENVIRONMENT}")
    logger.info(f"上传目录: {settings.UPLOAD_DIR}")
    logger.info(f"输出目录: {settings.OUTPUT_DIR}")
  
    # 确保必要目录存在
    for directory in [settings.UPLOAD_DIR, settings.OUTPUT_DIR, settings.TEMP_DIR]:
        os.makedirs(directory, exist_ok=True)
        logger.info(f"目录已准备: {directory}")
  
    yield
  
    # 关闭时执行
    logger.info("外教视频处理系统关闭")

# 创建 FastAPI 应用
app = FastAPI(
    title="外教视频处理系统",
    description="集成语音转文字和人像抠像功能的外教自我介绍视频处理系统",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应该限制具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(health.router)
app.include_router(video.router)

# 静态文件服务（用于提供处理后的视频文件）
if os.path.exists(settings.OUTPUT_DIR):
    app.mount(
        "/outputs", 
        StaticFiles(directory=settings.OUTPUT_DIR), 
        name="outputs"
    )

@app.get("/", response_class=HTMLResponse)
async def root():
    """主页"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>外教视频处理系统</title>
        <meta charset="utf-8">
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; }
            .container { max-width: 800px; margin: 0 auto; }
            .header { text-align: center; margin-bottom: 40px; }
            .feature { margin: 20px 0; padding: 20px; border-left: 4px solid #007bff; background: #f8f9fa; }
            .api-link { display: inline-block; margin: 10px; padding: 10px 20px; background: #007bff; color: white; text-decoration: none; border-radius: 5px; }
            .api-link:hover { background: #0056b3; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🎥 外教视频处理系统</h1>
                <p>集成语音转文字和人像抠像功能的专业视频处理平台</p>
            </div>
          
            <div class="feature">
                <h3>🎤 语音转文字</h3>
                <p>基于 OpenAI Whisper API，支持100+种语言的高精度语音识别，自动生成字幕和时间戳。</p>
            </div>
          
            <div class="feature">
                <h3>🖼️ 人像抠像</h3>
                <p>基于 Unscreen API，专业的视频背景移除，生成透明背景的人像视频。</p>
            </div>
          
            <div class="feature">
                <h3>⚡ 异步处理</h3>
                <p>支持大文件异步处理，实时进度跟踪，多任务并发处理。</p>
            </div>
          
            <div style="text-align: center; margin-top: 40px;">
                <a href="/docs" class="api-link">📚 API 文档</a>
                <a href="/api/v1/health/detailed" class="api-link">🔍 系统状态</a>
                <a href="/redoc" class="api-link">📖 ReDoc 文档</a>
            </div>
        </div>
    </body>
    </html>
    """

@app.exception_handler(404)
async def not_found_handler(request, exc):
    return {"error": "接口不存在", "detail": str(exc)}

@app.exception_handler(500)
async def internal_error_handler(request, exc):
    logger.error(f"内部服务器错误: {str(exc)}")
    return {"error": "内部服务器错误", "detail": "请联系管理员"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.ENVIRONMENT == "development",
        log_level=settings.LOG_LEVEL.lower()
    )
```

### 10. 文件处理工具 (`app/utils/file_handler.py`)

```python
import os
import shutil
import subprocess
import mimetypes
from typing import Dict, Optional, Tuple
import logging

logger = logging.getLogger(__name__)

def validate_video_file(file_path: str) -> Tuple[bool, str]:
    """
    验证视频文件
  
    Returns:
        Tuple[bool, str]: (是否有效, 错误信息)
    """
    try:
        if not os.path.exists(file_path):
            return False, "文件不存在"
      
        if os.path.getsize(file_path) == 0:
            return False, "文件为空"
      
        # 检查文件扩展名
        file_extension = os.path.splitext(file_path)[1].lower()
        if file_extension not in ['.mp4', '.mov', '.avi', '.mkv']:
            return False, f"不支持的文件格式: {file_extension}"
      
        # 检查 MIME 类型
        mime_type, _ = mimetypes.guess_type(file_path)
        if mime_type and not mime_type.startswith('video/'):
            return False, f"文件类型错误: {mime_type}"
      
        return True, ""
      
    except Exception as e:
        return False, f"文件验证失败: {str(e)}"

def get_video_info(file_path: str) -> Optional[Dict]:
    """
    获取视频文件信息
    """
    try:
        cmd = [
            'ffprobe', '-v', 'quiet', '-print_format', 'json',
            '-show_format', '-show_streams', file_path
        ]
      
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
      
        if result.returncode == 0:
            import json
            info = json.loads(result.stdout)
          
            # 提取视频流信息
            video_stream = None
            audio_stream = None
          
            for stream in info.get('streams', []):
                if stream.get('codec_type') == 'video' and not video_stream:
                    video_stream = stream
                elif stream.get('codec_type') == 'audio' and not audio_stream:
                    audio_stream = stream
          
            format_info = info.get('format', {})
          
            return {
                "filename": os.path.basename(file_path),
                "size": int(format_info.get('size', 0)),
                "duration": float(format_info.get('duration', 0)),
                "format": format_info.get('format_name', ''),
                "video": {
                    "codec": video_stream.get('codec_name', '') if video_stream else '',
                    "width": int(video_stream.get('width', 0)) if video_stream else 0,
                    "height": int(video_stream.get('height', 0)) if video_stream else 0,
                    "fps": eval(video_stream.get('r_frame_rate', '0/1')) if video_stream else 0
                } if video_stream else None,
                "audio": {
                    "codec": audio_stream.get('codec_name', '') if audio_stream else '',
                    "sample_rate": int(audio_stream.get('sample_rate', 0)) if audio_stream else 0,
                    "channels": int(audio_stream.get('channels', 0)) if audio_stream else 0
                } if audio_stream else None
            }
        else:
            logger.error(f"ffprobe 错误: {result.stderr}")
            return None
          
    except Exception as e:
        logger.error(f"获取视频信息失败: {str(e)}")
        return None

def clean_temp_files(temp_dir: str, max_age_hours: int = 24):
    """
    清理临时文件
    """
    try:
        import time
        current_time = time.time()
        max_age_seconds = max_age_hours * 3600
      
        for filename in os.listdir(temp_dir):
            file_path = os.path.join(temp_dir, filename)
          
            if os.path.isfile(file_path):
                file_age = current_time - os.path.getmtime(file_path)
              
                if file_age > max_age_seconds:
                    os.remove(file_path)
                    logger.info(f"删除过期临时文件: {file_path}")
      
    except Exception as e:
        logger.error(f"清理临时文件失败: {str(e)}")

def ensure_directory_exists(directory: str):
    """
    确保目录存在
    """
    try:
        os.makedirs(directory, exist_ok=True)
        return True
    except Exception as e:
        logger.error(f"创建目录失败 {directory}: {str(e)}")
        return False

def get_safe_filename(filename: str) -> str:
    """
    获取安全的文件名
    """
    import re
    # 移除或替换不安全的字符
    safe_filename = re.sub(r'[^\w\-_\.]', '_', filename)
    return safe_filename

def calculate_file_hash(file_path: str) -> str:
    """
    计算文件哈希值
    """
    import hashlib
  
    hash_md5 = hashlib.md5()
    try:
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    except Exception as e:
        logger.error(f"计算文件哈希失败: {str(e)}")
        return ""
```

### 11. 日志配置 (`app/utils/logger.py`)

```python
import logging
import logging.handlers
import os
from datetime import datetime
from app.config.settings import settings

def setup_logging():
    """设置日志配置"""
  
    # 创建日志目录
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)
  
    # 配置日志格式
    formatter = logging.Formatter(
        fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
  
    # 根日志记录器
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, settings.LOG_LEVEL.upper()))
  
    # 清除现有的处理器
    root_logger.handlers.clear()
  
    # 控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.INFO)
    root_logger.addHandler(console_handler)
  
    # 文件处理器（按日期轮转）
    file_handler = logging.handlers.TimedRotatingFileHandler(
        filename=os.path.join(log_dir, 'video_processor.log'),
        when='midnight',
        interval=1,
        backupCount=7,
        encoding='utf-8'
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(getattr(logging, settings.LOG_LEVEL.upper()))
    root_logger.addHandler(file_handler)
  
    # 错误日志文件处理器
    error_handler = logging.handlers.TimedRotatingFileHandler(
        filename=os.path.join(log_dir, 'errors.log'),
        when='midnight',
        interval=1,
        backupCount=30,
        encoding='utf-8'
    )
    error_handler.setFormatter(formatter)
    error_handler.setLevel(logging.ERROR)
    root_logger.addHandler(error_handler)
  
    # 禁用一些第三方库的详细日志
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
  
    logging.info("日志系统初始化完成")
```

---

## 启动和运行

### 1. 开发环境启动

```bash
# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env 文件，填入 API Keys

# 启动开发服务器
python -m app.main

# 或者使用 uvicorn
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 2. 生产环境部署

```bash
# 使用 Gunicorn
pip install gunicorn
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000

# 或者使用 Docker
docker-compose up -d
```

### 3. API 使用示例

```bash
# 健康检查
curl http://localhost:8000/api/v1/health/

# 上传并处理视频
curl -X POST "http://localhost:8000/api/v1/video/upload-and-process" \
  -F "file=@teacher_video.mp4" \
  -F "teacher_name=John Smith" \
  -F "language_hint=en"

# 查看处理进度
curl http://localhost:8000/api/v1/video/progress/{job_id}

# 下载处理后的视频
curl http://localhost:8000/api/v1/video/download/{job_id} -o processed_video.mp4
```

---

## 性能优化和监控

### 1. 性能配置建议

```python
# 在 settings.py 中调整
MAX_CONCURRENT_JOBS = 3  # 根据服务器性能调整
MAX_VIDEO_SIZE = 100 * 1024 * 1024  # 100MB
AUDIO_SAMPLE_RATE = 16000  # Whisper 最佳采样率
```

### 2. 监控指标

- 处理队列长度
- 平均处理时间
- API 调用成功率
- 磁盘空间使用
- 内存使用情况

### 3. 错误处理

- 自动重试机制
- 详细错误日志
- 用户友好的错误信息
- 资源清理机制

---

## 常见问题和解决方案

### 1. FFmpeg 相关问题

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install ffmpeg

# 验证安装
ffmpeg -version
```

### 2. API Key 问题

```bash
# 检查环境变量
echo $OPENAI_API_KEY
echo $UNSCREEN_API_KEY

# 验证 API Key 有效性
curl -H "Authorization: Bearer $OPENAI_API_KEY" \
  https://api.openai.com/v1/models
```

### 3. 文件权限问题

```bash
# 设置目录权限
chmod 755 uploads outputs temp
chown -R www-data:www-data uploads outputs temp
```

### 4. 内存优化

```python
# 大文件处理时分块读取
def process_large_file(file_path):
    chunk_size = 8192
    with open(file_path, 'rb') as f:
        while chunk := f.read(chunk_size):
            # 处理块
            pass
```

---

这个开发文档提供了完整的项目结构、核心代码、配置方法和部署指南。你可以按照这个文档逐步搭建和部署外教视频处理系统。有什么需要调整或补充的地方吗？