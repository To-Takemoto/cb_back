# infrastructure/sqlite_client.py
import uuid
from typing import List

from tortoise import Tortoise, fields
from tortoise.models import Model
from tortoise.contrib.pydantic import pydantic_model_creator

from ..port.message_repo import MessageRepository
from ..entity.message import Message, Role


# TortoiseORM用のモデル定義
class MessageModel(Model):
    """メッセージのデータベースモデル"""
    id = fields.IntField(pk=True)
    uuid = fields.CharField(max_length=36, unique=True)
    role = fields.CharField(max_length=20)
    content = fields.TextField()
    conversation_id = fields.CharField(max_length=36, index=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    
    class Meta:
        table = "messages"


class TortoiseMessageRepository(MessageRepository):
    """TortoiseORMを用いたメッセージリポジトリの実装"""
    
    def __init__(self, db_url: str):
        """
        Args:
            db_url: SQLiteデータベースのURL (例: 'sqlite://db.sqlite3')
        """
        self.db_url = db_url
        self._initialized = False
    
    async def _ensure_initialized(self):
        """必要に応じてデータベース接続を初期化する"""
        if not self._initialized:
            await Tortoise.init(
                db_url=self.db_url,
                modules={'models': ['src.infra.sqlite_client']}  # 実際のモジュールパスに合わせて調整する必要あり
            )
            await Tortoise.generate_schemas()
            self._initialized = True
    
    async def get_conversation_history(self, conversation_id: str) -> List[Message]:
        """会話履歴を取得する
        
        Args:
            conversation_id: 会話ID
            
        Returns:
            会話履歴のメッセージリスト
        """
        await self._ensure_initialized()
        
        # 会話IDでメッセージを検索し、IDの昇順で取得
        db_messages = await MessageModel.filter(
            conversation_id=conversation_id
        ).order_by('id')
        
        # ドメインエンティティに変換して返す
        messages = []
        for db_message in db_messages:
            messages.append(Message(
                id=db_message.id,
                uuid=db_message.uuid,
                role=Role(db_message.role),
                content=db_message.content
            ))
        
        return messages
    
    async def save(self, message: Message, conversation_id: str) -> Message:
        """メッセージを保存する
        
        Args:
            message: 保存するメッセージ
            conversation_id: 会話ID
            
        Returns:
            保存されたメッセージ
        """
        await self._ensure_initialized()
        
        # UUIDが空の場合は新規生成
        msg_uuid = message.uuid or str(uuid.uuid4())
        
        # データベースモデルを作成して保存
        db_message = await MessageModel.create(
            uuid=msg_uuid,
            role=message.role.value,
            content=message.content,
            conversation_id=conversation_id
        )
        
        # 保存されたメッセージをドメインエンティティとして返す
        return Message(
            id=db_message.id,
            uuid=db_message.uuid,
            role=message.role,
            content=db_message.content
        )
    
    async def close(self):
        """データベース接続を閉じる"""
        if self._initialized:
            await Tortoise.close_connections()
            self._initialized = False