#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
屏幕截图模块
提供高质量的屏幕截图功能
"""

import pyautogui
import base64
from io import BytesIO
from typing import Optional, Tuple
from PIL import Image


class ScreenCapture:
    """屏幕截图类"""
    
    def __init__(self):
        pass
        
    def capture(self, region: Optional[Tuple[int, int, int, int]] = None, 
                quality: int = 85, 
                resize: Optional[Tuple[int, int]] = None) -> str:
        """
        截取屏幕并返回 base64 编码的图像
        
        Args:
            region: 截图区域 (left, top, width, height)，None 表示全屏
            quality: JPEG 质量 (1-100)
            resize: 调整尺寸 (width, height)，None 表示不调整
            
        Returns:
            base64 编码的图像字符串 (data:image/jpeg;base64,...)
        """
        # 截取屏幕
        if region:
            screenshot = pyautogui.screenshot(region=region)
        else:
            screenshot = pyautogui.screenshot()
            
        # 调整尺寸（如果需要）
        if resize:
            screenshot = screenshot.resize(resize, Image.Resampling.LANCZOS)
            
        # 转换为 JPEG 并压缩
        buffer = BytesIO()
        screenshot.convert("RGB").save(buffer, format="JPEG", quality=quality, optimize=True)
        buffer.seek(0)
        
        # 转换为 base64
        img_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
        
        return f"data:image/jpeg;base64,{img_base64}"
        
    def capture_region(self, left: int, top: int, width: int, height: int,
                       quality: int = 85) -> str:
        """
        截取指定区域屏幕
        
        Args:
            left: 左上角 X 坐标
            top: 左上角 Y 坐标
            width: 区域宽度
            height: 区域高度
            quality: JPEG 质量
            
        Returns:
            base64 编码的图像字符串
        """
        return self.capture(region=(left, top, width, height), quality=quality)
        
    def capture_at_mouse(self, width: int = 400, height: int = 300,
                         quality: int = 85) -> str:
        """
        截取鼠标周围区域
        
        Args:
            width: 区域宽度
            height: 区域高度
            quality: JPEG 质量
            
        Returns:
            base64 编码的图像字符串
        """
        mouse_x, mouse_y = pyautogui.position()
        left = max(0, mouse_x - width // 2)
        top = max(0, mouse_y - height // 2)
        
        return self.capture(region=(left, top, width, height), quality=quality)
        
    def get_screen_size(self) -> dict:
        """
        获取屏幕尺寸
        
        Returns:
            包含 width 和 height 的字典
        """
        size = pyautogui.size()
        return {"width": size.width, "height": size.height}
        
    def save_screenshot(self, filepath: str, 
                        region: Optional[Tuple[int, int, int, int]] = None,
                        format: str = "PNG") -> str:
        """
        保存截图到文件
        
        Args:
            filepath: 保存路径
            region: 截图区域
            format: 图像格式 (PNG, JPEG, BMP)
            
        Returns:
            保存的文件路径
        """
        if region:
            screenshot = pyautogui.screenshot(region=region)
        else:
            screenshot = pyautogui.screenshot()
            
        screenshot.save(filepath, format=format)
        return filepath


# 测试代码
if __name__ == "__main__":
    import time
    
    print("3秒后开始截图测试...")
    time.sleep(3)
    
    capture = ScreenCapture()
    
    # 测试全屏截图
    print("测试全屏截图...")
    screen_size = capture.get_screen_size()
    print(f"屏幕尺寸: {screen_size['width']}x{screen_size['height']}")
    
    img_base64 = capture.capture()
    print(f"截图完成，base64长度: {len(img_base64)}")
    
    # 测试区域截图
    print("测试区域截图...")
    img_base64_region = capture.capture_region(100, 100, 400, 300)
    print(f"区域截图完成，base64长度: {len(img_base64_region)}")
    
    # 测试鼠标周围截图
    print("测试鼠标周围截图...")
    img_base64_mouse = capture.capture_at_mouse()
    print(f"鼠标周围截图完成，base64长度: {len(img_base64_mouse)}")
    
    print("测试完成")
