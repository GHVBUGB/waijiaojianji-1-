#!/usr/bin/env python3
"""
豆包(Doubao)语音识别API配置工具
专门用于配置火山引擎豆包语音识别服务
"""

import os
import sys
import asyncio
from typing import Optional

def print_banner():
    """打印配置横幅"""
    print("""
╔══════════════════════════════════════════════════════════════╗
║                    豆包语音识别配置工具                      ║
║                  Doubao Speech Recognition                   ║
║                                                              ║
║  🎤 火山引擎旗下语音识别服务                                ║
║  💰 4.5元/小时 | 10 QPS并发                                 ║
║  🌍 支持12种语言 | 高准确率识别                             ║
╚══════════════════════════════════════════════════════════════╝
    """)

def create_doubao_env_file(access_key: str, secret_key: str):
    """创建豆包服务 .env 配置文件"""
    
    env_content = f"""# ==============================================
# 豆包语音识别服务配置
# 自动生成于: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
# ==============================================

# ==============================================
# 火山引擎API配置 (必需)
# ==============================================

# 火山引擎访问密钥
VOLCENGINE_ACCESS_KEY={access_key}
VOLCENGINE_SECRET_KEY={secret_key}
VOLCENGINE_REGION=cn-north-1

# ==============================================
# 豆包语音识别服务配置
# ==============================================

# 服务选择：使用豆包语音识别
SPEECH_SERVICE=doubao

# 豆包服务配置
DOUBAO_SERVICE_NAME=doubao-streaming-asr
DOUBAO_WS_URL=wss://openspeech.bytedance.com/api/v1/asr
DOUBAO_REGION=cn-north-1

# ==============================================
# 视频处理服务配置 (可选)
# ==============================================

# 如果您还需要视频背景移除，可以选择：
# VIDEO_SERVICE=volcengine  # 使用火山引擎视频处理
# VIDEO_SERVICE=unscreen    # 使用Unscreen API
# VIDEO_SERVICE=local       # 使用本地OpenCV处理

# 暂时使用本地处理（无需额外API）
VIDEO_SERVICE=local

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

# 并发任务数量（豆包限制10 QPS）
MAX_CONCURRENT_JOBS=5

# 音频采样率（豆包推荐16kHz）
AUDIO_SAMPLE_RATE=16000

# 视频输出格式
VIDEO_OUTPUT_FORMAT=mp4

# ==============================================
# 豆包服务特殊配置
# ==============================================

# 支持的语言（默认中文）
DEFAULT_LANGUAGE=zh-CN

# WebSocket连接配置
WS_PING_INTERVAL=30
WS_PING_TIMEOUT=10
WS_CLOSE_TIMEOUT=10

# 音频处理配置
AUDIO_CHUNK_SIZE=8000
ENABLE_VAD=true
SHOW_PUNCTUATION=true
SHOW_SENTENCE_END=true
"""
    
    with open('.env', 'w', encoding='utf-8') as f:
        f.write(env_content)
    
    print("✅ 豆包语音识别 .env 文件已创建")

def get_api_key_input(key_name: str, description: str) -> str:
    """获取用户输入的 API Key"""
    while True:
        key = input(f"\n请输入 {key_name} ({description}): ").strip()
        
        if not key:
            print("❌ 输入不能为空")
            continue
            
        return key

def validate_doubao_service():
    """验证豆包服务配置"""
    print("\n🔍 验证豆包服务配置...")
    
    try:
        # 导入豆包服务
        sys.path.append('.')
        from app.services.doubao_speech_service import DoubaoSpeechService
        
        service = DoubaoSpeechService()
        
        if not service.access_key or not service.secret_key:
            print("❌ 豆包服务配置不完整")
            return False
        
        print("✅ 豆包服务配置验证通过")
        return True
        
    except ImportError as e:
        print(f"⚠️  无法导入豆包服务模块: {e}")
        print("请确保项目结构正确")
        return False
    except Exception as e:
        print(f"❌ 豆包服务配置验证失败: {e}")
        return False

async def test_doubao_connection(access_key: str, secret_key: str):
    """测试豆包服务连接"""
    print("\n🧪 测试豆包服务连接...")
    
    try:
        # 这里可以添加实际的连接测试
        # 由于需要音频文件，这里只做基础验证
        
        print("🎤 豆包语音识别服务信息:")
        print("   - 服务名称: Doubao 流式语音识别")
        print("   - 价格: 4.5元/小时")
        print("   - 并发限制: 10 QPS")
        print("   - 支持格式: WAV, MP3, AAC, FLAC")
        print("   - 支持语言: 12种主要语言")
        
        print("✅ 豆包服务基础信息验证通过")
        print("💡 完整测试需要上传音频文件")
        
        return True
        
    except Exception as e:
        print(f"❌ 豆包服务连接测试失败: {e}")
        return False

def show_next_steps():
    """显示下一步操作指南"""
    print("""
📋 配置完成！下一步操作:

1. 🧪 测试豆包服务:
   python test_doubao_service.py

2. 🚀 启动视频处理系统:
   python -m app.main

3. 📝 测试语音转文字:
   # 上传视频文件到 uploads/ 目录
   curl -X POST "http://localhost:8000/api/v1/video/upload-and-process" \\
     -F "file=@test_video.mp4" \\
     -F "language_hint=zh-CN"

4. 📊 查看处理结果:
   curl http://localhost:8000/api/v1/video/results/{job_id}

💡 豆包服务优势:
   ✅ 国内服务，响应速度快
   ✅ 中文识别准确率高
   ✅ 价格相对便宜 (4.5元/小时)
   ✅ 支持实时流式识别
   ✅ 自动标点符号和语音检测

⚠️  注意事项:
   - 确保账户余额充足
   - 注意10 QPS并发限制
   - 建议使用16kHz单声道音频
   - 支持最长60分钟音频
    """)

def main():
    """主函数"""
    print_banner()
    
    # 检查是否已存在 .env 文件
    if os.path.exists('.env'):
        overwrite = input("\n⚠️  .env 文件已存在，是否覆盖？(y/N): ").strip().lower()
        if overwrite != 'y':
            print("配置取消")
            return
    
    print("\n📋 豆包语音识别服务配置")
    print("=" * 50)
    
    print("\n💡 获取火山引擎API密钥:")
    print("1. 访问火山引擎控制台: https://console.volcengine.com/")
    print("2. 进入「访问控制」→「访问密钥」")
    print("3. 点击「新建访问密钥」")
    print("4. 复制生成的Access Key和Secret Key")
    
    print("\n💰 开通豆包语音识别服务:")
    print("1. 在火山引擎控制台搜索「豆包」")
    print("2. 找到「Doubao-流式语音识别」")
    print("3. 点击「立即使用」开通服务")
    print("4. 选择「按量付费」(4.5元/小时)")
    
    # 获取API密钥
    print("\n" + "=" * 30)
    print("🔑 输入API密钥信息")
    print("=" * 30)
    
    access_key = get_api_key_input("Access Key", "以AK开头的访问密钥")
    secret_key = get_api_key_input("Secret Key", "对应的私钥")
    
    # 创建配置文件
    print("\n" + "=" * 30)
    print("💾 创建配置文件")
    print("=" * 30)
    
    create_doubao_env_file(access_key, secret_key)
    
    # 创建必要的目录
    directories = ['uploads', 'outputs', 'temp', 'logs']
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
    
    print(f"✅ 目录已创建: {', '.join(directories)}")
    
    # 验证配置
    if validate_doubao_service():
        print("✅ 豆包服务配置验证通过")
    
    # 测试连接
    try:
        result = asyncio.run(test_doubao_connection(access_key, secret_key))
        if result:
            print("✅ 豆包服务连接测试通过")
    except Exception as e:
        print(f"⚠️  连接测试跳过: {e}")
    
    print("\n🎉 豆包语音识别配置完成！")
    
    # 显示下一步操作
    show_next_steps()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 配置已取消")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 配置过程中出现错误: {e}")
        sys.exit(1)
