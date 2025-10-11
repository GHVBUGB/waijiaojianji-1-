#!/usr/bin/env python3
import sys
sys.path.append('.')

try:
    from app.config.settings import settings
    print("配置加载测试:")
    print(f"TENCENT_SECRET_ID: {settings.TENCENT_SECRET_ID[:10] if settings.TENCENT_SECRET_ID else 'None'}...")
    print(f"TENCENT_COS_BUCKET: {settings.TENCENT_COS_BUCKET}")
    print(f"TENCENT_APP_ID: {settings.TENCENT_APP_ID}")
    print(f"TENCENT_REGION: {settings.TENCENT_REGION}")
    print("\n腾讯云万象服务测试:")
    
    from app.services.tencent_video_service import TencentVideoService
    service = TencentVideoService()
    print(f"服务初始化成功")
    print(f"Secret ID: {service.secret_id[:10] if service.secret_id else 'None'}...")
    print(f"COS Bucket: {service.bucket_name}")
    print(f"APP ID: {service.app_id}")
    print(f"Region: {service.region}")
    
    if service.secret_id and service.secret_key and service.bucket_name:
        print("✅ 配置完整，可以使用腾讯云万象API")
    else:
        print("❌ 配置不完整")
        if not service.secret_id:
            print("  - 缺少 TENCENT_SECRET_ID")
        if not service.secret_key:
            print("  - 缺少 TENCENT_SECRET_KEY")
        if not service.bucket_name:
            print("  - 缺少 TENCENT_COS_BUCKET")
            
except Exception as e:
    print(f"配置加载失败: {e}")
    import traceback
    traceback.print_exc()
