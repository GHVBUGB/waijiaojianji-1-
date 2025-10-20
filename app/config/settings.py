from pydantic_settings import BaseSettings
from pydantic import validator
from typing import List, Optional
import os
from dotenv import load_dotenv

# Ensure .env overrides any existing env vars and decode as UTF-8
load_dotenv(override=True, encoding="utf-8")

class Settings(BaseSettings):
    # API 配置
    OPENAI_API_KEY: Optional[str] = None
    UNSCREEN_API_KEY: Optional[str] = None
    
    # 腾讯云配置
    TENCENT_SECRET_ID: Optional[str] = None
    TENCENT_SECRET_KEY: Optional[str] = None
    TENCENT_REGION: str = "ap-beijing"
    TENCENT_APP_ID: Optional[str] = None
    TENCENT_COS_BUCKET: Optional[str] = None
    
    # 服务选择
    SPEECH_SERVICE: str = "openai"  # openai | doubao
    VIDEO_SERVICE: str = "tencent"  # tencent | unscreen | local

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
    
    # 字幕配置
    SUBTITLE_ENABLED: bool = True
    ASR_SERVICE: str = "xunfei"  # xunfei | tencent
    BURN_SUBTITLES_TO_VIDEO: bool = True
    GENERATE_SUBTITLE_FILE: bool = True
    SUBTITLE_FONT_SIZE: int = 20
    SUBTITLE_FONT_COLOR: str = "black"
    SUBTITLE_OUTLINE_COLOR: str = "black"
    SUBTITLE_OUTLINE_WIDTH: int = 3
    SUBTITLE_SHADOW: int = 2
    SUBTITLE_BOLD: bool = True
    SUBTITLE_ALIGNMENT: int = 2
    
    # 基础美颜（小幅度，统一应用）
    BASIC_BEAUTY_ENABLED: bool = True
    BASIC_BEAUTY_BRIGHTNESS: float = 0.03  # 降低亮度避免泛白
    BASIC_BEAUTY_CONTRAST: float = 1.08    # 增强对比度
    BASIC_BEAUTY_SATURATION: float = 1.12  # 轻微增强饱和度
    BASIC_BEAUTY_GAMMA: float = 1.05       # 伽马调整
    BASIC_BEAUTY_SHARPNESS: float = 0.3   # 锐化强度
    BASIC_BEAUTY_DENOISE: float = 0.8      # 降噪强度
    
    # 画质优化（最终增强）
    QUALITY_ENHANCEMENT_ENABLED: bool = True
    
    # 合成前景统一缩放（固定比例对齐）
    FG_SCALE_RATIO: float = 0.20         # 前景高度相对背景高度的比例 (0~1)
    FG_BOTTOM_MARGIN: int = 80           # 前景距底部像素边距
    FG_TOP_MARGIN: int = 80              # 前景距顶部像素边距（用于防止顶边贴边）
    FG_SAFE_MARGIN_RATIO: float = 0.08   # 左右安全边距占背景高度的比例，防止触边

    # 并发控制
    MAX_PARALLEL_JOBS: int = 1           # 同时处理的视频数量上限（回归单工串行）
    MAX_PARALLEL_ASR: int = 1            # ASR并发上限（建议1，稳定）

    # 全局分布式锁（Vercel 多实例）
    REDIS_URL: Optional[str] = os.getenv("REDIS_URL")
    ASR_LOCK_KEY: str = "asr:global:lock"
    ASR_LOCK_TTL_MS: int = 15 * 60 * 1000
    
    # 腾讯云优化配置
    TENCENT_FRAME_SKIP: int = 5
    TENCENT_MOTION_DETECTION: bool = True
    DAILY_API_LIMIT: int = 1000
    COST_WARNING_THRESHOLD: int = 50

    @validator("OPENAI_API_KEY")
    def validate_openai_key(cls, v, values):
        speech_service = values.get('SPEECH_SERVICE', 'openai')
        if speech_service == "openai" and not v:
            raise ValueError("OPENAI_API_KEY is required when SPEECH_SERVICE is openai")
        return v

    @validator("UNSCREEN_API_KEY")
    def validate_unscreen_key(cls, v, values):
        # 默认按 tencent 处理，避免因默认值导致误判
        video_service = values.get('VIDEO_SERVICE', 'tencent')
        if video_service == "unscreen" and not v:
            raise ValueError("UNSCREEN_API_KEY is required when VIDEO_SERVICE is unscreen")
        return v
        
    @validator("TENCENT_SECRET_ID")
    def validate_tencent_secret_id(cls, v, values):
        video_service = values.get('VIDEO_SERVICE', 'tencent')
        # 放宽为警告，由运行时服务自行校验并给出明确报错，避免启动失败
        if video_service == "tencent" and not v:
            print("[WARN] TENCENT_SECRET_ID missing while VIDEO_SERVICE=tencent; will be validated at runtime.")
        return v

    @validator("TENCENT_SECRET_KEY")
    def validate_tencent_secret_key(cls, v, values):
        video_service = values.get('VIDEO_SERVICE', 'tencent')
        if video_service == "tencent" and not v:
            print("[WARN] TENCENT_SECRET_KEY missing while VIDEO_SERVICE=tencent; will be validated at runtime.")
        return v

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # 创建必要的目录
        for directory in [self.UPLOAD_DIR, self.OUTPUT_DIR, self.TEMP_DIR]:
            os.makedirs(directory, exist_ok=True)

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "ignore"  # 忽略额外字段而不是报错

settings = Settings()