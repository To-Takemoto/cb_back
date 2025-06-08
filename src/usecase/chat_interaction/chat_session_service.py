"""
ChatSessionService - チャットセッション管理サービス

責務:
- 新しいチャットセッションの開始
- 既存チャットセッションの再開  
- チャット状態の管理

God Objectパターン解消の一環として、ChatInteractionから分離。
"""

import uuid
from typing import Optional
from ...domain.entity.message_entity import MessageEntity, Role
from ...domain.entity.chat_tree import ChatTree
from ...port.chat_repo import ChatRepository
from .message_cache import MessageCache
from .structure_handler import StructureHandle


class ChatSessionService:
    """チャットセッション管理サービス"""
    
    def __init__(self, chat_repo: ChatRepository, cache: MessageCache):
        """
        チャットセッションサービスを初期化
        
        Args:
            chat_repo: チャットデータの永続化インターフェース
            cache: メッセージキャッシュ
        """
        self.chat_repo = chat_repo
        self.cache = cache
        self.current_chat_uuid: Optional[str] = None
        self.structure_handler: Optional[StructureHandle] = None
    
    async def start_new_chat(self, initial_message: Optional[str] = None) -> str:
        """
        新しいチャットセッションを開始
        
        Args:
            initial_message: 初期システムメッセージ（Noneの場合は空文字列）
            
        Returns:
            str: 作成されたチャットのUUID
            
        Side Effects:
            - データベースに新しいチャットと初期メッセージを作成
            - 内部状態を新しいチャットに設定
            - メッセージキャッシュに初期メッセージを登録
        """
        # 初期メッセージエンティティを作成
        initial_message_entity = MessageEntity(
            id=0,  # データベース保存時に設定される
            uuid=str(uuid.uuid4()),
            role=Role.SYSTEM,
            content=initial_message or ""
        )
        
        # 新しいチャット構造を初期化
        chat_tree, saved_message = await self.chat_repo.init_structure(initial_message_entity)
        
        # 内部状態を更新
        self.current_chat_uuid = chat_tree.uuid
        
        # キャッシュに初期メッセージを保存
        self.cache.set(saved_message)
        
        return chat_tree.uuid
    
    async def restart_chat(self, chat_uuid: str) -> None:
        """
        既存のチャットセッションを再開
        
        Args:
            chat_uuid: 再開するチャットのUUID
            
        Raises:
            ChatNotFoundError: 指定されたチャットが存在しない場合
            
        Side Effects:
            - 内部状態を指定されたチャットに切り替え
            - ツリー構造をロードし、最新メッセージに移動
        """
        # チャットツリーをロード
        chat_tree = await self.chat_repo.load_tree(chat_uuid)
        
        # 内部状態を更新
        self.current_chat_uuid = chat_uuid
    
    def get_current_chat_uuid(self) -> Optional[str]:
        """現在のチャットUUIDを取得"""
        return self.current_chat_uuid
    
    def get_structure_handler(self) -> Optional[StructureHandle]:
        """構造ハンドラーを取得"""
        return self.structure_handler
    
    def is_chat_active(self) -> bool:
        """チャットがアクティブかどうかを確認"""
        return self.current_chat_uuid is not None