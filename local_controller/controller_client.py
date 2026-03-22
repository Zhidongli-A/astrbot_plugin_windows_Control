#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Windows 本地控制端程序 - 客户端模式
主动连接到 AstrBot 服务器，接收命令并执行鼠标/键盘操作
"""

import asyncio
import websockets
import json
import sys
import os
from pathlib import Path
from datetime import datetime

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from input_controller import InputController
from screen_capture import ScreenCapture


class LocalControllerClient:
    """本地控制端客户端 - 主动连接服务器"""
    
    def __init__(self, server_host: str, server_port: int = 7365):
        self.server_host = server_host
        self.server_port = server_port
        self.server_uri = f"ws://{server_host}:{server_port}"
        self.websocket = None
        self.connected = False
        self.running = False
        self.reconnect_interval = 5  # 重连间隔（秒）
        
        self.input_controller = InputController()
        self.screen_capture = ScreenCapture()
        
    async def connect(self) -> bool:
        """连接到服务器"""
        try:
            logger.info(f"正在连接到服务器: {self.server_uri}")
            self.websocket = await websockets.connect(
                self.server_uri,
                ping_interval=20,
                ping_timeout=10
            )
            self.connected = True
            logger.info(f"✅ 已连接到服务器: {self.server_uri}")
            return True
        except Exception as e:
            logger.error(f"❌ 连接服务器失败: {str(e)}")
            self.connected = False
            return False
            
    async def disconnect(self):
        """断开连接"""
        if self.websocket:
            try:
                await self.websocket.close()
            except:
                pass
        self.connected = False
        logger.info("已断开与服务器的连接")
        
    async def run(self):
        """主运行循环"""
        self.running = True
        logger.info("Windows 本地控制端启动")
        
        while self.running:
            try:
                # 尝试连接
                if not await self.connect():
                    logger.info(f"{self.reconnect_interval}秒后重试...")
                    await asyncio.sleep(self.reconnect_interval)
                    continue
                
                # 处理消息
                await self.handle_messages()
                
            except websockets.exceptions.ConnectionClosed:
                logger.warning("与服务器的连接已断开")
                self.connected = False
            except Exception as e:
                logger.error(f"运行时出错: {str(e)}")
                self.connected = False
                
            if self.running:
                logger.info(f"{self.reconnect_interval}秒后尝试重连...")
                await asyncio.sleep(self.reconnect_interval)
                
    async def handle_messages(self):
        """处理服务器消息"""
        async for message in self.websocket:
            try:
                data = json.loads(message)
                msg_type = data.get("type", "unknown")
                
                if msg_type == "command":
                    # 执行命令
                    await self.execute_command(data)
                elif msg_type == "ping":
                    # 响应心跳
                    await self.websocket.send(json.dumps({"type": "pong"}))
                else:
                    logger.warning(f"未知消息类型: {msg_type}")
                    
            except json.JSONDecodeError as e:
                logger.error(f"收到无效的 JSON: {message}")
                await self.send_error("无效的 JSON 格式")
            except Exception as e:
                logger.error(f"处理消息时出错: {str(e)}")
                await self.send_error(str(e))
                
    async def execute_command(self, command: dict):
        """执行控制命令"""
        action = command.get("action")
        params = command.get("params", {})
        
        logger.info(f"执行命令: {action}")
        
        try:
            if action == "mouse_move":
                result = self.cmd_mouse_move(params)
            elif action == "mouse_click":
                result = self.cmd_mouse_click(params)
            elif action == "mouse_down":
                result = self.cmd_mouse_down(params)
            elif action == "mouse_up":
                result = self.cmd_mouse_up(params)
            elif action == "key_press":
                result = self.cmd_key_press(params)
            elif action == "type_string":
                result = self.cmd_type_string(params)
            elif action == "screenshot":
                result = self.cmd_screenshot()
            elif action == "get_screen_size":
                result = self.cmd_get_screen_size()
            elif action == "get_mouse_position":
                result = self.cmd_get_mouse_position()
            else:
                raise ValueError(f"未知的命令: {action}")
                
            # 发送成功响应
            response = {
                "type": "result",
                "status": "success",
                "action": action,
                "result": result,
                "timestamp": datetime.now().isoformat()
            }
            await self.websocket.send(json.dumps(response))
            logger.info(f"命令执行完成: {action}")
            
        except Exception as e:
            logger.error(f"命令执行失败: {str(e)}")
            await self.send_error(str(e), action)
            
    async def send_error(self, error_msg: str, action: str = None):
        """发送错误响应"""
        response = {
            "type": "result",
            "status": "error",
            "action": action,
            "error": error_msg,
            "timestamp": datetime.now().isoformat()
        }
        try:
            await self.websocket.send(json.dumps(response))
        except:
            pass
            
    # ==================== 命令实现 ====================
    
    def cmd_mouse_move(self, params: dict) -> dict:
        """鼠标移动"""
        x = params.get("x", 0)
        y = params.get("y", 0)
        duration = params.get("duration", 0.5)
        
        self.input_controller.move_mouse(x, y, duration)
        screenshot = self.screen_capture.capture()
        
        return {
            "message": f"鼠标已移动到 ({x}, {y})",
            "screenshot": screenshot
        }
        
    def cmd_mouse_click(self, params: dict) -> dict:
        """鼠标点击"""
        button = params.get("button", "left")
        clicks = params.get("clicks", 1)
        interval = params.get("interval", 0.1)
        
        self.input_controller.click_mouse(button, clicks, interval)
        screenshot = self.screen_capture.capture()
        
        return {
            "message": f"已执行 {button} 键点击 {clicks} 次",
            "screenshot": screenshot
        }
        
    def cmd_mouse_down(self, params: dict) -> dict:
        """鼠标按下"""
        button = params.get("button", "left")
        self.input_controller.mouse_down(button)
        screenshot = self.screen_capture.capture()
        
        return {
            "message": f"已按下 {button} 键",
            "screenshot": screenshot
        }
        
    def cmd_mouse_up(self, params: dict) -> dict:
        """鼠标释放"""
        button = params.get("button", "left")
        self.input_controller.mouse_up(button)
        screenshot = self.screen_capture.capture()
        
        return {
            "message": f"已释放 {button} 键",
            "screenshot": screenshot
        }
        
    def cmd_key_press(self, params: dict) -> dict:
        """按键输入"""
        key = params.get("key", "")
        self.input_controller.press_key(key)
        screenshot = self.screen_capture.capture()
        
        return {
            "message": f"已按下按键: {key}",
            "screenshot": screenshot
        }
        
    def cmd_type_string(self, params: dict) -> dict:
        """输入字符串"""
        text = params.get("text", "")
        interval = params.get("interval", 0.01)
        
        self.input_controller.type_string(text, interval)
        screenshot = self.screen_capture.capture()
        
        return {
            "message": f"已输入文本: {text}",
            "screenshot": screenshot
        }
        
    def cmd_screenshot(self) -> dict:
        """屏幕截图"""
        screenshot = self.screen_capture.capture()
        return {
            "message": "截图完成",
            "screenshot": screenshot
        }
        
    def cmd_get_screen_size(self) -> dict:
        """获取屏幕尺寸"""
        size = self.screen_capture.get_screen_size()
        return {
            "message": f"屏幕尺寸: {size['width']}x{size['height']}",
            "screen_size": size
        }
        
    def cmd_get_mouse_position(self) -> dict:
        """获取鼠标位置"""
        pos = self.input_controller.get_mouse_position()
        return {
            "message": f"鼠标位置: ({pos['x']}, {pos['y']})",
            "position": pos
        }
        
    def stop(self):
        """停止客户端"""
        self.running = False
        logger.info("客户端正在停止...")


# 简单的日志记录器
class SimpleLogger:
    @staticmethod
    def info(msg: str):
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [INFO] {msg}")
        
    @staticmethod
    def warning(msg: str):
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [WARN] {msg}")
        
    @staticmethod
    def error(msg: str):
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [ERROR] {msg}")


logger = SimpleLogger()


async def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Windows 本地控制端 - 客户端模式")
    parser.add_argument("--server", "-s", required=True, help="AstrBot 服务器地址（公网IP或域名）")
    parser.add_argument("--port", "-p", type=int, default=7365, help="服务器端口 (默认: 7365)")
    args = parser.parse_args()
    
    client = LocalControllerClient(server_host=args.server, server_port=args.port)
    
    try:
        await client.run()
    except KeyboardInterrupt:
        print("\n接收到停止信号")
        client.stop()


if __name__ == "__main__":
    asyncio.run(main())
