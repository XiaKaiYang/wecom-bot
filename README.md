<img width="1024" height="572" alt="image" src="https://github.com/user-attachments/assets/2ffa9baa-54e4-4594-a9b4-e0ebd42bf198" />
<h1 align="center">WeCom-Bot</h1>


<p align="center">
  WeCom-Bot 是一个<strong>零封号风险</strong>、<strong>纯视觉感知 (RPA)</strong> 的企业微信智能自动化伴侣与群聊助手。<br>
  基于 RapidOCR 屏幕定轨与 LongCat / GLM 大模型，以“AI 蓝色气泡收尾铁律”实现 7×24h 智能交互与长效记忆沉淀。
</p>

<p align="center">
  <a href="https://github.com/XiaKaiYang/wecom-bot/stargazers"><img src="https://img.shields.io/github/stars/XiaKaiYang/wecom-bot?style=flat&label=Stars&labelColor=2A3B4C&color=60A5FA" alt="Stargazers"></a>
  <a href="https://github.com/XiaKaiYang/wecom-bot/network/members"><img src="https://img.shields.io/github/forks/XiaKaiYang/wecom-bot?style=flat&label=Forks&labelColor=2A3B4C&color=60A5FA" alt="Forks"></a>
  <a href="https://github.com/XiaKaiYang/wecom-bot/issues"><img src="https://img.shields.io/github/issues/XiaKaiYang/wecom-bot?style=flat&label=Issues&labelColor=2A3B4C&color=60A5FA" alt="Issues"></a>
  <a href="https://github.com/XiaKaiYang/wecom-bot/blob/main/LICENSE"><img src="https://img.shields.io/badge/License-MIT-60A5FA?style=flat&labelColor=2A3B4C&color=60A5FA" alt="License"></a>
</p>

> [!TIP]
> 本项目采用纯视觉屏幕感知与 Win32 原生硬件级输入仿真机制，**零 Hook、零内存注入、零协议篡改**，彻底告别封号风险！

---

## 主要功能

- 🛡️ **零封号安全架构**：纯 Windows UI 与 GDI 视觉截帧，无 DLL 注入
- ⚡ **AI 蓝色气泡收尾铁律**：视口最底端非自身蓝色气泡则必回复，绝无漏回
- 🧠 **轻量长效记忆引擎**：JSON + 内存字典毫秒级检索，大模型异步蒸馏新特征
- 👁️ **极速视觉自愈系统**：RapidOCR 像素级几何定轨，80ms 会话快速切换与防走丢
- ⛅ **实时气象数据直通**：内置天气接口，智能感知天气提问并融合城市实况
- 🎭 **多会话独立策略隔离**：群聊风趣助手与 1对1 私聊支持独立独立 Prompt 与上下文
- 🚀 **开箱即用**：提供 Windows 桌面一键双击启动脚本与环境自检机制
- 查看完整能力清单：[详细功能清单](#详细功能清单)

## 支持平台与运行环境

| 平台 | 支持架构 | 客户端版本 | 推荐运行方式 |
|------|----------|-----------|-------------|
| Windows | Windows 10 / 11（x64） | 企业微信桌面端 (WXWork) | 双击 `start.bat` / 命令行守护 |

## 详细功能清单

| 功能模块 | 说明 |
|---------|------|
| **零封号纯 RPA** | 完全基于操作系统级鼠标光标 (`SetCursorPos`) 与键盘事件 (`keybd_event`)，不篡改客户端数据与协议包 |
| **AI 气泡收尾铁律** | 实时采样视口最底部气泡 RGB 颜色与几何靠边判定，保证对话始终由 AI 蓝色气泡终结，杜绝冷场 |
| **长效记忆引擎** | 本地 `user_memories.json` 键值存储，查询耗时 `< 1ms`，零文件锁死锁；后台线程异步自动提炼群友新特征 |
| **极速几何定轨** | 使用 RapidOCR 对会话列表计算多边形几何中心点，快速精准点击，杜绝多模态大模型的坐标幻觉 |
| **会话防走丢** | 误触客服或系统联系人时自动感知并拉回主群；会话滑出屏幕时自动激活快捷重定向重回视野 |
| **实时天气直通** | 内置在线天气查询模块，检测到气温、下雨、天气等提问时秒级获取真实数据并注入 Prompt 上下文 |
| **提及智能清洗** | 自动剥离群聊中的 `@AI`、`@机器人`、`@助手` 等提及前缀，保证送入大模型的上下文干净整洁 |
| **控制台防冻结** | 底层调用 Windows API 关闭控制台 QuickEdit 模式，彻底杜绝鼠标误点 CMD 窗口导致线程挂起 |

## 项目结构

```text
wecom-bot/
├── bot.py                  # 核心服务主循环、窗口截帧与事件派发
├── config.py               # 配置中心（支持 .env 自动加载）
├── memory_manager.py       # 轻量级零锁群友/好友记忆管理器
├── visual_healer.py        # 屏幕几何定轨与多会话自动巡检切换
├── .env.example            # 环境变量配置模板
├── user_memories.example.json # 记忆库预置结构模板
├── requirements.txt        # Python 依赖清单
├── start.bat               # Windows 一键快速启动脚本
└── README.md               # 项目详细说明文档
```

## 快速上手

如果你想从源码运行或二次开发，请遵循以下步骤：

```bash
# 1. 克隆项目到本地
git clone https://github.com/XiaKaiYang/wecom-bot.git
cd wecom-bot

# 2. 安装项目依赖
pip install -r requirements.txt

# 3. 配置环境变量
copy .env.example .env
```

在生成的 `.env` 文件中填入您的 API Key：

```env
# LongCat 大模型 API 配置 (https://api.longcat.chat)
LONGCAT_API_KEY=your_longcat_api_key_here
LONGCAT_BASE_URL=https://api.longcat.chat/openai/v1
LONGCAT_MODEL=LongCat-2.5-Preview

# 智谱 GLM 视觉自愈与记忆蒸馏 API (https://open.bigmodel.cn)
GLM_API_KEY=your_glm_api_key_here
GLM_BASE_URL=https://open.bigmodel.cn/api/paas/v4
GLM_MODEL=glm-4v-flash
```

启动运行：

* **方式一：双击启动（推荐）**  
  直接双击根目录下的 **`start.bat`**。
* **方式二：命令行启动**  
  ```bash
  python bot.py
  ```

> **运行提示**：
> 1. 运行期间请保持企业微信客户端处于桌面打开或未最小化状态。
> 2. 脚本已自动集成防休眠与 Windows 控制台 QuickEdit 冻结禁用机制。

## 配置说明

核心参数可在 `config.py` 或 `.env` 中灵活定制：

| 配置项 | 说明 | 默认值 |
| :--- | :--- | :--- |
| `LONGCAT_API_KEY` | LongCat 平台 API Key | 从 `.env` 读取 |
| `LONGCAT_MODEL` | 对话大模型代号 | `LongCat-2.5-Preview` |
| `TARGET_CHATS` | 目标会话字典（支持多群聊、多私聊独立 Prompt） | 详见 `config.py` |
| `TRIGGER_MODE` | 触发模式：`ALL`（回复对方每条发言） / `KEYWORD`（仅关键词触发） | `ALL` |
| `TRIGGER_KEYWORDS` | 关键词列表（当 TRIGGER_MODE 为 KEYWORD 时生效） | `["@AI", "AI", "@bot", "助手"]` |
| `POLL_INTERVAL` | 界面轮询检测间隔（秒） | `2.0` |

---

## 贡献者

感谢所有做出贡献的开发者！

<p align="center">
  <a href="https://github.com/XiaKaiYang/wecom-bot/graphs/contributors">
    <img src="https://contrib.rocks/image?repo=XiaKaiYang/wecom-bot" alt="Contributors" />
  </a>
</p>

## Star History

<a href="https://www.star-history.com/#XiaKaiYang/wecom-bot&type=date&legend=top-left">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/svg?repos=XiaKaiYang/wecom-bot&type=date&theme=dark&legend=top-left" />
    <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/svg?repos=XiaKaiYang/wecom-bot&type=date&legend=top-left" />
    <img alt="Star History Chart" src="https://api.star-history.com/svg?repos=XiaKaiYang/wecom-bot&type=date&legend=top-left" />
  </picture>
</a>

<div align="center">

---

**请负责任地使用本工具，遵守相关法律法规与平台服务条款**

</div>
