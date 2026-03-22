#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
鼠标和键盘控制器
封装 pyautogui 提供统一的输入控制接口
"""

import pyautogui
import time
from typing import Optional, Tuple

# 配置 pyautogui
pyautogui.FAILSAFE = True  # 启用故障保护（将鼠标移到屏幕角落会抛出异常）
pyautogui.PAUSE = 0.1  # 每次操作后的默认暂停时间


class InputController:
    """输入控制器类"""
    
    def __init__(self):
        # 按钮映射
        self.button_map = {
            "left": "left",
            "right": "right",
            "middle": "middle",
            "左键": "left",
            "右键": "right",
            "中键": "middle"
        }
        
        # 特殊按键映射
        self.key_map = {
            # 功能键
            "enter": "enter",
            "return": "return",
            "esc": "esc",
            "escape": "esc",
            "tab": "tab",
            "space": "space",
            "backspace": "backspace",
            "delete": "delete",
            "del": "delete",
            "insert": "insert",
            "ins": "insert",
            "home": "home",
            "end": "end",
            "pageup": "pageup",
            "pagedown": "pagedown",
            # 方向键
            "up": "up",
            "down": "down",
            "left": "left",
            "right": "right",
            # 修饰键
            "shift": "shift",
            "ctrl": "ctrl",
            "control": "ctrl",
            "alt": "alt",
            "win": "win",
            "windows": "win",
            "command": "command",
            "cmd": "command",
            "option": "option",
            # F键
            "f1": "f1", "f2": "f2", "f3": "f3", "f4": "f4",
            "f5": "f5", "f6": "f6", "f7": "f7", "f8": "f8",
            "f9": "f9", "f10": "f10", "f11": "f11", "f12": "f12",
            # 其他常用键
            "capslock": "capslock",
            "numlock": "numlock",
            "scrolllock": "scrolllock",
            "printscreen": "printscreen",
            "pause": "pause",
            "break": "break",
        }
        
    def move_mouse(self, x: int, y: int, duration: float = 0.5):
        """
        移动鼠标到指定位置
        
        Args:
            x: 目标 X 坐标
            y: 目标 Y 坐标
            duration: 移动动画持续时间（秒）
        """
        pyautogui.moveTo(x, y, duration=duration)
        
    def move_mouse_relative(self, x_offset: int, y_offset: int, duration: float = 0.5):
        """
        相对当前位置移动鼠标
        
        Args:
            x_offset: X 轴偏移量
            y_offset: Y 轴偏移量
            duration: 移动动画持续时间（秒）
        """
        pyautogui.moveRel(x_offset, y_offset, duration=duration)
        
    def click_mouse(self, button: str = "left", clicks: int = 1, interval: float = 0.1):
        """
        鼠标点击
        
        Args:
            button: 按钮类型 (left/right/middle)
            clicks: 点击次数
            interval: 多次点击之间的间隔（秒）
        """
        btn = self.button_map.get(button.lower(), button.lower())
        pyautogui.click(button=btn, clicks=clicks, interval=interval)
        
    def mouse_down(self, button: str = "left"):
        """
        鼠标按下（不释放）
        
        Args:
            button: 按钮类型 (left/right/middle)
        """
        btn = self.button_map.get(button.lower(), button.lower())
        pyautogui.mouseDown(button=btn)
        
    def mouse_up(self, button: str = "left"):
        """
        鼠标释放
        
        Args:
            button: 按钮类型 (left/right/middle)
        """
        btn = self.button_map.get(button.lower(), button.lower())
        pyautogui.mouseUp(button=btn)
        
    def double_click(self, button: str = "left"):
        """
        双击鼠标
        
        Args:
            button: 按钮类型 (left/right/middle)
        """
        btn = self.button_map.get(button.lower(), button.lower())
        pyautogui.doubleClick(button=btn)
        
    def scroll(self, amount: int, x: Optional[int] = None, y: Optional[int] = None):
        """
        滚动鼠标滚轮
        
        Args:
            amount: 滚动量（正数向上，负数向下）
            x: 滚动时的鼠标 X 坐标（可选）
            y: 滚动时的鼠标 Y 坐标（可选）
        """
        if x is not None and y is not None:
            pyautogui.scroll(amount, x=x, y=y)
        else:
            pyautogui.scroll(amount)
            
    def get_mouse_position(self) -> dict:
        """
        获取当前鼠标位置
        
        Returns:
            包含 x, y 坐标的字典
        """
        x, y = pyautogui.position()
        return {"x": x, "y": y}
        
    def press_key(self, key: str):
        """
        按下并释放按键（单键或组合键）
        
        Args:
            key: 按键名称，组合键用 + 连接，如 "ctrl+c", "alt+tab"
        """
        # 解析组合键
        if "+" in key:
            keys = [k.strip().lower() for k in key.split("+")]
            # 转换按键名称
            keys = [self.key_map.get(k, k) for k in keys]
            # 按下所有修饰键，然后按下主键，最后释放
            pyautogui.hotkey(*keys)
        else:
            # 单键
            key_normalized = self.key_map.get(key.lower(), key.lower())
            pyautogui.press(key_normalized)
            
    def key_down(self, key: str):
        """
        按下按键（不释放）
        
        Args:
            key: 按键名称
        """
        key_normalized = self.key_map.get(key.lower(), key.lower())
        pyautogui.keyDown(key_normalized)
        
    def key_up(self, key: str):
        """
        释放按键
        
        Args:
            key: 按键名称
        """
        key_normalized = self.key_map.get(key.lower(), key.lower())
        pyautogui.keyUp(key_normalized)
        
    def type_string(self, text: str, interval: float = 0.01):
        """
        输入字符串（模拟键盘输入）
        
        Args:
            text: 要输入的文本
            interval: 每个字符之间的间隔（秒）
        """
        pyautogui.typewrite(text, interval=interval)
        
    def type_string_with_interval(self, text: str, interval: float = 0.1):
        """
        输入字符串（带较长间隔，适合需要明显输入效果的场景）
        
        Args:
            text: 要输入的文本
            interval: 每个字符之间的间隔（秒）
        """
        pyautogui.typewrite(text, interval=interval)


# 测试代码
if __name__ == "__main__":
    import time
    
    print("3秒后开始测试...")
    time.sleep(3)
    
    controller = InputController()
    
    # 测试鼠标移动
    print("测试鼠标移动...")
    controller.move_mouse(500, 500)
    time.sleep(1)
    
    # 测试点击
    print("测试鼠标点击...")
    controller.click_mouse("left")
    time.sleep(1)
    
    # 测试键盘输入
    print("测试键盘输入...")
    controller.type_string("Hello World!")
    time.sleep(1)
    
    # 测试组合键
    print("测试组合键...")
    controller.press_key("ctrl+a")
    
    print("测试完成")
