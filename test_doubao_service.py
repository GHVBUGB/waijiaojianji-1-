#!/usr/bin/env python3
"""
豆包(Doubao)语音识别服务测试脚本
"""

import asyncio
import sys
import os
from pathlib import Path

# 添加项目路径
sys.path.append(str(Path(__file__).parent))

try:
    from app.services.doubao_speech_service import DoubaoSpeechService
except ImportError as e:
    print(f"❌ 无法导入豆包服务: {e}")
    print("请确保项目结构正确并安装了所需依赖")
    sys.exit(1)

class DoubaoServiceTester:
    def __init__(self):
        self.service = DoubaoSpeechService()
    
    def test_configuration(self):
        """测试配置"""
        print("🔧 检查豆包服务配置...")
        
        if not self.service.access_key:
            print("❌ Access Key 未配置")
            return False
        
        if not self.service.secret_key:
            print("❌ Secret Key 未配置")
            return False
        
        print(f"✅ Access Key: {self.service.access_key[:10]}...")
        print(f"✅ Secret Key: 已配置")
        print(f"✅ 服务端点: {self.service.ws_url}")
        print(f"✅ 服务名称: {self.service.service_name}")
        
        return True
    
    async def test_supported_languages(self):
        """测试支持的语言"""
        print("\n🌍 检查支持的语言...")
        
        try:
            languages = await self.service.get_supported_languages()
            
            print(f"✅ 支持 {len(languages)} 种语言:")
            for lang in languages:
                marker = "⭐" if lang.get("recommended") else "  "
                print(f"   {marker} {lang['code']}: {lang['name']}")
            
            return True
        except Exception as e:
            print(f"❌ 获取支持语言失败: {e}")
            return False
    
    async def test_service_info(self):
        """测试服务信息"""
        print("\n📊 获取服务信息...")
        
        try:
            info = await self.service.get_service_info()
            
            print(f"✅ 服务名称: {info['service_name']}")
            print(f"✅ 服务提供商: {info['provider']}")
            print(f"✅ 价格: {info['pricing']}")
            print(f"✅ 并发限制: {info['concurrent_limit']}")
            print(f"✅ 支持格式: {', '.join(info['supported_formats'])}")
            print(f"✅ 采样率: {info['sample_rate']}")
            print(f"✅ 声道: {info['channel']}")
            print(f"✅ 最大时长: {info['max_duration']}")
            
            print("✅ 特性:")
            for feature in info['features']:
                print(f"   • {feature}")
            
            return True
        except Exception as e:
            print(f"❌ 获取服务信息失败: {e}")
            return False
    
    async def test_audio_extraction(self):
        """测试音频提取功能"""
        print("\n🎵 测试音频提取功能...")
        
        # 查找测试视频文件
        test_files = []
        for ext in ['.mp4', '.mov', '.avi', '.mkv']:
            test_files.extend(Path("uploads").glob(f'*{ext}'))
        
        if not test_files:
            print("⚠️  未找到测试视频文件")
            print("   请将测试视频文件放到 uploads/ 目录")
            print("   支持格式: .mp4, .mov, .avi, .mkv")
            return False
        
        test_file = test_files[0]
        print(f"📁 使用测试文件: {test_file.name}")
        
        try:
            # 测试音频提取
            audio_path = await self.service.extract_audio_from_video(str(test_file))
            
            if os.path.exists(audio_path):
                file_size = os.path.getsize(audio_path)
                print(f"✅ 音频提取成功")
                print(f"   输出路径: {audio_path}")
                print(f"   文件大小: {file_size / 1024:.1f} KB")
                
                # 清理临时文件
                os.unlink(audio_path)
                print("✅ 临时文件已清理")
                
                return True
            else:
                print("❌ 音频文件未生成")
                return False
                
        except Exception as e:
            print(f"❌ 音频提取失败: {e}")
            return False
    
    async def test_speech_recognition(self):
        """测试语音识别功能"""
        print("\n🎤 测试语音识别功能...")
        
        # 查找测试视频文件
        test_files = []
        for ext in ['.mp4', '.mov', '.avi', '.mkv']:
            test_files.extend(Path("uploads").glob(f'*{ext}'))
        
        if not test_files:
            print("⚠️  未找到测试视频文件")
            print("   请将包含语音的测试视频文件放到 uploads/ 目录")
            return False
        
        test_file = test_files[0]
        print(f"📁 使用测试文件: {test_file.name}")
        print("⏳ 正在进行语音识别，请稍候...")
        
        try:
            # 测试语音识别
            result = await self.service.transcribe_video(
                str(test_file), 
                language_hint="zh-CN"
            )
            
            if result["success"]:
                print("✅ 语音识别成功")
                print(f"   识别文本: {result['text'][:100]}...")
                print(f"   语言: {result['language']}")
                print(f"   时长: {result['duration']:.2f}秒")
                print(f"   处理时间: {result['processing_time']:.2f}秒")
                print(f"   语音段数: {len(result['segments'])}")
                print(f"   服务: {result.get('service', 'unknown')}")
                
                # 显示前几个语音段
                if result['segments']:
                    print("\n📝 语音段示例:")
                    for i, segment in enumerate(result['segments'][:3]):
                        print(f"   [{segment['start']:.1f}s-{segment['end']:.1f}s]: {segment['text']}")
                
                return True
            else:
                print(f"❌ 语音识别失败: {result.get('error', '未知错误')}")
                return False
                
        except Exception as e:
            print(f"❌ 语音识别测试失败: {e}")
            return False
    
    def test_ffmpeg_installation(self):
        """测试FFmpeg安装"""
        print("\n🔧 检查FFmpeg安装...")
        
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
    
    def create_test_summary(self, results):
        """创建测试总结"""
        print("\n" + "=" * 50)
        print("📊 豆包服务测试总结")
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
            print("\n🎉 所有测试通过！豆包语音识别服务配置正确。")
            print("\n📋 下一步:")
            print("1. 启动应用: python -m app.main")
            print("2. 访问: http://localhost:8000")
            print("3. 上传视频测试完整功能")
            
            print("\n💰 费用提醒:")
            print("- 豆包语音识别: 4.5元/小时")
            print("- 建议监控使用量避免意外费用")
            
        else:
            print("\n⚠️  部分测试失败，请检查配置后重新测试。")
            print("💡 获取帮助:")
            print("1. 查看配置指南: VOLCENGINE_API_DETAILED_GUIDE.md")
            print("2. 重新配置: python setup_doubao_api.py")
            print("3. 检查网络连接和API密钥")

async def main():
    """主测试函数"""
    print("🔥 豆包语音识别服务测试")
    print("=" * 50)
    
    tester = DoubaoServiceTester()
    results = {}
    
    # 运行所有测试
    results["配置检查"] = tester.test_configuration()
    results["FFmpeg安装"] = tester.test_ffmpeg_installation()
    results["支持语言"] = await tester.test_supported_languages()
    results["服务信息"] = await tester.test_service_info()
    results["音频提取"] = await tester.test_audio_extraction()
    results["语音识别"] = await tester.test_speech_recognition()
    
    # 生成测试总结
    tester.create_test_summary(results)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 测试已取消")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 测试过程中出现错误: {e}")
        sys.exit(1)
