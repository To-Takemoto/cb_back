"""
MessageProcessingService Unit Tests

メッセージ処理サービスの包括的なユニットテスト
メッセージ保存、LLM連携、ワークフロー管理をテスト
"""

import pytest
import sys
import os
from unittest.mock import AsyncMock, Mock

# Add path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from src.domain.entity.message_entity import MessageEntity, Role
from src.domain.exception.chat_exceptions import LLMServiceError
from src.port.dto.message_dto import MessageDTO
from src.usecase.chat_interaction.message_processing_service import MessageProcessingService
from src.usecase.chat_interaction.message_cache import MessageCache
from src.port.chat_repo import ChatRepository
from src.port.llm_client import LLMClient


class TestMessageProcessingService:
    """MessageProcessingServiceの包括的テスト"""
    
    @pytest.fixture
    def mock_chat_repo(self):
        """モックChatRepositoryフィクスチャ"""
        return AsyncMock(spec=ChatRepository)
    
    @pytest.fixture
    def mock_llm_client(self):
        """モックLLMClientフィクスチャ"""
        return AsyncMock(spec=LLMClient)
    
    @pytest.fixture
    def mock_cache(self):
        """モックMessageCacheフィクスチャ"""
        return Mock(spec=MessageCache)
    
    @pytest.fixture
    def service(self, mock_chat_repo, mock_llm_client, mock_cache):
        """MessageProcessingServiceインスタンス"""
        return MessageProcessingService(mock_chat_repo, mock_llm_client, mock_cache)
    
    @pytest.fixture
    def sample_user_message(self):
        """サンプルユーザーメッセージ"""
        return MessageEntity(
            id=1, uuid="user-msg-uuid", role=Role.USER, content="Hello, how are you?"
        )
    
    @pytest.fixture
    def sample_assistant_message(self):
        """サンプルアシスタントメッセージ"""
        return MessageEntity(
            id=2, uuid="assistant-msg-uuid", role=Role.ASSISTANT, content="I'm doing well, thank you!"
        )
    
    @pytest.fixture
    def sample_llm_response(self):
        """サンプルLLM応答"""
        return {
            "content": "I'm doing well, thank you!",
            "model": "test-model",
            "prompt_tokens": 10,
            "completion_tokens": 15,
            "total_tokens": 25
        }
    
    @pytest.fixture
    def sample_chat_history(self, sample_user_message):
        """サンプルチャット履歴"""
        return [sample_user_message]

    # === メッセージ処理テスト ===
    
    @pytest.mark.asyncio
    async def test_process_user_message_success(self, service, mock_chat_repo, mock_cache, sample_user_message):
        """ユーザーメッセージの正常処理"""
        # Given
        chat_uuid = "test-chat-uuid"
        message_dto = MessageDTO(Role.USER, "Hello, how are you?")
        mock_chat_repo.save_message.return_value = sample_user_message
        
        # When
        result = await service.process_message(chat_uuid, message_dto)
        
        # Then
        assert result == sample_user_message
        mock_chat_repo.save_message.assert_called_once_with(
            discussion_structure_uuid=chat_uuid,
            message_dto=message_dto,
            llm_details=None
        )
        mock_cache.set.assert_called_once_with(sample_user_message)
    
    @pytest.mark.asyncio
    async def test_process_assistant_message_with_llm_details(self, service, mock_chat_repo, mock_cache, sample_assistant_message, sample_llm_response):
        """LLM詳細付きアシスタントメッセージの処理"""
        # Given
        chat_uuid = "test-chat-uuid"
        message_dto = MessageDTO(Role.ASSISTANT, "I'm doing well, thank you!")
        mock_chat_repo.save_message.return_value = sample_assistant_message
        
        # When
        result = await service.process_message(chat_uuid, message_dto, sample_llm_response)
        
        # Then
        assert result == sample_assistant_message
        mock_chat_repo.save_message.assert_called_once_with(
            discussion_structure_uuid=chat_uuid,
            message_dto=message_dto,
            llm_details=sample_llm_response
        )
        mock_cache.set.assert_called_once_with(sample_assistant_message)
    
    @pytest.mark.asyncio
    async def test_process_message_repo_error(self, service, mock_chat_repo):
        """リポジトリエラー時の例外伝播"""
        # Given
        chat_uuid = "test-chat-uuid"
        message_dto = MessageDTO(Role.USER, "Test message")
        mock_chat_repo.save_message.side_effect = Exception("Database error")
        
        # When & Then
        with pytest.raises(Exception, match="Database error"):
            await service.process_message(chat_uuid, message_dto)

    # === LLM応答生成テスト ===
    
    @pytest.mark.asyncio
    async def test_generate_llm_response_success(self, service, mock_llm_client, sample_chat_history, sample_llm_response):
        """LLM応答の正常生成"""
        # Given
        mock_llm_client.complete_message.return_value = sample_llm_response
        
        # When
        result = await service.generate_llm_response(sample_chat_history)
        
        # Then
        assert result == sample_llm_response
        mock_llm_client.complete_message.assert_called_once_with(sample_chat_history)
    
    @pytest.mark.asyncio
    async def test_generate_llm_response_empty_content(self, service, mock_llm_client, sample_chat_history):
        """空のLLM応答に対するエラーハンドリング"""
        # Given
        empty_response = {"content": ""}
        mock_llm_client.complete_message.return_value = empty_response
        
        # When & Then
        with pytest.raises(LLMServiceError, match="Empty response from LLM service"):
            await service.generate_llm_response(sample_chat_history)
    
    @pytest.mark.asyncio
    async def test_generate_llm_response_missing_content(self, service, mock_llm_client, sample_chat_history):
        """contentキーが存在しない場合のエラーハンドリング"""
        # Given
        invalid_response = {"model": "test-model"}
        mock_llm_client.complete_message.return_value = invalid_response
        
        # When & Then
        with pytest.raises(LLMServiceError, match="Empty response from LLM service"):
            await service.generate_llm_response(sample_chat_history)
    
    @pytest.mark.asyncio
    async def test_generate_llm_response_client_error(self, service, mock_llm_client, sample_chat_history):
        """LLMクライアントエラーの適切な変換"""
        # Given
        mock_llm_client.complete_message.side_effect = Exception("Network error")
        
        # When & Then
        with pytest.raises(LLMServiceError, match="Failed to generate LLM response: Network error"):
            await service.generate_llm_response(sample_chat_history)

    # === 統合ワークフローテスト ===
    
    @pytest.mark.asyncio
    async def test_process_user_message_and_generate_response_success(self, service, mock_chat_repo, mock_llm_client, mock_cache, sample_user_message, sample_assistant_message, sample_llm_response, sample_chat_history):
        """ユーザーメッセージ処理とLLM応答生成の統合テスト"""
        # Given
        chat_uuid = "test-chat-uuid"
        user_content = "Hello, how are you?"
        
        # モック設定
        mock_chat_repo.save_message.side_effect = [sample_user_message, sample_assistant_message]
        mock_llm_client.complete_message.return_value = sample_llm_response
        
        # When
        result = await service.process_user_message_and_generate_response(
            chat_uuid, user_content, sample_chat_history
        )
        
        # Then
        assert result == sample_assistant_message
        
        # ユーザーメッセージとアシスタントメッセージの両方が保存されたか確認
        assert mock_chat_repo.save_message.call_count == 2
        
        # LLMクライアントが呼ばれたか確認
        mock_llm_client.complete_message.assert_called_once_with(sample_chat_history)
        
        # キャッシュが2回更新されたか確認
        assert mock_cache.set.call_count == 2
    
    @pytest.mark.asyncio
    async def test_process_user_message_and_generate_response_empty_content(self, service):
        """空のユーザーメッセージに対するエラーハンドリング"""
        # Given
        chat_uuid = "test-chat-uuid"
        empty_content = ""
        chat_history = []
        
        # When & Then
        with pytest.raises(ValueError, match="Message content cannot be empty"):
            await service.process_user_message_and_generate_response(
                chat_uuid, empty_content, chat_history
            )
    
    @pytest.mark.asyncio
    async def test_process_user_message_and_generate_response_whitespace_only(self, service):
        """空白文字のみのユーザーメッセージに対するエラーハンドリング"""
        # Given
        chat_uuid = "test-chat-uuid"
        whitespace_content = "   \n\t   "
        chat_history = []
        
        # When & Then
        with pytest.raises(ValueError, match="Message content cannot be empty"):
            await service.process_user_message_and_generate_response(
                chat_uuid, whitespace_content, chat_history
            )
    
    @pytest.mark.asyncio
    async def test_process_user_message_and_generate_response_llm_error(self, service, mock_chat_repo, mock_llm_client, sample_user_message):
        """LLMエラー時の適切な例外伝播"""
        # Given
        chat_uuid = "test-chat-uuid"
        user_content = "Hello"
        chat_history = []
        
        mock_chat_repo.save_message.return_value = sample_user_message
        mock_llm_client.complete_message.side_effect = LLMServiceError("LLM service unavailable")
        
        # When & Then
        with pytest.raises(LLMServiceError, match="LLM service unavailable"):
            await service.process_user_message_and_generate_response(
                chat_uuid, user_content, chat_history
            )

    # === 境界値・エッジケーステスト ===
    
    @pytest.mark.asyncio
    async def test_process_message_with_none_llm_details(self, service, mock_chat_repo, mock_cache, sample_user_message):
        """LLM詳細がNoneの場合の正常動作"""
        # Given
        chat_uuid = "test-chat-uuid"
        message_dto = MessageDTO(Role.USER, "Test")
        mock_chat_repo.save_message.return_value = sample_user_message
        
        # When
        result = await service.process_message(chat_uuid, message_dto, None)
        
        # Then
        assert result == sample_user_message
        mock_chat_repo.save_message.assert_called_once_with(
            discussion_structure_uuid=chat_uuid,
            message_dto=message_dto,
            llm_details=None
        )
    
    @pytest.mark.asyncio
    async def test_generate_llm_response_with_empty_history(self, service, mock_llm_client, sample_llm_response):
        """空の履歴でのLLM応答生成"""
        # Given
        empty_history = []
        mock_llm_client.complete_message.return_value = sample_llm_response
        
        # When
        result = await service.generate_llm_response(empty_history)
        
        # Then
        assert result == sample_llm_response
        mock_llm_client.complete_message.assert_called_once_with(empty_history)