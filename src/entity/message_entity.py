from dataclasses import dataclass
from enum import Enum

# 基本的な共通クラス
class Role(str, Enum):
    """メッセージの役割を表す列挙型"""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"

@dataclass
class Message:
    id: int
    uuid: str
    role: Role
    content: str