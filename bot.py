# -*- coding: utf-8 -*-
"""
企业微信 LongCat AI 自动化服务 (装载高可用即时群友记忆系统)
- 秒级快速响应（彻底移除耗时 60s 且容易引发文件锁死锁的 Qdrant 嵌入库）
- 自动检测并锁定目标群聊（防止被新好友/私聊弹窗顶走导致失效）
- 智能清洗 @ 提及标记（如 @AI、@机器人、@助手）
- 仅响应群友发言（严格屏蔽自身与AI消息）
- 详细双通道排查日志 (控制台 + bot.log 文件)
- 零死锁前台聚焦 (非阻塞 Alt 键机制)
"""
import sys
import io
import os
import time
import re
import ctypes
import hashlib
import logging
import threading
import requests
import numpy as np
from PIL import ImageGrab
import pyperclip
import win32gui
import win32con
import win32service
from openai import OpenAI
from rapidocr_onnxruntime import RapidOCR

from memory_manager import GroupMemoryManager
from visual_healer import VisualHealer
import config

# 安全设置控制台编码为 UTF-8
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

def disable_quick_edit():
    """彻底禁用控制台的 QuickEdit 模式，防止用户鼠标点击黑框导致 Windows 冻结进程"""
    try:
        kernel32 = ctypes.windll.kernel32
        hStdin = kernel32.GetStdHandle(-10) # STD_INPUT_HANDLE
        mode = ctypes.c_ulong()
        if kernel32.GetConsoleMode(hStdin, ctypes.byref(mode)):
            ENABLE_QUICK_EDIT_MODE = 0x0040
            ENABLE_INSERT_MODE = 0x0020
            mode.value &= ~ENABLE_QUICK_EDIT_MODE
            mode.value &= ~ENABLE_INSERT_MODE
            kernel32.SetConsoleMode(hStdin, mode)
    except Exception:
        pass

# 配置日志记录器（控制台 + bot.log 文件）
LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bot.log")

logger = logging.getLogger("WeComBot")
logger.setLevel(logging.INFO)
logger.handlers.clear()

file_handler = logging.FileHandler(LOG_FILE, mode="a", encoding="utf-8")
file_fmt = logging.Formatter("[%(asctime)s][%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
file_handler.setFormatter(file_fmt)
logger.addHandler(file_handler)

console_handler = logging.StreamHandler(sys.stdout)
console_fmt = logging.Formatter("[%(asctime)s] %(message)s", datefmt="%H:%M:%S")
console_handler.setFormatter(console_fmt)
logger.addHandler(console_handler)

def ensure_default_desktop():
    """确保线程在交互式桌面运行"""
    try:
        hdesk = win32service.OpenDesktop("default", 0, False, win32con.GENERIC_ALL)
        ctypes.windll.user32.SetThreadDesktop(int(hdesk))
        return hdesk
    except Exception as e:
        logger.debug(f"切换桌面提示: {e}")
        return None

def get_wework_hwnd():
    """查找企业微信主窗口句柄（优先匹配有效真实主窗口）"""
    hdesk = ensure_default_desktop()
    hwnds = []
    def enum_cb(h, l):
        if win32gui.GetClassName(h) == "WeWorkWindow":
            rect = win32gui.GetWindowRect(h)
            w = rect[2] - rect[0]
            h_len = rect[3] - rect[1]
            # 排除辅助隐藏小窗口 (0, 0, 1180, 760)
            if w > 200 and h_len > 200 and not (rect[0] == 0 and rect[1] == 0 and w == 1180):
                l.append((h, rect, win32gui.IsWindowVisible(h)))
    if hdesk:
        win32gui.EnumDesktopWindows(hdesk, enum_cb, hwnds)
    else:
        win32gui.EnumWindows(enum_cb, hwnds)

    if not hwnds:
        return None
    # 优先返回可见窗口，若都不可见则返回第一个主句柄
    for h, r, vis in hwnds:
        if vis:
            return h
    return hwnds[0][0]

def bring_wework_to_front(hwnd):
    """安全激活企业微信并置于前台"""
    ensure_default_desktop()
    try:
        if ctypes.windll.user32.IsIconic(hwnd) or not win32gui.IsWindowVisible(hwnd):
            ctypes.windll.user32.ShowWindow(hwnd, win32con.SW_RESTORE)
            ctypes.windll.user32.ShowWindow(hwnd, win32con.SW_SHOW)

        # 模拟 Alt 键安全赋予前台焦点
        ctypes.windll.user32.keybd_event(0x12, 0, 0, 0)
        ctypes.windll.user32.keybd_event(0x12, 0, 2, 0)

        ctypes.windll.user32.SetForegroundWindow(hwnd)
        ctypes.windll.user32.BringWindowToTop(hwnd)
    except Exception as e:
        logger.warning(f"激活前台异常: {e}")

# 初始化 LongCat 客户端与离线 OCR 引擎
llm_client = OpenAI(
    api_key=config.LONGCAT_API_KEY,
    base_url=config.LONGCAT_BASE_URL,
    timeout=15.0,
    max_retries=1,
)
ocr_engine = RapidOCR()

# 初始化轻量级毫秒级记忆系统 (永久存储在 user_memories.json)
mem_json_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "user_memories.json")
memory_manager = GroupMemoryManager(mem_json_path)
logger.info(f"个性化记忆系统已就绪 (毫秒级响应，存储: {mem_json_path})")

# 初始化 GLM 视觉自愈系统
visual_healer = VisualHealer()

# 自身回复内容黑名单缓存
sent_by_bot_history = set()

# 私聊多轮对话上下文缓存
private_dialog_history = {}

def async_distill_memory(sender, user_msg, ai_reply):
    """后台异步提取对话记忆，绝不阻塞前端回复发送"""
    def _worker():
        try:
            from openai import OpenAI
            client = OpenAI(
                api_key=config.GLM_API_KEY,
                base_url=config.GLM_BASE_URL,
                timeout=10.0
            )
            prompt = f"""请从以下对话中，提取出关于说话人【{sender}】的 1 条核心画像、个性习惯、偏好或重要事实（例如喜好、常住地、反感的人事物、近期烦恼等）。
如果是无实质信息的纯日常寒暄、单个字打招呼或重复语气词，请直接回复 NONE。

对话内容:
【{sender}】: {user_msg}
【AI】: {ai_reply}

输出要求:
若有价值，仅输出 1 句话的事实描述（20字以内），严禁输出任何解释或格式标签。"""

            resp = client.chat.completions.create(
                model="glm-4-flash",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=60
            )
            content = resp.choices[0].message.content
            if content:
                fact = content.strip()
                if "NONE" not in fact.upper() and len(fact) >= 3:
                    memory_manager.add_user_memory(sender, fact)
        except Exception as e:
            logger.debug(f"后台记忆沉淀提示: {e}")

    threading.Thread(target=_worker, daemon=True).start()

def get_private_reply(chat_name, prompt):
    """为 1对1 私聊定制的多轮对话回复"""
    global private_dialog_history
    try:
        if chat_name not in private_dialog_history:
            private_dialog_history[chat_name] = []

        history = private_dialog_history[chat_name]
        if len(history) > 8:
            history = history[-8:]

        user_mems = memory_manager.get_user_memory(chat_name)
        mem_context = ""
        if user_mems:
            mem_context = "\n【已知该用户的核心性格偏好】:\n" + "\n".join([f"- {m}" for m in user_mems])

        chat_cfg = config.TARGET_CHATS.get(chat_name, {})
        system_prompt = chat_cfg.get("prompt", config.SYSTEM_PROMPT) + mem_context
        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(history)
        messages.append({"role": "user", "content": prompt})

        logger.info(f"请求 LongCat 模型 (会话: {chat_name}, 发言: {prompt})...")
        start_time = time.time()
        response = llm_client.chat.completions.create(
            model=config.LONGCAT_MODEL,
            messages=messages,
            temperature=0.7,
            max_tokens=220,
        )
        elapsed = time.time() - start_time
        reply = response.choices[0].message.content.strip()
        logger.info(f"LongCat 响应完成 (耗时: {elapsed:.2f}s)")

        history.append({"role": "user", "content": prompt})
        history.append({"role": "assistant", "content": reply})
        private_dialog_history[chat_name] = history
        return reply

    except Exception as e:
        logger.error(f"LongCat 私聊回复异常: {e}")
        return "我在呢，有什么想聊的随时跟我说。"

def query_live_weather(city_name):
    """在线查询实时天气数据（超时设为 3 秒）"""
    try:
        cleaned = re.sub(r"^(查一下|帮我查|看看|问下|查|问)", "", city_name).strip()
        if not cleaned:
            cleaned = "盐城"
        url = f"https://wttr.in/{cleaned}?lang=zh&format=%l天气：%C+温度%t+风向%w+湿度%h"
        r = requests.get(url, timeout=3.0)
        if r.status_code == 200 and "Unknown location" not in r.text and "<html" not in r.text:
            return r.text.strip()
    except Exception as e:
        logger.debug(f"天气接口超时或异常: {e}")
    return None

def check_weather_inquiry(prompt):
    """检测是否在询问天气"""
    weather_keywords = ["天气", "下雨", "下不下雨", "气温", "温度", "多少度", "下雪", "有雨"]
    if not any(k in prompt for k in weather_keywords):
        return None

    m = re.search(r"([\u4e00-\u9fa5]{2,6}?(?:市|区|县|镇)?)(?:的)?(?:今天|明天|后天|周[一二三四五六日七]|这几天)?(?:天气|下雨|下不下雨|气温|温度)", prompt)
    city = "盐城"
    if m:
        extracted = m.group(1)
        extracted = re.sub(r"^(查一下|帮我查|问下|看看|查)", "", extracted).strip()
        if len(extracted) >= 2:
            city = extracted

    weather_data = query_live_weather(city)
    if not weather_data and city != "盐城":
        weather_data = query_live_weather("盐城")
    return weather_data

def get_ai_reply(sender_name, prompt):
    """调用 LongCat 大模型生成幽默回复（融合毫秒级记忆与天气实况）"""
    try:
        # 清理 prompt 中的 @提及
        clean_query = re.sub(r"@(AI|ai|bot|机器人|助手)\s*", "", prompt).strip()
        if not clean_query:
            clean_query = prompt

        # 1. 实时天气注入
        live_weather = check_weather_inquiry(clean_query)
        weather_context = ""
        if live_weather:
            logger.info(f"获取实时气象: {live_weather}")
            weather_context = f"\n【实时气象数据参考】: {live_weather}\n请结合该真实数据用风趣简短的语气直接回答对方。"

        # 2. 毫秒级群友记忆检索
        user_mems = memory_manager.get_user_memory(sender_name, clean_query)
        memory_context = ""
        if user_mems:
            pref_list = [f"- {m}" for m in user_mems]
            memory_context = f"\n【已知群友【{sender_name}】的个性特征/偏好】:\n" + "\n".join(pref_list)
            logger.info(f"命中群友【{sender_name}】记忆特征: {len(user_mems)} 条")

        # 3. 构造增强 Prompt
        user_content = f"群成员【{sender_name}】说：{clean_query}{weather_context}{memory_context}"
        
        logger.info(f"请求 LongCat 模型 (群友: {sender_name}, 内容: {clean_query})...")
        start_time = time.time()
        response = llm_client.chat.completions.create(
            model=config.LONGCAT_MODEL,
            messages=[
                {"role": "system", "content": config.SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
            ],
            temperature=0.7,
            max_tokens=200,
        )
        elapsed = time.time() - start_time
        logger.info(f"LongCat 响应完成 (耗时: {elapsed:.2f}s)")

        choice = response.choices[0]
        content = choice.message.content

        if not content:
            if hasattr(choice.message, "refusal") and choice.message.refusal:
                reply = "骂归骂，咱依然是群里最抗造的 AI，消消气哥们儿～ 😄"
            else:
                reply = "虽然你这么说我，但我情绪价值拉满，随时准备继续为你效劳！💪"
        else:
            reply = content.strip()

        # 4. 自动学习群友新特征（如自称“我喜欢...”、“我是...”）
        if "我喜欢" in clean_query or "我是" in clean_query or "我平时" in clean_query:
            memory_manager.add_user_memory(sender_name, clean_query)

        return reply

    except Exception as e:
        logger.error(f"LongCat API 调用异常: {e}")
        if "废物" in prompt or "笨" in prompt or "傻" in prompt:
            return "虽然被吐槽了，但本小助理主打一个皮实耐造，随时听候差遣！🫡"
        return "网络刚才稍微开了个小差，你再说一遍我准能答上来！"

def is_system_msg(text):
    """过滤时间戳、系统事件与界面控件文字"""
    if re.match(r"^\d{1,2}:\d{2}$", text):
        return True
    system_patterns = [
        "修改群名为", "加入了外部群聊", "加入了群聊", "移出了群聊",
        "邀请", "由企业微信用户创建", "含4位外部联系人", "客服名片",
        "点击名片即可", "快速会议", "发送(S)"
    ]
    for p in system_patterns:
        if p in text:
            return True
    return False

def clean_sender_name(raw_name):
    """清洗昵称，去除末尾由 Emoji 图标引起的 OCR 偶发错别字"""
    cleaned = re.sub(r"@\s*(微信|企业微信)", "", raw_name).strip()
    return cleaned

def get_current_chat_title(hwnd):
    """读取当前聊天视口顶部的标题"""
    ensure_default_desktop()
    rect = win32gui.GetWindowRect(hwnd)
    header_bbox = (
        rect[0] + 310,
        rect[1] + 15,
        rect[0] + min(600, rect[2] - rect[0]),
        rect[1] + 65
    )
    im = ImageGrab.grab(bbox=header_bbox)
    res, _ = ocr_engine(np.array(im))
    return "".join([item[1] for item in res]) if res else ""

def identify_chat_target(title_text):
    """识别当前属于哪个目标会话"""
    for key, cfg in config.TARGET_CHATS.items():
        for kw in cfg["keywords"]:
            if kw in title_text:
                return key
    return None

def ensure_valid_chat_focused(hwnd):
    """确保当前停留在已配置的目标会话上，若偏离到客服或其它无关会话则自动拉回主群"""
    title_text = get_current_chat_title(hwnd)
    target = identify_chat_target(title_text)
    if target:
        return target

    if not title_text or len(title_text.strip()) < 2:
        return "大专说唱"

    logger.info(f"检测到当前会话不在目标范围内 (当前为: {title_text})，正在自动切回【大专说唱】...")
    bring_wework_to_front(hwnd)
    time.sleep(0.1)
    if visual_healer and visual_healer.locate_and_switch(hwnd, "大专说唱"):
        time.sleep(0.2)
        return "大专说唱"
    return "大专说唱"

def get_session_previews(hwnd):
    """抓取左侧会话列表的前排最新预览，感知是否有新消息涌入"""
    ensure_default_desktop()
    rect = win32gui.GetWindowRect(hwnd)
    crop_session_list = (
        rect[0] + 60,
        rect[1] + 60,
        rect[0] + 320,
        rect[1] + 450
    )
    im = ImageGrab.grab(bbox=crop_session_list)
    res, _ = ocr_engine(np.array(im))
    if not res:
        return {}

    lines = []
    for item in res:
        box = item[0]
        text = str(item[1]).strip()
        y = (box[0][1] + box[2][1]) / 2
        lines.append((y, text))
    lines.sort(key=lambda x: x[0])

    previews = {}
    for i, (y, text) in enumerate(lines):
        for target in config.TARGET_CHATS.keys():
            if target in text:
                sub_parts = []
                for j in range(i + 1, min(i + 3, len(lines))):
                    sub_y, sub_text = lines[j]
                    if 15 <= sub_y - y <= 45:
                        sub_parts.append(sub_text)
                previews[target] = " ".join(sub_parts)
    return previews

def is_self_private_bubble(box, im, win_crop_w):
    """
    三重严格判定是否为自己发出的气泡:
    1. 右边缘紧靠视口右侧 (x_max > 680)
    2. 左起始点远离好友头像 (x_min > 80)
    3. 气泡背景色检测：浅蓝色 (B通道显著大于R通道)
    """
    xs = [p[0] for p in box]
    ys = [p[1] for p in box]
    x_min, x_max = min(xs), max(xs)
    y_min, y_max = min(ys), max(ys)

    if x_max > 680:
        return True

    if x_min > 80:
        return True

    sample_x = min(win_crop_w - 1, int(x_max + 5))
    sample_y = int((y_min + y_max) / 2)
    p = im.getpixel((sample_x, sample_y))
    if len(p) >= 3 and p[2] > p[0] + 25:
        return True

    return False

def parse_private_messages_only(hwnd):
    """
    抓取 1对1 私聊中对方发送的文字。
    严格基于【几何靠左锚点 (x_min <= 80 且 x_max < 680) + 蓝色气泡过滤】，
    彻底杜绝抓取自己发送的内容。
    """
    ensure_default_desktop()
    rect = win32gui.GetWindowRect(hwnd)
    win_w = rect[2] - rect[0]
    win_h = rect[3] - rect[1]

    crop_bbox = (
        rect[0] + 300,
        rect[1] + 60,
        rect[0] + win_w - 20,
        rect[1] + win_h - 160
    )
    im = ImageGrab.grab(bbox=crop_bbox)
    w_crop, _ = im.size
    result, _ = ocr_engine(np.array(im))
    if not result:
        return []

    lines = []
    for item in result:
        box = item[0]
        text = str(item[1]).strip()
        score = float(item[2])
        if score < 0.6 or not text or is_system_msg(text):
            continue

        # 排除右侧客户资料栏 (x > 830)
        x_min = min(p[0] for p in box)
        if x_min > 830:
            continue

        if any(sent_text in text or text in sent_text for sent_text in sent_by_bot_history):
            continue

        # 核心过滤：若为自身消息，坚决丢弃
        if is_self_private_bubble(box, im, w_crop):
            continue

        y_min = min(p[1] for p in box)
        lines.append({
            "text": text,
            "x": x_min,
            "y": y_min
        })

    lines.sort(key=lambda item: item["y"])

    friend_clusters = []
    current_cluster = []
    for line in lines:
        if not current_cluster:
            current_cluster.append(line)
        else:
            last_line = current_cluster[-1]
            if line["y"] - last_line["y"] < 50:
                current_cluster.append(line)
            else:
                friend_clusters.append(current_cluster)
                current_cluster = [line]

    if current_cluster:
        friend_clusters.append(current_cluster)

    messages = []
    for cluster in friend_clusters:
        combined_text = " ".join([c["text"] for c in cluster])
        messages.append({
            "sender": "好友",
            "text": combined_text,
            "y": cluster[0]["y"]
        })
    return messages

def parse_friend_messages_only(hwnd):
    """
    精确定位主聊天视口，且严格通过【左侧好友昵称锚点】匹配发言。
    绝不捕获自己的消息（右侧蓝色气泡无好友昵称头，且靠右对齐）。
    """
    ensure_default_desktop()
    rect = win32gui.GetWindowRect(hwnd)
    win_w = rect[2] - rect[0]
    win_h = rect[3] - rect[1]

    crop_bbox = (
        rect[0] + 300,
        rect[1] + 60,
        rect[0] + max(400, win_w - 200),
        rect[1] + max(300, win_h - 160)
    )

    im = ImageGrab.grab(bbox=crop_bbox)
    img_np = np.array(im)
    result, _ = ocr_engine(img_np)
    if not result:
        return []

    lines = []
    for item in result:
        box = item[0]
        text = str(item[1]).strip()
        score = float(item[2])
        if score < 0.6 or not text or is_system_msg(text):
            continue

        if any(sent_text in text or text in sent_text for sent_text in sent_by_bot_history):
            continue

        x_min = min(p[0] for p in box)
        y_min = min(p[1] for p in box)
        lines.append({
            "text": text,
            "x": x_min,
            "y": y_min,
            "score": score
        })

    lines.sort(key=lambda item: item["y"])

    friend_messages = []
    for i, line in enumerate(lines):
        text = line["text"]
        x = line["x"]
        y = line["y"]

        if ("@微信" in text or "@ 微信" in text or "@企业微信" in text or "@ 企业微信" in text) and x < 80:
            sender_name = clean_sender_name(text)

            msg_parts = []
            for j in range(i + 1, min(i + 4, len(lines))):
                next_line = lines[j]
                y_diff = next_line["y"] - y
                if 15 <= y_diff <= 85 and next_line["x"] < 80:
                    if not ("@微信" in next_line["text"] or "@企业微信" in next_line["text"]):
                        msg_parts.append(next_line["text"])

            if msg_parts:
                full_msg = " ".join(msg_parts)
                friend_messages.append({
                    "sender": sender_name,
                    "text": full_msg,
                    "y": y
                })

    return friend_messages

def send_chat_message(hwnd, reply_text):
    """将回复填入企业微信输入框并自动发送"""
    ensure_default_desktop()

    sent_by_bot_history.add(reply_text)
    if len(sent_by_bot_history) > 200:
        sent_by_bot_history.pop()

    bring_wework_to_front(hwnd)
    time.sleep(0.15)

    rect = win32gui.GetWindowRect(hwnd)
    win_w = rect[2] - rect[0]
    win_h = rect[3] - rect[1]

    input_x = rect[0] + 300 + max(100, int((win_w - 500) / 4))
    input_y = rect[1] + win_h - 60
    ctypes.windll.user32.SetCursorPos(input_x, input_y)
    time.sleep(0.05)
    ctypes.windll.user32.mouse_event(0x0002, 0, 0, 0, 0) # LEFTDOWN
    time.sleep(0.05)
    ctypes.windll.user32.mouse_event(0x0004, 0, 0, 0, 0) # LEFTUP
    time.sleep(0.1)

    pyperclip.copy(reply_text)
    ctypes.windll.user32.keybd_event(0x11, 0, 0, 0) # Ctrl down
    ctypes.windll.user32.keybd_event(0x56, 0, 0, 0) # V down
    time.sleep(0.05)
    ctypes.windll.user32.keybd_event(0x56, 0, 2, 0) # V up
    ctypes.windll.user32.keybd_event(0x11, 0, 2, 0) # Ctrl up

    time.sleep(0.1)
    ctypes.windll.user32.keybd_event(0x0D, 0, 0, 0) # Enter down
    time.sleep(0.05)
    ctypes.windll.user32.keybd_event(0x0D, 0, 2, 0) # Enter up

    logger.info(f"已成功发送回复: {reply_text}")

def check_chat_needs_reply(hwnd, active_target):
    """
    【AI 收尾铁律】:
    会话最底部的最后一个气泡必须是蓝色 (AI 回复)。
    如果最底部不是蓝色气泡 (而是白色的对方发言)，则无论何时，一律判定为【必须由 AI 进行收尾回复】！
    返回: (needs_reply: bool, unreplied_text: str, sender: str)
    """
    ensure_default_desktop()
    rect = win32gui.GetWindowRect(hwnd)
    win_w = rect[2] - rect[0]
    win_h = rect[3] - rect[1]

    crop_bbox = (
        rect[0] + 300,
        rect[1] + 60,
        rect[0] + win_w - 20,
        rect[1] + win_h - 160
    )
    im = ImageGrab.grab(bbox=crop_bbox)
    w_crop, _ = im.size
    res, _ = ocr_engine(np.array(im))
    if not res:
        return False, "", ""

    bubbles = []
    for item in res:
        box = item[0]
        text = str(item[1]).strip()
        score = float(item[2])
        if score < 0.6 or not text or is_system_msg(text):
            continue

        xs = [p[0] for p in box]
        ys = [p[1] for p in box]
        x_min, x_max = min(xs), max(xs)
        y_min, y_max = min(ys), max(ys)

        # 排除右侧 CRM 侧边栏
        if x_min > 830:
            continue

        # 采样颜色
        sample_x = min(w_crop - 1, int(x_max + 5))
        sample_y = int((y_min + y_max) / 2)
        p = im.getpixel((sample_x, sample_y))
        is_blue = len(p) >= 3 and p[2] > p[0] + 25

        if is_blue or x_max > 680:
            bubble_type = "BLUE" # AI / 自身
        elif x_min <= 100:
            bubble_type = "WHITE" # 对方
        else:
            continue

        bubbles.append({
            "text": text,
            "y": y_min,
            "type": bubble_type
        })

    bubbles.sort(key=lambda b: b["y"])
    if not bubbles:
        return False, "", ""

    # 最底部的气泡
    last_bubble = bubbles[-1]
    if last_bubble["type"] == "BLUE":
        # 已经由 AI 蓝色气泡收尾！无需再回
        return False, "", ""

    # 最底部不是蓝色气泡 -> 必须由 AI 回复收尾！
    # 收集自最后一条蓝色气泡以后的所有对方发言
    unreplied = []
    for b in reversed(bubbles):
        if b["type"] == "WHITE":
            unreplied.insert(0, b["text"])
        else:
            break

    full_text = " ".join(unreplied)
    sender = active_target if config.TARGET_CHATS.get(active_target, {}).get("type") == "private" else "群友"
    return True, full_text, sender

def run_bot():
    disable_quick_edit()
    logger.info("=" * 60)
    logger.info("  企业微信 LongCat AI 自动化服务启动 (AI收尾铁律执行版)")
    logger.info(f"  模型: {config.LONGCAT_MODEL}")
    logger.info(f"  已启用目标会话: {list(config.TARGET_CHATS.keys())}")
    logger.info(f"  - 核心铁律: 永远由 AI 收尾，最底部气泡非蓝色则必回复")
    logger.info(f"  - 会话支持: 群聊幽默助手 + 毫秒级群友记忆 + 气象实况")
    logger.info(f"  视觉自愈: 像素级几何定轨 + GLM-4V-Flash 兜底")
    logger.info(f"  排查日志文件: {LOG_FILE}")
    logger.info("=" * 60)

    hwnd = get_wework_hwnd()
    if not hwnd:
        logger.error("未检测到企业微信主窗口，请确保企业微信已登录并在桌面打开。")
        return

    bring_wework_to_front(hwnd)
    time.sleep(0.3)
    logger.info("服务就绪，启动会话协同监听与 AI 收尾巡检...\n")

    last_session_previews = get_session_previews(hwnd)
    loop_count = 0

    while True:
        try:
            loop_count += 1
            if loop_count % 15 == 0:
                disable_quick_edit()
                logger.info(f"[心跳正常] 持续巡检目标会话，保持 AI 蓝色气泡收尾...")

            hwnd = get_wework_hwnd()
            if not hwnd:
                logger.warning("未找到企业微信窗口，等待重试...")
                time.sleep(config.POLL_INTERVAL)
                continue

            # 1. 监测左侧会话列表是否有新消息涌入
            cur_previews = get_session_previews(hwnd)
            for chat_name, preview_text in cur_previews.items():
                if chat_name in last_session_previews:
                    old_prev = last_session_previews[chat_name]
                    if preview_text and preview_text != old_prev:
                        logger.info(f"🔔 检测到【{chat_name}】列表有新动向: '{preview_text}'，正在切入...")
                        visual_healer.locate_and_switch(hwnd, chat_name)
                        time.sleep(0.3)
                        break
            last_session_previews.update(cur_previews)

            # 2. 确保当前窗口在有效会话中
            active_target = ensure_valid_chat_focused(hwnd)

            # 3. 执行【AI 收尾铁律】核心判定
            needs_reply, unreplied_text, sender = check_chat_needs_reply(hwnd, active_target)
            if needs_reply and unreplied_text:
                logger.info(f"🎯 [未收尾触发] 检测到【{active_target}】最底部为对方发言: '{unreplied_text}'，执行 AI 蓝色气泡收尾！")
                
                chat_cfg = config.TARGET_CHATS.get(active_target, {})
                if chat_cfg.get("type") == "private":
                    reply = get_private_reply(active_target, unreplied_text)
                else:
                    reply = get_ai_reply(sender, unreplied_text)

                if reply:
                    send_chat_message(hwnd, reply)
                    async_distill_memory(sender, unreplied_text, reply)
                    time.sleep(0.5)

        except KeyboardInterrupt:
            logger.info("机器人服务已手动停止。")
            break
        except Exception as err:
            logger.error(f"监听主循环捕获异常: {err}", exc_info=True)

        time.sleep(config.POLL_INTERVAL)

if __name__ == "__main__":
    run_bot()
