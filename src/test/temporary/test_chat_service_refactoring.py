"""
TDD for God Object Pattern Resolution

ChatInteractionクラスのGod Objectパターンを解消するためのテスト
責務を4つのサービスに分割：
1. ChatSessionService - チャット開始/再開管理
2. MessageProcessingService - メッセージ処理とLLM連携
3. HistoryService - 履歴取得と管理  
4. StreamingService - ストリーミング応答処理
"""

import pytest
import uuid
import sys
import os
from unittest.mock import AsyncMock, Mock
from typing import List

# Add path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from src.domain.entity.message_entity import MessageEntity, Role
from src.domain.entity.chat_tree import ChatTree, ChatStructure
from src.port.dto.message_dto import MessageDTO
from src.port.chat_repo import ChatRepository
from src.port.llm_client import LLMClient
from src.usecase.chat_interaction.message_cache import MessageCache


class TestChatSessionService:
    """チャットセッション管理サービスのテスト"""
    
    @pytest.fixture
    def mock_chat_repo(self):
        return AsyncMock(spec=ChatRepository)
    
    @pytest.fixture  
    def mock_cache(self):
        return Mock(spec=MessageCache)
    
    @pytest.fixture
    def sample_message(self):
        return MessageEntity(
            id=1,
            uuid="test-uuid",
            role=Role.SYSTEM,
            content="System message"
        )
    
    @pytest.fixture
    def sample_chat_tree(self):
        root_node = ChatStructure(message_uuid="test-uuid")
        return ChatTree(id=1, uuid="chat-uuid", tree=root_node)

    @pytest.mark.asyncio
    async def test_start_new_chat_creates_structure(self, mock_chat_repo, mock_cache, sample_message, sample_chat_tree):
        """新しいチャット開始時に適切な構造が作成されることをテスト"""
        # Given
        from src.usecase.chat_interaction.chat_session_service import ChatSessionService
        
        mock_chat_repo.init_structure.return_value = (sample_chat_tree, sample_message)
        
        service = ChatSessionService(mock_chat_repo, mock_cache)
        
        # When
        result = await service.start_new_chat("Initial system message")
        
        # Then
        mock_chat_repo.init_structure.assert_called_once()
        mock_cache.set.assert_called_once_with(sample_message)
        assert result == sample_chat_tree.uuid
    
    @pytest.mark.asyncio
    async def test_restart_chat_loads_existing_structure(self, mock_chat_repo, mock_cache, sample_chat_tree):
        """既存チャット再開時に構造が適切にロードされることをテスト"""
        # Given
        from src.usecase.chat_interaction.chat_session_service import ChatSessionService
        
        mock_chat_repo.load_tree.return_value = sample_chat_tree
        
        service = ChatSessionService(mock_chat_repo, mock_cache)
        
        # When
        await service.restart_chat("chat-uuid")
        
        # Then
        mock_chat_repo.load_tree.assert_called_once_with("chat-uuid")
        assert service.current_chat_uuid == "chat-uuid"
    
    @pytest.mark.asyncio 
    async def test_start_new_chat_with_empty_system_message(self, mock_chat_repo, mock_cache, sample_chat_tree, sample_message):
        """空のシステムメッセージでチャット開始"""
        # Given
        from src.usecase.chat_interaction.chat_session_service import ChatSessionService
        
        mock_chat_repo.init_structure.return_value = (sample_chat_tree, sample_message)
        
        service = ChatSessionService(mock_chat_repo, mock_cache)
        
        # When
        result = await service.start_new_chat(None)
        
        # Then
        args = mock_chat_repo.init_structure.call_args[0][0]
        assert args.content == ""
        assert args.role == Role.SYSTEM


class TestMessageProcessingService:
    """メッセージ処理サービスのテスト"""
    
    @pytest.fixture
    def mock_chat_repo(self):
        return AsyncMock(spec=ChatRepository)
    
    @pytest.fixture
    def mock_llm_client(self):
        return AsyncMock(spec=LLMClient)
    
    @pytest.fixture
    def mock_cache(self):
        return Mock(spec=MessageCache)
    
    @pytest.fixture
    def sample_llm_response(self):
        return {
            "content": "LLM response content",
            "model": "test-model",
            "tokens": 100
        }
    
    @pytest.mark.asyncio
    async def test_process_user_message_saves_to_repo(self, mock_chat_repo, mock_llm_client, mock_cache):
        """ユーザーメッセージが適切に保存されることをテスト"""
        # Given
        from src.usecase.chat_interaction.message_processing_service import MessageProcessingService
        
        expected_message = MessageEntity(
            id=1, uuid="msg-uuid", role=Role.USER, content="User message"
        )
        mock_chat_repo.save_message.return_value = expected_message
        
        service = MessageProcessingService(mock_chat_repo, mock_llm_client, mock_cache)
        
        # When
        message_dto = MessageDTO(Role.USER, "User message")
        result = await service.process_message("chat-uuid", message_dto)
        
        # Then
        mock_chat_repo.save_message.assert_called_once()
        mock_cache.set.assert_called_once_with(expected_message)
        assert result == expected_message
    
    @pytest.mark.asyncio
    async def test_process_assistant_message_with_llm_details(self, mock_chat_repo, mock_llm_client, mock_cache, sample_llm_response):
        """LLM詳細付きアシスタントメッセージ処理をテスト"""
        # Given
        from src.usecase.chat_interaction.message_processing_service import MessageProcessingService
        
        expected_message = MessageEntity(
            id=1, uuid="msg-uuid", role=Role.ASSISTANT, content="Assistant response"
        )
        mock_chat_repo.save_message.return_value = expected_message
        
        service = MessageProcessingService(mock_chat_repo, mock_llm_client, mock_cache)
        
        # When
        message_dto = MessageDTO(Role.ASSISTANT, "Assistant response")
        result = await service.process_message("chat-uuid", message_dto, sample_llm_response)
        
        # Then
        call_args = mock_chat_repo.save_message.call_args
        assert call_args[1]["llm_details"] == sample_llm_response
        assert result == expected_message
    
    @pytest.mark.asyncio
    async def test_generate_llm_response_calls_client(self, mock_chat_repo, mock_llm_client, mock_cache, sample_llm_response):
        """LLM応答生成が適切にクライアントを呼び出すことをテスト"""
        # Given
        from src.usecase.chat_interaction.message_processing_service import MessageProcessingService
        
        mock_llm_client.complete_message.return_value = sample_llm_response
        history = [
            MessageEntity(id=1, uuid="1", role=Role.USER, content="Hello")
        ]
        
        service = MessageProcessingService(mock_chat_repo, mock_llm_client, mock_cache)
        
        # When
        result = await service.generate_llm_response(history)
        
        # Then
        mock_llm_client.complete_message.assert_called_once_with(history)
        assert result == sample_llm_response


class TestHistoryService:
    """履歴管理サービスのテスト"""
    
    @pytest.fixture
    def mock_chat_repo(self):
        return AsyncMock(spec=ChatRepository)
    
    @pytest.fixture
    def sample_history(self):
        return [
            MessageEntity(id=1, uuid="1", role=Role.USER, content="Hello"),
            MessageEntity(id=2, uuid="2", role=Role.ASSISTANT, content="Hi there")
        ]
    
    @pytest.mark.asyncio
    async def test_get_chat_history_returns_ordered_messages(self, mock_chat_repo, sample_history):
        """チャット履歴が順序正しく取得されることをテスト"""
        # Given
        from src.usecase.chat_interaction.history_service import HistoryService
        
        mock_chat_repo.get_history.return_value = sample_history
        
        service = HistoryService(mock_chat_repo)
        
        # When
        result = await service.get_chat_history(["1", "2"])
        
        # Then
        mock_chat_repo.get_history.assert_called_once_with(["1", "2"])
        assert result == sample_history
    
    @pytest.mark.asyncio
    async def test_get_history_excludes_last_assistant_message(self, mock_chat_repo, sample_history):
        """最後のアシスタントメッセージを除外して履歴取得"""
        # Given
        from src.usecase.chat_interaction.history_service import HistoryService
        
        service = HistoryService(mock_chat_repo)
        
        # When
        result = service.exclude_last_assistant_message(sample_history)
        
        # Then
        assert len(result) == 1
        assert result[0].role == Role.USER
        assert result[0].content == "Hello"


class TestStreamingService:
    """ストリーミング応答サービスのテスト"""
    
    @pytest.fixture
    def mock_llm_client(self):
        return AsyncMock(spec=LLMClient)
    
    @pytest.fixture
    def mock_message_processor(self):
        return AsyncMock()
    
    @pytest.fixture
    def sample_chunks(self):
        return [
            {"choices": [{"delta": {"content": "Hello"}}]},
            {"choices": [{"delta": {"content": " world"}}]},
            {"choices": [{"delta": {"content": "!"}}]}
        ]
    
    @pytest.mark.asyncio
    async def test_stream_response_accumulates_content(self, mock_llm_client, mock_message_processor, sample_chunks):
        """ストリーミング応答が適切に蓄積されることをテスト"""
        # Given
        from src.usecase.chat_interaction.streaming_service import StreamingService
        
        async def mock_stream_generator(chat_history):
            for chunk in sample_chunks:
                yield chunk
        
        # AsyncMockの正しい設定
        mock_llm_client.complete_message_stream = mock_stream_generator
        
        service = StreamingService(mock_llm_client, mock_message_processor)
        history = [MessageEntity(id=1, uuid="1", role=Role.USER, content="Test")]
        
        # When
        chunks = []
        async for chunk in service.stream_response(history):
            chunks.append(chunk)
        
        # Then
        assert len(chunks) >= 3  # 3つのストリーミングチャンク + 最終メッセージ
        # 最後のチャンクは完全なメッセージであるべき
        final_chunk = chunks[-1]
        assert not getattr(final_chunk, 'is_streaming', True)  # 最終メッセージはストリーミングではない
    
    @pytest.mark.asyncio
    async def test_streaming_message_has_temp_id(self, mock_llm_client, mock_message_processor, sample_chunks):
        """ストリーミングメッセージが一時IDを持つことをテスト"""
        # Given
        from src.usecase.chat_interaction.streaming_service import StreamingService
        
        async def mock_stream_generator(chat_history):
            yield sample_chunks[0]  # 1つだけ返す
        
        # AsyncMockの正しい設定
        mock_llm_client.complete_message_stream = mock_stream_generator
        
        service = StreamingService(mock_llm_client, mock_message_processor)
        history = [MessageEntity(id=1, uuid="1", role=Role.USER, content="Test")]
        
        # When
        async for streaming_message in service.stream_response(history):
            if getattr(streaming_message, 'is_streaming', False):
                # Then
                assert hasattr(streaming_message, 'temp_id')
                assert streaming_message.temp_id is not None
                break