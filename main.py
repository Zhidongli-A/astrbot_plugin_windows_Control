#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AstrBot Windows 远程控制插件
提供 LLM 工具调用接口，实现远程控制 Windows 电脑
"""

import asyncio
import websockets
import json
import base64
from datetime import datetime
from typing import Optional, Dict, Any

from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
import astrbot.api.message_components as Comp


class WebSocketClient:
    """WebSocket 客户端，用于连接本地控制端"""
    
    def __init__(self, host: str, port: int, timeout: int = 30):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.websocket: Optional[websockets.WebSocketClientProtocol] = None
        self.connected = False
        self.reconnect_interval = 5  # 重连间隔（秒）
        
    async def connect(self) -> bool:
        """连接到本地控制端"""
        try:
            uri = f"ws://{self.host}:{self.port}"
            self.websocket = await websockets.connect(uri, ping_interval=20, ping_timeout=10)
            self.connected = True
            logger.info(f"已连接到本地控制端: {uri}")
            return True
        except Exception as e:
            logger.error(f"连接本地控制端失败: {str(e)}")
            self.connected = False
            return False
            
    async def disconnect(self):
        """断开连接"""
        if self.websocket:
            await self.websocket.close()
            self.connected = False
            logger.info("已断开与本地控制端的连接")
            
    async def send_command(self, action: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        发送命令到本地控制端
        
        Args:
            action: 命令动作
            params: 命令参数
            
        Returns:
            执行结果
        """
        if not self.connected or not self.websocket:
            # 尝试重新连接
            if not await self.connect():
                return {"status": "error", "error": "未连接到本地控制端"}
        
        try:
            command = {
                "action": action,
                "params": params or {},
                "timestamp": datetime.now().isoformat()
            }
            
            await self.websocket.send(json.dumps(command))
            
            # 等待响应
            response = await asyncio.wait_for(
                self.websocket.recv(),
                timeout=self.timeout
            )
            
            return json.loads(response)
            
        except asyncio.TimeoutError:
            logger.error("命令执行超时")
            return {"status": "error", "error": "命令执行超时"}
        except websockets.exceptions.ConnectionClosed:
            logger.error("连接已关闭")
            self.connected = False
            return {"status": "error", "error": "连接已关闭"}
        except Exception as e:
            logger.error(f"发送命令失败: {str(e)}")
            return {"status": "error", "error": str(e)}
            
    async def ensure_connection(self) -> bool:
        """确保连接状态"""
        if not self.connected:
            return await self.connect()
        return True


@register("windows_control", "枝动力", "Windows 远程控制插件，支持鼠标键盘操作和屏幕截图", "2.0.0")
class WindowsControlPlugin(Star):
    """Windows 远程控制插件主类"""
    
    def __init__(self, context: Context):
        super().__init__(context)
        self.context = context
        self.ws_client: Optional[WebSocketClient] = None
        self.controller_host = "localhost"
        self.controller_port = 8765
        self.default_timeout = 30
        
    async def initialize(self):
        """插件初始化"""
        # 从配置中读取设置
        config = self.context.get_config()
        plugin_config = config.get("windows_control", {})
        
        self.controller_host = plugin_config.get("host", "localhost")
        self.controller_port = plugin_config.get("port", 8765)
        self.default_timeout = plugin_config.get("timeout", 30)
        
        # 初始化 WebSocket 客户端
        self.ws_client = WebSocketClient(
            host=self.controller_host,
            port=self.controller_port,
            timeout=self.default_timeout
        )
        
        logger.info(f"Windows 控制插件初始化完成，目标: {self.controller_host}:{self.controller_port}")
        
    async def terminate(self):
        """插件销毁"""
        if self.ws_client:
            await self.ws_client.disconnect()
        logger.info("Windows 控制插件已卸载")
        
    # ==================== 指令命令 ====================
    
    @filter.command("wconnect")
    async def connect_controller(self, event: AstrMessageEvent):
        """连接到本地控制端"""
        if not self.ws_client:
            yield event.plain_result("插件未初始化")
            return
            
        result = await self.ws_client.connect()
        if result:
            yield event.plain_result(f"✅ 已连接到本地控制端 {self.controller_host}:{self.controller_port}")
        else:
            yield event.plain_result(f"❌ 连接失败，请确保本地控制端已启动")
            
    @filter.command("wdisconnect")
    async def disconnect_controller(self, event: AstrMessageEvent):
        """断开与本地控制端的连接"""
        if self.ws_client:
            await self.ws_client.disconnect()
            yield event.plain_result("已断开连接")
        else:
            yield event.plain_result("未连接")
            
    @filter.command("wstatus")
    async def get_status(self, event: AstrMessageEvent):
        """获取连接状态"""
        if self.ws_client and self.ws_client.connected:
            yield event.plain_result(f"✅ 已连接到 {self.controller_host}:{self.controller_port}")
        else:
            yield event.plain_result(f"❌ 未连接，目标: {self.controller_host}:{self.controller_port}")
            
    @filter.command("wscreen")
    async def get_screenshot(self, event: AstrMessageEvent):
        """获取屏幕截图"""
        if not self.ws_client:
            yield event.plain_result("插件未初始化")
            return
            
        yield event.plain_result("📸 正在截图...")
        
        result = await self.ws_client.send_command("screenshot")
        
        if result.get("status") == "success":
            screenshot_data = result.get("result", {}).get("screenshot")
            if screenshot_data:
                chain = [
                    Comp.Plain("屏幕截图："),
                    Comp.Image.fromURL(screenshot_data)
                ]
                yield event.chain_result(chain)
            else:
                yield event.plain_result("截图失败：无图像数据")
        else:
            error = result.get("error", "未知错误")
            yield event.plain_result(f"截图失败: {error}")
            
    @filter.command("wmove")
    async def move_mouse_cmd(self, event: AstrMessageEvent, x: int, y: int):
        """移动鼠标到指定位置"""
        if not self.ws_client:
            yield event.plain_result("插件未初始化")
            return
            
        yield event.plain_result(f"🖱️ 正在移动鼠标到 ({x}, {y})...")
        
        result = await self.ws_client.send_command("mouse_move", {"x": x, "y": y, "duration": 0.5})
        
        if result.get("status") == "success":
            screenshot_data = result.get("result", {}).get("screenshot")
            message = result.get("result", {}).get("message", "")
            if screenshot_data:
                chain = [
                    Comp.Plain(f"{message}\n"),
                    Comp.Image.fromURL(screenshot_data)
                ]
                yield event.chain_result(chain)
            else:
                yield event.plain_result(message)
        else:
            error = result.get("error", "未知错误")
            yield event.plain_result(f"操作失败: {error}")
            
    @filter.command("wclick")
    async def click_mouse_cmd(self, event: AstrMessageEvent, button: str = "left"):
        """鼠标点击"""
        if not self.ws_client:
            yield event.plain_result("插件未初始化")
            return
            
        yield event.plain_result(f"🖱️ 正在执行 {button} 键点击...")
        
        result = await self.ws_client.send_command("mouse_click", {"button": button, "clicks": 1})
        
        if result.get("status") == "success":
            screenshot_data = result.get("result", {}).get("screenshot")
            message = result.get("result", {}).get("message", "")
            if screenshot_data:
                chain = [
                    Comp.Plain(f"{message}\n"),
                    Comp.Image.fromURL(screenshot_data)
                ]
                yield event.chain_result(chain)
            else:
                yield event.plain_result(message)
        else:
            error = result.get("error", "未知错误")
            yield event.plain_result(f"操作失败: {error}")
            
    @filter.command("wtype")
    async def type_text_cmd(self, event: AstrMessageEvent, text: str):
        """输入文本"""
        if not self.ws_client:
            yield event.plain_result("插件未初始化")
            return
            
        yield event.plain_result(f"⌨️ 正在输入: {text}")
        
        result = await self.ws_client.send_command("type_string", {"text": text, "interval": 0.01})
        
        if result.get("status") == "success":
            screenshot_data = result.get("result", {}).get("screenshot")
            message = result.get("result", {}).get("message", "")
            if screenshot_data:
                chain = [
                    Comp.Plain(f"{message}\n"),
                    Comp.Image.fromURL(screenshot_data)
                ]
                yield event.chain_result(chain)
            else:
                yield event.plain_result(message)
        else:
            error = result.get("error", "未知错误")
            yield event.plain_result(f"操作失败: {error}")
            
    @filter.command("wkey")
    async def press_key_cmd(self, event: AstrMessageEvent, key: str):
        """按下按键"""
        if not self.ws_client:
            yield event.plain_result("插件未初始化")
            return
            
        yield event.plain_result(f"⌨️ 正在按下: {key}")
        
        result = await self.ws_client.send_command("key_press", {"key": key})
        
        if result.get("status") == "success":
            screenshot_data = result.get("result", {}).get("screenshot")
            message = result.get("result", {}).get("message", "")
            if screenshot_data:
                chain = [
                    Comp.Plain(f"{message}\n"),
                    Comp.Image.fromURL(screenshot_data)
                ]
                yield event.chain_result(chain)
            else:
                yield event.plain_result(message)
        else:
            error = result.get("error", "未知错误")
            yield event.plain_result(f"操作失败: {error}")

    # ==================== LLM 工具函数 ====================
    
    @filter.llm_tool(name="mouse_move")
    async def llm_mouse_move(self, event: AstrMessageEvent, x: int, y: int) -> MessageEventResult:
        '''
        移动鼠标到屏幕指定坐标位置
        
        Args:
            x(int): 目标位置的 X 坐标（像素）
            y(int): 目标位置的 Y 坐标（像素）
        '''
        if not self.ws_client:
            return event.plain_result("错误：未连接到本地控制端")
            
        result = await self.ws_client.send_command("mouse_move", {"x": x, "y": y, "duration": 0.5})
        
        if result.get("status") == "success":
            screenshot_data = result.get("result", {}).get("screenshot")
            message = result.get("result", {}).get("message", "鼠标移动完成")
            
            if screenshot_data:
                chain = [
                    Comp.Plain(f"{message}\n当前屏幕状态：\n"),
                    Comp.Image.fromURL(screenshot_data)
                ]
                return event.chain_result(chain)
            else:
                return event.plain_result(message)
        else:
            error = result.get("error", "操作失败")
            return event.plain_result(f"错误：{error}")
            
    @filter.llm_tool(name="mouse_click")
    async def llm_mouse_click(self, event: AstrMessageEvent, button: str = "left") -> MessageEventResult:
        '''
        执行鼠标点击操作
        
        Args:
            button(string): 鼠标按钮类型，可选值为 "left"（左键）、"right"（右键）、"middle"（中键），默认为 "left"
        '''
        if not self.ws_client:
            return event.plain_result("错误：未连接到本地控制端")
            
        result = await self.ws_client.send_command("mouse_click", {"button": button, "clicks": 1})
        
        if result.get("status") == "success":
            screenshot_data = result.get("result", {}).get("screenshot")
            message = result.get("result", {}).get("message", "点击完成")
            
            if screenshot_data:
                chain = [
                    Comp.Plain(f"{message}\n当前屏幕状态：\n"),
                    Comp.Image.fromURL(screenshot_data)
                ]
                return event.chain_result(chain)
            else:
                return event.plain_result(message)
        else:
            error = result.get("error", "操作失败")
            return event.plain_result(f"错误：{error}")
            
    @filter.llm_tool(name="mouse_right_click")
    async def llm_mouse_right_click(self, event: AstrMessageEvent) -> MessageEventResult:
        '''
        执行鼠标右键点击操作
        '''
        if not self.ws_client:
            return event.plain_result("错误：未连接到本地控制端")
            
        result = await self.ws_client.send_command("mouse_click", {"button": "right", "clicks": 1})
        
        if result.get("status") == "success":
            screenshot_data = result.get("result", {}).get("screenshot")
            message = result.get("result", {}).get("message", "右键点击完成")
            
            if screenshot_data:
                chain = [
                    Comp.Plain(f"{message}\n当前屏幕状态：\n"),
                    Comp.Image.fromURL(screenshot_data)
                ]
                return event.chain_result(chain)
            else:
                return event.plain_result(message)
        else:
            error = result.get("error", "操作失败")
            return event.plain_result(f"错误：{error}")
            
    @filter.llm_tool(name="type_string")
    async def llm_type_string(self, event: AstrMessageEvent, text: str) -> MessageEventResult:
        '''
        输入字符串文本（支持连续输入多个字符）
        
        Args:
            text(string): 要输入的文本字符串
        '''
        if not self.ws_client:
            return event.plain_result("错误：未连接到本地控制端")
            
        result = await self.ws_client.send_command("type_string", {"text": text, "interval": 0.01})
        
        if result.get("status") == "success":
            screenshot_data = result.get("result", {}).get("screenshot")
            message = result.get("result", {}).get("message", "文本输入完成")
            
            if screenshot_data:
                chain = [
                    Comp.Plain(f"{message}\n当前屏幕状态：\n"),
                    Comp.Image.fromURL(screenshot_data)
                ]
                return event.chain_result(chain)
            else:
                return event.plain_result(message)
        else:
            error = result.get("error", "操作失败")
            return event.plain_result(f"错误：{error}")
            
    @filter.llm_tool(name="press_key")
    async def llm_press_key(self, event: AstrMessageEvent, key: str) -> MessageEventResult:
        '''
        按下单个按键或组合键
        
        Args:
            key(string): 按键名称。单键如 "a", "enter", "esc"；组合键用 + 连接，如 "ctrl+c", "alt+tab", "win+d"
        '''
        if not self.ws_client:
            return event.plain_result("错误：未连接到本地控制端")
            
        result = await self.ws_client.send_command("key_press", {"key": key})
        
        if result.get("status") == "success":
            screenshot_data = result.get("result", {}).get("screenshot")
            message = result.get("result", {}).get("message", "按键操作完成")
            
            if screenshot_data:
                chain = [
                    Comp.Plain(f"{message}\n当前屏幕状态：\n"),
                    Comp.Image.fromURL(screenshot_data)
                ]
                return event.chain_result(chain)
            else:
                return event.plain_result(message)
        else:
            error = result.get("error", "操作失败")
            return event.plain_result(f"错误：{error}")
            
    @filter.llm_tool(name="get_screenshot")
    async def llm_get_screenshot(self, event: AstrMessageEvent) -> MessageEventResult:
        '''
        获取当前屏幕截图，用于查看操作后的屏幕状态
        '''
        if not self.ws_client:
            return event.plain_result("错误：未连接到本地控制端")
            
        result = await self.ws_client.send_command("screenshot")
        
        if result.get("status") == "success":
            screenshot_data = result.get("result", {}).get("screenshot")
            message = result.get("result", {}).get("message", "截图完成")
            
            if screenshot_data:
                chain = [
                    Comp.Plain(f"{message}\n"),
                    Comp.Image.fromURL(screenshot_data)
                ]
                return event.chain_result(chain)
            else:
                return event.plain_result("截图失败：无图像数据")
        else:
            error = result.get("error", "截图失败")
            return event.plain_result(f"错误：{error}")
            
    @filter.llm_tool(name="get_screen_info")
    async def llm_get_screen_info(self, event: AstrMessageEvent) -> MessageEventResult:
        '''
        获取屏幕尺寸和鼠标位置信息
        '''
        if not self.ws_client:
            return event.plain_result("错误：未连接到本地控制端")
            
        # 获取屏幕尺寸
        result_size = await self.ws_client.send_command("get_screen_size")
        # 获取鼠标位置
        result_pos = await self.ws_client.send_command("get_mouse_position")
        
        if result_size.get("status") == "success" and result_pos.get("status") == "success":
            screen_size = result_size.get("result", {}).get("screen_size", {})
            mouse_pos = result_pos.get("result", {}).get("position", {})
            
            info = f"""屏幕信息：
屏幕尺寸: {screen_size.get('width', '未知')} x {screen_size.get('height', '未知')}
鼠标位置: ({mouse_pos.get('x', '未知')}, {mouse_pos.get('y', '未知')})"""
            
            return event.plain_result(info)
        else:
            error = result_size.get("error") or result_pos.get("error", "获取信息失败")
            return event.plain_result(f"错误：{error}")
