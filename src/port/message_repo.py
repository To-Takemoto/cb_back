from typing import Protocol

from ..entity.message import Message

class MessageRepository(Protocol):
    """メッセージリポジトリのインターフェース"""
    
    async def get_conversation_history(self, conversation_id: str) -> list[Message]:
        """会話履歴を取得する"""
    
    async def save(self, message: Message, conversation_id: str) -> Message:
        """メッセージを保存する"""