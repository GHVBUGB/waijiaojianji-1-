#!/usr/bin/env python3
"""
腾讯云视频背景移除配置工具
经济实惠的Unscreen替代方案
"""

import os
import sys
from typing import Optional

def print_banner():
    """打印配置横幅"""
    print("""
╔══════════════════════════════════════════════════════════════╗
║                    腾讯云视频背景移除                        ║
║                  Tencent Cloud Video Processing              ║
║                                                              ║
║  💰 ¥0.15/次 vs Unscreen ¥0.7/次                           ║
║  🚀 节省成本 80%+ | 国内服务速度快                          ║
║  🎯 专业人像分割 | 按需付费无月费                           ║
╚══════════════════════════════════════════════════════════════╝
    """)

def show_cost_comparison():
    """显示成本对比"""
    print("\n💰 成本对比分析:")
    print("=" * 50)
    
    scenarios = [
        ("个人用户", 20, "每月"),
        ("小型企业", 100, "每月"), 
        ("中型企业", 500, "每月")
    ]
    
    for scenario, count, period in scenarios:
        tencent_cost = count * 0.15
        unscreen_cost = 145 if count <= 200 else (count / 200) * 145
        savings = unscreen_cost - tencent_cost
        savings_pct = (savings / unscreen_cost) * 100
        
        print(f"\n📊 {scenario} ({count}个视频/{period}):")
        print(f"   Unscreen:  ¥{unscreen_cost:.2f}")
        print(f"   腾讯云:    ¥{tencent_cost:.2f}")
        print(f"   节省:      ¥{savings:.2f} ({savings_pct:.1f}%)")

def create_tencent_env_file(secret_id: str, secret_key: str, speech_service: str = "doubao"):
    """创建腾讯云 .env 配置文件"""
    
    env_content = f"""# ==============================================
# 混合方案配置 - 豆包语音 + 腾讯云视频
# 自动生成于: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
# ==============================================

# ==============================================
# 语音识别服务 (豆包)
# ==============================================

# 火山引擎访问密钥 (用于豆包语音识别)
VOLCENGINE_ACCESS_KEY=your-volcengine-access-key
VOLCENGINE_SECRET_KEY=your-volcengine-secret-key
VOLCENGINE_REGION=cn-north-1

# 语音服务选择
SPEECH_SERVICE={speech_service}

# ==============================================
# 视频处理服务 (腾讯云)
# ==============================================

# 腾讯云访问密钥
TENCENT_SECRET_ID={secret_id}
TENCENT_SECRET_KEY={secret_key}
TENCENT_REGION=ap-beijing

# 视频服务选择
VIDEO_SERVICE=tencent

# ==============================================
# 腾讯云人体分析配置
# ==============================================

# API端点
TENCENT_BDA_ENDPOINT=bda.tencentcloudapi.com
TENCENT_BDA_VERSION=2020-03-24

# 处理配置
TENCENT_FRAME_SKIP=5  # 每5帧处理一次（降低成本）
TENCENT_ENABLE_CACHE=true  # 启用结果缓存

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

# 音频采样率
AUDIO_SAMPLE_RATE=16000

# 视频输出格式
VIDEO_OUTPUT_FORMAT=mp4

# ==============================================
# 成本控制配置
# ==============================================

# 每日最大API调用次数（防止意外超支）
DAILY_API_LIMIT=1000

# 成本预警阈值（元）
COST_WARNING_THRESHOLD=50

# 启用成本跟踪
ENABLE_COST_TRACKING=true
"""
    
    with open('.env', 'w', encoding='utf-8') as f:
        f.write(env_content)
    
    print("✅ 腾讯云混合方案 .env 文件已创建")

def get_api_key_input(key_name: str, description: str) -> str:
    """获取用户输入的 API Key"""
    while True:
        key = input(f"\n请输入 {key_name} ({description}): ").strip()
        
        if not key:
            print("❌ 输入不能为空")
            continue
            
        return key

def show_tencent_cloud_guide():
    """显示腾讯云开通指南"""
    print("\n📋 腾讯云人体分析服务开通指南:")
    print("=" * 50)
    
    print("\n1️⃣ 注册腾讯云账户:")
    print("   - 访问: https://cloud.tencent.com/")
    print("   - 点击「免费注册」")
    print("   - 完成实名认证")
    
    print("\n2️⃣ 开通人体分析服务:")
    print("   - 搜索「人体分析」或访问:")
    print("     https://console.cloud.tencent.com/bda")
    print("   - 点击「立即开通」")
    print("   - 选择「按量付费」")
    
    print("\n3️⃣ 创建API密钥:")
    print("   - 访问: https://console.cloud.tencent.com/cam/capi")
    print("   - 点击「新建密钥」")
    print("   - 复制SecretId和SecretKey")
    
    print("\n4️⃣ 账户充值:")
    print("   - 建议充值¥50-100用于测试")
    print("   - 人像分割: ¥0.15/次")
    print("   - 前1000次有优惠价格")

def validate_tencent_config():
    """验证腾讯云配置"""
    print("\n🔍 验证腾讯云配置...")
    
    try:
        # 检查是否安装了腾讯云SDK
        try:
            import tencentcloud
            print("✅ 腾讯云SDK已安装")
        except ImportError:
            print("⚠️  腾讯云SDK未安装，将使用本地处理")
            print("   安装命令: pip install tencentcloud-sdk-python")
        
        # 导入服务
        sys.path.append('.')
        from app.services.tencent_video_service import TencentVideoService
        
        service = TencentVideoService()
        print("✅ 腾讯云服务模块加载成功")
        return True
        
    except ImportError as e:
        print(f"⚠️  无法导入腾讯云服务模块: {e}")
        print("请确保项目结构正确")
        return False
    except Exception as e:
        print(f"❌ 腾讯云服务配置验证失败: {e}")
        return False

def show_next_steps():
    """显示下一步操作指南"""
    print("""
🎉 腾讯云视频背景移除配置完成！

📋 下一步操作:

1. 🔧 安装腾讯云SDK (如果还没安装):
   pip install tencentcloud-sdk-python

2. 🧪 测试腾讯云服务:
   python test_tencent_video.py

3. 🎤 配置豆包语音识别 (如果还没配置):
   python setup_doubao_api.py

4. 🚀 启动完整系统:
   python -m app.main

5. 📝 测试完整流程:
   curl -X POST "http://localhost:8000/api/v1/video/upload-and-process" \\
     -F "file=@test_video.mp4" \\
     -F "language_hint=zh-CN"

💡 混合方案优势:
   🎤 语音识别: 豆包 (4.5元/小时, 国内服务)
   🎬 背景移除: 腾讯云 (0.15元/次, 节省80%成本)
   🚀 总成本: 比全用国外服务节省70%+

⚠️  成本控制提醒:
   - 已配置每日API调用限制
   - 启用成本跟踪和预警
   - 建议先小批量测试效果
    """)

def main():
    """主函数"""
    print_banner()
    show_cost_comparison()
    
    # 检查是否已存在 .env 文件
    if os.path.exists('.env'):
        overwrite = input("\n⚠️  .env 文件已存在，是否覆盖？(y/N): ").strip().lower()
        if overwrite != 'y':
            print("配置取消")
            return
    
    # 显示开通指南
    show_tencent_cloud_guide()
    
    # 获取用户确认
    ready = input("\n✅ 您是否已完成腾讯云开通并获取了API密钥？(y/N): ").strip().lower()
    if ready != 'y':
        print("\n💡 请先完成腾讯云开通，然后重新运行此配置工具")
        print("如有问题可参考: AFFORDABLE_VIDEO_BACKGROUND_SOLUTIONS.md")
        return
    
    # 获取API密钥
    print("\n" + "=" * 30)
    print("🔑 输入腾讯云API密钥")
    print("=" * 30)
    
    secret_id = get_api_key_input("SecretId", "腾讯云访问密钥ID")
    secret_key = get_api_key_input("SecretKey", "腾讯云私有访问密钥")
    
    # 选择语音识别服务
    print("\n" + "=" * 30)
    print("🎤 选择语音识别服务")
    print("=" * 30)
    
    print("1. 豆包语音识别 (推荐) - 4.5元/小时")
    print("2. OpenAI Whisper - $0.006/分钟")
    print("3. 暂不配置语音识别")
    
    choice = input("\n请选择 (1-3): ").strip()
    speech_service = {
        "1": "doubao",
        "2": "openai", 
        "3": "none"
    }.get(choice, "doubao")
    
    # 创建配置文件
    print("\n" + "=" * 30)
    print("💾 创建配置文件")
    print("=" * 30)
    
    create_tencent_env_file(secret_id, secret_key, speech_service)
    
    # 创建必要的目录
    directories = ['uploads', 'outputs', 'temp', 'logs']
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
    
    print(f"✅ 目录已创建: {', '.join(directories)}")
    
    # 验证配置
    if validate_tencent_config():
        print("✅ 腾讯云服务配置验证通过")
    
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
