# Windows 远程控制插件 - AstrBot

## 插件简介

Windows 远程控制插件是一个基于 AstrBot 的服务端插件，允许通过 WebSocket 连接远程控制 Windows 系统。该插件提供了多种远程控制工具，包括鼠标移动、点击、输入文本、按键操作、截图和获取屏幕信息等功能。

## 功能特性

- **鼠标控制**：移动鼠标到指定坐标、执行左键/右键点击
- **键盘操作**：输入文本、按下单个按键或组合键
- **屏幕操作**：获取屏幕截图、获取屏幕尺寸和鼠标位置信息
- **WebSocket 服务**：等待本地控制端主动连接
- **Agent 集成**：支持通过 AstrBot 的 Agent 系统调用控制工具

## 系统要求

- AstrBot 版本 >= v4.5.7
- Python 3.8+
- Windows 操作系统（控制端）

## 安装方法

1. 克隆或下载插件到 AstrBot 的插件目录
2. 确保安装了必要的依赖：
   ```bash
   pip install websockets
   ```
3. 重启 AstrBot 以加载插件

## 配置说明

插件需要在 AstrBot 的 WebUI 中进行配置：

1. 打开 AstrBot 的 WebUI
2. 进入「插件管理」页面
3. 找到「Windows 远程控制插件」
4. 配置以下参数：
   - **host**：服务端监听地址（如 `0.0.0.0` 表示监听所有网络接口）
   - **port**：服务端监听端口（如 `8765`）

## 使用方法

### 1. 启动本地控制端

需要在 Windows 系统上运行一个本地控制端程序，该程序会连接到插件的 WebSocket 服务。

### 2. 通过 Agent 调用工具

可以通过 AstrBot 的 Agent 系统调用以下工具：

- **mouse_move**：移动鼠标到指定坐标
  ```
  mouse_move(x: number, y: number)
  ```

- **mouse_click**：执行鼠标点击操作
  ```
  mouse_click(button: string)  # button: left, right, middle
  ```

- **mouse_right_click**：执行鼠标右键点击操作
  ```
  mouse_right_click()
  ```

- **type_string**：输入文本字符串
  ```
  type_string(text: string)
  ```

- **press_key**：按下单个按键或组合键
  ```
  press_key(key: string)  # 如 a, enter, ctrl+c
  ```

- **get_screenshot**：获取屏幕截图
  ```
  get_screenshot()
  ```

- **get_screen_info**：获取屏幕信息
  ```
  get_screen_info()
  ```

## 本地控制端开发

本地控制端需要实现以下功能：

1. 连接到插件的 WebSocket 服务（如 `ws://localhost:8765`）
2. 接收并处理来自服务端的命令
3. 执行相应的操作并返回结果

### 命令格式

服务端发送的命令格式：
```json
{
  "type": "command",
  "action": "<操作类型>",
  "params": {<参数>},
  "timestamp": "<时间戳>"
}
```

### 支持的操作类型

- **mouse_move**：移动鼠标
  - 参数：`x` (number), `y` (number), `duration` (number)

- **mouse_click**：点击鼠标
  - 参数：`button` (string), `clicks` (number)

- **type_string**：输入文本
  - 参数：`text` (string), `interval` (number)

- **key_press**：按键操作
  - 参数：`key` (string)

- **screenshot**：截图
  - 无参数

- **get_screen_size**：获取屏幕尺寸
  - 无参数

- **get_mouse_position**：获取鼠标位置
  - 无参数

### 响应格式

本地控制端应返回以下格式的响应：
```json
{
  "status": "success" | "error",
  "result": {<结果数据>},  // 当 status 为 success 时
  "error": "<错误信息>"  // 当 status 为 error 时
}
```

## 示例

### 移动鼠标到坐标 (100, 200)

服务端发送：
```json
{
  "type": "command",
  "action": "mouse_move",
  "params": {"x": 100, "y": 200, "duration": 0.5},
  "timestamp": "2026-03-28T12:00:00"
}
```

控制端返回：
```json
{
  "status": "success",
  "result": {"message": "鼠标移动完成"}
}
```

## 故障排除

1. **服务端启动失败**：检查端口是否被占用，尝试使用不同的端口
2. **控制端连接失败**：检查网络连接和防火墙设置，确保端口已开放
3. **命令执行失败**：检查控制端是否正确实现了相应的操作

## 版本历史

- v1.0.1：优化工具调用返回值处理，修复截图工具图片数据处理问题
- v1.0.0：初始版本，实现基本的远程控制功能

## 许可证

本插件采用 MIT 许可证开源。