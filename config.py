# -*- coding: utf-8 -*-
"""
企业微信 LongCat AI 配置文件
"""
import os

# 自动读取同级目录下的 .env 环境变量文件
_env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
if os.path.exists(_env_path):
    try:
        with open(_env_path, "r", encoding="utf-8") as _f:
            for _line in _f:
                _line = _line.strip()
                if _line and not _line.startswith("#") and "=" in _line:
                    _k, _v = _line.split("=", 1)
                    os.environ.setdefault(_k.strip(), _v.strip())
    except Exception:
        pass

# LongCat API 配置
LONGCAT_API_KEY = os.getenv("LONGCAT_API_KEY", "")
LONGCAT_BASE_URL = os.getenv("LONGCAT_BASE_URL", "https://api.longcat.chat/openai/v1")
LONGCAT_MODEL = os.getenv("LONGCAT_MODEL", "LongCat-2.5-Preview")

# 监听的目标会话配置（支持多会话独立 Prompt 与模式）
TARGET_GROUP_NAME = "大专说唱"

TARGET_CHATS = {
    "大专说唱": {
        "type": "group",
        "keywords": ["大专说唱", "大专", "说唱"],
        "name": "大专说唱",
        "prompt": (
            "你是微信群【大专说唱】里的常驻智能助手（基于 LongCat 大模型并装载了长期记忆系统）。"
            "性格幽默风趣、接地气、机智生动，回复言简意赅，通常用 1~2 句话直接回答，避免废话和长篇大论。"
            "在对话中，请巧妙利用你对该群友的个性记忆，给出针对性、懂他的回复。"
        ),
    }
}

# 触发模式:
# "ALL"     - 回复群内好友发送的所有新消息（适合小群/好友闲聊）
# "KEYWORD" - 仅当消息包含触发词或 @ 时才回复
TRIGGER_MODE = "ALL"

# 关键词触发列表（当 TRIGGER_MODE 为 "KEYWORD" 时生效）
TRIGGER_KEYWORDS = ["@AI", "AI", "ai", "@bot", "bot", "LongCat", "longcat", "@助手", "助手"]

# 是否启用个性化记忆层 (自动学习每位群友的特征与偏好)
ENABLE_MEM0 = True

# AI 助手的角色设定
SYSTEM_PROMPT = (
    "你是微信群【大专说唱】里的常驻智能助手（基于 LongCat 大模型并装载了长期记忆系统）。"
    "性格幽默风趣、接地气、机智生动，回复言简意赅，通常用 1~2 句话直接回答，避免废话和长篇大论。"
    "在对话中，请巧妙利用你对该群友的个性记忆，给出针对性、懂他的回复。"
)

# 轮询检测间隔（秒）
POLL_INTERVAL = 2.0

# 智谱 GLM 视觉自愈与记忆蒸馏配置
GLM_API_KEY = os.getenv("GLM_API_KEY", "")
GLM_BASE_URL = os.getenv("GLM_BASE_URL", "https://open.bigmodel.cn/api/paas/v4")
GLM_MODEL = os.getenv("GLM_MODEL", "glm-4v-flash")
ENABLE_VISUAL_HEALER = True
