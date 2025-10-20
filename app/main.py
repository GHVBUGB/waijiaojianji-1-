from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, StreamingResponse
import logging
import os
from contextlib import asynccontextmanager
from pydantic import BaseModel

from app.config.settings import settings
from app.api.routes import video, batch, health
from app.utils.logger import setup_logging

# 设置日志
logger = setup_logging()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    应用生命周期管理
    """
    # 启动时执行
    logger.info("正在启动外教视频处理系统...")

    # 确保必要的目录存在
    for directory in [settings.UPLOAD_DIR, settings.OUTPUT_DIR, settings.TEMP_DIR, "logs"]:
        os.makedirs(directory, exist_ok=True)

    logger.info("系统启动完成")
    yield

    # 关闭时执行
    logger.info("正在关闭外教视频处理系统...")

# 创建FastAPI应用
app = FastAPI(
    title="外教视频处理系统",
    description="基于 FastAPI 的外教自我介绍视频处理系统，集成 OpenAI Whisper API 和 Unscreen API",
    version="1.0.0",
    lifespan=lifespan
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 在生产环境中应该配置具体的域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 启用GZip压缩，提升前端加载速度
app.add_middleware(GZipMiddleware, minimum_size=1024)

# 挂载静态文件目录（为大资源设置缓存头）
app.mount("/static", StaticFiles(directory="app/static"), name="static")
app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")
app.mount("/outputs", StaticFiles(directory=settings.OUTPUT_DIR), name="outputs")

# 注册路由
app.include_router(health.router)
app.include_router(video.router)
app.include_router(batch.router)

@app.get("/", response_class=HTMLResponse)
async def root():
    """
    根路径 - 重定向到操作界面
    """
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/static/index.html")

@app.get("/status", response_class=HTMLResponse)
async def status():
    """
    系统状态页面
    """
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>外教视频处理系统</title>
        <meta charset="utf-8">
        <style>
            body {
                font-family: Arial, sans-serif;
                max-width: 800px;
                margin: 0 auto;
                padding: 20px;
                background-color: #f5f5f5;
            }
            .container {
                background-color: white;
                padding: 30px;
                border-radius: 10px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }
            h1 {
                color: #333;
                text-align: center;
            }
            .feature {
                background-color: #f8f9fa;
                padding: 15px;
                margin: 10px 0;
                border-radius: 5px;
                border-left: 4px solid #007bff;
            }
            .api-link {
                display: inline-block;
                background-color: #007bff;
                color: white;
                padding: 10px 20px;
                text-decoration: none;
                border-radius: 5px;
                margin: 5px;
            }
            .api-link:hover {
                background-color: #0056b3;
            }
            .status {
                text-align: center;
                padding: 20px;
                background-color: #d4edda;
                border: 1px solid #c3e6cb;
                border-radius: 5px;
                color: #155724;
                margin: 20px 0;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🎥 外教视频处理系统</h1>

            <div class="status">
                <h3>✅ 系统运行正常</h3>
                <p>基于 FastAPI 的视频处理服务已启动</p>
            </div>

            <div class="feature">
                <h3>🎯 核心功能</h3>
                <ul>
                    <li>🎥 视频人像背景移除（透明背景）</li>
                    <li>🎤 多语言语音转文字识别</li>
                    <li>📝 自动生成字幕和时间戳</li>
                    <li>🔄 异步处理，支持批量操作</li>
                    <li>📊 处理进度跟踪</li>
                </ul>
            </div>

            <div class="feature">
                <h3>🔗 API 接口</h3>
                <p>
                    <a href="/docs" class="api-link">📚 API 文档</a>
                    <a href="/api/v1/health/" class="api-link">🏥 健康检查</a>
                </p>
            </div>

            <div class="feature">
                <h3>📋 主要接口</h3>
                <ul>
                    <li><strong>POST /api/v1/video/upload-and-process</strong> - 上传并处理视频</li>
                    <li><strong>GET /api/v1/video/progress/{job_id}</strong> - 查看处理进度</li>
                    <li><strong>GET /api/v1/video/download/{job_id}</strong> - 下载处理后的视频</li>
                    <li><strong>GET /api/v1/video/results/{job_id}</strong> - 获取完整处理结果</li>
                </ul>
            </div>

            <div class="feature">
                <h3>⚙️ 技术栈</h3>
                <ul>
                    <li><strong>后端框架:</strong> FastAPI</li>
                    <li><strong>语音转文字:</strong> OpenAI Whisper API</li>
                    <li><strong>背景移除:</strong> Unscreen API</li>
                    <li><strong>视频处理:</strong> FFmpeg</li>
                    <li><strong>异步处理:</strong> Python asyncio</li>
                </ul>
            </div>

            <div style="text-align: center; margin-top: 30px; color: #666;">
                <p>© 2024 外教视频处理系统 - Powered by FastAPI</p>
            </div>
        </div>
    </body>
    </html>
    """

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """
    全局HTTP异常处理
    """
    logger.error(f"HTTP异常: {exc.status_code} - {exc.detail}")
    return {
        "success": False,
        "message": "请求处理失败",
        "error": exc.detail,
        "status_code": exc.status_code
    }

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """
    全局异常处理
    """
    logger.error(f"未处理的异常: {str(exc)}", exc_info=True)
    return {
        "success": False,
        "message": "服务器内部错误",
        "error": "内部服务器错误，请稍后重试"
    }

# 腾讯云万象API测试相关的数据模型
class CIJobRequest(BaseModel):
    job_id: str

@app.post("/check-ci-status")
async def check_ci_status(request: CIJobRequest):
    """
    检查腾讯云万象任务状态
    """
    try:
        from app.services.tencent_video_service import TencentVideoService
        service = TencentVideoService()
        
        status = await service._check_job_status(request.job_id)
        return status
        
    except Exception as e:
        logger.error(f"检查万象任务状态失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/download-ci-result")
async def download_ci_result(request: CIJobRequest):
    """
    下载腾讯云万象处理结果
    """
    try:
        from app.services.tencent_video_service import TencentVideoService
        service = TencentVideoService()
        
        # 检查任务状态
        status = await service._check_job_status(request.job_id)
        if status['state'] != 'Success':
            raise HTTPException(status_code=400, detail=f"任务未完成，当前状态: {status['state']}")
        
        # 下载文件
        output_object = f"output/ci_no_bg_058868c1-61c7-4e74-bec0-380e4898e7f9.mp4"  # 根据实际情况调整
        temp_path = f"temp/download_{request.job_id}.mp4"
        
        await service._download_from_cos(output_object, temp_path)
        
        # 返回文件流
        def iterfile(file_path: str):
            with open(file_path, mode="rb") as file_like:
                yield from file_like
        
        return StreamingResponse(
            iterfile(temp_path), 
            media_type="video/mp4",
            headers={"Content-Disposition": f"attachment; filename=ci_processed_{request.job_id}.mp4"}
        )
        
    except Exception as e:
        logger.error(f"下载万象处理结果失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn

    logger.info(f"启动外教视频处理系统 - 环境: {settings.ENVIRONMENT}")
    logger.info(f"服务地址: http://{settings.HOST}:{settings.PORT}")

    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.ENVIRONMENT == "development",
        reload_dirs=["app"],
        reload_excludes=[
            "uploads/*",
            "outputs/*",
            "logs/*",
            "*.mp4",
            "*.mov",
            "*.avi"
        ],
        log_level=settings.LOG_LEVEL.lower()
    )