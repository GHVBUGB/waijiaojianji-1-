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
from .name_overlay_service import NameOverlayService

# 只导入腾讯云服务
if settings.VIDEO_SERVICE == "tencent":
    from .tencent_video_service import TencentVideoService
else:
    raise ValueError(f"当前只支持腾讯云视频服务，请设置 VIDEO_SERVICE=tencent")

# 导入字幕相关服务
from .tencent_speech_service import TencentASRService

logger = logging.getLogger(__name__)

class VideoProcessorService:
    def __init__(self):
        # 初始化语音服务（用于字幕）- 支持多种ASR服务
        if getattr(settings, 'SUBTITLE_ENABLED', False):
            asr_service = getattr(settings, 'ASR_SERVICE', 'tencent').lower()
            
            if asr_service == 'xunfei':
                try:
                    from app.services.xunfei_asr_service import xunfei_asr_service
                    if xunfei_asr_service:
                        self.speech_service = xunfei_asr_service
                        logger.info("字幕功能已启用 - 使用讯飞ASR服务")
                    else:
                        raise Exception("讯飞ASR服务初始化失败")
                except Exception as e:
                    logger.warning(f"讯飞ASR服务初始化失败，回退到腾讯云: {str(e)}")
                    asr_service = 'tencent'
            
            if asr_service == 'tencent':
                try:
                    from app.services.tencent_asr_sdk import TencentASRSDKService
                    self.speech_service = TencentASRSDKService()
                    logger.info("字幕功能已启用 - 使用腾讯云ASR SDK服务")
                except Exception as e:
                    logger.warning(f"腾讯云SDK服务初始化失败，使用备用服务: {str(e)}")
                    self.speech_service = TencentASRService()
                    logger.info("字幕功能已启用 - 使用腾讯云备用ASR服务")
        else:
            self.speech_service = None
            logger.info("字幕功能已禁用")
        
        # 初始化视频服务 - 只支持腾讯云服务
        if settings.VIDEO_SERVICE == "tencent":
            self.bg_removal_service = TencentVideoService()
        else:
            raise ValueError(f"当前只支持腾讯云视频服务，请设置 VIDEO_SERVICE=tencent")
        
        # 初始化视频合成服务
        self.compositor_service = VideoCompositorService()
        
        # 初始化名字叠加服务
        self.name_overlay_service = NameOverlayService()
        
        self.executor = ThreadPoolExecutor(max_workers=settings.MAX_CONCURRENT_JOBS)
        
        # 存储处理进度的字典
        self.job_progress = {}

    async def process_teacher_video_background(
        self,
        job_id: str,
        video_path: str,
        teacher_name: str,
        original_filename: Optional[str] = None,
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
                    processed_video_path = bg_removal_result.get("output_path")
                    logger.info(f"[{job_id}] 腾讯云背景处理成功")
                    self._update_progress(job_id, 70, "腾讯云背景处理完成，开始添加名字叠加")
                    
                    # 添加名字叠加功能
                    if original_filename:
                        extracted_name = self.name_overlay_service.extract_name_from_filename(original_filename)
                        if extracted_name:
                            # 创建临时输出文件路径
                            temp_output_path = processed_video_path.replace('.mp4', '_with_name.mp4')
                            
                            # 添加名字叠加
                            overlay_success = self.name_overlay_service.add_name_overlay_to_video(
                                input_video_path=processed_video_path,
                                output_video_path=temp_output_path,
                                name=extracted_name,
                                position="center_right"
                            )
                            
                            if overlay_success and os.path.exists(temp_output_path):
                                # 如果叠加成功，使用带名字的视频作为最终结果
                                final_output_path = temp_output_path
                                logger.info(f"[{job_id}] 成功添加名字叠加: {extracted_name}")
                            else:
                                final_output_path = processed_video_path
                                logger.warning(f"[{job_id}] 名字叠加失败，使用原始处理结果")
                        else:
                            final_output_path = processed_video_path
                            logger.info(f"[{job_id}] 无法从文件名 '{original_filename}' 中提取名字，跳过名字叠加")
                    else:
                        final_output_path = processed_video_path
                        logger.info(f"[{job_id}] 未提供原始文件名，跳过名字叠加")
                    
                    # 处理字幕功能
                    subtitle_file = None
                    if self.speech_service and getattr(settings, 'SUBTITLE_ENABLED', False):
                        try:
                            self._update_progress(job_id, 75, "开始生成字幕...")
                            logger.info(f"[{job_id}] 开始语音转文字处理")
                            
                            # 检查ASR服务类型并调用相应的方法
                            asr_service_type = getattr(settings, 'ASR_SERVICE', 'tencent').lower()
                            
                            if asr_service_type == 'xunfei':
                                # 讯飞ASR服务：先提取音频，然后转录
                                import subprocess
                                
                                # 从视频中提取音频
                                audio_path = final_output_path.replace('.mp4', '_audio.wav')
                                subprocess.run([
                                    'ffmpeg', '-i', final_output_path, '-vn', '-acodec', 'pcm_s16le',
                                    '-ar', '16000', '-ac', '1', '-y', audio_path
                                ], check=True, capture_output=True)
                                
                                # 使用讯飞ASR转录音频
                                segments = self.speech_service.transcribe_audio(audio_path)
                                
                                # 清理临时音频文件
                                if os.path.exists(audio_path):
                                    os.remove(audio_path)
                                
                                # 转换为标准格式
                                transcript_result = {
                                    "success": True,
                                    "segments": [{"text": seg["text"], "start": seg["start_time"], "end": seg["end_time"]} 
                                               for seg in segments] if segments else []
                                }
                            else:
                                # 腾讯云ASR服务：使用原有接口
                                transcript_result = await self.speech_service.transcribe_video(final_output_path, language_hint or "zh-CN")
                            
                            if transcript_result.get("success") and transcript_result.get("segments"):
                                segments = transcript_result["segments"]
                                logger.info(f"[{job_id}] 语音识别成功，识别到 {len(segments)} 个片段")
                                
                                # 生成字幕文件
                                subtitle_file = await self._generate_subtitle_file(segments, final_output_path)
                                
                                if subtitle_file:
                                    logger.info(f"[{job_id}] 字幕文件生成成功: {subtitle_file}")
                                    
                                    # 将字幕烧录到抠图后的视频中
                                    if getattr(settings, 'BURN_SUBTITLES_TO_VIDEO', True):
                                        self._update_progress(job_id, 85, "正在烧录字幕到抠图视频...")
                                        final_with_subtitles = await self._burn_subtitles_to_video(final_output_path, subtitle_file)
                                        if final_with_subtitles:
                                            final_output_path = final_with_subtitles
                                            logger.info(f"[{job_id}] 字幕烧录成功，最终输出: {final_output_path}")
                                        else:
                                            logger.warning(f"[{job_id}] 字幕烧录失败，使用无字幕版本")
                                else:
                                    logger.warning(f"[{job_id}] 字幕文件生成失败")
                            else:
                                logger.warning(f"[{job_id}] 语音识别失败或无识别结果")
                                if transcript_result.get("error"):
                                    logger.error(f"[{job_id}] ASR错误: {transcript_result['error']}")
                        except Exception as e:
                            logger.error(f"[{job_id}] 字幕处理异常: {str(e)}")
                            # 字幕处理失败不影响主流程，继续使用抠图后的视频
                    
                    self._update_progress(job_id, 90, "名字叠加完成")
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
                "output_path": final_output_path,  # 添加output_path字段以保持一致性
                "foreground_video": None,  # 腾讯云直接输出最终视频
                "transcript": "字幕已生成" if subtitle_file else "字幕功能已禁用",
                "transcript_file": subtitle_file,
                "subtitle_file": subtitle_file,
                "subtitle_enabled": getattr(settings, 'SUBTITLE_ENABLED', False),  # 添加字幕启用状态
                "subtitle_video": final_output_path if subtitle_file and "_with_subtitles" in final_output_path else None,  # 带字幕的视频路径
                "processing_time": processing_duration,
                "created_at": start_time.isoformat(),
                "completed_at": completed_at.isoformat(),
                "speech_service": "xunfei" if self.speech_service and getattr(settings, 'ASR_SERVICE', 'tencent').lower() == 'xunfei' else ("tencent" if self.speech_service else "disabled"),
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

    async def _generate_subtitle_file(self, segments: list, video_path: str) -> Optional[str]:
        """生成字幕文件"""
        try:
            import os
            
            # 生成字幕文件路径
            base_name = os.path.splitext(video_path)[0]
            subtitle_file = f"{base_name}.srt"
            
            # 生成SRT格式字幕
            with open(subtitle_file, 'w', encoding='utf-8') as f:
                for i, segment in enumerate(segments, 1):
                    start_time = self._format_time(segment.get('start', 0))
                    end_time = self._format_time(segment.get('end', 0))
                    text = segment.get('text', '').strip()
                    
                    f.write(f"{i}\n")
                    f.write(f"{start_time} --> {end_time}\n")
                    f.write(f"{text}\n\n")
            
            return subtitle_file
        except Exception as e:
            logger.error(f"生成字幕文件失败: {str(e)}")
            return None

    def _format_time(self, seconds: float) -> str:
        """将秒数转换为SRT时间格式"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millisecs = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millisecs:03d}"

    async def _burn_subtitles_to_video(self, video_path: str, subtitle_file: str) -> Optional[str]:
        """将字幕烧录到视频中"""
        try:
            import subprocess
            import os
            
            # 生成输出文件路径
            base_name = os.path.splitext(video_path)[0]
            output_path = f"{base_name}_with_subtitles.mp4"
            
            # 获取FFmpeg路径
            ffmpeg_path = os.getenv('FFMPEG_PATH', 'ffmpeg')
            if ffmpeg_path == 'ffmpeg':
                # 如果是默认值，尝试使用完整路径
                ffmpeg_path = r'C:\ffmpeg\bin\ffmpeg.exe'
            
            # 转换为相对路径以避免Windows路径问题
            try:
                # 获取相对路径
                rel_video_path = os.path.relpath(video_path)
                rel_subtitle_path = os.path.relpath(subtitle_file)
                rel_output_path = os.path.relpath(output_path)
            except (OSError, ValueError):
                    # 如果相对路径失败，使用原始路径
                    rel_video_path = video_path
                    rel_subtitle_path = subtitle_file
                    rel_output_path = output_path
            
            # 使用FFmpeg烧录字幕 - 使用增强的字幕样式确保可见性
            # 将路径转换为Unix格式并正确转义
            subtitle_path_unix = rel_subtitle_path.replace('\\', '/').replace(':', '\\:')
            
            cmd = [
                ffmpeg_path,
                '-i', rel_video_path,
                '-vf', f"subtitles=filename={subtitle_path_unix}:force_style='FontSize=32,PrimaryColour=&Hffffff,OutlineColour=&H000000,Outline=3,Shadow=2,Bold=1,Alignment=2'",  # 增强字幕样式
                '-c:v', 'libx264',  # 指定视频编码器
                '-crf', '18',       # 高质量设置 (18-23为高质量范围)
                '-preset', 'medium', # 编码速度与质量平衡
                '-c:a', 'copy',     # 保持音频不变
                '-y',
                rel_output_path
            ]
            
            logger.info(f"执行字幕烧录命令: {' '.join(cmd)}")
            
            # 添加详细日志记录
            log_file = f"{base_name}_subtitle_log.txt"
            with open(log_file, 'w', encoding='utf-8') as f:
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
                f.write(f"Command: {' '.join(cmd)}\n")
                f.write(f"Return code: {result.returncode}\n")
                f.write(f"STDOUT:\n{result.stdout}\n")
                f.write(f"STDERR:\n{result.stderr}\n")
            
            if result.returncode == 0 and os.path.exists(output_path):
                logger.info(f"字幕烧录成功: {output_path}")
                return output_path
            else:
                logger.error(f"字幕烧录失败: {result.stderr}")
                logger.error(f"详细日志已保存到: {log_file}")
                return None
                
        except Exception as e:
            logger.error(f"字幕烧录异常: {str(e)}")
            return None

    def get_job_progress(self, job_id: str) -> Optional[Dict]:
        """获取任务进度"""
        return self.job_progress.get(job_id)

    def get_all_jobs(self) -> Dict[str, Dict]:
        """获取所有任务状态"""
        return self.job_progress.copy()

    async def get_service_status(self) -> Dict:
        """获取服务状态"""
        try:
            services = {
                "speech_service": {
                    "name": getattr(settings, 'ASR_SERVICE', 'tencent'),
                    "status": "active" if self.speech_service else "disabled",
                    "enabled": getattr(settings, 'SUBTITLE_ENABLED', False),
                    "config": {
                        "service": getattr(settings, 'ASR_SERVICE', 'tencent')
                    }
                },
                "video_service": {
                    "name": settings.VIDEO_SERVICE,
                    "status": "active", 
                    "enabled": True,  # 视频服务默认启用
                    "config": {
                        "service": settings.VIDEO_SERVICE
                    }
                }
            }
            
            system_info = {
                "max_concurrent_jobs": settings.MAX_CONCURRENT_JOBS,
                "active_jobs": len([j for j in self.job_progress.values() if j.get("status") == "processing"]),
                "total_jobs": len(self.job_progress)
            }
            
            return {
                "success": True,
                "services": services,
                "active_jobs": system_info["active_jobs"],
                "total_jobs": system_info["total_jobs"],
                "system": system_info
            }
            
        except Exception as e:
            logger.error(f"获取服务状态失败: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "services": {},
                "active_jobs": 0,
                "total_jobs": 0
            }

# 创建全局实例
video_processor = VideoProcessorService()