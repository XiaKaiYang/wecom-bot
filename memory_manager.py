# -*- coding: utf-8 -*-
"""
轻量级个性化群友记忆库 (零锁、毫秒级响应、永久持久化)
"""
import os
import json
import logging
import threading

logger = logging.getLogger("WeComBot")

class GroupMemoryManager:
    def __init__(self, storage_path):
        self.storage_path = storage_path
        self.lock = threading.Lock()
        self.memories = {}
        self.load()

    def load(self):
        with self.lock:
            if os.path.exists(self.storage_path):
                try:
                    with open(self.storage_path, "r", encoding="utf-8") as f:
                        self.memories = json.load(f)
                except Exception as e:
                    logger.warning(f"读取记忆库异常: {e}")
                    self.memories = {}
            else:
                example_path = os.path.join(os.path.dirname(self.storage_path), "user_memories.example.json")
                if os.path.exists(example_path):
                    try:
                        with open(example_path, "r", encoding="utf-8") as f:
                            self.memories = json.load(f)
                    except Exception:
                        self.memories = {}
                else:
                    self.memories = {}
                self.save_unlocked()

    def save_unlocked(self):
        try:
            with open(self.storage_path, "w", encoding="utf-8") as f:
                json.dump(self.memories, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存记忆库异常: {e}")

    def get_user_memory(self, user_name, query=""):
        """毫秒级检索群友记忆，无网络延迟与文件锁"""
        with self.lock:
            user_mems = self.memories.get(user_name, [])
            if not user_mems:
                # 模糊匹配
                for k, v in self.memories.items():
                    if k in user_name or user_name in k:
                        return v[:4]
                return []
            return user_mems[:4]

    def add_user_memory(self, user_name, fact):
        """新增群友个性特征"""
        if not fact or len(fact) < 2:
            return
        with self.lock:
            if user_name not in self.memories:
                self.memories[user_name] = []
            if fact not in self.memories[user_name]:
                self.memories[user_name].append(fact)
                if len(self.memories[user_name]) > 10:
                    self.memories[user_name].pop(0)
                self.save_unlocked()
                logger.info(f"已沉淀群友【{user_name}】新特征: {fact}")
