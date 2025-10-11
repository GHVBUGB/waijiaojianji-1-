#!/usr/bin/env python3
"""
创建黄色背景图片
"""

from PIL import Image, ImageDraw, ImageFont
import os

def create_sitalk_background():
    """创建SITalk黄色背景图片"""
    
    # 创建1024x768的图片
    width, height = 1024, 768
    img = Image.new('RGB', (width, height), color='#E6D635')  # 黄色背景
    
    draw = ImageDraw.Draw(img)
    
    # 绘制主要的椭圆形区域
    ellipse_bbox = [112, 84, 912, 684]  # (left, top, right, bottom)
    draw.ellipse(ellipse_bbox, fill='#F5F5DC', outline='#4A90E2', width=8)
    
    # 绘制左上角的蓝色装饰
    left_decoration = [(100, 50), (200, 80), (300, 120), (250, 180), (180, 200), (120, 150)]
    draw.polygon(left_decoration, fill='#4A90E2')
    
    # 绘制右下角的白色装饰
    right_decoration = [(750, 600), (850, 620), (920, 650), (880, 720), (800, 730), (720, 680)]
    draw.polygon(right_decoration, fill='#FFFFFF')
    
    # 绘制右上角的蓝色装饰
    top_right_decoration = [(850, 100), (950, 130), (980, 180), (920, 220), (850, 200), (800, 150)]
    draw.polygon(top_right_decoration, fill='#4A90E2')
    
    # 尝试添加文字（如果字体不可用，会跳过）
    try:
        # 尝试使用系统字体
        font_size = 48
        try:
            font = ImageFont.truetype("arial.ttf", font_size)
        except:
            try:
                font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", font_size)
            except:
                font = ImageFont.load_default()
        
        # 绘制SITalk文字
        draw.text((60, 50), "SITalk", fill='#4A90E2', font=font)
        
    except Exception as e:
        print(f"无法添加文字: {e}")
    
    # 绘制小星星
    star_points = [(150, 120), (155, 130), (165, 130), (157, 137), (160, 147), (150, 141), (140, 147), (143, 137), (135, 130), (145, 130)]
    draw.polygon(star_points, fill='#FFFFFF')
    
    # 绘制猴子头像（简化版）
    # 头部背景圆
    draw.ellipse([845, 15, 915, 85], fill='#4A90E2')
    # 猴子脸
    draw.ellipse([855, 30, 905, 80], fill='#D2691E')
    # 眼睛
    draw.ellipse([863, 35, 869, 41], fill='#000000')
    draw.ellipse([891, 35, 897, 41], fill='#000000')
    # 嘴巴
    draw.ellipse([872, 60, 888, 70], fill='#FF6B6B')
    
    return img

def main():
    """主函数"""
    print("🎨 创建SITalk背景图片...")
    
    # 创建背景图片
    img = create_sitalk_background()
    
    # 保存图片
    output_path = r"C:\Users\guhongji001\Desktop\44\backgrounds\sitalk_background.png"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    img.save(output_path, 'PNG')
    print(f"✅ 背景图片已保存: {output_path}")
    
    # 显示图片信息
    print(f"📏 图片尺寸: {img.size}")
    print(f"📄 图片格式: {img.format}")
    print(f"📊 图片模式: {img.mode}")

if __name__ == "__main__":
    main()