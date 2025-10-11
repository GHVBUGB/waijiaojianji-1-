# 腾讯云API配置指南

## 📋 概述

本指南将帮助您配置腾讯云API，用于视频背景处理功能。

## 🔑 API密钥配置

### 获取API密钥

1. 登录腾讯云控制台
2. 访问访问管理 > API密钥管理
3. 创建新的API密钥

### 配置格式

在 `env_config.txt` 文件中配置您的API密钥：

```bash
TENCENT_SECRET_ID=your_secret_id_here
TENCENT_SECRET_KEY=your_secret_key_here
TENCENT_REGION=ap-beijing
```

### 密钥格式说明

- SecretId: 以字母开头的32位字符串
- SecretKey: 32位随机字符串
- Region: 选择最近的服务区域

## 💰 费用说明

使用腾讯云视频处理服务会产生费用，请确保账户有足够余额。

## 🔒 安全提醒

- 请妥善保管您的API密钥
- 不要将密钥提交到版本控制系统
- 定期更换API密钥以确保安全