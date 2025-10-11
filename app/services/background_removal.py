import requests
import asyncio
import os
import time
import logging
from typing import Dict
from app.config.settings import settings

logger = logging.getLogger(__name__)

class UnscreenService:
    def __init__(self):
        self.api_key = settings.UNSCREEN_API_KEY
        self.base_url = "https://api.unscreen.com/v1.0"

    async def remove_background(self, video_file_path: str, output_dir: str) -> Dict:
        """
        移除视频背景

        Args:
            video_file_path: 输入视频路径
            output_dir: 输出目录

        Returns:
            Dict: 处理结果
        """
        start_time = time.time()

        try:
            logger.info(f"开始处理视频背景移除: {video_file_path}")

            # 检查文件是否存在
            if not os.path.exists(video_file_path):
                raise FileNotFoundError(f"视频文件不存在: {video_file_path}")

            original_size = os.path.getsize(video_file_path)
            logger.info(f"原始文件大小: {original_size / (1024*1024):.2f}MB")

            # 1. 上传并处理视频
            clip_url = await self._process_video(video_file_path)

            # 2. 下载处理后的视频
            output_filename = f"no_bg_{os.path.basename(video_file_path)}"
            output_path = os.path.join(output_dir, output_filename)

            await self._download_video(clip_url, output_path)

            processed_size = os.path.getsize(output_path)
            processing_time = time.time() - start_time

            logger.info(f"背景移除完成: {output_path}")
            logger.info(f"处理耗时: {processing_time:.2f}秒")
            logger.info(f"处理后大小: {processed_size / (1024*1024):.2f}MB")

            return {
                "success": True,
                "output_path": output_path,
                "original_size": original_size,
                "processed_size": processed_size,
                "processing_time": processing_time
            }

        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"背景移除失败: {str(e)}")
            return {
                "success": False,
                "output_path": "",
                "original_size": 0,
                "processed_size": 0,
                "processing_time": processing_time,
                "error": str(e)
            }

    async def _process_video(self, video_file_path: str) -> str:
        """上传并处理视频"""
        headers = {"Authorization": f"Bearer {self.api_key}"}

        try:
            with open(video_file_path, 'rb') as f:
                files = {"clip_file": f}
                data = {
                    "output_format": settings.VIDEO_OUTPUT_FORMAT,
                    "enhance": "true",       # 边缘增强
                    "matting": "alpha"       # 透明通道处理
                }

                logger.info("正在上传视频到 Unscreen...")
                response = requests.post(
                    f"{self.base_url}/account/credits/v1.0/process",
                    headers=headers,
                    files=files,
                    data=data,
                    timeout=300  # 5分钟超时
                )

            if response.status_code == 200:
                result = response.json()
                clip_url = result["clip_url"]
                logger.info("视频处理成功，获取到下载链接")
                return clip_url
            else:
                error_msg = f"Unscreen API错误: {response.status_code} - {response.text}"
                logger.error(error_msg)
                raise Exception(error_msg)

        except requests.exceptions.Timeout:
            raise Exception("上传视频超时，请检查网络连接")
        except requests.exceptions.RequestException as e:
            raise Exception(f"网络请求失败: {str(e)}")

    async def _download_video(self, clip_url: str, output_path: str):
        """下载处理后的视频"""
        try:
            logger.info("正在下载处理后的视频...")

            # 确保输出目录存在
            os.makedirs(os.path.dirname(output_path), exist_ok=True)

            response = requests.get(clip_url, stream=True, timeout=300)
            response.raise_for_status()

            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)

            logger.info(f"视频下载完成: {output_path}")

        except requests.exceptions.RequestException as e:
            raise Exception(f"下载视频失败: {str(e)}")

    async def get_account_credits(self) -> Dict:
        """查询账户余额"""
        headers = {"Authorization": f"Bearer {self.api_key}"}

        try:
            response = requests.get(
                f"{self.base_url}/account/credits",
                headers=headers,
                timeout=30
            )

            if response.status_code == 200:
                return response.json()
            else:
                raise Exception(f"获取余额失败: {response.status_code} - {response.text}")

        except requests.exceptions.RequestException as e:
            raise Exception(f"查询余额失败: {str(e)}")