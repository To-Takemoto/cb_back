"""
StreamingService - ストリーミング応答処理サービス

責務:
- LLMストリーミング応答の処理
- 部分的メッセージの生成と配信
- 最終メッセージの確定と保存

God Objectパターン解消の一環として、ChatInteractionから分離。
"""

import uuid
from typing import AsyncGenerator, List
from ...domain.entity.message_entity import MessageEntity, Role
from ...domain.exception.chat_exceptions import LLMServiceError
from ...port.llm_client import LLMClient


class StreamingService:
    """ストリーミング応答処理サービス"""
    
    def __init__(self, llm_client: LLMClient, message_processor):
        """
        ストリーミングサービスを初期化
        
        Args:
            llm_client: LLMサービスとの通信インターフェース
            message_processor: メッセージ処理サービス
        """
        self.llm_client = llm_client
        self.message_processor = message_processor
    
    async def stream_response(self, chat_history: List[MessageEntity]) -> AsyncGenerator[MessageEntity, None]:
        """
        チャット履歴を使用してストリーミング応答を生成
        
        Args:
            chat_history: チャット履歴のメッセージリスト
            
        Yields:
            MessageEntity: ストリーミング中の部分メッセージと最終確定メッセージ
            
        Raises:
            LLMServiceError: LLMサービスとの通信でエラーが発生した場合
        """
        try:
            # ストリーミングレスポンスの蓄積
            accumulated_content = ""
            temp_id = str(uuid.uuid4())
            
            # LLMからのストリーミングレスポンスを処理
            async for chunk in self.llm_client.complete_message_stream(chat_history):
                # 安全にコンテンツを抽出
                choices = chunk.get("choices", [])
                if not choices:
                    continue
                
                delta = choices[0].get("delta", {})
                delta_content = delta.get("content", "")
                
                if delta_content:
                    accumulated_content += delta_content
                    
                    # 部分的なメッセージエンティティを配信
                    streaming_message = MessageEntity(
                        id=0,  # 一時的な値
                        uuid="",  # 一時的な値
                        role=Role.ASSISTANT,
                        content=accumulated_content,
                        is_streaming=True,
                        temp_id=temp_id
                    )
                    yield streaming_message
            
            # 空のレスポンスチェック
            if not accumulated_content.strip():
                raise LLMServiceError("Empty response from LLM service")
            
            # 最終メッセージを作成（ストリーミングフラグを無効化）
            final_message = MessageEntity(
                id=0,  # 実際の保存時に設定
                uuid=str(uuid.uuid4()),
                role=Role.ASSISTANT,
                content=accumulated_content,
                is_streaming=False,
                temp_id=None
            )
            
            # 最終確定メッセージを配信
            yield final_message
            
        except Exception as e:
            if isinstance(e, LLMServiceError):
                raise
            raise LLMServiceError(f"Failed to stream chat: {str(e)}")
    
    async def stream_user_message_and_response(
        self, 
        chat_uuid: str,
        user_content: str, 
        chat_history: List[MessageEntity]
    ) -> AsyncGenerator[MessageEntity, None]:
        """
        ユーザーメッセージを処理し、ストリーミング応答を生成
        
        Args:
            chat_uuid: 対象チャットのUUID
            user_content: ユーザーメッセージの内容
            chat_history: 現在のチャット履歴
            
        Yields:
            MessageEntity: ストリーミング中の部分メッセージと最終確定メッセージ
            
        Raises:
            ValueError: メッセージ内容が空の場合
            LLMServiceError: LLM処理でエラーが発生した場合
        """
        if not user_content.strip():
            raise ValueError("Message content cannot be empty")
        
        # ユーザーメッセージを処理
        from ...port.dto.message_dto import MessageDTO
        user_message_dto = MessageDTO(Role.USER, user_content)
        await self.message_processor.process_message(chat_uuid, user_message_dto)
        
        # ストリーミング応答を生成・配信
        final_message = None
        async for message_chunk in self.stream_response(chat_history):
            if getattr(message_chunk, 'is_streaming', False):
                # ストリーミング中のメッセージを配信
                yield message_chunk
            else:
                # 最終メッセージを保存
                from ...port.dto.message_dto import MessageDTO
                llm_message_dto = MessageDTO(Role.ASSISTANT, message_chunk.content)
                llm_details = {"content": message_chunk.content}
                final_message = await self.message_processor.process_message(
                    chat_uuid, llm_message_dto, llm_details
                )
                
                # 最終確定メッセージを配信
                yield final_message