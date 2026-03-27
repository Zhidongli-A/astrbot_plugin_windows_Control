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
from typing import Optional, Dict, Any, Set
from dataclasses import dataclass, field

from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
import astrbot.api.message_components as Comp


@dataclass
class ControllerClient:
    """控制器客户端信息"""
    websocket: websockets.WebSocketServerProtocol
    client_id: str
    connected_at: datetime = field(default_factory=datetime.now)
    last_ping: datetime = field(default_factory=datetime.now)
    is_busy: bool = False


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
        """处理客户端连接"""
        client_id = f"{websocket.remote_address[0]}:{websocket.remote_address[1]}"
        client = ControllerClient(websocket=websocket, client_id=client_id)
        
        self.clients[client_id] = client
        logger.info(f"本地控制端已连接: {client_id}")
        
        try:
            async for message in websocket:
                try:
                    data = json.loads(message)
                    msg_type = data.get("type", "unknown")
                    
                    if msg_type == "pong":
                        client.last_ping = datetime.now()
                    elif msg_type == "result":
                        # 命令执行结果，由 send_command 方法处理
                        pass
                    else:
                        logger.warning(f"未知消息类型: {msg_type}")
                        
                except json.JSONDecodeError:
                    logger.error(f"收到无效的 JSON: {message}")
                except Exception as e:
                    logger.error(f"处理消息时出错: {str(e)}")
                    
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
                
        if client.is_busy:
            return {"status": "error", "error": "客户端正忙"}
            
        client.is_busy = True
        
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
        finally:
            client.is_busy = False
            
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


@register("windows_control", "枝动力", "Windows 远程控制插件 - 服务端模式，等待本地控制端主动连接", "v1.0.1")
class WindowsControlPlugin(Star):
    """Windows 远程控制插件主类 - 服务端模式"""
    
    def __init__(self, context: Context):
        super().__init__(context)
        self.context = context
        self.controller_server: Optional[ControllerServer] = None
        self.server_host = None
        self.server_port = None
        
    async def initialize(self):
        """插件初始化"""
        # 从配置中读取设置
        try:
            from astrbot.core.config.astrbot_config import AstrBotConfig
            config = self.context.get_config()
            if isinstance(config, AstrBotConfig):
                plugin_config = config.get("windows_control", {})
            else:
                plugin_config = config
        except:
            plugin_config = self.context.get_config()
        
        raw_host = plugin_config.get("host") if hasattr(plugin_config, 'get') else None
        self.server_host = raw_host.strip() if raw_host else ""
        self.server_port = plugin_config.get("port") if hasattr(plugin_config, 'get') else None
        
        logger.info(f"配置读取: host='{self.server_host}', port={self.server_port}, raw_host={raw_host}, config_type={type(plugin_config)}")
        
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
        logger.info("Windows 控制插件已卸载")
        
    def _check_connection(self) -> tuple[bool, str]:
        """检查连接状态"""
        if not self.controller_server:
            return False, "服务端未初始化"
        if not self.controller_server.has_connected_client():
            return False, "没有本地控制端连接"
        return True, ""
        
    # ==================== LLM 工具函数 ====================
    
    @filter.llm_tool(name="mouse_move")
    async def llm_mouse_move(self, event: AstrMessageEvent, x: int, y: int) -> MessageEventResult:
        '''
        移动鼠标到屏幕指定坐标位置
        
        Args:
            x(int): 目标位置的 X 坐标（像素）
            y(int): 目标位置的 Y 坐标（像素）
        '''
        connected, error_msg = self._check_connection()
        if not connected:
            return event.plain_result(f"错误：{error_msg}")
            
        result = await self.controller_server.send_command(
            None, "mouse_move", {"x": x, "y": y, "duration": 0.5}
        )
        
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
        connected, error_msg = self._check_connection()
        if not connected:
            return event.plain_result(f"错误：{error_msg}")
            
        result = await self.controller_server.send_command(
            None, "mouse_click", {"button": button, "clicks": 1}
        )
        
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
        connected, error_msg = self._check_connection()
        if not connected:
            return event.plain_result(f"错误：{error_msg}")
            
        result = await self.controller_server.send_command(
            None, "mouse_click", {"button": "right", "clicks": 1}
        )
        
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
        connected, error_msg = self._check_connection()
        if not connected:
            return event.plain_result(f"错误：{error_msg}")
            
        result = await self.controller_server.send_command(
            None, "type_string", {"text": text, "interval": 0.01}
        )
        
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
        connected, error_msg = self._check_connection()
        if not connected:
            return event.plain_result(f"错误：{error_msg}")
            
        result = await self.controller_server.send_command(
            None, "key_press", {"key": key}
        )
        
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
        connected, error_msg = self._check_connection()
        if not connected:
            return event.plain_result(f"错误：{error_msg}")
            
        result = await self.controller_server.send_command(None, "screenshot")
        
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
        connected, error_msg = self._check_connection()
        if not connected:
            return event.plain_result(f"错误：{error_msg}")
            
        # 获取屏幕尺寸
        result_size = await self.controller_server.send_command(None, "get_screen_size")
        # 获取鼠标位置
        result_pos = await self.controller_server.send_command(None, "get_mouse_position")
        
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
