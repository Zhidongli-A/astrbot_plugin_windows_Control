# AstrBot Windows 远程控制插件

一个功能强大的 AstrBot 插件，支持通过 LLM 函数调用远程控制 Windows 电脑，实现鼠标键盘操作和屏幕截图功能。

## 系统架构

本系统采用**服务端-客户端**架构：

```
┌─────────────────────────────────────────────────────────────┐
│                    AstrBot 服务器（公网）                    │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  AstrBot 插件端 (main.py) - 服务端模式                 │  │
│  │  • WebSocket 服务端（等待客户端连接）                   │  │
│  │  • LLM 工具注册（7个工具函数）                          │  │
│  │  • 命令转发与结果接收                                   │  │
│  └───────────────────────────────────────────────────────┘  │
└──────────────────────────┬──────────────────────────────────┘
                           │ WebSocket 连接（客户端主动连接）
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                    Windows 本地电脑                          │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  本地控制端 (controller_client.py) - 客户端模式         │  │
│  │  • WebSocket 客户端（主动连接服务器）                   │  │
│  │  • 命令接收与执行                                       │  │
│  │  • 自动重连机制                                         │  │
│  └───────────────────────────────────────────────────────┘  │
│                           │                                 │
│  ┌───────────────────────┐│┌───────────────────────────────┐│
│  │  InputController      │││  ScreenCapture                ││
│  │  • 鼠标移动/点击      │││  • 全屏截图                   ││
│  │  • 键盘输入           │││  • Base64编码                 ││
│  │  • 组合键支持         │││                               ││
│  └───────────────────────┘│└───────────────────────────────┘│
└───────────────────────────┴─────────────────────────────────┘
```

**连接方式**：本地控制端（Windows电脑）主动连接到 AstrBot 服务器（公网）

## 功能特性

- **鼠标控制**：移动、左键点击、右键点击
- **键盘输入**：单键输入、连续字符串输入、组合键支持（如 ctrl+c, alt+tab）
- **屏幕截图**：每个操作后自动返回截图，让 LLM 了解操作结果
- **LLM 集成**：通过 AstrBot 的 LLM 工具调用接口，实现 AI 自动化控制
- **自动重连**：本地控制端断开后自动重连

## 安装步骤

### 1. 安装 AstrBot 插件

将本插件安装到 AstrBot 的插件目录：

```bash
cd AstrBot/data/plugins
git clone https://github.com/Zhidongli-A/astrbot_plugin_windows_Control.git
```

安装依赖：
```bash
cd astrbot_plugin_windows_Control
pip install -r requirements.txt
```

### 2. 配置 AstrBot 插件

在 AstrBot WebUI 中配置插件：

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| host | 服务端监听地址 | 0.0.0.0 |
| port | 服务端监听端口 | 7365 |

**注意**：如果 AstrBot 部署在云服务器上，需要在安全组/防火墙中开放配置的端口。

### 3. 部署本地控制端（在 Windows 电脑上）

1. 将 `local_controller/` 目录复制到 Windows 电脑

2. 安装依赖：
```bash
cd local_controller
pip install -r requirements.txt
```

3. 启动控制端（连接到 AstrBot 服务器）：
```bash
python controller_client.py --server <AstrBot服务器公网IP> --port 7365
```

例如：
```bash
python controller_client.py --server 123.45.67.89 --port 7365
```

**启动参数说明**：
- `--server` 或 `-s`: AstrBot 服务器的公网 IP 地址（必填）
- `--port` 或 `-p`: 服务器端口（默认：7365）

### 4. 使用 PyInstaller 打包（可选）

可以将本地控制端打包为可执行文件，方便在没有 Python 环境的电脑上运行：

```bash
pip install pyinstaller
pyinstaller --onefile --name WindowsController controller_client.py
```

打包后，使用方式：
```bash
WindowsController.exe --server 123.45.67.89 --port 7365
```

## LLM 工具调用

当 LLM 需要控制 Windows 电脑时，会自动调用以下工具：

### 1. mouse_move - 移动鼠标
```json
{
  "x": 500,
  "y": 300
}
```

### 2. mouse_click - 鼠标点击
```json
{
  "button": "left"
}
```
可选值：`left`（左键）、`right`（右键）、`middle`（中键）

### 3. mouse_right_click - 右键点击
无需参数

### 4. type_string - 输入字符串
```json
{
  "text": "Hello World"
}
```

### 5. press_key - 按下按键
```json
{
  "key": "enter"
}
```
支持单键（如 `a`, `enter`, `esc`）和组合键（如 `ctrl+c`, `alt+tab`, `win+d`）

### 6. get_screenshot - 获取截图
无需参数，返回当前屏幕截图

### 7. get_screen_info - 获取屏幕信息
无需参数，返回屏幕尺寸和鼠标位置

## 工作流程示例

1. 用户在聊天中发送："帮我打开记事本并输入一段文字"
2. LLM 分析需求，依次调用：
   - `press_key` (win+r) 打开运行对话框
   - `type_string` (notepad) 输入记事本命令
   - `press_key` (enter) 确认打开
   - `get_screenshot` 确认记事本已打开
   - `type_string` (要输入的文字) 输入内容
3. 每个操作后，LLM 都能看到截图反馈，确保操作正确执行

## 网络配置

确保 AstrBot 服务器的防火墙/安全组已开放插件端口（默认 7365）。

本地控制端使用服务器公网 IP 连接：
```bash
python controller_client.py --server 123.45.67.89 --port 7365
```

## 安全注意事项

1. **网络安全**：
   - 建议配合防火墙使用，限制访问来源 IP
   - 不要直接将 AstrBot 服务器暴露在公网而不加防护

2. **操作安全**：
   - 本地控制端启用了 PyAutoGUI 的故障保护（将鼠标移到屏幕角落会停止）
   - 避免在关键系统上运行，以防误操作
   - 建议先在测试环境验证所有功能

3. **访问控制**：
   - 仅授权用户可以使用控制功能
   - 建议配合 AstrBot 的权限管理使用

## 故障排除

### 本地控制端无法连接
- 检查 AstrBot 服务器端口是否已开放
- 检查服务器防火墙/安全组设置
- 验证服务器地址和端口是否正确
- 查看 AstrBot 日志确认服务端是否启动

### 命令执行无响应
- 检查 Windows 电脑是否处于锁定状态
- 确认 pyautogui 有权限控制鼠标键盘
- 尝试以管理员权限运行控制端

### 截图失败
- 检查 Pillow 是否安装正确
- 确认屏幕分辨率设置正常

## 依赖要求

### AstrBot 插件端
- Python >= 3.8
- websockets >= 11.0.0

### 本地控制端（Windows）
- Python >= 3.8
- pyautogui >= 0.9.54
- Pillow >= 10.0.0
- websockets >= 11.0.0

## 更新日志

### v2.0.0
- 全新架构，改为客户端-服务端模式
- 本地控制端主动连接 AstrBot 服务器
- 新增自动重连机制
- 支持 LLM 工具调用
- 新增 7 个 LLM 工具函数
- 每个操作后自动返回截图

### v1.0.0
- 初始版本

## 许可证

MIT License

## 作者

枝动力 (Zhidongli-A)

## 问题反馈

如有问题，请在 GitHub Issues 中提交：
https://github.com/Zhidongli-A/astrbot_plugin_windows_Control/issues
