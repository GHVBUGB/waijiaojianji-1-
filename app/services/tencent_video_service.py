"""
腾讯云万象视频人像抠图服务 - 视频背景移除
使用腾讯云数据万象的SegmentVideoBody API
"""

import asyncio
import json
import logging
import os
import tempfile
import time
import base64
from typing import Dict
import requests
import xml.etree.ElementTree as ET
from datetime import datetime
import hashlib
import hmac
import urllib.parse
import urllib3

# 禁用SSL警告（用于解决网络环境SSL问题）
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

from app.config.settings import settings
from app.services.robust_cos_uploader import RobustCOSUploader

logger = logging.getLogger(__name__)

class TencentVideoService:
    """腾讯云万象视频人像抠图服务"""
    
    def __init__(self):
        self.secret_id = getattr(settings, 'TENCENT_SECRET_ID', None)
        self.secret_key = getattr(settings, 'TENCENT_SECRET_KEY', None)
        self.region = getattr(settings, 'TENCENT_REGION', 'ap-singapore')
        
        # 腾讯云万象配置
        self.bucket_name = getattr(settings, 'TENCENT_COS_BUCKET', None)
        self.app_id = getattr(settings, 'TENCENT_APP_ID', None)
        
        # 性能优化配置
        self.frame_skip = getattr(settings, 'TENCENT_FRAME_SKIP', 5)
        self.motion_detection = getattr(settings, 'TENCENT_MOTION_DETECTION', True)
        self.max_concurrent_jobs = getattr(settings, 'MAX_CONCURRENT_JOBS', 3)
        self.chunk_size = getattr(settings, 'UPLOAD_CHUNK_SIZE', 8 * 1024 * 1024)
        
        # 初始化健壮的COS上传器
        if self.secret_id and self.secret_key and self.bucket_name:
            self.cos_uploader = RobustCOSUploader(
                self.secret_id, 
                self.secret_key, 
                self.region, 
                self.bucket_name
            )
        else:
            self.cos_uploader = None
            logger.warning("腾讯云COS上传器初始化失败：缺少必要配置")
        
        if not self.secret_id or not self.secret_key:
            logger.warning("腾讯云视频服务未配置访问密钥")
        if not self.bucket_name:
            logger.warning("腾讯云万象服务需要配置COS存储桶")
    
    def _open_ai_bucket(self) -> bool:
        """调用万象 API: 开通 AI 内容识别（异步）服务并生成队列。
        POST https://<Bucket-APPID>.ci.<Region>.myqcloud.com/ai_bucket
        请求体为空。
        """
        ci_host = f"{self.bucket_name}.ci.{self.region}.myqcloud.com"
        url = f"https://{ci_host}/ai_bucket"
        headers = {
            'Authorization': self._generate_authorization("POST", "/ai_bucket"),
            'Host': ci_host,
            'Content-Type': 'application/xml',
            'Date': datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S GMT')
        }
        try:
            logger.info("🧩 尝试开通 AI 内容识别服务 (POST /ai_bucket)")
            response = requests.post(url, data=b"", headers=headers, timeout=30, verify=True)
            logger.info(f"🧩 开通AI服务响应: {response.status_code}")
            if response.status_code == 200:
                logger.info(f"🧩 开通AI服务结果: {response.text}")
                return True
            logger.error(f"🧩 开通AI服务失败: {response.status_code} - {response.text}")
            return False
        except Exception as e:
            logger.error(f"🧩 开通AI服务异常: {str(e)}")
            return False

    def _generate_authorization(self, method: str, uri: str, body: str = "", headers: dict = None) -> str:
        """生成腾讯云万象API授权签名"""
        if headers is None:
            headers = {}
        
        # 时间戳
        now = int(time.time())
        expired = now + 3600  # 1小时后过期
        
        # 生成 KeyTime
        key_time = f"{now};{expired}"
        
        # 生成 SignKey
        sign_key = hmac.new(
            self.secret_key.encode('utf-8'),
            key_time.encode('utf-8'),
            hashlib.sha1
        ).hexdigest()
        
        # 生成 HttpString - 万象API格式，需要包含host头
        http_string = f"{method.lower()}\n{uri}\n\nhost={self.bucket_name}.ci.{self.region}.myqcloud.com\n"
        
        # 生成 StringToSign
        string_to_sign = f"sha1\n{key_time}\n{hashlib.sha1(http_string.encode('utf-8')).hexdigest()}\n"
        
        # 生成 Signature
        signature = hmac.new(
            sign_key.encode('utf-8'),
            string_to_sign.encode('utf-8'),
            hashlib.sha1
        ).hexdigest()
        
        # 生成 Authorization - 万象API格式，需要包含host在header-list中
        authorization = (
            f"q-sign-algorithm=sha1&"
            f"q-ak={self.secret_id}&"
            f"q-sign-time={key_time}&"
            f"q-key-time={key_time}&"
            f"q-header-list=host&"
            f"q-url-param-list=&"
            f"q-signature={signature}"
        )
        
        return authorization
    
    def _cos_hosts(self) -> list:
        """按优先级返回可用的 COS 域名候选"""
        use_accelerate = os.getenv("TENCENT_COS_ACCELERATE", "false").lower() == "true"
        hosts = []
        
        # 全球加速（优先级最高）
        if use_accelerate:
            hosts.append(f"{self.bucket_name}.cos.accelerate.myqcloud.com")
        
        # 地域域名
        hosts.append(f"{self.bucket_name}.cos.{self.region}.myqcloud.com")
        
        # 备用域名
        hosts.append(f"{self.bucket_name}.cos.{self.region}.tencentcos.cn")
        
        return hosts
    
    async def _upload_to_cos(self, local_path: str, object_key: str):
        """使用健壮的COS上传器上传文件"""
        logger.info(f"📤 使用健壮上传器上传文件: {local_path} -> {object_key}")
        
        if not self.cos_uploader:
            raise Exception("COS上传器未初始化")
        
        success = await self.cos_uploader.upload_file(local_path, object_key)
        if not success:
            raise Exception("文件上传失败")
    
    async def _download_from_cos(self, object_key: str, local_path: str):
        """使用健壮的COS下载器下载文件"""
        logger.info(f"📥 使用健壮下载器下载文件: {object_key} -> {local_path}")
        
        if not self.cos_uploader:
            raise Exception("COS上传器未初始化")
        
        success = await self.cos_uploader.download_file(object_key, local_path)
        if not success:
            raise Exception("文件下载失败")
    
    def _activate_ai_queue(self, queue_id: str) -> bool:
        """将 AI 队列置为 Active 状态 (PUT /ai_queue/<queueId>)"""
        if not queue_id:
            return False
        ci_host = f"{self.bucket_name}.ci.{self.region}.myqcloud.com"
        url = f"https://{ci_host}/ai_queue/{queue_id}"
        headers = {
            'Authorization': self._generate_authorization("PUT", f"/ai_queue/{queue_id}"),
            'Host': ci_host,
            'Content-Type': 'application/xml',
            'Date': datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S GMT')
        }
        # 置为 Active，关闭回调
        body_xml = """
<Request>
    <Name>AI-Queue</Name>
    <State>Active</State>
    <NotifyConfig>
        <State>Off</State>
    </NotifyConfig>
</Request>
""".strip()
        try:
            logger.info(f"🛠️ 激活AI队列: {queue_id}")
            resp = requests.put(url, data=body_xml.encode('utf-8'), headers=headers, timeout=30, verify=True)
            logger.info(f"🛠️ 激活响应: {resp.status_code}")
            return resp.status_code == 200
        except Exception as e:
            logger.error(f"🛠️ 激活AI队列异常: {str(e)}")
            return False

    async def _get_queue_id(self) -> str:
        """获取万象服务的队列ID（使用 /ai_queue，优先选择 AIProcess 队列）"""
        logger.info("🔍 获取万象服务队列ID")
        
        ci_host = f"{self.bucket_name}.ci.{self.region}.myqcloud.com"
        url = f"https://{ci_host}/ai_queue"
        
        authorization = self._generate_authorization("GET", "/ai_queue")
        headers = {
            'Authorization': authorization,
            'Host': ci_host,
            'Date': datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S GMT')
        }
        
        try:
            response = requests.get(url, headers=headers, timeout=30, verify=True)
            logger.info(f"📡 队列查询响应: {response.status_code}")
            
            if response.status_code != 200:
                logger.warning(f"⚠️ 队列查询失败: {response.status_code}")
                return ""

            logger.info(f"📄 队列响应内容: {response.text}")
            root = ET.fromstring(response.content)

            ai_queue_id = None
            any_active_queue_id = None

            queue_list = root.find('.//QueueList')
            if queue_list is not None:
                logger.info("📋 找到队列列表")
                for queue in queue_list.findall('Queue'):
                    queue_id_el = queue.find('QueueId')
                    state_el = queue.find('State')
                    name_el = queue.find('Name')
                    queue_type_el = queue.find('QueueType') or queue.find('Category')

                    queue_id = queue_id_el.text if queue_id_el is not None else None
                    state = state_el.text if state_el is not None else 'Unknown'
                    name = name_el.text if name_el is not None else 'Unknown'
                    queue_type = queue_type_el.text if queue_type_el is not None else 'Unknown'

                    logger.info(f"📝 队列信息: ID={queue_id}, State={state}, Type={queue_type}, Name={name}")

                    if state == 'Paused' and queue_id and (queue_type == 'AIProcess'):
                        # 自动尝试激活
                        self._activate_ai_queue(queue_id)
                        # 激活后优先返回该队列
                        ai_queue_id = queue_id
                        break

                    if state == 'Active' and queue_id:
                        # 记录任一活跃队列
                        if any_active_queue_id is None:
                            any_active_queue_id = queue_id
                        # 优先选择 AIProcess
                        if queue_type == 'AIProcess':
                            ai_queue_id = queue_id
                            break

            if ai_queue_id:
                logger.info(f"✅ 选择 AIProcess 队列: {ai_queue_id}")
                return ai_queue_id

            if any_active_queue_id:
                logger.warning("⚠️ 未找到 AIProcess 队列，后续将不传 QueueId，避免误用 Transcoding 队列")
                return ""

            # 未找到任何队列，尝试自动开通 AI 服务
            logger.warning("⚠️ 未找到任何队列，自动尝试开通 AI 内容识别服务后重试查询队列")
            if self._open_ai_bucket():
                # 开通后等待几秒再查
                time.sleep(3)
                try:
                    response2 = requests.get(url, headers=headers, timeout=30, verify=True)
                    if response2.status_code == 200:
                        root2 = ET.fromstring(response2.content)
                        # 再次优先选择 AIProcess 队列
                        queue_list2 = root2.find('.//QueueList')
                        if queue_list2 is not None:
                            for q in queue_list2.findall('Queue'):
                                qid = q.findtext('QueueId')
                                qtype = q.findtext('QueueType') or q.findtext('Category')
                                qstate = q.findtext('State')
                                if qid and (qtype == 'AIProcess'):
                                    if qstate == 'Paused':
                                        self._activate_ai_queue(qid)
                                    logger.info(f"✅ 开通后获得 AIProcess 队列: {qid}")
                                    return qid
                except Exception:
                    pass
            logger.error("❌ 未找到任何可用队列，且自动开通失败或未生效。请在控制台启用‘AI 内容识别’并创建/启用 AIProcess 队列，或更换到支持地域的桶。")
            return ""

        except Exception as e:
            logger.error(f"💥 队列查询异常: {str(e)}")
            return ""

    async def _submit_ci_job(self, input_key: str, output_key: str, background_url: str = None) -> str:
        """提交万象API视频抠图任务"""
        logger.info(f"🎬 提交万象API任务: {input_key} -> {output_key}")
        
        # 获取队列ID（可能返回空字符串，表示不传 QueueId）
        queue_id = await self._get_queue_id()
        
        # 万象API的URL - 使用正确的域名格式
        ci_host = f"{self.bucket_name}.ci.{self.region}.myqcloud.com"
        url = f"https://{ci_host}/jobs"
        
        # 构建任务配置 - 使用 Combination 模式实现背景替换
        segment_config = {
            "SegmentType": "HumanSeg",
            "BinaryThreshold": "0.1"  # 降低阈值以保留更多细节
        }
        
        # 根据是否提供背景图片选择模式
        if background_url:
            segment_config["Mode"] = "Combination"  # 背景合成模式
            segment_config["BackgroundLogoUrl"] = background_url  # 根据官方文档使用正确的参数名称
            logger.info(f"🖼️ 使用背景合成模式，背景图片: {background_url}")
        else:
            segment_config["Mode"] = "Foreground"  # 前景模式
            logger.info("🎭 使用前景模式（无背景替换）")
        
        job_config = {
            "Tag": "SegmentVideoBody",
            "Input": {
                "Object": input_key
            },
            "Operation": {
                "SegmentVideoBody": segment_config,
                "Output": {
                    "Region": self.region,
                    "Bucket": self.bucket_name,
                    "Object": output_key,
                    "Format": "mp4"  # 明确指定输出格式
                }
            },
        }

        # 仅当发现 AIProcess 队列时才附加 QueueId
        if queue_id:
            job_config["QueueId"] = queue_id
        
        # 生成签名
        authorization = self._generate_authorization("POST", "/jobs")
        headers = {
            'Authorization': authorization,
            'Host': ci_host,
            'Content-Type': 'application/xml',
            'Date': datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S GMT')
        }
        
        # 转换为XML格式
        xml_data = self._dict_to_xml(job_config, "Request")
        logger.info(f"📄 提交的XML数据: {xml_data}")
        
        try:
            response = requests.post(url, data=xml_data, headers=headers, timeout=30, verify=True)
            logger.info(f"📡 万象API响应: {response.status_code}")
            logger.info(f"📄 万象API响应内容: {response.text}")
            
            if response.status_code == 200:
                # 解析响应获取JobId
                root = ET.fromstring(response.content)
                job_id = root.find('.//JobId').text if root.find('.//JobId') is not None else None
                
                if job_id:
                    logger.info(f"✅ 任务提交成功: {job_id}")
                    return job_id
                else:
                    logger.error(f"❌ 无法获取JobId: {response.text}")
                    raise Exception("无法获取JobId")
            else:
                logger.error(f"❌ 任务提交失败: {response.status_code} - {response.text}")
                try:
                    err_root = ET.fromstring(response.text)
                    err_code = err_root.findtext('.//Code', default='Unknown')
                    err_msg = err_root.findtext('.//Message', default='')
                except Exception:
                    err_code, err_msg = 'Unknown', response.text

                if err_code == 'AIBucketUnBinded':
                    logger.warning("⚠️ 检测到 AIBucketUnBinded，尝试自动开通 AI 内容识别服务后重试提交任务")
                    if self._open_ai_bucket():
                        # 等待几秒让配置生效后重试一次
                        time.sleep(3)
                        retry_resp = requests.post(url, data=xml_data, headers=headers, timeout=30, verify=True)
                        logger.info(f"📡 重试提交响应: {retry_resp.status_code}")
                        logger.info(f"📄 重试响应内容: {retry_resp.text}")
                        if retry_resp.status_code == 200:
                            root_retry = ET.fromstring(retry_resp.content)
                            job_id_retry = root_retry.findtext('.//JobId')
                            if job_id_retry:
                                logger.info(f"✅ 重试提交成功: {job_id_retry}")
                                return job_id_retry
                    raise Exception("该存储桶未开通或未绑定 数据万象 AI 内容识别与视频人像抠图，请在控制台为桶开启‘数据万象’，启用‘AI 内容识别’，并创建/启用类型为 AIProcess 的队列；若地域不支持该能力，请在支持地域新建桶并更新配置")

                raise Exception(f"任务提交失败: {response.status_code}, Code={err_code}, Message={err_msg}")
                
        except Exception as e:
            logger.error(f"💥 万象API异常: {str(e)}")
            raise Exception(f"万象API调用失败: {str(e)}")
    
    def _dict_to_xml(self, data: dict, root_name: str = "Request") -> str:
        """将字典转换为XML格式"""
        def build_xml(element, obj):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    sub_element = ET.SubElement(element, key)
                    build_xml(sub_element, value)
            elif isinstance(obj, list):
                for item in obj:
                    build_xml(element, item)
            else:
                element.text = str(obj)
        
        root = ET.Element(root_name)
        build_xml(root, data)
        return ET.tostring(root, encoding='unicode')
    
    async def _wait_for_job_completion(self, job_id: str, timeout: int = 300) -> bool:
        """等待任务完成"""
        logger.info(f"⏳ 等待任务完成: {job_id}")
        
        ci_host = f"{self.bucket_name}.ci.{self.region}.myqcloud.com"
        url = f"https://{ci_host}/jobs/{job_id}"
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                authorization = self._generate_authorization("GET", f"/jobs/{job_id}")
                headers = {
                    'Authorization': authorization,
                    'Host': ci_host,
                    'Date': datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S GMT')
                }
                
                response = requests.get(url, headers=headers, timeout=30, verify=True)
                
                if response.status_code == 200:
                    root = ET.fromstring(response.content)
                    state = root.find('.//State').text if root.find('.//State') is not None else "Unknown"
                    
                    logger.info(f"📊 任务状态: {state}")
                    
                    if state == "Success":
                        logger.info(f"✅ 任务完成成功: {job_id}")
                        return True
                    elif state == "Failed":
                        error_msg = root.find('.//Message').text if root.find('.//Message') is not None else "未知错误"
                        logger.error(f"❌ 任务失败: {error_msg}")
                        return False
                    elif state in ["Submitted", "Running"]:
                        logger.info(f"🔄 任务进行中: {state}")
                        await asyncio.sleep(10)  # 等待10秒后再次检查
                    else:
                        logger.warning(f"⚠️ 未知状态: {state}")
                        await asyncio.sleep(5)
                else:
                    logger.warning(f"⚠️ 状态查询失败: {response.status_code}")
                    await asyncio.sleep(5)
                    
            except Exception as e:
                logger.error(f"💥 状态查询异常: {str(e)}")
                await asyncio.sleep(5)
        
        logger.error(f"⏰ 任务超时: {job_id}")
        return False
    
    async def _process_with_ci_api(self, video_file_path: str, output_dir: str, background_url: str = None) -> str:
        """使用万象API处理视频"""
        logger.info(f"🎬 开始万象API处理: {video_file_path}")
        
        # 生成唯一的对象键
        timestamp = int(time.time())
        input_key = f"input/video_{timestamp}.mp4"
        output_key = f"output/processed_{timestamp}.mp4"
        
        try:
            # 步骤1: 上传视频到COS
            logger.info("📤 步骤1: 上传视频到COS")
            await self._upload_to_cos(video_file_path, input_key)
            
            # 步骤2: 提交万象API任务
            logger.info("🎬 步骤2: 提交万象API任务")
            job_id = await self._submit_ci_job(input_key, output_key, background_url)
            
            # 步骤3: 等待任务完成
            logger.info("⏳ 步骤3: 等待任务完成")
            success = await self._wait_for_job_completion(job_id)
            
            if not success:
                raise Exception("万象API处理失败")
            
            # 步骤4: 下载处理结果
            logger.info("📥 步骤4: 下载处理结果")
            output_path = os.path.join(output_dir, f"ci_processed_{timestamp}.mp4")
            await self._download_from_cos(output_key, output_path)
            
            # 步骤5: 标准化视频格式以确保字幕兼容性
            logger.info("🔧 步骤5: 标准化视频格式")
            normalized_path = output_path.replace(".mp4", "_normalized.mp4")
            await self._normalize_video_for_subtitles(output_path, normalized_path)
            
            # 替换为标准化后的视频
            if os.path.exists(normalized_path) and os.path.getsize(normalized_path) > 0:
                import shutil
                shutil.move(normalized_path, output_path)
                logger.info(f"✅ 视频已标准化: {output_path}")
            
            logger.info(f"✅ 万象API处理完成: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"💥 万象API处理失败: {str(e)}")
            raise e
    
    async def _normalize_video_for_subtitles(self, input_video: str, output_video: str) -> None:
        """标准化视频格式以确保字幕烧录兼容性"""
        import subprocess
        import shutil
        
        ffmpeg = os.getenv("FFMPEG_PATH") or shutil.which("ffmpeg") or r"C:\ffmpeg\bin\ffmpeg.exe"
        
        # 重新编码为标准H.264+AAC，确保元数据完整
        cmd = [
            ffmpeg,
            "-i", input_video,
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "20",
            "-c:a", "aac",
            "-b:a", "128k",
            "-movflags", "+faststart",
            "-y", output_video
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            if result.returncode == 0:
                logger.info(f"视频标准化成功: {output_video}")
            else:
                logger.error(f"视频标准化失败: {result.stderr}")
        except Exception as e:
            logger.error(f"视频标准化异常: {str(e)}")
    
    async def upload_background_image(self, image_file_path: str) -> str:
        """
        上传背景图片到COS存储桶
        
        Args:
            image_file_path: 背景图片文件路径
            
        Returns:
            str: 背景图片的COS URL
        """
        try:
            logger.info(f"📤 开始上传背景图片到COS: {image_file_path}")
            
            # 检查文件是否存在
            if not os.path.exists(image_file_path):
                raise FileNotFoundError(f"背景图片文件不存在: {image_file_path}")
            
            # 生成唯一的对象键
            timestamp = int(time.time())
            file_ext = os.path.splitext(image_file_path)[1].lower()
            background_key = f"backgrounds/bg_{timestamp}{file_ext}"
            
            # 上传到COS
            await self._upload_to_cos(image_file_path, background_key)
            
            # 构建COS URL
            background_url = f"https://{self.bucket_name}.cos.{self.region}.myqcloud.com/{background_key}"
            
            logger.info(f"✅ 背景图片上传成功: {background_url}")
            return background_url
            
        except Exception as e:
            logger.error(f"💥 背景图片上传失败: {str(e)}")
            raise Exception(f"背景图片上传失败: {str(e)}")
    
    async def remove_background(self, video_file_path: str, output_dir: str, quality: str = "medium", background_url: str = None, background_file_path: str = None) -> Dict:
        """
        使用腾讯云万象API移除视频背景
        
        Args:
            video_file_path: 输入视频文件路径
            output_dir: 输出目录
            quality: 处理质量（暂未使用）
            background_url: 背景图片URL（用于Combination模式）
            background_file_path: 背景图片文件路径（会自动上传到COS）
        """
        start_time = time.time()
        
        try:
            logger.info(f"开始使用腾讯云万象API处理视频背景移除: {video_file_path}")
            
            # 检查文件是否存在
            if not os.path.exists(video_file_path):
                raise FileNotFoundError(f"视频文件不存在: {video_file_path}")
            
            # 检查配置
            if not self.bucket_name:
                raise Exception("未配置COS存储桶")
            
            original_size = os.path.getsize(video_file_path)
            logger.info(f"原始文件大小: {original_size / (1024*1024):.2f}MB")
            
            # 处理背景图片
            final_background_url = background_url
            if background_file_path and not background_url:
                # 如果提供了背景文件路径但没有URL，先上传背景图片
                logger.info("🖼️ 检测到背景图片文件，开始上传到COS")
                final_background_url = await self.upload_background_image(background_file_path)
            
            # 使用万象API处理视频
            output_path = await self._process_with_ci_api(video_file_path, output_dir, final_background_url)
            
            processed_size = os.path.getsize(output_path) if os.path.exists(output_path) else 0
            processing_time = time.time() - start_time
            
            logger.info(f"腾讯云万象背景移除完成: {output_path}")
            return {
                "success": True,
                "output_path": output_path,
                "original_size": original_size,
                "processed_size": processed_size,
                "processing_time": processing_time,
                "service": "tencent_ci",
                "cost_estimate": "按万象API计费",
                "background_mode": "Combination" if final_background_url else "Foreground",
                "background_url": final_background_url
            }
            
        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"腾讯云万象背景移除失败: {str(e)}")
            return {
                "success": False,
                "output_path": "",
                "original_size": 0,
                "processed_size": 0,
                "processing_time": processing_time,
                "service": "failed",
                "error": str(e)
            }