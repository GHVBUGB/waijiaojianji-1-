#!/usr/bin/env python3
"""
快速启动脚本
一键检查配置、测试 API 并启动服务
"""

import os
import sys
import subprocess
import asyncio
from pathlib import Path

def print_banner():
    """打印启动横幅"""
    print("""
╔══════════════════════════════════════════════════════════════╗
║                    外教视频处理系统                          ║
║                  Quick Start - 快速启动                     ║
║                                                              ║
║  🎤 OpenAI Whisper - 语音转文字                             ║
║  🎬 Unscreen API - 视频背景移除                             ║
╚══════════════════════════════════════════════════════════════╝
    """)

def check_python_version():
    """检查 Python 版本"""
    print("🐍 检查 Python 版本...")
    
    if sys.version_info < (3, 9):
        print(f"❌ Python 版本过低: {sys.version}")
        print("   需要 Python >= 3.9")
        return False
    
    print(f"✅ Python 版本: {sys.version.split()[0]}")
    return True

def check_dependencies():
    """检查依赖包"""
    print("\n📦 检查依赖包...")
    
    required_packages = [
        'fastapi', 'uvicorn', 'openai', 'requests', 
        'python-multipart', 'aiofiles', 'pydantic'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
            print(f"✅ {package}")
        except ImportError:
            print(f"❌ {package} (缺失)")
            missing_packages.append(package)
    
    if missing_packages:
        print(f"\n⚠️  缺少依赖包: {', '.join(missing_packages)}")
        print("运行以下命令安装:")
        print("pip install -r requirements.txt")
        return False
    
    return True

def check_env_file():
    """检查环境变量文件"""
    print("\n🔧 检查环境配置...")
    
    if not os.path.exists('.env'):
        print("❌ .env 文件不存在")
        print("💡 解决方案:")
        print("1. 运行: python setup_api_keys.py")
        print("2. 或手动创建 .env 文件")
        return False
    
    print("✅ .env 文件存在")
    
    # 检查关键配置
    from app.config.settings import settings
    
    issues = []
    if not settings.OPENAI_API_KEY:
        issues.append("OPENAI_API_KEY")
    if not settings.UNSCREEN_API_KEY:
        issues.append("UNSCREEN_API_KEY")
    
    if issues:
        print(f"❌ 缺少配置: {', '.join(issues)}")
        return False
    
    print("✅ API Keys 已配置")
    return True

def create_directories():
    """创建必要的目录"""
    print("\n📁 创建目录...")
    
    directories = ['uploads', 'outputs', 'temp', 'logs']
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        print(f"✅ {directory}/")
    
    return True

async def run_api_tests():
    """运行 API 测试"""
    print("\n🧪 运行 API 集成测试...")
    
    try:
        # 导入测试模块
        sys.path.append(str(Path(__file__).parent))
        from test_api_integration import APITester
        
        tester = APITester()
        
        # 快速测试
        tests = {
            "环境变量": tester.test_environment_variables(),
            "OpenAI API": tester.test_openai_connection(),
            "Unscreen API": tester.test_unscreen_connection(),
            "FFmpeg": tester.check_ffmpeg()
        }
        
        all_passed = all(tests.values())
        
        if all_passed:
            print("✅ 所有 API 测试通过")
        else:
            print("⚠️  部分 API 测试失败")
            for test_name, passed in tests.items():
                if not passed:
                    print(f"   ❌ {test_name}")
        
        return all_passed
        
    except Exception as e:
        print(f"❌ API 测试失败: {e}")
        return False

def start_server():
    """启动服务器"""
    print("\n🚀 启动服务器...")
    
    try:
        # 检查端口是否被占用
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(('localhost', 8000))
        sock.close()
        
        if result == 0:
            print("⚠️  端口 8000 已被占用")
            print("请检查是否已有服务在运行")
            return False
        
        print("启动中...")
        print("📍 服务地址: http://localhost:8000")
        print("📚 API 文档: http://localhost:8000/docs")
        print("💡 按 Ctrl+C 停止服务")
        print("-" * 50)
        
        # 启动 FastAPI 应用
        subprocess.run([
            sys.executable, "-m", "uvicorn", 
            "app.main:app", 
            "--host", "0.0.0.0", 
            "--port", "8000", 
            "--reload"
        ])
        
        return True
        
    except KeyboardInterrupt:
        print("\n\n👋 服务已停止")
        return True
    except Exception as e:
        print(f"❌ 启动失败: {e}")
        return False

def show_usage_examples():
    """显示使用示例"""
    print("""
📋 快速使用指南:

1. 🎤 语音转文字:
   curl -X POST "http://localhost:8000/api/v1/video/upload-and-process" \\
     -F "file=@teacher_video.mp4" \\
     -F "language_hint=en"

2. 🎬 背景移除:
   (上传的视频会自动进行背景移除处理)

3. 📊 查看进度:
   curl http://localhost:8000/api/v1/video/progress/{job_id}

4. 📥 下载结果:
   curl http://localhost:8000/api/v1/video/download/{job_id} -o result.mp4

5. 🔍 健康检查:
   curl http://localhost:8000/api/v1/health/

💡 更多信息请查看: API_INTEGRATION_GUIDE.md
    """)

async def main():
    """主函数"""
    print_banner()
    
    # 检查步骤
    checks = [
        ("Python 版本", check_python_version),
        ("依赖包", check_dependencies),
        ("环境配置", check_env_file),
        ("目录结构", create_directories)
    ]
    
    print("🔍 系统检查...")
    print("=" * 50)
    
    all_checks_passed = True
    
    for check_name, check_func in checks:
        if not check_func():
            all_checks_passed = False
            break
    
    if not all_checks_passed:
        print("\n❌ 系统检查失败，请解决上述问题后重试")
        print("\n💡 获取帮助:")
        print("1. 查看 API_INTEGRATION_GUIDE.md")
        print("2. 运行 python setup_api_keys.py")
        return
    
    # API 测试
    api_tests_passed = await run_api_tests()
    
    if not api_tests_passed:
        print("\n⚠️  API 测试部分失败，但仍可以启动服务")
        continue_start = input("是否继续启动服务？(y/N): ").strip().lower()
        if continue_start != 'y':
            return
    
    print("\n✅ 所有检查完成！")
    
    # 显示使用示例
    show_usage_examples()
    
    # 询问是否启动服务
    start_service = input("\n是否立即启动服务？(Y/n): ").strip().lower()
    if start_service in ['', 'y', 'yes']:
        start_server()
    else:
        print("\n👋 手动启动服务:")
        print("python -m app.main")
        print("或")
        print("uvicorn app.main:app --reload")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 启动已取消")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ 启动过程中出现错误: {e}")
        sys.exit(1)
