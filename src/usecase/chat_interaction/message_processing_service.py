"""
MessageProcessingService - メッセージ処理サービス

責務:
- メッセージの保存とキャッシュ更新
- LLMとの連携と応答生成
- メッセージ処理のワークフロー管理

God Objectパターン解消の一環として、ChatInteractionから分離。
"""

from typing import Optional, List
from ...domain.entity.message_entity import MessageEntity
from ...domain.exception.chat_exceptions import LLMServiceError
from ...port.dto.message_dto import MessageDTO
from ...port.chat_repo import ChatRepository
from ...port.llm_client import LLMClient
from .message_cache import MessageCache


class MessageProcessingService:
    """メッセージ処理サービス"""
    
    def __init__(self, chat_repo: ChatRepository, llm_client: LLMClient, cache: MessageCache):
        """
        メッセージ処理サービスを初期化
        
        Args:
            chat_repo: チャットデータの永続化インターフェース
            llm_client: LLMサービスとの通信インターフェース
            cache: メッセージキャッシュ
        """
        self.chat_repo = chat_repo
        self.llm_client = llm_client
        self.cache = cache
    
    async def process_message(
        self, 
        chat_uuid: str, 
        message_dto: MessageDTO, 
        llm_details: Optional[dict] = None
    ) -> MessageEntity:
        """
        メッセージを処理してデータベースに保存
        
        Args:
            chat_uuid: 対象チャットのUUID
            message_dto: 保存するメッセージのデータ
            llm_details: LLMレスポンスの詳細情報（トークン数、モデル情報等）
        
        Returns:
            MessageEntity: 保存されたメッセージエンティティ
            
        Side Effects:
            - データベースにメッセージを保存
            - メッセージキャッシュを更新
        """
        # メッセージをデータベースに保存
        message_entity = await self.chat_repo.save_message(
            discussion_structure_uuid=chat_uuid,
            message_dto=message_dto,
            llm_details=llm_details
        )
        
        # キャッシュを更新
        self.cache.set(message_entity)
        
        return message_entity
    
    async def generate_llm_response(self, chat_history: List[MessageEntity]) -> dict:
        """
        チャット履歴を使用してLLM応答を生成
        
        Args:
            chat_history: チャット履歴のメッセージリスト
            
        Returns:
            dict: LLMからの応答データ
            
        Raises:
            LLMServiceError: LLMサービスとの通信でエラーが発生した場合
        """
        try:
            llm_response = await self.llm_client.complete_message(chat_history)
            
            if not llm_response.get("content"):
                raise LLMServiceError("Empty response from LLM service")
            
            return llm_response
        
        except Exception as e:
            if isinstance(e, LLMServiceError):
                raise
            raise LLMServiceError(f"Failed to generate LLM response: {str(e)}")
    
    async def process_user_message_and_generate_response(
        self, 
        chat_uuid: str, 
        user_content: str, 
        chat_history: List[MessageEntity]
    ) -> MessageEntity:
        """
        ユーザーメッセージを処理し、LLM応答を生成して保存
        
        Args:
            chat_uuid: 対象チャットのUUID
            user_content: ユーザーメッセージの内容
            chat_history: 現在のチャット履歴
            
        Returns:
            MessageEntity: 生成されたLLMメッセージ
            
        Raises:
            ValueError: メッセージ内容が空の場合
            LLMServiceError: LLM処理でエラーが発生した場合
        """
        if not user_content.strip():
            raise ValueError("Message content cannot be empty")
        
        # ユーザーメッセージを処理
        from ...domain.entity.message_entity import Role
        user_message_dto = MessageDTO(Role.USER, user_content)
        await self.process_message(chat_uuid, user_message_dto)
        
        # LLM応答を生成
        llm_response = await self.generate_llm_response(chat_history)
        
        # LLMメッセージを処理
        llm_message_dto = MessageDTO(Role.ASSISTANT, llm_response["content"])
        llm_message = await self.process_message(chat_uuid, llm_message_dto, llm_response)
        
        return llm_message