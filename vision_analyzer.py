#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
视觉分析模块 - 使用多模态 AI 分析屏幕截图
"""

import base64
import aiohttp
import json
from typing import Optional
from astrbot.api import logger


class VisionAnalyzer:
    """视觉分析器 - 调用多模态 AI API 分析截图"""
    
    def __init__(
        self,
        api_provider: str = "openai",
        api_key: str = "",
        api_endpoint: str = "https://api.openai.com/v1",
        model: str = "gpt-4o"
    ):
        self.api_provider = api_provider
        self.api_key = api_key
        self.api_endpoint = api_endpoint.rstrip("/")
        self.model = model
        self.enabled = bool(api_key)
        
    def is_configured(self) -> bool:
        """检查是否已配置"""
        return self.enabled and bool(self.api_key)
        
    async def analyze_screenshot(self, image_path: str) -> str:
        """
        分析截图
        
        Args:
            image_path: 截图文件路径
            
        Returns:
            AI 分析结果文本
        """
        if not self.is_configured():
            return "视觉分析未配置"
            
        try:
            # 读取图片并转为 base64
            with open(image_path, "rb") as f:
                image_data = base64.b64encode(f.read()).decode("utf-8")
                
            # 构建提示词
            prompt = """请详细分析这张屏幕截图，识别并列出所有 UI 元素：

1. 识别所有可见的按钮、输入框、文本标签、图标等 UI 元素
2. 对于每个元素，提供：
   - 元素类型（按钮/输入框/文本/图标等）
   - 显示的文字内容（如果有）
   - 大致坐标位置（用左上角和右下角描述，如 "左上角 (100, 200)，右下角 (300, 400)"）
3. 描述当前屏幕的整体布局和状态
4. 指出当前鼠标指针位置（如果有明显标识）

请以结构化的格式输出，便于理解和后续操作。"""

            # 调用 API
            if self.api_provider == "openai":
                return await self._call_openai_api(image_data, prompt)
            else:
                return await self._call_custom_api(image_data, prompt)
                
        except Exception as e:
            logger.error(f"视觉分析失败: {str(e)}")
            return f"视觉分析失败: {str(e)}"
            
    async def _call_openai_api(self, image_base64: str, prompt: str) -> str:
        """调用 OpenAI API"""
        url = f"{self.api_endpoint}/chat/completions"
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{image_base64}"
                            }
                        }
                    ]
                }
            ],
            "max_tokens": 2000
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    return data["choices"][0]["message"]["content"]
                else:
                    error_text = await response.text()
                    raise Exception(f"API 错误 {response.status}: {error_text}")
                    
    async def _call_custom_api(self, image_base64: str, prompt: str) -> str:
        """调用自定义 API（兼容 OpenAI 格式）"""
        # 自定义 API 使用与 OpenAI 相同的格式
        return await self._call_openai_api(image_base64, prompt)


# 全局视觉分析器实例
_vision_analyzer: Optional[VisionAnalyzer] = None


def get_vision_analyzer() -> Optional[VisionAnalyzer]:
    """获取全局视觉分析器实例"""
    return _vision_analyzer


def set_vision_analyzer(analyzer: Optional[VisionAnalyzer]):
    """设置全局视觉分析器实例"""
    global _vision_analyzer
    _vision_analyzer = analyzer


async def analyze_screenshot_with_ai(image_path: str) -> str:
    """
    使用 AI 分析截图的便捷函数
    
    Args:
        image_path: 截图文件路径
        
    Returns:
        AI 分析结果
    """
    analyzer = get_vision_analyzer()
    if not analyzer:
        return "视觉分析器未初始化"
    return await analyzer.analyze_screenshot(image_path)