#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
批量处理API路由
"""
import os
import uuid
import zipfile
import asyncio
from datetime import datetime
from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.api.routes.video import ApiResponse
from app.services.video_processor import video_processor
from app.config.settings import settings
from app.utils.logger import logger

router = APIRouter(prefix="/api/v1/batch", tags=["批量处理"])

# 批量任务状态存储
batch_jobs = {}

class BatchJobStatus(BaseModel):
    batch_id: str
    total_files: int
    completed_files: int
    failed_files: int
    status: str  # "processing", "completed", "failed"
    created_at: str
    completed_at: Optional[str] = None
    download_ready: bool = False
    download_path: Optional[str] = None
    job_ids: List[str] = []
    background_file_path: Optional[str] = None
    background_url: Optional[str] = None

class BatchProcessRequest(BaseModel):
    teacher_name: str
    language_hint: Optional[str] = None
    quality: str = "medium"
    output_format: str = "mp4"

@router.post("/upload", response_model=ApiResponse)
async def batch_upload_videos(
    files: List[UploadFile] = File(...),
    teacher_name: str = "Teacher",
    language_hint: Optional[str] = None,
    quality: str = "medium",
    output_format: str = "mp4",
    background_image: Optional[UploadFile] = File(None),
    background_url: Optional[str] = None,
    background_tasks: BackgroundTasks = None,
):
    """
    批量上传视频文件
    """
    try:
        batch_id = str(uuid.uuid4())
        upload_dir = Path("uploads") / batch_id
        upload_dir.mkdir(parents=True, exist_ok=True)
        
        uploaded_files = []
        background_file_path = None
        
        # 处理背景图片
        if background_image and background_image.filename:
            background_file_path = upload_dir / f"background_{background_image.filename}"
            with open(background_file_path, "wb") as f:
                content = await background_image.read()
                f.write(content)
            logger.info(f"背景图片已保存: {background_file_path}")
        
        for file in files:
            if not file.filename.lower().endswith(('.mp4', '.avi', '.mov', '.mkv')):
                continue
                
            # 保存文件
            file_path = upload_dir / file.filename
            with open(file_path, "wb") as f:
                content = await file.read()
                f.write(content)
            
            uploaded_files.append({
                "filename": file.filename,
                "path": str(file_path),
                "size": len(content)
            })
        
        if not uploaded_files:
            raise HTTPException(status_code=400, detail="没有有效的视频文件")
        
        # 初始化批量任务状态
        batch_jobs[batch_id] = BatchJobStatus(
            batch_id=batch_id,
            total_files=len(uploaded_files),
            completed_files=0,
            failed_files=0,
            status="uploaded",
            created_at=datetime.now().isoformat(),
            job_ids=[]
        )
        
        # 保存背景信息到批量任务中
        if background_file_path:
            batch_jobs[batch_id].background_file_path = str(background_file_path)
        elif background_url:
            batch_jobs[batch_id].background_url = background_url
        
        logger.info(f"批量上传完成: {batch_id}, 文件数量: {len(uploaded_files)}")

        # 自动启动批量处理（顺序处理）
        try:
            batch_jobs[batch_id].status = "processing"
            if background_tasks is not None:
                background_tasks.add_task(
                    process_batch_videos,
                    batch_id,
                    teacher_name,
                    language_hint,
                    quality,
                    output_format,
                )
                logger.info(f"已自动启动批量处理: {batch_id}")
        except Exception as e:
            logger.error(f"自动启动批量处理失败: {e}")

        return ApiResponse(
            success=True,
            message=f"批量上传成功，已自动开始处理（共{len(uploaded_files)}个文件）",
            data={
                "batch_id": batch_id,
                "uploaded_files": uploaded_files,
                "total_files": len(uploaded_files)
            }
        )
        
    except Exception as e:
        logger.error(f"批量上传失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/process/{batch_id}", response_model=ApiResponse)
async def start_batch_processing(
    batch_id: str,
    background_tasks: BackgroundTasks,
    request: BatchProcessRequest
):
    """
    开始批量处理视频
    """
    try:
        if batch_id not in batch_jobs:
            raise HTTPException(status_code=404, detail="批量任务不存在")
        
        batch_job = batch_jobs[batch_id]
        if batch_job.status != "uploaded":
            raise HTTPException(status_code=400, detail="批量任务状态不正确")
        
        # 更新状态为处理中
        batch_job.status = "processing"
        
        # 在后台启动批量处理
        background_tasks.add_task(
            process_batch_videos,
            batch_id,
            request.teacher_name,
            request.language_hint,
            request.quality,
            request.output_format
        )
        
        return ApiResponse(
            success=True,
            message="批量处理已开始",
            data={"batch_id": batch_id, "status": "processing"}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"启动批量处理失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

async def process_batch_videos(
    batch_id: str,
    teacher_name: str,
    language_hint: Optional[str],
    quality: str,
    output_format: str
):
    """
    后台批量处理视频
    """
    logger.info(f"🚀 开始批量处理任务: {batch_id}")
    
    try:
        if batch_id not in batch_jobs:
            logger.error(f"批量任务不存在: {batch_id}")
            return
            
        batch_job = batch_jobs[batch_id]
        upload_dir = Path("uploads") / batch_id
        
        if not upload_dir.exists():
            logger.error(f"上传目录不存在: {upload_dir}")
            batch_job.status = "failed"
            return
        
        # 获取所有视频文件
        video_files = list(upload_dir.glob("*.mp4")) + \
                     list(upload_dir.glob("*.avi")) + \
                     list(upload_dir.glob("*.mov")) + \
                     list(upload_dir.glob("*.mkv"))
        
        job_ids = []
        
        # 获取背景信息
        background_file_path = getattr(batch_job, 'background_file_path', None)
        background_url = getattr(batch_job, 'background_url', None)
        
        logger.info(f"开始批量处理 {len(video_files)} 个视频文件")
        
        # 逐个处理视频
        for i, video_file in enumerate(video_files, 1):
            try:
                job_id = str(uuid.uuid4())
                job_ids.append(job_id)
                
                logger.info(f"开始处理第 {i}/{len(video_files)} 个视频: {video_file.name}")
                
                # 启动单个视频处理 - 使用完整的处理流程
                await video_processor.process_teacher_video_background(
                    job_id=job_id,
                    video_path=str(video_file),
                    teacher_name=teacher_name,
                    original_filename=video_file.name,
                    language_hint=language_hint,
                    quality=quality,
                    output_format=output_format,
                    background_file_path=background_file_path
                )
                
                # 等待处理完成
                max_wait_time = 600  # 最大等待10分钟
                wait_time = 0
                
                while wait_time < max_wait_time:
                    progress = video_processor.get_job_progress(job_id)
                    if not progress:
                        logger.warning(f"任务 {job_id} 进度信息丢失")
                        batch_job.failed_files += 1
                        break
                    
                    status = progress.get("status")
                    current_progress = progress.get("progress", 0)
                    current_step = progress.get("current_step", "处理中")
                    
                    logger.info(f"视频 {i}/{len(video_files)} 进度: {current_progress}% - {current_step}")
                    
                    if status == "completed":
                        batch_job.completed_files += 1
                        logger.info(f"视频 {i}/{len(video_files)} 处理完成")
                        break
                    elif status == "failed":
                        batch_job.failed_files += 1
                        error_msg = progress.get("error", "未知错误")
                        logger.error(f"视频 {i}/{len(video_files)} 处理失败: {error_msg}")
                        break
                    
                    await asyncio.sleep(3)  # 每3秒检查一次
                    wait_time += 3
                
            except Exception as e:
                logger.error(f"处理视频失败 {video_file.name}: {str(e)}")
                batch_job.failed_files += 1
        
        # 更新批量任务状态
        batch_job.job_ids = job_ids
        batch_job.status = "completed" if batch_job.failed_files == 0 else "partial"
        batch_job.completed_at = datetime.now().isoformat()
        
        # 创建打包下载
        if batch_job.completed_files > 0:
            download_path = await create_batch_download_package(batch_id, job_ids)
            batch_job.download_ready = True
            batch_job.download_path = download_path
        
        logger.info(f"批量处理完成: {batch_id}, 成功: {batch_job.completed_files}, 失败: {batch_job.failed_files}")
        
    except Exception as e:
        logger.error(f"批量处理异常: {str(e)}")
        batch_jobs[batch_id].status = "failed"

async def create_batch_download_package(batch_id: str, job_ids: List[str]) -> str:
    """
    创建批量下载打包文件
    """
    try:
        # 创建下载目录
        download_dir = Path("outputs") / "batch_downloads"
        download_dir.mkdir(parents=True, exist_ok=True)
        
        # 创建时间戳文件夹
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        package_name = f"batch_{batch_id[:8]}_{timestamp}"
        zip_path = download_dir / f"{package_name}.zip"
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for job_id in job_ids:
                progress = video_processor.get_job_progress(job_id)
                if not progress or progress.get("status") != "completed":
                    continue
                
                result = progress.get("result", {})
                
                # 添加处理后的视频
                processed_video = result.get("processed_video")
                if processed_video and os.path.exists(processed_video):
                    video_name = Path(processed_video).name
                    zipf.write(processed_video, f"videos/{video_name}")
                
                # 添加字幕文件
                subtitle_file = result.get("subtitle_file")
                if subtitle_file and os.path.exists(subtitle_file):
                    srt_name = Path(subtitle_file).name
                    zipf.write(subtitle_file, f"subtitles/{srt_name}")
        
        logger.info(f"批量下载包创建完成: {zip_path}")
        return str(zip_path)
        
    except Exception as e:
        logger.error(f"创建下载包失败: {str(e)}")
        raise e

@router.get("/status/{batch_id}", response_model=ApiResponse)
async def get_batch_status(batch_id: str):
    """
    获取批量处理状态
    """
    try:
        if batch_id not in batch_jobs:
            raise HTTPException(status_code=404, detail="批量任务不存在")
        
        batch_job = batch_jobs[batch_id]
        
        return ApiResponse(
            success=True,
            message="获取状态成功",
            data=batch_job.dict()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取批量状态失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/download/{batch_id}")
async def download_batch_results(batch_id: str):
    """
    下载批量处理结果
    """
    try:
        if batch_id not in batch_jobs:
            raise HTTPException(status_code=404, detail="批量任务不存在")
        
        batch_job = batch_jobs[batch_id]
        
        if not batch_job.download_ready or not batch_job.download_path:
            raise HTTPException(status_code=400, detail="下载包未准备好")
        
        if not os.path.exists(batch_job.download_path):
            raise HTTPException(status_code=404, detail="下载文件不存在")
        
        filename = Path(batch_job.download_path).name
        
        return FileResponse(
            batch_job.download_path,
            media_type="application/zip",
            filename=filename
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"下载批量结果失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/list", response_model=ApiResponse)
async def list_batch_jobs():
    """
    获取所有批量任务列表
    """
    try:
        jobs_list = []
        for batch_id, job in batch_jobs.items():
            jobs_list.append({
                "batch_id": batch_id,
                "total_files": job.total_files,
                "completed_files": job.completed_files,
                "failed_files": job.failed_files,
                "status": job.status,
                "created_at": job.created_at,
                "completed_at": job.completed_at,
                "download_ready": job.download_ready
            })
        
        # 按创建时间倒序排列
        jobs_list.sort(key=lambda x: x["created_at"], reverse=True)
        
        return ApiResponse(
            success=True,
            message="获取批量任务列表成功",
            data={"jobs": jobs_list, "total": len(jobs_list)}
        )
        
    except Exception as e:
        logger.error(f"获取批量任务列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{batch_id}", response_model=ApiResponse)
async def delete_batch_job(batch_id: str):
    """
    删除批量任务及相关文件
    """
    try:
        if batch_id not in batch_jobs:
            raise HTTPException(status_code=404, detail="批量任务不存在")
        
        batch_job = batch_jobs[batch_id]
        
        # 删除上传文件夹
        upload_dir = Path("uploads") / batch_id
        if upload_dir.exists():
            import shutil
            shutil.rmtree(upload_dir)
        
        # 删除下载包
        if batch_job.download_path and os.path.exists(batch_job.download_path):
            os.remove(batch_job.download_path)
        
        # 从内存中删除任务
        del batch_jobs[batch_id]
        
        logger.info(f"批量任务已删除: {batch_id}")
        
        return ApiResponse(
            success=True,
            message="批量任务删除成功",
            data={"batch_id": batch_id}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除批量任务失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
