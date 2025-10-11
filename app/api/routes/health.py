from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
import logging
from datetime import datetime

from app.services.video_processor import video_processor

router = APIRouter(prefix="/api/v1", tags=["健康检查"])

logger = logging.getLogger(__name__)

@router.get("/health/")
async def health_check():
    """
    健康检查接口
    """
    try:
        # 获取服务状态
        service_status = await video_processor.get_service_status()

        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "services": service_status.get("services", {}),
            "active_jobs": service_status.get("active_jobs", 0),
            "total_jobs": service_status.get("total_jobs", 0)
        }

    except Exception as e:
        logger.error(f"健康检查失败: {str(e)}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "timestamp": datetime.now().isoformat(),
                "error": str(e)
            }
        )

@router.get("/health/detailed")
async def detailed_health_check():
    """
    详细健康检查接口
    """
    try:
        service_status = await video_processor.get_service_status()

        health_info = {
            "status": "healthy" if service_status.get("success") else "unhealthy",
            "timestamp": datetime.now().isoformat(),
            "services": service_status.get("services", {}),
            "system": {
                "active_jobs": service_status.get("active_jobs", 0),
                "total_jobs": service_status.get("total_jobs", 0),
                "max_concurrent_jobs": 3  # 从配置中获取
            }
        }

        if not service_status.get("success"):
            health_info["error"] = service_status.get("error")

        return health_info

    except Exception as e:
        logger.error(f"详细健康检查失败: {str(e)}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "timestamp": datetime.now().isoformat(),
                "error": str(e)
            }
        )