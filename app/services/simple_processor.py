import os
import uuid
import asyncio
import logging
from datetime import datetime
from typing import Dict, Optional

from app.config.settings import settings

logger = logging.getLogger(__name__)

class SimpleVideoProcessor:
    def __init__(self):
        # 存储处理进度的字典
        self.job_progress = {}

    async def process_teacher_video_background(
        self,
        job_id: str,
        video_path: str,
        teacher_name: str,
        language_hint: Optional[str] = None
    ) -> None:
        """
        简化的视频处理流程（仅用于测试）
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
            logger.info(f"开始简化处理 - 任务ID: {job_id}, 外教: {teacher_name}")
            
            # 验证输入文件
            if not os.path.exists(video_path):
                raise FileNotFoundError(f"视频文件不存在: {video_path}")
            
            # 模拟处理步骤
            self._update_progress(job_id, 20, "分析视频文件...")
            await asyncio.sleep(2)
            
            self._update_progress(job_id, 50, "处理中...")
            await asyncio.sleep(3)
            
            self._update_progress(job_id, 80, "生成结果...")
            await asyncio.sleep(2)
            
            # 生成模拟结果
            completed_at = datetime.now()
            processing_duration = (completed_at - start_time).total_seconds()
            
            # 构建完整结果
            result = {
                "job_id": job_id,
                "teacher_name": teacher_name,
                "original_file": video_path,
                "processed_video": video_path,  # 暂时使用原文件
                "transcript": f"Hello, I'm {teacher_name}. This is a test transcript.",
                "processing_time": processing_duration,
                "created_at": start_time.isoformat(),
                "completed_at": completed_at.isoformat(),
                "speech_service": "test",
                "video_service": "test"
            }
            
            # 更新最终状态
            self.job_progress[job_id].update({
                "status": "completed",
                "progress": 100,
                "current_step": "处理完成",
                "completed_at": completed_at.isoformat(),
                "result": result
            })
            
            logger.info(f"[{job_id}] 简化处理完成，耗时: {processing_duration:.2f}秒")
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
        return {
            "speech_service": {"name": "test", "status": "active"},
            "video_service": {"name": "test", "status": "active"},
            "system": {
                "max_concurrent_jobs": settings.MAX_CONCURRENT_JOBS,
                "active_jobs": len([j for j in self.job_progress.values() if j.get("status") == "processing"]),
                "total_jobs": len(self.job_progress)
            }
        }

# 创建简化处理器实例
simple_processor = SimpleVideoProcessor()
