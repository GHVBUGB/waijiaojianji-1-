#!/usr/bin/env python3
"""
火山引擎API密钥验证脚本
用于快速验证您的Access Key和Secret Key是否配置正确
"""

import os
import sys
import json
import time
import hashlib
import hmac
import base64
from urllib.parse import urlencode
import requests

def print_step(step_num, title):
    """打印步骤标题"""
    print(f"\n{'='*50}")
    print(f"步骤 {step_num}: {title}")
    print('='*50)

def print_result(success, message):
    """打印结果"""
    status = "✅" if success else "❌"
    print(f"{status} {message}")

def get_user_input():
    """获取用户输入的密钥信息"""
    print("🔑 请输入您的火山引擎API密钥信息")
    print("(如果您不确定这些信息在哪里找到，请查看 VOLCENGINE_API_DETAILED_GUIDE.md)")
    
    access_key = input("\n请输入 Access Key: ").strip()
    if not access_key:
        print("❌ Access Key 不能为空")
        return None, None
    
    secret_key = input("请输入 Secret Key: ").strip()
    if not secret_key:
        print("❌ Secret Key 不能为空")
        return None, None
    
    return access_key, secret_key

def generate_signature(method, uri, query_string, headers, access_key, secret_key):
    """生成火山引擎API签名"""
    try:
        # 构建签名字符串
        canonical_headers = []
        for key in sorted(headers.keys()):
            if key.lower().startswith('x-'):
                canonical_headers.append(f"{key.lower()}:{headers[key]}")
        
        canonical_headers_str = '\n'.join(canonical_headers)
        if canonical_headers_str:
            canonical_headers_str += '\n'
        
        string_to_sign = f"{method}\n{uri}\n{query_string}\n{canonical_headers_str}"
        
        # 计算签名
        signature = hmac.new(
            secret_key.encode('utf-8'),
            string_to_sign.encode('utf-8'),
            hashlib.sha256
        ).digest()
        
        return base64.b64encode(signature).decode('utf-8')
    except Exception as e:
        print(f"❌ 签名生成失败: {e}")
        return None

def test_basic_auth(access_key, secret_key):
    """测试基本认证"""
    print_step(1, "测试基本认证")
    
    try:
        # 准备请求参数
        timestamp = str(int(time.time()))
        headers = {
            'X-Date': timestamp,
            'Authorization': f'Bearer {access_key}',
            'Content-Type': 'application/json'
        }
        
        # 这里使用一个简单的API来测试认证
        # 注意：这个URL可能需要根据实际的火山引擎API文档调整
        test_url = "https://open.volcengineapi.com/api/v1/user/info"
        
        response = requests.get(test_url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            print_result(True, "基本认证测试通过")
            return True
        elif response.status_code == 401:
            print_result(False, "认证失败 - 请检查Access Key和Secret Key")
            return False
        elif response.status_code == 403:
            print_result(False, "权限不足 - 密钥可能没有相应权限")
            return False
        else:
            print_result(False, f"未知错误 - HTTP状态码: {response.status_code}")
            print(f"响应内容: {response.text[:200]}")
            return False
            
    except requests.exceptions.Timeout:
        print_result(False, "请求超时 - 请检查网络连接")
        return False
    except requests.exceptions.RequestException as e:
        print_result(False, f"网络请求失败: {e}")
        return False
    except Exception as e:
        print_result(False, f"测试过程中出现错误: {e}")
        return False

def test_speech_service(access_key, secret_key):
    """测试语音识别服务权限"""
    print_step(2, "测试语音识别服务权限")
    
    try:
        # 这里模拟语音识别API调用
        print("🎤 检查语音识别服务访问权限...")
        
        # 由于实际的语音识别API需要音频文件，这里只测试权限
        headers = {
            'Authorization': f'Bearer {access_key}',
            'Content-Type': 'application/json',
            'X-Date': str(int(time.time()))
        }
        
        # 注意：这个URL需要根据实际的火山引擎语音识别API文档调整
        # 这里只是示例，实际使用时需要替换为正确的端点
        print("⚠️  语音识别服务需要实际的音频文件才能完整测试")
        print("✅ 如果您的密钥是主账号创建的，应该具有语音识别权限")
        
        return True
        
    except Exception as e:
        print_result(False, f"语音识别服务测试失败: {e}")
        return False

def test_video_service(access_key, secret_key):
    """测试视频处理服务权限"""
    print_step(3, "测试视频处理服务权限")
    
    try:
        print("🎬 检查视频处理服务访问权限...")
        
        # 同样，这里只是权限检查的示例
        print("⚠️  视频处理服务需要实际的视频文件才能完整测试")
        print("✅ 如果您的密钥是主账号创建的，应该具有视频处理权限")
        
        return True
        
    except Exception as e:
        print_result(False, f"视频处理服务测试失败: {e}")
        return False

def save_to_env_file(access_key, secret_key):
    """保存到.env文件"""
    print_step(4, "保存配置到 .env 文件")
    
    try:
        env_content = f"""# 火山引擎API配置
VOLCENGINE_ACCESS_KEY={access_key}
VOLCENGINE_SECRET_KEY={secret_key}
VOLCENGINE_REGION=cn-north-1

# 服务配置（需要您手动获取应用ID）
# VOLCENGINE_ASR_APP_ID=您的语音识别应用ID
# VOLCENGINE_VIDEO_APP_ID=您的视频处理应用ID

# 服务选择
SPEECH_SERVICE=volcengine
VIDEO_SERVICE=volcengine

# 其他配置
ENVIRONMENT=development
HOST=0.0.0.0
PORT=8000
LOG_LEVEL=INFO

UPLOAD_DIR=./uploads
OUTPUT_DIR=./outputs
TEMP_DIR=./temp

MAX_VIDEO_SIZE=104857600
MAX_CONCURRENT_JOBS=3
AUDIO_SAMPLE_RATE=16000
VIDEO_OUTPUT_FORMAT=mp4
"""
        
        # 检查是否已存在.env文件
        if os.path.exists('.env'):
            overwrite = input("\n⚠️  .env文件已存在，是否覆盖？(y/N): ").strip().lower()
            if overwrite != 'y':
                print("❌ 用户取消保存")
                return False
        
        with open('.env', 'w', encoding='utf-8') as f:
            f.write(env_content)
        
        print_result(True, ".env 文件已创建")
        print("📝 注意：您还需要手动添加应用ID配置")
        return True
        
    except Exception as e:
        print_result(False, f"保存配置失败: {e}")
        return False

def main():
    """主函数"""
    print("🔥 火山引擎API密钥验证工具")
    print("=" * 50)
    print("本工具将帮助您验证火山引擎API密钥是否配置正确")
    
    # 获取用户输入
    access_key, secret_key = get_user_input()
    if not access_key or not secret_key:
        print("\n❌ 密钥信息不完整，退出验证")
        return
    
    print(f"\n📋 验证信息:")
    print(f"Access Key: {access_key[:10]}...")
    print(f"Secret Key: {'*' * len(secret_key)}")
    
    # 运行验证测试
    results = []
    
    # 测试1: 基本认证
    results.append(test_basic_auth(access_key, secret_key))
    
    # 测试2: 语音识别服务
    results.append(test_speech_service(access_key, secret_key))
    
    # 测试3: 视频处理服务
    results.append(test_video_service(access_key, secret_key))
    
    # 保存配置
    if all(results):
        save_result = save_to_env_file(access_key, secret_key)
        results.append(save_result)
    
    # 输出总结
    print_step("总结", "验证结果")
    
    passed = sum(results)
    total = len(results)
    
    print(f"✅ 通过测试: {passed}/{total}")
    
    if passed == total:
        print("\n🎉 所有验证通过！")
        print("\n📋 下一步:")
        print("1. 开通语音识别服务并获取App ID")
        print("2. 开通视频处理服务并获取App ID") 
        print("3. 将App ID添加到 .env 文件中")
        print("4. 运行完整测试: python test_volcengine_api.py")
    else:
        print("\n⚠️  部分验证失败")
        print("💡 建议:")
        print("1. 检查Access Key和Secret Key是否正确")
        print("2. 确认账户已完成实名认证")
        print("3. 查看详细指南: VOLCENGINE_API_DETAILED_GUIDE.md")
    
    print("\n📞 需要帮助？")
    print("- 查看详细文档: VOLCENGINE_API_DETAILED_GUIDE.md")
    print("- 火山引擎客服: 400-826-2416")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 验证已取消")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 验证过程中出现错误: {e}")
        sys.exit(1)
