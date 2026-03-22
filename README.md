# AstrBot Windows 远程控制插件

一个功能强大的 AstrBot 插件，支持通过 LLM 函数调用远程控制 Windows 电脑，实现鼠标键盘操作和屏幕截图功能。

## 功能特性

- **鼠标控制**：移动、左键点击、右键点击
- **键盘输入**：单键输入、连续字符串输入、组合键支持
- **屏幕截图**：实时获取操作后的屏幕状态
- **LLM 集成**：通过 AstrBot 的 LLM 工具调用接口，实现 AI 自动化控制
- **实时反馈**：每个操作后自动返回截图，让 LLM 了解操作结果

## 系统架构

本系统由两部分组成：

1. **AstrBot 插件端** (`main.py`)：运行在 AstrBot 服务器上，提供 LLM 工具调用接口
2. **本地控制端** (`local_controller/`)：运行在 Windows 电脑上，执行实际的鼠标键盘操作

通信方式：WebSocket 双向实时通信

## 安装步骤

### 1. 安装 AstrBot 插件

将本插件安装到 AstrBot 的插件目录：

```bash
cd AstrBot/data/plugins
git clone https://github.com/Zhidongli-A/astrbot_plugin_windows_Control.git
```

### 2. 安装插件依赖

```bash
cd astrbot_plugin_windows_Control
pip install -r requirements.txt
```

### 3. 部署本地控制端（在 Windows 电脑上）

#### 方式一：直接运行 Python 脚本

1. 将 `local_controller/` 目录复制到 Windows 电脑
2. 安装依赖：
```bash
cd local_controller
pip install -r requirements.txt
```
3. 启动控制端：
```bash
python controller.py --host 0.0.0.0 --port 8765
```

#### 方式二：打包为可执行文件（可选）

使用 PyInstaller 打包：
```bash
pip install pyinstaller
pyinstaller --onefile --name WindowsController controller.py
```

### 4. 配置网络（重要）

如果 AstrBot 和 Windows 电脑不在同一网络：

1. **Windows 电脑需要公网 IP 或使用内网穿透工具**（如 frp、ngrok）
2. **配置防火墙**：开放控制端端口（默认 8765）
3. **在 AstrBot WebUI 中配置插件**：
   - 进入插件配置页面
   - 设置 `host` 为 Windows 电脑的公网 IP 或内网穿透地址
   - 设置 `port` 为控制端监听的端口

## 使用方法

### 手动指令

插件提供以下手动指令：

| 指令 | 说明 | 示例 |
|------|------|------|
| `/wconnect` | 连接到本地控制端 | `/wconnect` |
| `/wdisconnect` | 断开连接 | `/wdisconnect` |
| `/wstatus` | 查看连接状态 | `/wstatus` |
| `/wscreen` | 获取屏幕截图 | `/wscreen` |
| `/wmove` | 移动鼠标 | `/wmove 500 300` |
| `/wclick` | 鼠标点击 | `/wclick left` 或 `/wclick right` |
| `/wtype` | 输入文本 | `/wtype Hello World` |
| `/wkey` | 按下按键 | `/wkey enter` 或 `/wkey ctrl+c` |

### LLM 工具调用

当 LLM 需要控制 Windows 电脑时，会自动调用以下工具：

#### 1. mouse_move - 移动鼠标
```json
{
  "x": 500,
  "y": 300
}
```

#### 2. mouse_click - 鼠标点击
```json
{
  "button": "left"
}
```
可选值：`left`（左键）、`right`（右键）、`middle`（中键）

#### 3. mouse_right_click - 右键点击
无需参数

#### 4. type_string - 输入字符串
```json
{
  "text": "Hello World"
}
```

#### 5. press_key - 按下按键
```json
{
  "key": "enter"
}
```
支持单键（如 `a`, `enter`, `esc`）和组合键（如 `ctrl+c`, `alt+tab`, `win+d`）

#### 6. get_screenshot - 获取截图
无需参数，返回当前屏幕截图

#### 7. get_screen_info - 获取屏幕信息
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

## 配置说明

在 AstrBot WebUI 的插件配置页面，可以设置：

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| host | 本地控制端地址 | localhost |
| port | 本地控制端端口 | 8765 |
| timeout | 命令超时时间（秒） | 30 |

## 安全注意事项

1. **网络安全**：
   - 建议使用内网穿透工具配合身份验证
   - 不要直接将控制端暴露在公网
   - 考虑使用 VPN 或 SSH 隧道

2. **操作安全**：
   - 本地控制端启用了 PyAutoGUI 的故障保护（将鼠标移到屏幕角落会停止）
   - 避免在关键系统上运行，以防误操作
   - 建议先在测试环境验证所有功能

3. **访问控制**：
   - 仅授权用户可以使用控制功能
   - 建议配合 AstrBot 的权限管理使用

## 故障排除

### 连接失败
- 检查控制端是否已启动
- 检查防火墙设置
- 验证 host 和 port 配置是否正确
- 查看 AstrBot 日志和控制端日志

### 操作无响应
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
- 全新架构，支持 LLM 工具调用
- 新增 WebSocket 实时通信
- 新增屏幕截图自动反馈
- 支持组合键操作
- 新增手动指令

### v1.0.0
- 初始版本

## 许可证

MIT License

## 作者

枝动力 (Zhidongli-A)

## 问题反馈

如有问题，请在 GitHub Issues 中提交：
https://github.com/Zhidongli-A/astrbot_plugin_windows_Control/issues
