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