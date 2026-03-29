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
                quality: int = 85) -> str:
        """
        截取屏幕并返回 base64 编码的图像
        
        Args:
            region: 截图区域 (left, top, width, height)，None 表示全屏
            quality: JPEG 质量 (1-100)
            
        Returns:
            base64 编码的图像字符串 (data:image/jpeg;base64,...)
        """
        # 截取屏幕
        if region:
            screenshot = pyautogui.screenshot(region=region)
        else:
            screenshot = pyautogui.screenshot()
            
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
