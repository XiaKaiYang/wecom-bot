# 企业微信 LongCat AI 自动化助手 (WeCom-LongCat-Bot)

> **基于原生 Windows UI 模拟 (RPA) + 极速屏幕 OCR 视觉感知的全自动企业微信 AI 伴侣与群聊助手。**  
> **零 Hook、零内存注入、零篡改协议，彻底告别封号风险！**

---

## 🌟 核心特性与创新设计

### 1. 🛡️ 零封号安全架构（Zero-Ban Risk）
* **纯视觉与系统级输入模拟**：通过 `RapidOCR` + Windows 标准 GDI 屏幕截帧，结合 Win32 原生光标定位与键盘事件（`SetCursorPos` + `keybd_event`）。
* **杜绝任何危险 Hook**：不注入任何 DLL，不读取内存指针，不篡改本地 SQLite 数据库或修改网络协议包，完全以真实用户的使用方式与企业微信交互。

### 2. ⚡ AI 收尾铁律（Bottom-Bubble Invariant）
* **必须由 AI 终结对话**：通过屏幕颜色与几何坐标实时判定视口底部的最后一条气泡。
* **判定原则**：只要最底部的气泡不是**自身蓝色气泡**（即为好友或群友的白色气泡），机器人立刻触发回复收尾，杜绝消息漏回或未读挂起。

### 3. 🎭 多重会话智能协同与个性化人设
* **群聊互动模式**：
  * 幽默风趣、接地气的智能群聊小助手。
  * 融合实时天气查询（调用 `wttr.in` 获取城市气象实况）。
  * 毫秒级群友个性化画像注入（自动识别发言者偏好）。
* **1对1 私聊模式**：
  * 支持配置独立私聊会话与定制专属提示词（Prompt），提供贴心自然的沟通体验。

### 4. 🧠 异步长效记忆引擎（LLM Distillation Memory）
* **轻量毫秒级响应**：本地持久化 JSON 键值索引，纯内存哈希查询耗时 `< 1ms`，零文件锁冲突。
* **后台异步智能提炼**：每次对话完成后，后台守护线程通过 `glm-4-flash` 大模型自动从对话中提炼关键事实（偏好、习惯、反感的人事物等），自动追加沉淀到记忆库。

### 5. 👁️ 视觉自愈巡检（Visual Healer）
* **像素级几何对齐**：通过快速 OCR 动态获取会话列表，计算多边形中心点精确定位并点击，会话切换延迟低至 80ms。
* **会话防走丢**：若误点至无关联系人（如企业微信团队等），自动感知并拉回目标会话；若会话滑出可视区域，自动激活快捷搜索重定向。

---

## 📂 项目结构

```text
wecom_longcat_bot/
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

---

## 🚀 快速上手

### 1. 环境准备
推荐使用 Python 3.10+ 环境：
```bash
git clone https://github.com/XiaKaiYang/wecom-bot.git
cd wecom-bot
pip install -r requirements.txt
```

### 2. 配置环境变量
复制根目录下的 `.env.example` 为 `.env`：
```bash
cp .env.example .env
```
在 `.env` 中填入你的 API Key：
```env
# LongCat 平台 API 配置 (https://api.longcat.chat)
LONGCAT_API_KEY=your_longcat_api_key_here
LONGCAT_BASE_URL=https://api.longcat.chat/openai/v1
LONGCAT_MODEL=LongCat-2.5-Preview

# 智谱 GLM 视觉自愈与记忆蒸馏 API (https://open.bigmodel.cn)
GLM_API_KEY=your_glm_api_key_here
GLM_BASE_URL=https://open.bigmodel.cn/api/paas/v4
GLM_MODEL=glm-4v-flash
```

### 3. 运行服务
* **方式一：双击启动（推荐）**
  直接双击根目录下的 **`start.bat`**。
* **方式二：命令行运行**
  ```bash
  python bot.py
  ```

> **运行提示**：
> 1. 请保持企业微信客户端处于桌面打开或未最小化状态。
> 2. 脚本已自动集成防休眠与 Windows 控制台 QuickEdit 冻结禁用机制。

---

## ⚙️ 个性化定制

可在 `config.py` 中自定义目标会话与触发规则：
* **`TARGET_CHATS`**：添加或修改需要监听的群聊/私聊名称、会话类型及独立的专属 System Prompt。
* **`TRIGGER_MODE`**：
  * `"ALL"`：回复目标会话中对方发送的所有新消息。
  * `"KEYWORD"`：仅当消息包含特定关键词或 `@` 时触发回复。
* **`POLL_INTERVAL`**：视口巡检间隔，默认 `2.0` 秒。

---

## 📄 开源许可
MIT License. 仅供学习交流与自动化办公探索，请合理合法合规使用。
