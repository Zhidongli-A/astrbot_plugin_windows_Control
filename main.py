#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AstrBot Windows 远程控制插件 - 服务端模式
本地控制端主动连接到此服务端，服务端通过 WebSocket 发送命令并接收结果
"""

import asyncio
import websockets
import json
import base64
import functools
from datetime import datetime
from typing import Optional, Dict, Any, Set, Tuple
from dataclasses import dataclass, field

from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
import astrbot.api.message_components as Comp

# 导入 MCP 类型（AstrBot 借用 MCP 协议的类型定义）
from mcp.types import CallToolResult, ImageContent, TextContent

from astrbot.core.agent.run_context import ContextWrapper
from astrbot.core.agent.tool import FunctionTool, ToolExecResult
from astrbot.core.astr_agent_context import AstrAgentContext


# 全局变量，用于存储 controller_server 实例
_controller_server_instance: Optional['ControllerServer'] = None


def get_controller_server() -> Optional['ControllerServer']:
    """获取全局 controller_server 实例"""
    return _controller_server_instance


def set_controller_server(server: Optional['ControllerServer']):
    """设置全局 controller_server 实例"""
    global _controller_server_instance
    _controller_server_instance = server


def screenshot_data_to_imagecontent(screenshot_data: str):
    """
    将截图数据转换为 ImageContent 格式，让 LLM 直接"看到"图片
    
    Args:
        screenshot_data: 包含 data:image/jpeg;base64, 前缀的 base64 图片数据
        
    Returns:
        CallToolResult 包含 ImageContent
    """
    try:
        # 判断图片格式并去除 base64 前缀
        mime_type = "image/jpeg"  # 默认格式
        if screenshot_data.startswith("data:image/jpeg;base64,"):
            screenshot_data = screenshot_data[len("data:image/jpeg;base64,"):]
            mime_type = "image/jpeg"
        elif screenshot_data.startswith("data:image/jpg;base64,"):
            screenshot_data = screenshot_data[len("data:image/jpg;base64,"):]
            mime_type = "image/jpeg"
        elif screenshot_data.startswith("data:image/png;base64,"):
            screenshot_data = screenshot_data[len("data:image/png;base64,"):]
            mime_type = "image/png"
        elif screenshot_data.startswith("data:image/gif;base64,"):
            screenshot_data = screenshot_data[len("data:image/gif;base64,"):]
            mime_type = "image/gif"
        elif screenshot_data.startswith("data:image/webp;base64,"):
            screenshot_data = screenshot_data[len("data:image/webp;base64,"):]
            mime_type = "image/webp"
        
        # 只返回图片，不返回文本
        return CallToolResult(content=[
            ImageContent(type="image", data=screenshot_data, mimeType=mime_type)
        ])
    except Exception as e:
        logger.error(f"转换截图数据失败: {str(e)}")
        return CallToolResult(content=[TextContent(type="text", text=f"处理截图失败: {str(e)}")])





@dataclass
class ControllerClient:
    """控制器客户端信息"""
    websocket: websockets.WebSocketServerProtocol
    client_id: str
    connected_at: datetime = field(default_factory=datetime.now)
    last_ping: datetime = field(default_factory=datetime.now)
    is_busy: bool = False
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)


class ControllerServer:
    """控制端服务端 - 等待本地控制端连接"""
    
    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port
        self.clients: Dict[str, ControllerClient] = {}
        self.server = None
        self.running = False
        
    async def start(self):
        """启动服务端"""
        self.running = True
        
        try:
            logger.info(f"Windows 控制服务端启动: {self.host}:{self.port}")
            
            self.server = await websockets.serve(
                functools.partial(self.handle_client),
                self.host,
                self.port,
                ping_interval=20,
                ping_timeout=10
            )
            
            logger.info("等待本地控制端连接...")
            return True
            
        except OSError as e:
            if "address already in use" in str(e).lower():
                logger.error(f"端口 {self.port} 已被占用，请修改配置或关闭占用该端口的程序")
            else:
                logger.error(f"启动服务端失败: {str(e)}")
            return False
        
    async def stop(self):
        """停止服务端"""
        self.running = False
        
        # 关闭所有客户端连接
        for client in list(self.clients.values()):
            try:
                await client.websocket.close()
            except:
                pass
        self.clients.clear()
        
        if self.server:
            self.server.close()
            await self.server.wait_closed()
        logger.info("服务端已停止")
        
    async def handle_client(self, websocket: websockets.WebSocketServerProtocol):
        """处理客户端连接 - 只保持连接状态，不主动接收消息"""
        client_id = f"{websocket.remote_address[0]}:{websocket.remote_address[1]}"
        client = ControllerClient(websocket=websocket, client_id=client_id)
        
        self.clients[client_id] = client
        logger.info(f"本地控制端已连接: {client_id}")
        
        try:
            # 保持连接，等待断开
            await websocket.wait_closed()
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"本地控制端断开连接: {client_id}")
        finally:
            if client_id in self.clients:
                del self.clients[client_id]
                
    async def send_command(self, client_id: Optional[str], action: str, params: Dict[str, Any] = None, timeout: int = 30) -> Dict[str, Any]:
        """
        向指定客户端发送命令
        
        Args:
            client_id: 客户端ID，None 表示使用第一个可用客户端
            action: 命令动作
            params: 命令参数
            timeout: 超时时间（秒）
            
        Returns:
            执行结果
        """
        # 获取客户端
        if client_id is None:
            if not self.clients:
                return {"status": "error", "error": "没有可用的本地控制端连接"}
            client = list(self.clients.values())[0]
        else:
            client = self.clients.get(client_id)
            if not client:
                return {"status": "error", "error": f"未找到客户端: {client_id}"}
                
        # 使用锁保护 recv 操作，防止并发冲突
        async with client.lock:
            try:
                command = {
                    "type": "command",
                    "action": action,
                    "params": params or {},
                    "timestamp": datetime.now().isoformat()
                }
                
                await client.websocket.send(json.dumps(command))
                
                # 等待响应
                response = await asyncio.wait_for(
                    client.websocket.recv(),
                    timeout=timeout
                )
                
                result = json.loads(response)
                return result
                
            except asyncio.TimeoutError:
                logger.error("命令执行超时")
                return {"status": "error", "error": "命令执行超时"}
            except websockets.exceptions.ConnectionClosed:
                logger.error("连接已关闭")
                if client_id in self.clients:
                    del self.clients[client_id]
                return {"status": "error", "error": "连接已关闭"}
            except Exception as e:
                logger.error(f"发送命令失败: {str(e)}")
                return {"status": "error", "error": str(e)}
            
    def get_connected_clients(self) -> list:
        """获取已连接的客户端列表"""
        return [
            {
                "client_id": c.client_id,
                "connected_at": c.connected_at.isoformat(),
                "last_ping": c.last_ping.isoformat()
            }
            for c in self.clients.values()
        ]
        
    def has_connected_client(self) -> bool:
        """检查是否有已连接的客户端"""
        return len(self.clients) > 0


# ==================== FunctionTool 类定义 ====================

@dataclass
class MouseMoveTool(FunctionTool[AstrAgentContext]):
    """鼠标移动工具"""
    name: str = "mouse_move"
    description: str = "移动鼠标到屏幕指定坐标位置"
    parameters: dict = field(default_factory=lambda: {
        "type": "object",
        "properties": {
            "x": {"type": "number", "description": "目标位置的 X 坐标（像素）"},
            "y": {"type": "number", "description": "目标位置的 Y 坐标（像素）"}
        },
        "required": ["x", "y"]
    })
    
    async def call(self, context: ContextWrapper[AstrAgentContext], **kwargs):
        x = kwargs.get("x", 0)
        y = kwargs.get("y", 0)
        
        # 通过全局变量获取 controller_server
        controller_server = get_controller_server()
        if not controller_server:
            return "错误：插件未初始化"
        if not controller_server.has_connected_client():
            return "错误：没有本地控制端连接"
        
        result = await controller_server.send_command(
            None, "mouse_move", {"x": x, "y": y, "duration": 0.5}
        )
        
        if result.get("status") == "success":
            message = result.get("result", {}).get("message", "鼠标移动完成")
            screenshot_data = result.get("result", {}).get("screenshot")
            if screenshot_data:
                # 使用 ImageContent 让 LLM 直接看到图片
                return screenshot_data_to_imagecontent(screenshot_data)
            return message
        else:
            return f"错误：{result.get('error', '操作失败')}"


@dataclass
class MouseClickTool(FunctionTool[AstrAgentContext]):
    """鼠标点击工具"""
    name: str = "mouse_click"
    description: str = "执行鼠标点击操作"
    parameters: dict = field(default_factory=lambda: {
        "type": "object",
        "properties": {
            "button": {"type": "string", "description": "鼠标按钮类型，可选值为 left（左键）、right（右键）、middle（中键），默认为 left"}
        },
        "required": []
    })
    
    async def call(self, context: ContextWrapper[AstrAgentContext], **kwargs):
        button = kwargs.get("button", "left")
        
        controller_server = get_controller_server()
        if not controller_server:
            return "错误：插件未初始化"
        if not controller_server.has_connected_client():
            return "错误：没有本地控制端连接"
        
        result = await controller_server.send_command(
            None, "mouse_click", {"button": button, "clicks": 1}
        )
        
        if result.get("status") == "success":
            message = result.get("result", {}).get("message", "点击完成")
            screenshot_data = result.get("result", {}).get("screenshot")
            if screenshot_data:
                # 使用 ImageContent 让 LLM 直接看到图片
                return screenshot_data_to_imagecontent(screenshot_data)
            return message
        else:
            return f"错误：{result.get('error', '操作失败')}"


@dataclass
class MouseRightClickTool(FunctionTool[AstrAgentContext]):
    """鼠标右键点击工具"""
    name: str = "mouse_right_click"
    description: str = "执行鼠标右键点击操作"
    parameters: dict = field(default_factory=lambda: {
        "type": "object",
        "properties": {},
        "required": []
    })
    
    async def call(self, context: ContextWrapper[AstrAgentContext], **kwargs):
        controller_server = get_controller_server()
        if not controller_server:
            return "错误：插件未初始化"
        if not controller_server.has_connected_client():
            return "错误：没有本地控制端连接"
        
        result = await controller_server.send_command(
            None, "mouse_click", {"button": "right", "clicks": 1}
        )
        
        if result.get("status") == "success":
            message = result.get("result", {}).get("message", "右键点击完成")
            screenshot_data = result.get("result", {}).get("screenshot")
            if screenshot_data:
                # 使用 ImageContent 让 LLM 直接看到图片
                return screenshot_data_to_imagecontent(screenshot_data)
            return message
        else:
            return f"错误：{result.get('error', '操作失败')}"


@dataclass
class TypeStringTool(FunctionTool[AstrAgentContext]):
    """输入字符串工具"""
    name: str = "type_string"
    description: str = "输入字符串文本（支持连续输入多个字符）"
    parameters: dict = field(default_factory=lambda: {
        "type": "object",
        "properties": {
            "text": {"type": "string", "description": "要输入的文本字符串"}
        },
        "required": ["text"]
    })
    
    async def call(self, context: ContextWrapper[AstrAgentContext], **kwargs):
        text = kwargs.get("text", "")
        
        controller_server = get_controller_server()
        if not controller_server:
            return "错误：插件未初始化"
        if not controller_server.has_connected_client():
            return "错误：没有本地控制端连接"
        
        result = await controller_server.send_command(
            None, "type_string", {"text": text, "interval": 0.01}
        )
        
        if result.get("status") == "success":
            message = result.get("result", {}).get("message", "文本输入完成")
            screenshot_data = result.get("result", {}).get("screenshot")
            if screenshot_data:
                # 使用 ImageContent 让 LLM 直接看到图片
                return screenshot_data_to_imagecontent(screenshot_data)
            return message
        else:
            return f"错误：{result.get('error', '操作失败')}"


@dataclass
class PressKeyTool(FunctionTool[AstrAgentContext]):
    """按键工具"""
    name: str = "press_key"
    description: str = "按下单个按键或组合键"
    parameters: dict = field(default_factory=lambda: {
        "type": "object",
        "properties": {
            "key": {"type": "string", "description": "按键名称。单键如 a, enter, esc；组合键用 + 连接，如 ctrl+c, alt+tab, win+d"}
        },
        "required": ["key"]
    })
    
    async def call(self, context: ContextWrapper[AstrAgentContext], **kwargs):
        key = kwargs.get("key", "")
        
        controller_server = get_controller_server()
        if not controller_server:
            return "错误：插件未初始化"
        if not controller_server.has_connected_client():
            return "错误：没有本地控制端连接"
        
        result = await controller_server.send_command(
            None, "key_press", {"key": key}
        )
        
        if result.get("status") == "success":
            message = result.get("result", {}).get("message", "按键操作完成")
            screenshot_data = result.get("result", {}).get("screenshot")
            if screenshot_data:
                # 使用 ImageContent 让 LLM 直接看到图片
                return screenshot_data_to_imagecontent(screenshot_data)
            return message
        else:
            return f"错误：{result.get('error', '操作失败')}"


@dataclass
class GetScreenshotTool(FunctionTool[AstrAgentContext]):
    """截图工具"""
    name: str = "get_screenshot"
    description: str = "获取当前屏幕截图，用于查看操作后的屏幕状态"
    parameters: dict = field(default_factory=lambda: {
        "type": "object",
        "properties": {},
        "required": []
    })
    
    async def call(self, context: ContextWrapper[AstrAgentContext], **kwargs):
        controller_server = get_controller_server()
        if not controller_server:
            return "错误：插件未初始化"
        if not controller_server.has_connected_client():
            return "错误：没有本地控制端连接"
        
        result = await controller_server.send_command(None, "screenshot")
        
        if result.get("status") == "success":
            screenshot_data = result.get("result", {}).get("screenshot")
            message = result.get("result", {}).get("message", "截图完成")
            if screenshot_data:
                # 使用 ImageContent 让 LLM 直接看到图片
                return screenshot_data_to_imagecontent(screenshot_data)
            else:
                return "错误：截图失败，无图像数据"
        else:
            return f"错误：{result.get('error', '截图失败')}"


@dataclass
class GetScreenInfoTool(FunctionTool[AstrAgentContext]):
    """获取屏幕信息工具"""
    name: str = "get_screen_info"
    description: str = "获取屏幕尺寸和鼠标位置信息"
    parameters: dict = field(default_factory=lambda: {
        "type": "object",
        "properties": {},
        "required": []
    })
    
    async def call(self, context: ContextWrapper[AstrAgentContext], **kwargs):
        controller_server = get_controller_server()
        if not controller_server:
            return "错误：插件未初始化"
        if not controller_server.has_connected_client():
            return "错误：没有本地控制端连接"
        
        # 获取屏幕尺寸
        result_size = await controller_server.send_command(None, "get_screen_size")
        # 获取鼠标位置
        result_pos = await controller_server.send_command(None, "get_mouse_position")
        
        if result_size.get("status") == "success" and result_pos.get("status") == "success":
            screen_size = result_size.get("result", {}).get("screen_size", {})
            mouse_pos = result_pos.get("result", {}).get("position", {})
            
            info = f"""屏幕信息：
屏幕尺寸: {screen_size.get('width', '未知')} x {screen_size.get('height', '未知')}
鼠标位置: ({mouse_pos.get('x', '未知')}, {mouse_pos.get('y', '未知')})"""
            
            return info
        else:
            error = result_size.get("error") or result_pos.get("error", "获取信息失败")
            return f"错误：{error}"


@register("windows_control", "枝动力", "Windows 远程控制插件 - 服务端模式，等待本地控制端主动连接", "v1.0.2")
class WindowsControlPlugin(Star):
    """Windows 远程控制插件主类 - 服务端模式"""
    
    def __init__(self, context: Context, config: dict = None):
        super().__init__(context)
        self.context = context
        self.config = config  # 插件配置
        self.controller_server: Optional[ControllerServer] = None
        self.server_host = None
        self.server_port = None
        
        # 注册 FunctionTool 工具
        self._register_tools()
        
    def _register_tools(self):
        """注册 FunctionTool 工具到 AstrBot"""
        try:
            # 创建工具实例
            tools = [
                MouseMoveTool(),
                MouseClickTool(),
                MouseRightClickTool(),
                TypeStringTool(),
                PressKeyTool(),
                GetScreenshotTool(),
                GetScreenInfoTool()
            ]
            
            # 注册工具到 AstrBot (v4.5.1+)
            if hasattr(self.context, 'add_llm_tools'):
                self.context.add_llm_tools(*tools)
                logger.info(f"已注册 {len(tools)} 个 FunctionTool 工具")
            else:
                # 旧版本兼容
                logger.warning("当前 AstrBot 版本不支持 add_llm_tools，请升级到 v4.5.1+")
                
        except Exception as e:
            logger.error(f"注册工具失败: {e}")
        
    async def initialize(self):
        """插件初始化"""
        # 从配置中读取设置
        if self.config and isinstance(self.config, dict):
            self.server_host = self.config.get('host')
            self.server_port = self.config.get('port')
        
        # 处理值
        self.server_host = str(self.server_host).strip() if self.server_host else ""
        self.server_port = int(self.server_port) if self.server_port else None
        
        # 检查必要配置
        if not self.server_host:
            logger.error("未配置 host，请在面板中设置服务器地址")
            return
        if not self.server_port or self.server_port == 0:
            logger.error("未配置 port，请在面板中设置服务器端口")
            return
        
        # 初始化服务端
        self.controller_server = ControllerServer(
            host=self.server_host,
            port=self.server_port
        )
        
        # 设置全局变量，供工具类使用
        set_controller_server(self.controller_server)
        
        # 启动服务端
        success = await self.controller_server.start()
        
        if success:
            logger.info(f"Windows 控制插件初始化完成，监听: {self.server_host}:{self.server_port}")
        else:
            logger.error("Windows 控制插件启动失败")
        
    async def terminate(self):
        """插件销毁"""
        if self.controller_server:
            await self.controller_server.stop()
        # 清除全局变量
        set_controller_server(None)
        logger.info("Windows 控制插件已卸载")
        
    def _check_connection(self) -> Tuple[bool, str]:
        """检查连接状态"""
        if not self.controller_server:
            return False, "服务端未初始化"
        if not self.controller_server.has_connected_client():
            return False, "没有本地控制端连接"
        return True, ""
