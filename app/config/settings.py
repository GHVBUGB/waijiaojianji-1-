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