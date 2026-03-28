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


# 默认提示词模板 - 经过优化，可以准确识别 UI 元素坐标和文字
DEFAULT_VISION_PROMPT = """请详细分析这张屏幕截图，识别并列出所有 UI 元素，以便自动化控制：

## 分析要求

1. **识别所有可见的 UI 元素**，包括但不限于：
   - 按钮（Button）
   - 输入框（Input/TextField）
   - 文本标签（Label/Text）
   - 图标（Icon）
   - 下拉菜单（Dropdown/Select）
   - 复选框（Checkbox）
   - 单选按钮（Radio）
   - 链接（Link）
   - 菜单项（Menu Item）
   - 窗口标题栏
   - 滚动条
   - 任何其他可交互元素

2. **对于每个元素，必须提供以下信息**：
   - **元素类型**：使用标准 UI 组件名称
   - **显示文字**：元素上显示的所有文字内容（如果有）
   - **坐标位置**：使用像素坐标，格式为 "左上角 (x1, y1)，右下角 (x2, y2)"
     * x1, y1 是元素左上角的 X, Y 坐标
     * x2, y2 是元素右下角的 X, Y 坐标
     * 坐标应该是相对于屏幕左上角的绝对坐标
   - **元素状态**：如启用/禁用、选中/未选中、可见/隐藏等
   - **元素大小**：宽度和高度（可选但建议提供）

3. **特殊元素识别**：
   - **鼠标指针**：指出当前鼠标光标的位置坐标
   - **活动窗口**：识别当前活动窗口的标题和边界
   - **对话框/弹窗**：如果有模态对话框，优先描述
   - **输入光标**：如果有文本输入框被激活，指出光标位置

4. **整体布局描述**：
   - 屏幕分辨率和整体布局
   - 窗口层级关系（主窗口、子窗口、对话框）
   - 背景颜色和主题风格
   - 任何异常状态（错误提示、加载状态等）

## 输出格式

请使用以下结构化格式输出：

```
屏幕信息：
- 分辨率: [宽度] x [高度]
- 鼠标位置: ([x], [y])

UI 元素列表：

1. [元素类型] - [元素名称/描述]
   - 文字内容: [显示的文字]
   - 坐标: 左上角 ([x1], [y1])，右下角 ([x2], [y2])
   - 大小: [宽度] x [高度]
   - 状态: [状态描述]

2. [元素类型] - [元素名称/描述]
   ...

布局描述：
[整体布局的文字描述]

操作建议：
[基于当前界面状态，给出可能的下一步操作建议]
```

请确保坐标信息准确，这是用于自动化控制的关键数据。"""


class VisionAnalyzer:
    """视觉分析器 - 调用多模态 AI API 分析截图"""
    
    def __init__(
        self,
        api_provider: str = "openai",
        api_key: str = "",
        api_endpoint: str = "https://api.openai.com/v1",
        model: str = "gpt-4o",
        custom_prompt: str = ""
    ):
        self.api_provider = api_provider
        self.api_key = api_key
        self.api_endpoint = api_endpoint.rstrip("/")
        self.model = model
        self.custom_prompt = custom_prompt
        self.enabled = bool(api_key)
        
    def is_configured(self) -> bool:
        """检查是否已配置"""
        return self.enabled and bool(self.api_key)
        
    def get_prompt(self) -> str:
        """获取提示词，优先使用自定义提示词"""
        if self.custom_prompt and self.custom_prompt.strip():
            return self.custom_prompt
        return DEFAULT_VISION_PROMPT
        
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
                
            # 获取提示词
            prompt = self.get_prompt()

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
                                "url": f"data:image/png;base64,{image_base64}",
                                "detail": "high"  # 使用高分辨率模式
                            }
                        }
                    ]
                }
            ],
            "max_tokens": 4000,  # 增加 token 限制以获取更详细的分析
            "temperature": 0.2   # 降低温度以获得更确定的输出
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