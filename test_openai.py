#!/usr/bin/env python3
import sys
sys.path.append('.')

from app.config.settings import settings
from openai import OpenAI

def test_openai_api():
    print("=== OpenAI API 测试 ===")
    
    print(f"API Key: {settings.OPENAI_API_KEY[:20]}..." if settings.OPENAI_API_KEY else "未设置")
    
    if not settings.OPENAI_API_KEY:
        print("❌ OpenAI API Key 未配置")
        return
    
    try:
        client = OpenAI(api_key=settings.OPENAI_API_KEY)
        
        # 测试简单的API调用
        print("🔍 测试API连接...")
        
        # 创建一个简单的测试音频文件
        import tempfile
        import wave
        import numpy as np
        
        # 生成1秒的静音音频
        sample_rate = 16000
        duration = 1  # 1秒
        samples = np.zeros(sample_rate * duration, dtype=np.int16)
        
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
            with wave.open(temp_file.name, 'w') as wav_file:
                wav_file.setnchannels(1)  # 单声道
                wav_file.setsampwidth(2)  # 16位
                wav_file.setframerate(sample_rate)
                wav_file.writeframes(samples.tobytes())
            
            print(f"📄 创建测试音频文件: {temp_file.name}")
            
            # 测试Whisper API
            with open(temp_file.name, "rb") as audio_file:
                transcript = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    response_format="text"
                )
                
            print(f"✅ API调用成功")
            print(f"📝 转录结果: '{transcript}' (静音音频，结果为空是正常的)")
            
    except Exception as e:
        print(f"❌ API测试失败: {e}")
        
        # 检查是否是认证问题
        if "401" in str(e) or "Unauthorized" in str(e):
            print("💡 这是认证问题，请检查API密钥是否正确")
        elif "quota" in str(e).lower():
            print("💡 这是配额问题，请检查OpenAI账户余额")
        else:
            print("💡 这可能是网络或其他问题")

if __name__ == "__main__":
    test_openai_api()
