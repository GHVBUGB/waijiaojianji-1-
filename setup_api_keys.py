#!/usr/bin/env python3
"""
API Keys 配置工具
用于快速配置 OpenAI 和 Unscreen API Keys
"""

import os
import sys
import requests
from typing import Optional

def create_env_file(openai_key: str, unscreen_key: str):
    """创建 .env 配置文件"""
    
    env_content = f"""# ==============================================
# 外教视频处理系统 - 环境变量配置
# 自动生成于: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
# ==============================================

# ==============================================
# API 配置 (必需)
# ==============================================

# OpenAI Whisper API Key
OPENAI_API_KEY={openai_key}

# Unscreen API Key  
UNSCREEN_API_KEY={unscreen_key}

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
"""
    
    with open('.env', 'w', encoding='utf-8') as f:
        f.write(env_content)
    
    print("✅ .env 文件已创建")

def validate_openai_key(api_key: str) -> bool:
    """验证 OpenAI API Key"""
    try:
        headers = {"Authorization": f"Bearer {api_key}"}
        response = requests.get(
            "https://api.openai.com/v1/models", 
            headers=headers, 
            timeout=10
        )
        
        if response.status_code == 200:
            print("✅ OpenAI API Key 验证成功")
            return True
        elif response.status_code == 401:
            print("❌ OpenAI API Key 无效")
            return False
        else:
            print(f"⚠️  OpenAI API 响应异常: {response.status_code}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"⚠️  无法连接到 OpenAI API: {e}")
        return False

def validate_unscreen_key(api_key: str) -> bool:
    """验证 Unscreen API Key"""
    try:
        headers = {"Authorization": f"Bearer {api_key}"}
        response = requests.get(
            "https://api.unscreen.com/v1.0/account/credits", 
            headers=headers, 
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            credits = data.get('credits', 0)
            print(f"✅ Unscreen API Key 验证成功 (余额: {credits} credits)")
            return True
        elif response.status_code == 401:
            print("❌ Unscreen API Key 无效")
            return False
        else:
            print(f"⚠️  Unscreen API 响应异常: {response.status_code}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"⚠️  无法连接到 Unscreen API: {e}")
        return False

def get_api_key_input(service_name: str, key_format: str) -> str:
    """获取用户输入的 API Key"""
    while True:
        key = input(f"\n请输入 {service_name} API Key ({key_format}): ").strip()
        
        if not key:
            print("❌ API Key 不能为空")
            continue
            
        if service_name == "OpenAI" and not key.startswith("sk-"):
            print("❌ OpenAI API Key 应该以 'sk-' 开头")
            continue
            
        return key

def main():
    """主函数"""
    print("🚀 外教视频处理系统 - API Keys 配置工具")
    print("=" * 50)
    
    # 检查是否已存在 .env 文件
    if os.path.exists('.env'):
        overwrite = input("\n⚠️  .env 文件已存在，是否覆盖？(y/N): ").strip().lower()
        if overwrite != 'y':
            print("配置取消")
            return
    
    print("\n📋 您需要获取以下 API Keys:")
    print("1. OpenAI API Key - 访问: https://platform.openai.com/api-keys")
    print("2. Unscreen API Key - 访问: https://www.unscreen.com/api")
    print("\n💡 提示: 请确保账户已充值并有足够余额")
    
    # 获取 OpenAI API Key
    print("\n" + "=" * 30)
    print("🎤 配置 OpenAI Whisper API")
    print("=" * 30)
    
    openai_key = get_api_key_input("OpenAI", "sk-...")
    
    print("正在验证 OpenAI API Key...")
    if not validate_openai_key(openai_key):
        if input("是否继续配置？(y/N): ").strip().lower() != 'y':
            return
    
    # 获取 Unscreen API Key
    print("\n" + "=" * 30)
    print("🎬 配置 Unscreen API")
    print("=" * 30)
    
    unscreen_key = get_api_key_input("Unscreen", "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx")
    
    print("正在验证 Unscreen API Key...")
    if not validate_unscreen_key(unscreen_key):
        if input("是否继续配置？(y/N): ").strip().lower() != 'y':
            return
    
    # 创建 .env 文件
    print("\n" + "=" * 30)
    print("💾 创建配置文件")
    print("=" * 30)
    
    create_env_file(openai_key, unscreen_key)
    
    # 创建必要的目录
    directories = ['uploads', 'outputs', 'temp', 'logs']
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
    
    print(f"✅ 目录已创建: {', '.join(directories)}")
    
    print("\n🎉 配置完成！")
    print("\n📋 下一步:")
    print("1. 运行应用: python -m app.main")
    print("2. 测试 API: curl http://localhost:8000/api/v1/health/")
    print("3. 查看文档: 阅读 API_INTEGRATION_GUIDE.md")
    
    print("\n⚠️  安全提醒:")
    print("- 不要将 .env 文件提交到代码仓库")
    print("- 定期轮换 API Keys")
    print("- 监控 API 使用量和费用")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n配置已取消")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 配置过程中出现错误: {e}")
        sys.exit(1)
