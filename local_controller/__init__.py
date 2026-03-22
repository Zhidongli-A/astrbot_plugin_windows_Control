#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Windows 本地控制端模块
"""

from .controller import LocalController
from .input_controller import InputController
from .screen_capture import ScreenCapture

__all__ = ["LocalController", "InputController", "ScreenCapture"]
