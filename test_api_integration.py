#!/usr/bin/env python3
"""
API 集成测试脚本
测试 OpenAI Whisper 和 Unscreen API 集成是否正常
"""

import asyncio
import os
import sys
import requests
from pathlib import Path

# 添加项目路径
sys.path.append(str(Path(__file__).parent))

from app.config.settings import settings
from app.services.speech_to_text import WhisperService
from app.services.background_removal import UnscreenService

class APITester:
    def __init__(self):
        self.whisper = WhisperService()
        self.unscreen = UnscreenService()
    
    def test_environment_variables(self):
        """测试环境变量配置"""
        print("🔧 检查环境变量配置...")
        
        issues = []
        
        # 检查 OpenAI API Key
        if not settings.OPENAI_API_KEY:
            issues.append("❌ OPENAI_API_KEY 未设置")
        elif not settings.OPENAI_API_KEY.startswith("sk-"):
            issues.append("❌ OPENAI_API_KEY 格式错误 (应以 'sk-' 开头)")
        else:
            print("✅ OpenAI API Key 已配置")
        
        # 检查 Unscreen API Key
        if not settings.UNSCREEN_API_KEY:
            issues.append("❌ UNSCREEN_API_KEY 未设置")
        else:
            print("✅ Unscreen API Key 已配置")
        
        # 检查目录
        directories = [settings.UPLOAD_DIR, settings.OUTPUT_DIR, settings.TEMP_DIR]
        for directory in directories:
            if not os.path.exists(directory):
                issues.append(f"❌ 目录不存在: {directory}")
            else:
                print(f"✅ 目录存在: {directory}")
        
        if issues:
            print("\n⚠️  发现配置问题:")
            for issue in issues:
                print(f"   {issue}")
            return False
        
        print("✅ 环境变量配置正常")
        return True
    
    def test_openai_connection(self):
        """测试 OpenAI API 连接"""
        print("\n🎤 测试 OpenAI Whisper API 连接...")
        
        try:
            headers = {"Authorization": f"Bearer {settings.OPENAI_API_KEY}"}
            response = requests.get(
                "https://api.openai.com/v1/models", 
                headers=headers, 
                timeout=10
            )
            
            if response.status_code == 200:
                models = response.json()
                whisper_models = [m for m in models.get('data', []) if 'whisper' in m.get('id', '')]
                print(f"✅ OpenAI API 连接成功")
                print(f"✅ 找到 Whisper 模型: {len(whisper_models)} 个")
                return True
            elif response.status_code == 401:
                print("❌ OpenAI API Key 无效或已过期")
                return False
            else:
                print(f"⚠️  OpenAI API 响应异常: {response.status_code}")
                print(f"响应内容: {response.text[:200]}")
                return False
                
        except requests.exceptions.RequestException as e:
            print(f"❌ 无法连接到 OpenAI API: {e}")
            return False
    
    def test_unscreen_connection(self):
        """测试 Unscreen API 连接"""
        print("\n🎬 测试 Unscreen API 连接...")
        
        try:
            headers = {"Authorization": f"Bearer {settings.UNSCREEN_API_KEY}"}
            response = requests.get(
                "https://api.unscreen.com/v1.0/account/credits", 
                headers=headers, 
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                credits = data.get('credits', 0)
                print(f"✅ Unscreen API 连接成功")
                print(f"✅ 账户余额: {credits} credits")
                
                if credits <= 0:
                    print("⚠️  账户余额不足，请充值")
                    return False
                return True
            elif response.status_code == 401:
                print("❌ Unscreen API Key 无效或已过期")
                return False
            else:
                print(f"⚠️  Unscreen API 响应异常: {response.status_code}")
                print(f"响应内容: {response.text[:200]}")
                return False
                
        except requests.exceptions.RequestException as e:
            print(f"❌ 无法连接到 Unscreen API: {e}")
            return False
    
    def check_ffmpeg(self):
        """检查 FFmpeg 是否安装"""
        print("\n🔧 检查 FFmpeg 安装...")
        
        try:
            import subprocess
            result = subprocess.run(['ffmpeg', '-version'], 
                                  capture_output=True, text=True, timeout=5)
            
            if result.returncode == 0:
                version_line = result.stdout.split('\n')[0]
                print(f"✅ FFmpeg 已安装: {version_line}")
                return True
            else:
                print("❌ FFmpeg 命令执行失败")
                return False
                
        except FileNotFoundError:
            print("❌ FFmpeg 未安装")
            print("   安装方法:")
            print("   - Ubuntu/Debian: sudo apt install ffmpeg")
            print("   - macOS: brew install ffmpeg")
            print("   - Windows: 下载 https://ffmpeg.org/download.html")
            return False
        except subprocess.TimeoutExpired:
            print("❌ FFmpeg 命令超时")
            return False
    
    async def test_whisper_service(self):
        """测试 Whisper 服务（需要测试文件）"""
        print("\n🎵 测试 Whisper 语音转文字服务...")
        
        # 检查是否有测试视频文件
        test_files = []
        for ext in ['.mp4', '.mov', '.avi']:
            test_files.extend(Path(settings.UPLOAD_DIR).glob(f'*{ext}'))
        
        if not test_files:
            print("⚠️  未找到测试视频文件")
            print(f"   请将测试视频文件放到 {settings.UPLOAD_DIR} 目录")
            return False
        
        test_file = test_files[0]
        print(f"📁 使用测试文件: {test_file.name}")
        
        try:
            # 测试音频提取
            audio_path = await self.whisper.extract_audio_from_video(str(test_file))
            print("✅ 音频提取成功")
            
            # 清理临时文件
            if os.path.exists(audio_path):
                os.unlink(audio_path)
            
            print("✅ Whisper 服务测试通过")
            return True
            
        except Exception as e:
            print(f"❌ Whisper 服务测试失败: {e}")
            return False
    
    def create_test_summary(self, results):
        """创建测试总结"""
        print("\n" + "=" * 50)
        print("📊 API 集成测试总结")
        print("=" * 50)
        
        total_tests = len(results)
        passed_tests = sum(results.values())
        
        print(f"总测试数: {total_tests}")
        print(f"通过测试: {passed_tests}")
        print(f"失败测试: {total_tests - passed_tests}")
        print(f"通过率: {passed_tests/total_tests*100:.1f}%")
        
        print("\n📋 详细结果:")
        for test_name, passed in results.items():
            status = "✅ 通过" if passed else "❌ 失败"
            print(f"   {test_name}: {status}")
        
        if passed_tests == total_tests:
            print("\n🎉 所有测试通过！您的 API 集成配置正确。")
            print("\n📋 下一步:")
            print("1. 启动应用: python -m app.main")
            print("2. 访问: http://localhost:8000")
            print("3. 测试上传视频功能")
        else:
            print("\n⚠️  部分测试失败，请检查配置后重新测试。")
            print("💡 获取帮助:")
            print("1. 查看 API_INTEGRATION_GUIDE.md")
            print("2. 运行配置工具: python setup_api_keys.py")

async def main():
    """主测试函数"""
    print("🧪 API 集成测试开始...")
    print("=" * 50)
    
    tester = APITester()
    results = {}
    
    # 运行所有测试
    results["环境变量配置"] = tester.test_environment_variables()
    results["FFmpeg 安装"] = tester.check_ffmpeg()
    results["OpenAI API 连接"] = tester.test_openai_connection()
    results["Unscreen API 连接"] = tester.test_unscreen_connection()
    results["Whisper 服务"] = await tester.test_whisper_service()
    
    # 生成测试总结
    tester.create_test_summary(results)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n测试已取消")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 测试过程中出现错误: {e}")
        sys.exit(1)
