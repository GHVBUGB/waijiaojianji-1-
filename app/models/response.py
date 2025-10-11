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