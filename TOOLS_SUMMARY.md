# 🛠️ 工具和脚本总览

本文档列出了项目中所有可用的工具和脚本，帮助您快速上手和管理系统。

## 📋 目录

- [快速启动工具](#快速启动工具)
- [配置工具](#配置工具)
- [测试工具](#测试工具)
- [API 集成指南](#api-集成指南)
- [使用建议](#使用建议)

---

## 🚀 快速启动工具

### `quick_start.py` - 一键启动脚本

**功能**: 自动检查环境、配置 API Keys、测试连接并启动服务

```bash
python quick_start.py
```

**特点**:
- ✅ 自动检查 Python 版本和依赖
- ✅ 验证环境配置
- ✅ 测试 API 连接
- ✅ 创建必要目录
- ✅ 启动开发服务器
- ✅ 提供使用示例

**适用场景**: 首次部署、快速验证环境

---

## ⚙️ 配置工具

### `setup_api_keys.py` - API Keys 配置工具

**功能**: 交互式配置 OpenAI 和 Unscreen API Keys

```bash
python setup_api_keys.py
```

**特点**:
- 🔐 安全的 API Key 输入
- ✅ 实时验证 API Key 有效性
- 💰 显示账户余额
- 📁 自动创建 .env 文件
- 🛡️ 安全提醒和最佳实践

**适用场景**: 初始配置、更换 API Keys

---

## 🧪 测试工具

### `test_api_integration.py` - API 集成测试

**功能**: 全面测试 OpenAI Whisper 和 Unscreen API 集成

```bash
python test_api_integration.py
```

**测试项目**:
- 🔧 环境变量配置检查
- 🎤 OpenAI API 连接测试
- 🎬 Unscreen API 连接测试
- 📹 FFmpeg 安装检查
- 🎵 Whisper 服务功能测试

**输出**: 详细的测试报告和修复建议

### `test_api.py` - 基础服务测试

**功能**: 测试运行中的 FastAPI 服务

```bash
# 先启动服务
python -m app.main

# 另一个终端运行测试
python test_api.py
```

**测试项目**:
- 🏠 根页面访问
- ❤️ 健康检查接口
- 📚 API 文档页面

---

## 📖 API 集成指南

### `API_INTEGRATION_GUIDE.md` - 完整集成指南

**内容包括**:

#### 🎤 OpenAI Whisper 集成
- 📝 账户注册步骤
- 🔑 API Key 获取方法
- 💰 定价信息
- 🌍 支持的语言列表
- 🛠️ 功能特点说明

#### 🎬 Unscreen API 集成
- 📝 账户注册步骤
- 💳 订阅计划对比
- 🔑 API Key 获取方法
- 📹 支持的视频格式
- ⚡ 性能特点

#### ⚙️ 配置说明
- 🔧 环境变量详解
- 🔒 安全注意事项
- ✅ 配置验证方法
- 🐛 常见问题解答

#### 💡 使用示例
- 📝 代码示例
- 🌐 API 调用示例
- 🔧 故障排除指南

---

## 📊 使用建议

### 🆕 首次使用

1. **快速开始**（推荐）:
   ```bash
   pip install -r requirements.txt
   python quick_start.py
   ```

2. **手动配置**:
   ```bash
   pip install -r requirements.txt
   python setup_api_keys.py
   python test_api_integration.py
   python -m app.main
   ```

### 🔄 日常维护

1. **检查 API 状态**:
   ```bash
   python test_api_integration.py
   ```

2. **更新 API Keys**:
   ```bash
   python setup_api_keys.py
   ```

3. **验证服务运行**:
   ```bash
   python test_api.py
   ```

### 🐛 问题排查

1. **环境问题**: 运行 `python quick_start.py` 进行全面检查
2. **API 问题**: 运行 `python test_api_integration.py` 进行诊断
3. **服务问题**: 检查日志文件 `logs/app.log`
4. **配置问题**: 查看 `API_INTEGRATION_GUIDE.md`

### 🚀 生产部署

1. **Docker 部署**:
   ```bash
   docker-compose up -d
   ```

2. **手动部署**:
   ```bash
   # 生产环境配置
   export ENVIRONMENT=production
   
   # 启动服务
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
   ```

---

## 📁 文件结构

```
项目根目录/
├── quick_start.py              # 一键启动脚本
├── setup_api_keys.py           # API Keys 配置工具
├── test_api_integration.py     # API 集成测试
├── test_api.py                 # 基础服务测试
├── API_INTEGRATION_GUIDE.md    # 完整集成指南
├── TOOLS_SUMMARY.md           # 本文档
├── README.md                  # 项目说明
├── requirements.txt           # Python 依赖
├── .env.example              # 环境变量模板
└── .env                      # 环境变量配置（需创建）
```

---

## 🔗 相关链接

- **OpenAI Platform**: https://platform.openai.com/
- **OpenAI API Keys**: https://platform.openai.com/api-keys
- **OpenAI API 文档**: https://platform.openai.com/docs
- **Unscreen 官网**: https://www.unscreen.com/
- **Unscreen API**: https://www.unscreen.com/api
- **Unscreen API 文档**: https://www.unscreen.com/api-documentation

---

## 💡 提示

- 🔐 始终保护好您的 API Keys，不要提交到代码仓库
- 💰 定期检查 API 使用量和费用
- 🔄 建议每 3-6 个月轮换一次 API Keys
- 📊 监控系统日志以及时发现问题
- 🚀 生产环境建议使用 Docker 部署

---

## 🆘 获取帮助

如果遇到问题，请按以下顺序尝试：

1. 📖 查看 `API_INTEGRATION_GUIDE.md`
2. 🧪 运行 `python test_api_integration.py`
3. 🔧 运行 `python quick_start.py`
4. 📋 检查日志文件 `logs/app.log`
5. 🌐 查看官方 API 文档

祝您使用愉快！🎉
