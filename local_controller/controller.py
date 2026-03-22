#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Windows 本地控制端程序
常驻运行，接收远程命令并执行鼠标/键盘操作
"""

import asyncio
import websockets
import json
import base64
import io
import sys
import os
from pathlib import Path
from datetime import datetime

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from input_controller import InputController
from screen_capture import ScreenCapture


class LocalController:
    """本地控制端主类"""
    
    def __init__(self, host="0.0.0.0", port=8765):
        self.host = host
        self.port = port
        self.input_controller = InputController()
        self.screen_capture = ScreenCapture()
        self.clients = set()
        self.running = False
        
    async def handle_client(self, websocket, path):
        """处理客户端连接"""
        self.clients.add(websocket)
        client_addr = websocket.remote_address
        print(f"[{datetime.now()}] 客户端已连接: {client_addr}")
        
        try:
            async for message in websocket:
                try:
                    # 解析命令
                    command = json.loads(message)
                    print(f"[{datetime.now()}] 收到命令: {command.get('action')}")
                    
                    # 执行命令
                    result = await self.execute_command(command)
                    
                    # 发送结果
                    response = {
                        "status": "success",
                        "action": command.get("action"),
                        "result": result,
                        "timestamp": datetime.now().isoformat()
                    }
                    await websocket.send(json.dumps(response))
                    print(f"[{datetime.now()}] 命令执行完成: {command.get('action')}")
                    
                except json.JSONDecodeError as e:
                    error_response = {
                        "status": "error",
                        "error": f"无效的JSON格式: {str(e)}",
                        "timestamp": datetime.now().isoformat()
                    }
                    await websocket.send(json.dumps(error_response))
                    
                except Exception as e:
                    error_response = {
                        "status": "error",
                        "error": str(e),
                        "timestamp": datetime.now().isoformat()
                    }
                    await websocket.send(json.dumps(error_response))
                    print(f"[{datetime.now()}] 命令执行错误: {str(e)}")
                    
        except websockets.exceptions.ConnectionClosed:
            print(f"[{datetime.now()}] 客户端断开连接: {client_addr}")
        finally:
            self.clients.discard(websocket)
            
    async def execute_command(self, command: dict) -> dict:
        """执行控制命令"""
        action = command.get("action")
        params = command.get("params", {})
        
        if action == "mouse_move":
            # 鼠标移动
            x = params.get("x", 0)
            y = params.get("y", 0)
            duration = params.get("duration", 0.5)
            self.input_controller.move_mouse(x, y, duration)
            
            # 截图返回
            screenshot = self.screen_capture.capture()
            return {
                "message": f"鼠标已移动到 ({x}, {y})",
                "screenshot": screenshot
            }
            
        elif action == "mouse_click":
            # 鼠标点击
            button = params.get("button", "left")  # left, right, middle
            clicks = params.get("clicks", 1)
            interval = params.get("interval", 0.1)
            self.input_controller.click_mouse(button, clicks, interval)
            
            screenshot = self.screen_capture.capture()
            return {
                "message": f"已执行 {button} 键点击 {clicks} 次",
                "screenshot": screenshot
            }
            
        elif action == "mouse_down":
            # 鼠标按下
            button = params.get("button", "left")
            self.input_controller.mouse_down(button)
            
            screenshot = self.screen_capture.capture()
            return {
                "message": f"已按下 {button} 键",
                "screenshot": screenshot
            }
            
        elif action == "mouse_up":
            # 鼠标释放
            button = params.get("button", "left")
            self.input_controller.mouse_up(button)
            
            screenshot = self.screen_capture.capture()
            return {
                "message": f"已释放 {button} 键",
                "screenshot": screenshot
            }
            
        elif action == "key_press":
            # 按键输入（单键或组合键）
            key = params.get("key", "")
            self.input_controller.press_key(key)
            
            screenshot = self.screen_capture.capture()
            return {
                "message": f"已按下按键: {key}",
                "screenshot": screenshot
            }
            
        elif action == "type_string":
            # 输入字符串
            text = params.get("text", "")
            interval = params.get("interval", 0.01)
            self.input_controller.type_string(text, interval)
            
            screenshot = self.screen_capture.capture()
            return {
                "message": f"已输入文本: {text}",
                "screenshot": screenshot
            }
            
        elif action == "screenshot":
            # 仅截图
            screenshot = self.screen_capture.capture()
            return {
                "message": "截图完成",
                "screenshot": screenshot
            }
            
        elif action == "get_screen_size":
            # 获取屏幕尺寸
            size = self.screen_capture.get_screen_size()
            return {
                "message": f"屏幕尺寸: {size['width']}x{size['height']}",
                "screen_size": size
            }
            
        elif action == "get_mouse_position":
            # 获取鼠标位置
            pos = self.input_controller.get_mouse_position()
            return {
                "message": f"鼠标位置: ({pos['x']}, {pos['y']})",
                "position": pos
            }
            
        else:
            raise ValueError(f"未知的命令: {action}")
            
    async def start(self):
        """启动控制端服务"""
        self.running = True
        print(f"[{datetime.now()}] Windows 本地控制端启动中...")
        print(f"[{datetime.now()}] 监听地址: {self.host}:{self.port}")
        
        async with websockets.serve(self.handle_client, self.host, self.port):
            print(f"[{datetime.now()}] 服务已启动，等待连接...")
            while self.running:
                await asyncio.sleep(1)
                
    def stop(self):
        """停止控制端服务"""
        self.running = False
        print(f"[{datetime.now()}] 服务正在停止...")


async def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Windows 本地控制端")
    parser.add_argument("--host", default="0.0.0.0", help="监听地址 (默认: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8765, help="监听端口 (默认: 8765)")
    args = parser.parse_args()
    
    controller = LocalController(host=args.host, port=args.port)
    
    try:
        await controller.start()
    except KeyboardInterrupt:
        print("\n接收到停止信号")
        controller.stop()


if __name__ == "__main__":
    asyncio.run(main())
