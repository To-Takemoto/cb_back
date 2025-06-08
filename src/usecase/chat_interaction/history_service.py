"""
HistoryService - 履歴管理サービス

責務:
- チャット履歴の取得と管理
- 履歴データの変換と操作
- パスベースの履歴アクセス

God Objectパターン解消の一環として、ChatInteractionから分離。
"""

from typing import List
from ...domain.entity.message_entity import MessageEntity, Role
from ...port.chat_repo import ChatRepository


class HistoryService:
    """履歴管理サービス"""
    
    def __init__(self, chat_repo: ChatRepository):
        """
        履歴サービスを初期化
        
        Args:
            chat_repo: チャットデータの永続化インターフェース
        """
        self.chat_repo = chat_repo
    
    async def get_chat_history(self, uuid_list: List[str]) -> List[MessageEntity]:
        """
        指定されたUUIDリストに対応するメッセージ履歴を取得
        
        Args:
            uuid_list: 取得するメッセージのUUIDリスト
            
        Returns:
            List[MessageEntity]: 時間的順序でソートされたメッセージ一覧
        """
        return await self.chat_repo.get_history(uuid_list)
    
    def exclude_last_assistant_message(self, chat_history: List[MessageEntity]) -> List[MessageEntity]:
        """
        最後のアシスタントメッセージを除外した履歴を返す
        
        Args:
            chat_history: 元のチャット履歴
            
        Returns:
            List[MessageEntity]: 最後のアシスタントメッセージを除いた履歴
        """
        if not chat_history:
            return chat_history
        
        # 最後のメッセージがアシスタントメッセージの場合は除外
        if chat_history[-1].role == Role.ASSISTANT:
            return chat_history[:-1]
        
        return chat_history
    
    def find_last_user_message(self, chat_history: List[MessageEntity]) -> MessageEntity:
        """
        履歴から最後のユーザーメッセージを取得
        
        Args:
            chat_history: チャット履歴
            
        Returns:
            MessageEntity: 最後のユーザーメッセージ
            
        Raises:
            ValueError: ユーザーメッセージが見つからない場合
        """
        for message in reversed(chat_history):
            if message.role == Role.USER:
                return message
        
        raise ValueError("No user message found in chat history")
    
    def get_messages_up_to_last_user(self, chat_history: List[MessageEntity]) -> List[MessageEntity]:
        """
        最後のユーザーメッセージまでの履歴を取得
        
        Args:
            chat_history: 元のチャット履歴
            
        Returns:
            List[MessageEntity]: 最後のユーザーメッセージまでの履歴
        """
        # 最後のアシスタントメッセージを除外
        history_without_last_assistant = self.exclude_last_assistant_message(chat_history)
        
        if not history_without_last_assistant:
            return []
        
        # 最後のメッセージがユーザーメッセージでない場合はエラー
        if history_without_last_assistant[-1].role != Role.USER:
            raise ValueError("Last message is not from user")
        
        return history_without_last_assistant