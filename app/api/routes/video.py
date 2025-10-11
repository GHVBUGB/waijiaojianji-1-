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
from app.api.dependencies import validate_video_file, get_video_info
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/video", tags=["视频处理"])

@router.post("/upload-and-process", response_model=ApiResponse)
async def upload_and_process_video(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="视频文件"),
    teacher_name: Optional[str] = Form("", description="外教姓名（可选）"),
    quality: Optional[str] = Form("medium", description="处理质量（fast/medium/high）"),
    output_format: Optional[str] = Form("mp4", description="输出格式"),
    description: Optional[str] = Form(None, description="视频描述"),
    background_image: Optional[UploadFile] = File(None, description="背景图片文件（可选，用于背景替换）")
):
    """
    上传并处理外教自我介绍视频
    """
    try:
        # 验证文件
        await validate_video_file(file)

        # 生成唯一文件名
        file_extension = os.path.splitext(file.filename)[1]
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        upload_path = os.path.join(settings.UPLOAD_DIR, unique_filename)

        # 保存上传的文件
        with open(upload_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # 获取视频信息
        video_info = get_video_info(upload_path)

        logger.info(f"文件上传成功: {file.filename} -> {upload_path}")
        logger.info(f"视频信息: {video_info}")

        # 处理背景图片文件（如果提供）
        background_file_path = None
        if background_image and background_image.filename:
            # 验证背景图片文件
            if not background_image.filename.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp', '.webp')):
                raise HTTPException(status_code=400, detail="背景文件必须是图片格式（jpg, jpeg, png, bmp, webp）")
            
            # 保存背景图片
            bg_extension = os.path.splitext(background_image.filename)[1]
            bg_unique_filename = f"bg_{uuid.uuid4()}{bg_extension}"
            background_file_path = os.path.join(settings.UPLOAD_DIR, bg_unique_filename)
            
            with open(background_file_path, "wb") as bg_buffer:
                shutil.copyfileobj(background_image.file, bg_buffer)
            
            logger.info(f"背景图片上传成功: {background_image.filename} -> {background_file_path}")

        # 创建后台任务处理视频
        job_id = str(uuid.uuid4())
        
        # 使用后台任务异步处理
        background_tasks.add_task(
            video_processor.process_teacher_video_background,
            job_id,
            upload_path,
            teacher_name,
            None,  # language_hint 暂时不使用
            quality,
            output_format,
            background_file_path  # 传递背景图片路径
        )

        return ApiResponse(
            success=True,
            message="视频上传成功，开始后台处理",
            data={
                "job_id": job_id,
                "original_filename": file.filename,
                "video_info": video_info,
                "teacher_name": teacher_name,
                "description": description,
                "background_file": background_image.filename if background_image and background_image.filename else None,
                "background_mode": "Combination" if background_file_path else "Foreground"
            }
        )

    except Exception as e:
        logger.error(f"视频上传失败: {str(e)}")
        return ApiResponse(
            success=False,
            message="视频上传失败",
            error=str(e)
        )

@router.get("/progress/{job_id}", response_model=ApiResponse)
async def get_processing_progress(job_id: str):
    """
    获取视频处理进度
    """
    try:
        progress = video_processor.get_job_progress(job_id)
        if not progress:
            return ApiResponse(
                success=False,
                message="任务不存在",
                error=f"找不到任务ID: {job_id}"
            )

        return ApiResponse(
            success=True,
            message="获取进度成功",
            data=progress
        )

    except Exception as e:
        logger.error(f"获取进度失败: {str(e)}")
        return ApiResponse(
            success=False,
            message="获取进度失败",
            error=str(e)
        )

@router.get("/download/{job_id}")
async def download_processed_video(job_id: str):
    """
    下载处理后的视频
    """
    try:
        progress = video_processor.get_job_progress(job_id)
        if not progress:
            raise HTTPException(status_code=404, detail="任务不存在")

        if progress.get("status") != "completed":
            raise HTTPException(status_code=400, detail="视频处理未完成")

        result = progress.get("result", {})
        processed_video_path = result.get("processed_video")

        if not processed_video_path or not os.path.exists(processed_video_path):
            raise HTTPException(status_code=404, detail="处理后的视频文件不存在")

        return FileResponse(
            processed_video_path,
            media_type="video/mp4",
            filename=os.path.basename(processed_video_path)
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"下载视频失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/results/{job_id}", response_model=ApiResponse)
async def get_processing_results(job_id: str):
    """
    获取完整的处理结果
    """
    try:
        progress = video_processor.get_job_progress(job_id)
        if not progress:
            return ApiResponse(
                success=False,
                message="任务不存在",
                error=f"找不到任务ID: {job_id}"
            )

        result = progress.get("result", {})
        if not result:
            return ApiResponse(
                success=False,
                message="处理结果不存在",
                error="任务可能还在处理中"
            )

        return ApiResponse(
            success=True,
            message="获取结果成功",
            data=result
        )

    except Exception as e:
        logger.error(f"获取结果失败: {str(e)}")
        return ApiResponse(
            success=False,
            message="获取结果失败",
            error=str(e)
        )

@router.get("/jobs", response_model=ApiResponse)
async def get_all_jobs():
    """
    获取所有任务状态
    """
    try:
        all_jobs = video_processor.get_all_jobs()

        # 格式化任务列表
        job_list = []
        for job_id, job_info in all_jobs.items():
            job_list.append({
                "job_id": job_id,
                "status": job_info.get("status"),
                "progress": job_info.get("progress", 0),
                "current_step": job_info.get("current_step", ""),
                "created_at": job_info.get("created_at"),
                "completed_at": job_info.get("completed_at"),
                "error": job_info.get("error")
            })

        return ApiResponse(
            success=True,
            message="获取任务列表成功",
            data={
                "jobs": job_list,
                "total_count": len(job_list)
            }
        )

    except Exception as e:
        logger.error(f"获取任务列表失败: {str(e)}")
        return ApiResponse(
            success=False,
            message="获取任务列表失败",
            error=str(e)
        )

@router.get("/output-files", response_model=ApiResponse)
async def list_output_files():
    """
    获取所有输出文件列表
    """
    try:
        import os
        from datetime import datetime
        
        output_dir = settings.OUTPUT_DIR
        files = []
        
        if os.path.exists(output_dir):
            for filename in os.listdir(output_dir):
                file_path = os.path.join(output_dir, filename)
                if os.path.isfile(file_path) and filename.lower().endswith(('.mp4', '.mov', '.avi')):
                    stat = os.stat(file_path)
                    size_mb = stat.st_size / (1024 * 1024)
                    modified_time = datetime.fromtimestamp(stat.st_mtime)
                    
                    files.append({
                        "name": filename,
                        "size": f"{size_mb:.1f} MB",
                        "size_bytes": stat.st_size,
                        "modified": modified_time.strftime("%Y-%m-%d %H:%M:%S"),
                        "url": f"/outputs/{filename}"
                    })
        
        # 按修改时间排序，最新的在前
        files.sort(key=lambda x: x["modified"], reverse=True)
        
        return ApiResponse(
            success=True,
            message=f"找到 {len(files)} 个输出文件",
            data={"files": files}
        )
        
    except Exception as e:
        logger.error(f"获取输出文件列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取文件列表失败")
