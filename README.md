# 外教视频处理系统

基于 FastAPI 的外教自我介绍视频处理系统，集成 **OpenAI Whisper API**（语音转文字）和 **Unscreen API**（视频人像抠像）功能。

## 🎯 核心功能

- 🎥 **视频人像背景移除** - 自动移除视频背景，生成透明背景视频
- 🎤 **多语言语音转文字** - 支持多种语言的语音识别和转录
- 📝 **自动生成字幕** - 生成带时间戳的字幕文件
- 🔄 **异步处理** - 支持批量视频处理和进度跟踪
- 📊 **处理进度实时跟踪** - 实时查看处理状态和进度

## 📁 项目结构

```
teacher_video_processor/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI 应用入口
│   ├── config/
│   │   ├── __init__.py
│   │   └── settings.py         # 配置文件
│   ├── models/
│   │   ├── __init__.py
│   │   ├── video.py           # 视频相关模型
│   │   └── response.py        # API响应模型
│   ├── services/
│   │   ├── __init__.py
│   │   ├── video_processor.py  # 主处理服务
│   │   ├── background_removal.py  # 背景移除服务
│   │   └── speech_to_text.py   # 语音转文字服务
│   ├── api/
│   │   ├── __init__.py
│   │   ├── routes/
│   │   │   ├── __init__.py
│   │   │   ├── video.py       # 视频处理路由
│   │   │   └── health.py      # 健康检查
│   │   └── dependencies.py    # 依赖注入
│   └── utils/
│       ├── __init__.py
│       ├── file_handler.py    # 文件处理工具
│       └── logger.py          # 日志配置
├── uploads/                   # 上传目录
├── outputs/                   # 输出目录
├── temp/                      # 临时文件目录
├── logs/                      # 日志目录
├── requirements.txt           # Python依赖
├── .env                       # 环境变量
├── .env.example              # 环境变量示例
├── docker-compose.yml        # Docker配置
├── Dockerfile               # Docker镜像
└── README.md               # 项目说明
```

## 🚀 快速开始

### 方式一：一键启动（推荐）

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 一键配置和启动
python quick_start.py
```

该脚本会自动：
- ✅ 检查系统环境
- ✅ 验证依赖包
- ✅ 引导配置 API Keys
- ✅ 测试 API 连接
- ✅ 启动服务

### 方式二：手动配置

#### 1. 环境要求

- Python >= 3.9
- FFmpeg >= 4.0
- OpenAI API Key
- Unscreen API Key

#### 2. 安装依赖

```bash
# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/macOS
# venv\Scripts\activate     # Windows

# 安装Python依赖
pip install -r requirements.txt

# 安装系统依赖（Ubuntu/Debian）
sudo apt update && sudo apt install ffmpeg

# 安装系统依赖（macOS）
brew install ffmpeg
```

#### 3. 配置 API Keys

```bash
# 使用配置工具（推荐）
python setup_api_keys.py

# 或手动配置
cp .env.example .env
nano .env  # 编辑配置文件
```

**获取 API Keys：**
- **OpenAI API Key**: [OpenAI Platform](https://platform.openai.com/api-keys) 
- **Unscreen API Key**: [Unscreen API](https://www.unscreen.com/api)

详细配置指南请查看：[API_INTEGRATION_GUIDE.md](API_INTEGRATION_GUIDE.md)

#### 4. 测试配置

```bash
# 测试 API 集成
python test_api_integration.py

# 测试服务运行
python test_api.py
```

#### 5. 启动服务

```bash
# 开发环境
python -m app.main

# 或使用 uvicorn
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

访问 `http://localhost:8000` 查看系统状态页面。

## 📖 API 使用

### 主要接口

#### 1. 上传并处理视频
```bash
curl -X POST "http://localhost:8000/api/v1/video/upload-and-process" \
  -F "file=@teacher_video.mp4" \
  -F "teacher_name=John Smith" \
  -F "language_hint=en"
```

#### 2. 查看处理进度
```bash
curl http://localhost:8000/api/v1/video/progress/{job_id}
```

#### 3. 下载处理后的视频
```bash
curl http://localhost:8000/api/v1/video/download/{job_id} -o processed_video.mp4
```

#### 4. 获取完整处理结果
```bash
curl http://localhost:8000/api/v1/video/results/{job_id}
```

#### 5. 健康检查
```bash
curl http://localhost:8000/api/v1/health/
```

### 响应格式

所有API响应都遵循统一的格式：

```json
{
  "success": true,
  "message": "操作成功",
  "data": {
    // 具体数据
  },
  "error": null,
  "timestamp": "2024-01-01T12:00:00Z"
}
```

## 🐳 Docker 部署

```bash
# 构建并启动服务
docker-compose up -d

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down
```

## ⚙️ 配置选项

在 `.env` 文件中可以配置以下选项：

```bash
# API配置
OPENAI_API_KEY=sk-your-openai-api-key-here
UNSCREEN_API_KEY=your-unscreen-api-key-here

# 应用配置
ENVIRONMENT=development
HOST=0.0.0.0
PORT=8000
LOG_LEVEL=INFO

# 文件限制
MAX_VIDEO_SIZE=104857600  # 100MB
MAX_CONCURRENT_JOBS=3

# 存储目录
UPLOAD_DIR=./uploads
OUTPUT_DIR=./outputs
TEMP_DIR=./temp
```

## 🔧 开发指南

### 添加新功能

1. **模型定义**: 在 `app/models/` 中添加新的数据模型
2. **服务逻辑**: 在 `app/services/` 中实现业务逻辑
3. **API路由**: 在 `app/api/routes/` 中添加新的接口
4. **工具函数**: 在 `app/utils/` 中添加通用工具

### 错误处理

系统实现了全面的错误处理机制：
- 自动重试机制
- 详细的错误日志
- 用户友好的错误信息
- 资源清理机制

### 日志配置

日志文件保存在 `logs/` 目录下，按日期分割。可以通过 `LOG_LEVEL` 环境变量调整日志级别。

## 📊 性能优化

### 建议配置

```python
# 在 settings.py 中调整
MAX_CONCURRENT_JOBS = 3  # 根据服务器性能调整
MAX_VIDEO_SIZE = 100 * 1024 * 1024  # 100MB
AUDIO_SAMPLE_RATE = 16000  # Whisper 最佳采样率
```

### 监控指标

- 处理队列长度
- 平均处理时间
- API 调用成功率
- 磁盘空间使用
- 内存使用情况

## 🐛 常见问题

### 1. FFmpeg 相关问题

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install ffmpeg

# 验证安装
ffmpeg -version
```

### 2. API Key 问题

```bash
# 检查环境变量
echo $OPENAI_API_KEY
echo $UNSCREEN_API_KEY

# 验证 API Key 有效性
curl -H "Authorization: Bearer $OPENAI_API_KEY" \
  https://api.openai.com/v1/models
```

### 3. 文件权限问题

```bash
# 设置目录权限
chmod 755 uploads outputs temp
```

## 🔒 安全注意事项

1. **API Key 安全**: 不要将 API Keys 提交到代码仓库
2. **文件上传安全**: 系统会对上传文件进行验证
3. **访问控制**: 在生产环境中应该添加身份验证
4. **资源限制**: 合理配置文件大小和处理并发数

## 📄 许可证

此项目基于 MIT 许可证开源。

## 🤝 贡献

欢迎提交 Issue 和 Pull Request 来改进这个项目。

## 📞 支持

如有问题，请查看日志文件或在项目仓库中提交 Issue。