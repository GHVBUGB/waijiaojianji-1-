"""
健壮的腾讯云COS上传器 - 解决所有可能的上传问题
"""

import asyncio
import hashlib
import hmac
import logging
import os
import time
import socket
import requests
from datetime import datetime, timezone
from typing import List, Dict, Optional
import urllib3
from urllib.parse import quote
import json

# 禁用SSL警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger(__name__)

class RobustCOSUploader:
    """健壮的COS上传器"""
    
    def __init__(self, secret_id: str, secret_key: str, region: str, bucket: str):
        self.secret_id = secret_id
        self.secret_key = secret_key
        self.region = region
        self.bucket = bucket
        
        # 多域名策略 - 只保留有效域名
        self.domains = [
            f"{bucket}.cos.{region}.tencentcos.cn",  # 这个域名工作正常
            f"{bucket}.cos.{region}.myqcloud.com"    # 备用域名
        ]
        
        # 重试配置
        self.max_retries = 5
        self.retry_delays = [1, 2, 4, 8, 16]  # 指数退避
        self.timeout_configs = [30, 60, 120, 180, 300]  # 递增超时
        
    def _get_utc_timestamp(self) -> int:
        """获取UTC时间戳，避免时区问题"""
        return int(datetime.now(timezone.utc).timestamp())
    
    def _generate_authorization(self, method: str, uri: str, host: str) -> str:
        """生成COS授权签名 - 修复时间戳和签名问题"""
        try:
            # 使用UTC时间避免时区问题
            now = self._get_utc_timestamp()
            expired = now + 3600
            
            key_time = f"{now};{expired}"
            
            # 生成SignKey
            sign_key = hmac.new(
                self.secret_key.encode('utf-8'),
                key_time.encode('utf-8'),
                hashlib.sha1
            ).hexdigest()
            
            # 规范化URI，处理特殊字符
            normalized_uri = quote(uri, safe='/')
            
            # 生成HttpString - 严格按照腾讯云规范
            http_string = f"{method.lower()}\n{normalized_uri}\n\nhost={host.lower()}\n"
            
            # 生成StringToSign
            string_to_sign = f"sha1\n{key_time}\n{hashlib.sha1(http_string.encode('utf-8')).hexdigest()}\n"
            
            # 生成Signature
            signature = hmac.new(
                sign_key.encode('utf-8'),
                string_to_sign.encode('utf-8'),
                hashlib.sha1
            ).hexdigest()
            
            # 生成Authorization
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
            
        except Exception as e:
            logger.error(f"签名生成失败: {e}")
            raise
    
    def _test_network_connectivity(self, host: str) -> bool:
        """测试网络连通性"""
        try:
            # DNS解析测试
            socket.gethostbyname(host)
            
            # TCP连接测试
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(10)
            result = sock.connect_ex((host, 80))
            sock.close()
            
            return result == 0
        except Exception:
            return False
    
    def _get_optimal_domains(self) -> List[str]:
        """获取最优域名列表"""
        logger.info("🔍 测试域名连通性...")
        
        available_domains = []
        for domain in self.domains:
            if self._test_network_connectivity(domain):
                available_domains.append(domain)
                logger.info(f"✅ 域名可用: {domain}")
            else:
                logger.warning(f"❌ 域名不可用: {domain}")
        
        if not available_domains:
            logger.warning("⚠️ 所有域名都不可用，使用原始列表")
            return self.domains
        
        return available_domains
    
    def _prepare_headers(self, host: str, content_length: int, content_type: str = None) -> Dict[str, str]:
        """准备请求头"""
        headers = {
            'Host': host,
            'Date': datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S GMT'),
            'Content-Length': str(content_length),
            'User-Agent': 'robust-cos-uploader/1.0'
        }
        
        if content_type:
            headers['Content-Type'] = content_type
        else:
            headers['Content-Type'] = 'application/octet-stream'
        
        return headers
    
    def _get_content_type(self, file_path: str) -> str:
        """根据文件扩展名获取Content-Type"""
        ext = os.path.splitext(file_path)[1].lower()
        content_types = {
            '.mp4': 'video/mp4',
            '.avi': 'video/x-msvideo',
            '.mov': 'video/quicktime',
            '.mkv': 'video/x-matroska',
            '.wmv': 'video/x-ms-wmv',
            '.flv': 'video/x-flv',
            '.webm': 'video/webm'
        }
        return content_types.get(ext, 'application/octet-stream')
    
    def _chunk_upload(self, file_path: str, url: str, headers: Dict[str, str], chunk_size: int = 8*1024*1024) -> requests.Response:
        """分块上传大文件"""
        file_size = os.path.getsize(file_path)
        
        if file_size <= chunk_size:
            # 小文件直接上传
            with open(file_path, 'rb') as f:
                return requests.put(url, data=f, headers=headers, timeout=300, verify=False)
        
        # 大文件分块上传（简化版，实际应该用multipart upload）
        logger.info(f"📦 大文件分块上传: {file_size / (1024*1024):.2f}MB")
        
        with open(file_path, 'rb') as f:
            return requests.put(url, data=f, headers=headers, timeout=600, verify=False)
    
    async def upload_file(self, local_path: str, object_key: str) -> bool:
        """健壮的文件上传"""
        logger.info(f"📤 开始健壮上传: {local_path} -> {object_key}")
        
        # 检查文件
        if not os.path.exists(local_path):
            raise FileNotFoundError(f"文件不存在: {local_path}")
        
        file_size = os.path.getsize(local_path)
        content_type = self._get_content_type(local_path)
        
        logger.info(f"📁 文件信息: {file_size / (1024*1024):.2f}MB, {content_type}")
        
        # 文件大小检查
        if file_size > 5 * 1024 * 1024 * 1024:  # 5GB
            raise ValueError("文件过大，超过5GB限制")
        
        # 获取可用域名
        available_domains = self._get_optimal_domains()
        
        # 多域名多重试策略
        for retry_count in range(self.max_retries):
            for domain_index, domain in enumerate(available_domains):
                try:
                    logger.info(f"📶 尝试 {retry_count+1}/{self.max_retries} - 域名 {domain_index+1}/{len(available_domains)}: {domain}")
                    
                    # 构建URL和签名
                    normalized_key = quote(object_key, safe='/')
                    url = f"http://{domain}/{normalized_key}"
                    uri = f"/{normalized_key}"
                    
                    # 生成签名
                    authorization = self._generate_authorization("PUT", uri, domain)
                    
                    # 准备请求头
                    headers = self._prepare_headers(domain, file_size, content_type)
                    headers['Authorization'] = authorization
                    
                    # 设置代理
                    proxies = {}
                    if os.getenv('HTTP_PROXY'):
                        proxies['http'] = os.getenv('HTTP_PROXY')
                    if os.getenv('HTTPS_PROXY'):
                        proxies['https'] = os.getenv('HTTPS_PROXY')
                    
                    # 动态超时时间
                    timeout = self.timeout_configs[min(retry_count, len(self.timeout_configs)-1)]
                    
                    # 执行上传
                    start_time = time.time()
                    
                    if file_size > 100 * 1024 * 1024:  # 100MB以上使用分块上传
                        response = self._chunk_upload(local_path, url, headers)
                    else:
                        with open(local_path, 'rb') as f:
                            response = requests.put(
                                url, 
                                data=f, 
                                headers=headers, 
                                timeout=timeout,
                                verify=False,
                                proxies=proxies if proxies else None
                            )
                    
                    upload_time = time.time() - start_time
                    speed = file_size / upload_time / 1024 / 1024  # MB/s
                    
                    logger.info(f"📡 响应: {response.status_code}, 用时: {upload_time:.2f}s, 速度: {speed:.2f}MB/s")
                    
                    if response.status_code in [200, 201]:
                        logger.info(f"✅ 上传成功: {object_key}")
                        return True
                    elif response.status_code == 403:
                        logger.error(f"❌ 权限错误: {response.text}")
                        # 权限错误不重试
                        raise PermissionError(f"COS权限错误: {response.text}")
                    elif response.status_code == 404:
                        logger.error(f"❌ 存储桶不存在: {response.text}")
                        raise ValueError(f"存储桶不存在: {self.bucket}")
                    else:
                        logger.warning(f"⚠️ 上传失败: {response.status_code} - {response.text}")
                        
                except requests.exceptions.Timeout:
                    logger.warning(f"⏰ 上传超时: {domain} (超时: {timeout}s)")
                except requests.exceptions.ConnectionError as e:
                    logger.warning(f"🌐 连接错误: {domain} - {e}")
                except Exception as e:
                    logger.error(f"💥 上传异常: {domain} - {e}")
            
            # 重试延迟
            if retry_count < self.max_retries - 1:
                delay = self.retry_delays[min(retry_count, len(self.retry_delays)-1)]
                logger.info(f"⏳ 等待 {delay}s 后重试...")
                await asyncio.sleep(delay)
        
        logger.error("❌ 所有上传尝试均失败")
        return False
    
    async def download_file(self, object_key: str, local_path: str) -> bool:
        """健壮的文件下载"""
        logger.info(f"📥 开始下载: {object_key} -> {local_path}")
        
        available_domains = self._get_optimal_domains()
        
        for domain in available_domains:
            try:
                normalized_key = quote(object_key, safe='/')
                url = f"http://{domain}/{normalized_key}"
                uri = f"/{normalized_key}"
                
                authorization = self._generate_authorization("GET", uri, domain)
                headers = {
                    'Authorization': authorization,
                    'Host': domain,
                    'Date': datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S GMT')
                }
                
                response = requests.get(url, headers=headers, timeout=300, verify=False, stream=True)
                
                if response.status_code == 200:
                    os.makedirs(os.path.dirname(local_path), exist_ok=True)
                    
                    with open(local_path, 'wb') as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            f.write(chunk)
                    
                    logger.info(f"✅ 下载成功: {object_key}")
                    return True
                else:
                    logger.warning(f"⚠️ 下载失败: {domain} - {response.status_code}")
                    
            except Exception as e:
                logger.error(f"💥 下载异常: {domain} - {e}")
        
        logger.error("❌ 所有下载尝试均失败")
        return False
