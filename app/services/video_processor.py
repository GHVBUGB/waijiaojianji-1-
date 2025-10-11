import os
import uuid
import asyncio
import logging
from datetime import datetime
from typing import Dict, Optional
from concurrent.futures import ThreadPoolExecutor

from app.config.settings import settings
from app.models.response import VideoProcessResult, ProcessingStatus
from .video_compositor import VideoCompositorService

# 只导入腾讯云服务
if settings.VIDEO_SERVICE == "tencent":
    from .tencent_video_service import TencentVideoService
else:
    raise ValueError(f"当前只支持腾讯云视频服务，请设置 VIDEO_SERVICE=tencent")

logger = logging.getLogger(__name__)

class VideoProcessorService:
    def __init__(self):
        # 暂时禁用语音服务
        self.speech_service = None
        logger.info("语音转文字功能已暂停")
        
        # 初始化视频服务 - 只支持腾讯云服务
        if settings.VIDEO_SERVICE == "tencent":
            self.bg_removal_service = TencentVideoService()
        else:
            raise ValueError(f"当前只支持腾讯云视频服务，请设置 VIDEO_SERVICE=tencent")
        
        # 初始化视频合成服务
        self.compositor_service = VideoCompositorService()
        
        self.executor = ThreadPoolExecutor(max_workers=settings.MAX_CONCURRENT_JOBS)
        
        # 存储处理进度的字典
        self.job_progress = {}

    async def process_teacher_video_background(
        self,
        job_id: str,
        video_path: str,
        teacher_name: str,
        language_hint: Optional[str] = None,
        quality: str = "medium",
        output_format: str = "mp4",
        background_file_path: Optional[str] = None
    ) -> None:
        """
        后台处理外教自我介绍视频的完整流程
        
        Args:
            job_id: 任务ID
            video_path: 视频文件路径
            teacher_name: 外教姓名
            language_hint: 语言提示
            quality: 处理质量
            output_format: 输出格式
            background_file_path: 背景图片文件路径（可选，用于背景替换）
        """
        start_time = datetime.now()
        
        # 初始化任务进度
        self.job_progress[job_id] = {
            "status": "processing",
            "progress": 0,
            "current_step": "开始处理",
            "created_at": start_time.isoformat(),
            "teacher_name": teacher_name,
            "original_file": video_path
        }
        
        try:
            logger.info(f"开始处理外教视频 - 任务ID: {job_id}, 外教: {teacher_name}")
            
            # 验证输入文件
            if not os.path.exists(video_path):
                raise FileNotFoundError(f"视频文件不存在: {video_path}")
            
            # 检查视频长度和估算处理时间
            import cv2
            cap = cv2.VideoCapture(video_path)
            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            duration = frame_count / fps if fps > 0 else 0
            cap.release()
            
            # 视频长度限制（最大5分钟）
            max_duration = 300  # 5分钟
            if duration > max_duration:
                error_msg = f"视频长度 {duration:.1f}秒 超过最大限制 {max_duration}秒，请上传较短的视频"
                logger.error(f"[{job_id}] {error_msg}")
                self.job_progress[job_id].update({
                    "status": "failed",
                    "error": error_msg,
                    "progress": 0
                })
                return
            
            # 估算处理时间（快速模式：约为视频长度的0.5-1倍）
            estimated_time = max(30, duration * 0.8)  # 最少30秒，通常为视频长度的0.8倍
            logger.info(f"[{job_id}] 视频长度: {duration:.1f}秒, 预计处理时间: {estimated_time:.1f}秒")
            self._update_progress(job_id, 5, f"视频长度: {duration:.1f}秒, 预计处理: {estimated_time:.1f}秒")
            
            # 跳过语音转文字，直接进行视频背景移除
            logger.info(f"[{job_id}] 开始腾讯云背景处理")
            
            # 只使用腾讯云服务进行背景处理
            logger.info(f"[{job_id}] 使用腾讯云背景处理服务")
            self._update_progress(job_id, 10, "正在使用腾讯云背景处理...")
            
            try:
                # 传递背景图片路径到腾讯云服务
                bg_removal_result = await self.bg_removal_service.remove_background(
                    video_path,
                    settings.OUTPUT_DIR,
                    quality=quality,
                    background_file_path=background_file_path  # 传递背景图片路径
                )
                
                if bg_removal_result.get("success"):
                    final_output_path = bg_removal_result.get("output_path")
                    logger.info(f"[{job_id}] 腾讯云背景处理成功")
                    self._update_progress(job_id, 90, "腾讯云背景处理完成")
                else:
                    # 腾讯云处理失败，直接返回失败
                    error_msg = bg_removal_result.get('error', '未知错误')
                    logger.error(f"[{job_id}] 腾讯云处理失败: {error_msg}")
                    self._update_progress(job_id, 0, f"处理失败: {error_msg}")
                    
                    # 更新任务状态为失败
                    self.job_progress[job_id].update({
                        "status": "failed",
                        "error": f"腾讯云背景处理失败: {error_msg}",
                        "completed_at": datetime.now()
                    })
                    return
                    
            except Exception as e:
                # 腾讯云处理异常，直接返回失败
                error_msg = f"腾讯云处理异常: {str(e)}"
                logger.error(f"[{job_id}] {error_msg}")
                self._update_progress(job_id, 0, f"处理失败: {error_msg}")
                
                # 更新任务状态为失败
                self.job_progress[job_id].update({
                    "status": "failed",
                    "error": error_msg,
                    "completed_at": datetime.now()
                })
                return
            
            self._update_progress(job_id, 90, "视频合成完成")
            
            # 生成最终结果
            self._update_progress(job_id, 95, "生成处理结果...")
            
            completed_at = datetime.now()
            processing_duration = (completed_at - start_time).total_seconds()
            
            # 构建完整结果（只使用腾讯云处理）
            result = {
                "job_id": job_id,
                "teacher_name": teacher_name,
                "original_file": video_path,
                "processed_video": final_output_path,
                "foreground_video": None,  # 腾讯云直接输出最终视频
                "transcript": "语音转文字功能已暂停",
                "transcript_file": None,
                "processing_time": processing_duration,
                "created_at": start_time.isoformat(),
                "completed_at": completed_at.isoformat(),
                "speech_service": "disabled",
                "video_service": settings.VIDEO_SERVICE,
                "has_background": True,
                "processing_method": "tencent_cloud"
            }
            
            # 更新最终状态
            self.job_progress[job_id].update({
                "status": "completed",
                "progress": 100,
                "current_step": "处理完成",
                "completed_at": completed_at.isoformat(),
                "result": result
            })
            
            logger.info(f"[{job_id}] 处理完成，耗时: {processing_duration:.2f}秒")
            return
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"[{job_id}] 处理失败: {error_msg}")
            
            # 更新错误状态
            self.job_progress[job_id].update({
                "status": "failed",
                "current_step": "处理失败",
                "error": error_msg,
                "completed_at": datetime.now().isoformat()
            })
            
            return

    def _update_progress(self, job_id: str, progress: int, step: str):
        """更新任务进度"""
        if job_id in self.job_progress:
            self.job_progress[job_id].update({
                "progress": progress,
                "current_step": step
            })
            logger.info(f"[{job_id}] 进度: {progress}% - {step}")

    def get_job_progress(self, job_id: str) -> Optional[Dict]:
        """获取任务进度"""
        return self.job_progress.get(job_id)

    def get_all_jobs(self) -> Dict[str, Dict]:
        """获取所有任务状态"""
        return self.job_progress.copy()

    async def get_service_status(self) -> Dict:
        """获取服务状态"""
        try:
            status = {
                "speech_service": {
                    "name": settings.SPEECH_SERVICE,
                    "status": "active",
                    "config": {
                        "service": settings.SPEECH_SERVICE
                    }
                },
                "video_service": {
                    "name": settings.VIDEO_SERVICE,
                    "status": "active", 
                    "config": {
                        "service": settings.VIDEO_SERVICE
                    }
                },
                "system": {
                    "max_concurrent_jobs": settings.MAX_CONCURRENT_JOBS,
                    "active_jobs": len([j for j in self.job_progress.values() if j.get("status") == "processing"]),
                    "total_jobs": len(self.job_progress)
                }
            }
            
            return status
            
        except Exception as e:
            logger.error(f"获取服务状态失败: {str(e)}")
            return {
                "speech_service": {"status": "error", "error": str(e)},
                "video_service": {"status": "error", "error": str(e)},
                "system": {"status": "error", "error": str(e)}
            }

# 创建全局实例
video_processor = VideoProcessorService()