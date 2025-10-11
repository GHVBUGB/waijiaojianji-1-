# 🚀 API 服务集成指南

本指南详细介绍如何获取和配置 **OpenAI Whisper** 和 **Unscreen API** 服务。

## 📋 目录

- [OpenAI Whisper 集成](#openai-whisper-集成)
- [Unscreen API 集成](#unscreen-api-集成)
- [环境变量配置](#环境变量配置)
- [验证配置](#验证配置)
- [常见问题](#常见问题)

---

## 🎤 OpenAI Whisper 集成

### 1. 获取 OpenAI API Key

#### 步骤 1: 注册 OpenAI 账户
1. 访问 [OpenAI Platform](https://platform.openai.com/)
2. 点击 "Sign up" 注册新账户或使用现有账户登录
3. 验证邮箱地址

#### 步骤 2: 创建 API Key
1. 登录后，点击右上角头像
2. 选择 "View API keys" 或直接访问：https://platform.openai.com/api-keys
3. 点击 "Create new secret key"
4. 为 API Key 命名（如：`video-processor-key`）
5. **重要**: 复制生成的 API Key 并安全保存（格式：`sk-...`）

#### 步骤 3: 账户充值
1. 访问 [Billing 页面](https://platform.openai.com/account/billing)
2. 点击 "Add payment method" 添加付款方式
3. 充值账户（建议至少 $5-$10）

#### 💰 Whisper API 定价
- **音频转录**: $0.006 / 分钟
- **音频翻译**: $0.006 / 分钟
- 示例：10分钟视频转录费用 ≈ $0.06

### 2. Whisper 功能特点

✅ **已实现功能**：
- 多语言自动检测（99+ 种语言）
- 高质量语音转文字
- 精确时间戳分割
- 自动音频提取
- 翻译成英文功能

✅ **支持的主要语言**：
```
中文 (zh)    英文 (en)    西班牙文 (es)
法文 (fr)    德文 (de)    日文 (ja)
韩文 (ko)    俄文 (ru)    意大利文 (it)
葡萄牙文 (pt) 阿拉伯文 (ar) 印地文 (hi)
```

---

## 🎬 Unscreen API 集成

### 1. 获取 Unscreen API Key

#### 步骤 1: 注册 Unscreen 账户
1. 访问 [Unscreen.com](https://www.unscreen.com/)
2. 点击右上角 "Sign Up" 注册账户
3. 验证邮箱地址

#### 步骤 2: 订阅 API 计划
1. 登录后访问 [API 页面](https://www.unscreen.com/api)
2. 点击 "Get API Access"
3. 选择适合的订阅计划：

| 计划 | 价格/月 | 视频数量 | 适用场景 |
|------|---------|----------|----------|
| **Basic** | $9.99 | 50 clips | 个人用户/小型项目 |
| **Pro** | $19.99 | 200 clips | 中小企业/频繁使用 |
| **Business** | $39.99 | 500 clips | 大型项目/商业用途 |
| **Enterprise** | 定制 | 无限制 | 企业级应用 |

#### 步骤 3: 获取 API Key
1. 订阅后，在 Dashboard 中找到 "API Keys" 部分
2. 复制您的 API Key（格式：`xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`）

### 2. Unscreen 功能特点

✅ **已实现功能**：
- AI 驱动的人像背景移除
- 边缘增强处理
- 透明通道 (Alpha Channel) 输出
- 多种视频格式支持
- 高质量输出（保持原始分辨率）

✅ **支持的视频格式**：
```
MP4, MOV, AVI, MKV, WMV, FLV
最大文件大小: 500MB
最大时长: 30分钟
分辨率: 最高 4K
```

---

## ⚙️ 环境变量配置

### 1. 创建配置文件

在项目根目录创建 `.env` 文件：

```bash
# 复制示例配置文件
cp .env.example .env

# 编辑配置文件
nano .env  # Linux/macOS
# notepad .env  # Windows
```

### 2. 配置 API Keys

```bash
# ==============================================
# API 配置 (必需)
# ==============================================

# OpenAI Whisper API Key
OPENAI_API_KEY=sk-your-actual-openai-api-key-here

# Unscreen API Key  
UNSCREEN_API_KEY=your-actual-unscreen-api-key-here

# ==============================================
# 应用配置
# ==============================================

ENVIRONMENT=development
HOST=0.0.0.0
PORT=8000
LOG_LEVEL=INFO

# ==============================================
# 文件处理配置
# ==============================================

UPLOAD_DIR=./uploads
OUTPUT_DIR=./outputs  
TEMP_DIR=./temp

# 文件大小限制: 100MB
MAX_VIDEO_SIZE=104857600

# 并发任务数量
MAX_CONCURRENT_JOBS=3

# 音频采样率 (Whisper 推荐)
AUDIO_SAMPLE_RATE=16000

# 视频输出格式
VIDEO_OUTPUT_FORMAT=mp4
```

### 3. 安全注意事项

🔒 **重要安全提醒**：

1. **不要将 API Keys 提交到代码仓库**
   ```bash
   # 确保 .env 文件在 .gitignore 中
   echo ".env" >> .gitignore
   ```

2. **定期轮换 API Keys**
   - 建议每 3-6 个月更换一次
   - 如果怀疑泄露，立即更换

3. **限制 API Key 权限**
   - 只授予必要的权限
   - 设置使用限额

---

## ✅ 验证配置

### 1. 验证 OpenAI API Key

```bash
# 使用 curl 测试
curl -H "Authorization: Bearer $OPENAI_API_KEY" \
  https://api.openai.com/v1/models
```

### 2. 验证 Unscreen API Key

```bash
# 检查账户余额
curl -H "Authorization: Bearer $UNSCREEN_API_KEY" \
  https://api.unscreen.com/v1.0/account/credits
```

### 3. 运行系统测试

```bash
# 启动应用
python -m app.main

# 测试健康检查
curl http://localhost:8000/api/v1/health/

# 测试 API Keys 配置
python test_api.py
```

---

## 🔧 使用示例

### 1. 语音转文字示例

```python
from app.services.speech_to_text import WhisperService

# 初始化服务
whisper = WhisperService()

# 转录视频
result = await whisper.transcribe_video(
    video_path="teacher_video.mp4",
    language_hint="en"  # 可选：指定语言
)

print(f"转录文本: {result['text']}")
print(f"检测语言: {result['language']}")
print(f"视频时长: {result['duration']}秒")
```

### 2. 背景移除示例

```python
from app.services.background_removal import UnscreenService

# 初始化服务
unscreen = UnscreenService()

# 移除背景
result = await unscreen.remove_background(
    video_file_path="teacher_video.mp4",
    output_dir="./outputs"
)

print(f"输出路径: {result['output_path']}")
print(f"处理时间: {result['processing_time']}秒")
```

### 3. 完整 API 调用示例

```bash
# 上传并处理视频
curl -X POST "http://localhost:8000/api/v1/video/upload-and-process" \
  -F "file=@teacher_video.mp4" \
  -F "teacher_name=John Smith" \
  -F "language_hint=en"

# 查看处理进度
curl http://localhost:8000/api/v1/video/progress/{job_id}

# 下载结果
curl http://localhost:8000/api/v1/video/download/{job_id} -o result.mp4
```

---

## ❓ 常见问题

### Q1: OpenAI API Key 无效？

**解决方案**：
1. 检查 API Key 格式是否正确（以 `sk-` 开头）
2. 确认账户已充值且有余额
3. 验证 API Key 权限设置
4. 检查是否超出使用限额

### Q2: Unscreen 处理失败？

**解决方案**：
1. 检查视频文件大小（最大 500MB）
2. 确认视频格式支持
3. 验证账户余额是否充足
4. 检查网络连接稳定性

### Q3: 音频提取失败？

**解决方案**：
1. 确保安装了 FFmpeg
   ```bash
   # Ubuntu/Debian
   sudo apt install ffmpeg
   
   # macOS
   brew install ffmpeg
   
   # 验证安装
   ffmpeg -version
   ```

### Q4: 处理速度慢？

**优化建议**：
1. 调整并发任务数量：`MAX_CONCURRENT_JOBS=5`
2. 使用更快的存储设备（SSD）
3. 增加服务器内存和 CPU 资源
4. 考虑使用 GPU 加速（如果支持）

### Q5: API 调用频率限制？

**解决方案**：
1. 实现请求重试机制（已内置）
2. 添加请求间隔延迟
3. 升级到更高级别的 API 计划
4. 使用多个 API Key 轮换

---

## 📞 技术支持

如果遇到问题，请按以下顺序尝试：

1. **查看日志文件**：`logs/app.log`
2. **检查系统状态**：访问 `/api/v1/health/`
3. **验证 API Keys**：使用上述验证命令
4. **查看官方文档**：
   - [OpenAI API 文档](https://platform.openai.com/docs)
   - [Unscreen API 文档](https://www.unscreen.com/api-documentation)

---

## 🎯 下一步

配置完成后，您可以：

1. **测试基本功能**：上传一个短视频测试
2. **调整参数**：根据需求优化配置
3. **监控使用量**：定期检查 API 使用情况
4. **扩展功能**：基于现有框架添加新特性

祝您使用愉快！🚀
