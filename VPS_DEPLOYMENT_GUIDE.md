# VPS 部署指南 - 外教视频处理系统

本文档提供在云服务器（VPS）上部署完整视频处理系统的详细步骤。

---

## 一、准备工作

### 1.1 租用 VPS

推荐配置：
- **CPU**: 2核及以上
- **内存**: 4GB 及以上（视频处理需要）
- **硬盘**: 50GB 及以上（SSD 更佳）
- **操作系统**: Ubuntu 20.04/22.04 LTS 或 CentOS 7/8
- **带宽**: 5Mbps 及以上

推荐服务商：
- 阿里云 ECS（国内）
- 腾讯云 CVM（国内）
- AWS EC2（国际）
- Vultr / DigitalOcean（国际）

### 1.2 安全组/防火墙配置

开放端口：
- **22**: SSH 远程连接
- **8000**: FastAPI 服务端口（或通过 Nginx 反向代理使用 80/443）

---

## 二、快速部署（Docker 方式，推荐）

### 2.1 安装 Docker 和 Docker Compose

```bash
# 更新软件包
sudo apt update && sudo apt upgrade -y

# 安装 Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# 启动 Docker 服务
sudo systemctl start docker
sudo systemctl enable docker

# 安装 Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# 验证安装
docker --version
docker-compose --version
```

### 2.2 上传项目文件

```bash
# 方式 1: 使用 Git 克隆（推荐）
cd /home
git clone https://github.com/GHVBUGB/waijiaojianji-1-.git
cd waijiaojianji-1-

# 方式 2: 使用 SCP 上传本地文件
# 本地执行：
# scp -r C:\Users\guhongji\Desktop\44 root@你的服务器IP:/home/video-processor
```

### 2.3 配置环境变量

```bash
# 复制并编辑环境变量文件
cp .env.example .env
nano .env  # 或使用 vim .env

# 必须配置的关键变量：
# TENCENT_SECRET_ID=你的腾讯云SecretId
# TENCENT_SECRET_KEY=你的腾讯云SecretKey
# TENCENT_APP_ID=你的腾讯云AppId
# TENCENT_COS_BUCKET=你的COS桶名称
# TENCENT_REGION=ap-beijing
# 
# 讯飞 ASR（如果使用）
# XUNFEI_APP_ID=你的讯飞AppId
# XUNFEI_API_KEY=你的讯飞APIKey
# XUNFEI_API_SECRET=你的讯飞APISecret
#
# Redis（可选，多实例并发控制）
# REDIS_URL=redis://localhost:6379/0
```

### 2.4 构建并启动服务

```bash
# 构建 Docker 镜像
docker-compose build

# 启动服务（后台运行）
docker-compose up -d

# 查看日志
docker-compose logs -f

# 查看服务状态
docker-compose ps
```

### 2.5 验证服务

```bash
# 本地测试
curl http://localhost:8000/api/v1/health/

# 外部测试（浏览器访问）
http://你的服务器IP:8000
```

---

## 三、传统部署（不使用 Docker）

### 3.1 安装系统依赖

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install -y python3.11 python3.11-venv python3-pip ffmpeg

# CentOS/RHEL
sudo yum install -y python3.11 python3-pip ffmpeg
```

### 3.2 安装 Python 依赖

```bash
# 创建虚拟环境
python3.11 -m venv venv
source venv/bin/activate

# 安装依赖
pip install --upgrade pip
pip install -r requirements.txt
```

### 3.3 配置环境变量

```bash
cp .env.example .env
nano .env  # 填入你的密钥
```

### 3.4 启动服务

```bash
# 前台运行（测试）
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000

# 后台运行（生产）
nohup python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 > app.log 2>&1 &
```

### 3.5 配置系统服务（推荐）

创建 systemd 服务文件：

```bash
sudo nano /etc/systemd/system/video-processor.service
```

内容：

```ini
[Unit]
Description=Video Processor FastAPI Service
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/home/waijiaojianji-1-
Environment="PATH=/home/waijiaojianji-1-/venv/bin"
ExecStart=/home/waijiaojianji-1-/venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

启动服务：

```bash
sudo systemctl daemon-reload
sudo systemctl start video-processor
sudo systemctl enable video-processor
sudo systemctl status video-processor
```

---

## 四、配置 Nginx 反向代理（可选，推荐）

### 4.1 安装 Nginx

```bash
sudo apt install -y nginx
```

### 4.2 配置站点

```bash
sudo nano /etc/nginx/sites-available/video-processor
```

内容：

```nginx
server {
    listen 80;
    server_name 你的域名或IP;

    client_max_body_size 200M;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket 支持（如需要）
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        
        # 超时设置（视频处理时间长）
        proxy_connect_timeout 600;
        proxy_send_timeout 600;
        proxy_read_timeout 600;
    }

    location /static/ {
        alias /home/waijiaojianji-1-/app/static/;
    }

    location /outputs/ {
        alias /home/waijiaojianji-1-/outputs/;
    }
}
```

启用站点：

```bash
sudo ln -s /etc/nginx/sites-available/video-processor /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### 4.3 配置 SSL（推荐，使用 Let's Encrypt）

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d 你的域名
```

---

## 五、日常运维

### 5.1 查看日志

```bash
# Docker 方式
docker-compose logs -f

# 传统方式
tail -f logs/app.log
sudo journalctl -u video-processor -f
```

### 5.2 重启服务

```bash
# Docker 方式
docker-compose restart

# 传统方式
sudo systemctl restart video-processor
```

### 5.3 更新代码

```bash
# Docker 方式
git pull
docker-compose down
docker-compose build
docker-compose up -d

# 传统方式
git pull
sudo systemctl restart video-processor
```

### 5.4 清理临时文件

```bash
# 清理超过 7 天的上传和输出文件
find uploads -type f -mtime +7 -delete
find outputs -type f -mtime +7 -delete
find temp -type f -mtime +1 -delete
```

### 5.5 监控资源

```bash
# 查看容器资源占用（Docker）
docker stats

# 查看系统资源
htop
df -h
free -h
```

---

## 六、常见问题

### 6.1 端口被占用

```bash
# 查看占用 8000 端口的进程
sudo lsof -i :8000
# 或
sudo netstat -tulnp | grep 8000

# 杀死进程
sudo kill -9 进程ID
```

### 6.2 权限问题

```bash
# 确保目录权限正确
sudo chown -R $USER:$USER /home/waijiaojianji-1-
chmod -R 755 /home/waijiaojianji-1-
```

### 6.3 内存不足

- 增加系统 Swap：
```bash
sudo fallocate -l 4G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

### 6.4 FFmpeg 未安装

```bash
# Ubuntu
sudo apt install -y ffmpeg

# CentOS（需要 EPEL 仓库）
sudo yum install -y epel-release
sudo yum install -y ffmpeg
```

---

## 七、安全建议

1. **修改 SSH 端口**，禁用密码登录，只允许密钥认证
2. **配置防火墙**（ufw/firewalld），只开放必要端口
3. **定期更新系统**：`sudo apt update && sudo apt upgrade -y`
4. **使用 HTTPS**：配置 SSL 证书
5. **限制 API 访问**：在 Nginx 配置 IP 白名单或使用 API 密钥认证
6. **备份数据**：定期备份 `.env`、数据库（如有）、关键文件

---

## 八、性能优化

1. **增加并发处理数**：在 `.env` 中调整 `MAX_PARALLEL_JOBS`
2. **使用 Redis 缓存**：配置 `REDIS_URL` 用于任务队列和缓存
3. **优化腾讯云 COS**：使用 CDN 加速下载
4. **调整视频处理参数**：降低 CRF、使用更快的 preset（`fast`/`veryfast`）

---

## 需要帮助？

- 查看项目 README.md
- 查看日志文件排查错误
- 联系技术支持

---

**部署完成后，访问 `http://你的服务器IP:8000` 即可使用完整功能！**

