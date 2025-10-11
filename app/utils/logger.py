import logging
import os
from datetime import datetime
from app.config.settings import settings

def setup_logging():
    """
    配置日志系统
    """
    # 创建日志目录
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)

    # 配置日志格式
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"

    # 设置日志级别
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)

    # 配置文件处理器
    log_filename = os.path.join(log_dir, f"app_{datetime.now().strftime('%Y%m%d')}.log")
    file_handler = logging.FileHandler(log_filename, encoding='utf-8')
    file_handler.setLevel(log_level)
    file_formatter = logging.Formatter(log_format, date_format)
    file_handler.setFormatter(file_formatter)

    # 配置控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_formatter = logging.Formatter(log_format, date_format)
    console_handler.setFormatter(console_formatter)

    # 配置根日志记录器
    logging.basicConfig(
        level=log_level,
        handlers=[file_handler, console_handler],
        format=log_format,
        datefmt=date_format
    )

    # 设置特定模块的日志级别
    logging.getLogger("uvicorn").setLevel(log_level)
    logging.getLogger("fastapi").setLevel(log_level)

    return logging.getLogger(__name__)

def get_logger(name: str) -> logging.Logger:
    """
    获取指定名称的日志记录器
    """
    return logging.getLogger(name)

# 初始化日志系统
setup_logging()

# 创建默认logger实例
logger = logging.getLogger("app")