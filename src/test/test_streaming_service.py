"""
StreamingService Unit Tests

ストリーミング応答処理サービスの包括的なユニットテスト
ストリーミング処理、部分メッセージ生成、最終メッセージ確定をテスト
"""

import pytest
import sys
import os
from unittest.mock import AsyncMock, Mock

# Add path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from src.domain.entity.message_entity import MessageEntity, Role
from src.domain.exception.chat_exceptions import LLMServiceError
from src.usecase.chat_interaction.streaming_service import StreamingService
from src.port.llm_client import LLMClient


class TestStreamingService:
    """StreamingServiceの包括的テスト"""
    
    @pytest.fixture
    def mock_llm_client(self):
        """モックLLMClientフィクスチャ"""
        return AsyncMock(spec=LLMClient)
    
    @pytest.fixture
    def mock_message_processor(self):
        """モックメッセージプロセッサー"""
        return AsyncMock()
    
    @pytest.fixture
    def service(self, mock_llm_client, mock_message_processor):
        """StreamingServiceインスタンス"""
        return StreamingService(mock_llm_client, mock_message_processor)
    
    @pytest.fixture
    def sample_chat_history(self):
        """サンプルチャット履歴"""
        return [
            MessageEntity(id=1, uuid="msg-1", role=Role.USER, content="Hello, how are you?")
        ]
    
    @pytest.fixture
    def sample_streaming_chunks(self):
        """サンプルストリーミングチャンク"""
        return [
            {"choices": [{"delta": {"content": "I'm"}}]},
            {"choices": [{"delta": {"content": " doing"}}]},
            {"choices": [{"delta": {"content": " well,"}}]},
            {"choices": [{"delta": {"content": " thank"}}]},
            {"choices": [{"delta": {"content": " you!"}}]}
        ]
    
    @pytest.fixture
    def empty_chunks(self):
        """空のコンテンツのチャンク"""
        return [
            {"choices": [{"delta": {}}]},
            {"choices": [{"delta": {"content": ""}}]},
            {"choices": [{"delta": {"content": None}}]}
        ]

    # === ストリーミング応答生成テスト ===
    
    @pytest.mark.asyncio
    async def test_stream_response_success(self, service, mock_llm_client, sample_chat_history, sample_streaming_chunks):
        """正常なストリーミング応答処理"""
        # Given
        async def mock_stream_generator(chat_history):
            for chunk in sample_streaming_chunks:
                yield chunk
        
        mock_llm_client.complete_message_stream = mock_stream_generator
        
        # When
        chunks = []
        async for message_chunk in service.stream_response(sample_chat_history):
            chunks.append(message_chunk)
        
        # Then
        assert len(chunks) == 6  # 5つのストリーミング + 1つの最終メッセージ
        
        # ストリーミングメッセージの検証
        for i in range(5):
            chunk = chunks[i]
            assert chunk.role == Role.ASSISTANT
            assert getattr(chunk, 'is_streaming', False) == True
            assert hasattr(chunk, 'temp_id')
            assert chunk.temp_id is not None
        
        # 最終メッセージの検証
        final_message = chunks[-1]
        assert final_message.content == "I'm doing well, thank you!"
        assert getattr(final_message, 'is_streaming', True) == False
        assert getattr(final_message, 'temp_id', "not_none") is None
    
    @pytest.mark.asyncio
    async def test_stream_response_content_accumulation(self, service, mock_llm_client, sample_chat_history, sample_streaming_chunks):
        """コンテンツの正しい蓄積"""
        # Given
        async def mock_stream_generator(chat_history):
            for chunk in sample_streaming_chunks:
                yield chunk
        
        mock_llm_client.complete_message_stream = mock_stream_generator
        
        # When
        accumulated_contents = []
        async for message_chunk in service.stream_response(sample_chat_history):
            if getattr(message_chunk, 'is_streaming', False):
                accumulated_contents.append(message_chunk.content)
        
        # Then
        expected_accumulations = ["I'm", "I'm doing", "I'm doing well,", "I'm doing well, thank", "I'm doing well, thank you!"]
        assert accumulated_contents == expected_accumulations
    
    @pytest.mark.asyncio
    async def test_stream_response_empty_chunks(self, service, mock_llm_client, sample_chat_history, empty_chunks):
        """空のチャンクが適切にスキップされる"""
        # Given
        async def mock_stream_generator(chat_history):
            for chunk in empty_chunks:
                yield chunk
        
        mock_llm_client.complete_message_stream = mock_stream_generator
        
        # When & Then
        with pytest.raises(LLMServiceError, match="Empty response from LLM service"):
            chunks = []
            async for message_chunk in service.stream_response(sample_chat_history):
                chunks.append(message_chunk)
    
    @pytest.mark.asyncio
    async def test_stream_response_mixed_empty_and_content_chunks(self, service, mock_llm_client, sample_chat_history):
        """空チャンクとコンテンツチャンクが混在する場合"""
        # Given
        mixed_chunks = [
            {"choices": [{"delta": {}}]},  # 空
            {"choices": [{"delta": {"content": "Hello"}}]},  # コンテンツあり
            {"choices": [{"delta": {"content": ""}}]},  # 空のコンテンツ
            {"choices": [{"delta": {"content": " world"}}]},  # コンテンツあり
        ]
        
        async def mock_stream_generator(chat_history):
            for chunk in mixed_chunks:
                yield chunk
        
        mock_llm_client.complete_message_stream = mock_stream_generator
        
        # When
        streaming_messages = []
        final_message = None
        async for message_chunk in service.stream_response(sample_chat_history):
            if getattr(message_chunk, 'is_streaming', False):
                streaming_messages.append(message_chunk)
            else:
                final_message = message_chunk
        
        # Then
        assert len(streaming_messages) == 2  # 空でないチャンクのみ
        assert streaming_messages[0].content == "Hello"
        assert streaming_messages[1].content == "Hello world"
        assert final_message.content == "Hello world"
    
    @pytest.mark.asyncio
    async def test_stream_response_llm_client_error(self, service, mock_llm_client, sample_chat_history):
        """LLMクライアントエラーの適切な処理"""
        # Given
        async def failing_stream_generator(chat_history):
            raise Exception("Network connection failed")
            yield  # unreachable but required for async generator
        
        mock_llm_client.complete_message_stream = failing_stream_generator
        
        # When & Then
        with pytest.raises(LLMServiceError, match="Failed to stream chat: Network connection failed"):
            async for message_chunk in service.stream_response(sample_chat_history):
                pass

    # === 統合ストリーミングワークフローテスト ===
    
    @pytest.mark.asyncio
    async def test_stream_user_message_and_response_success(self, service, mock_llm_client, mock_message_processor, sample_chat_history, sample_streaming_chunks):
        """ユーザーメッセージ処理とストリーミング応答の統合"""
        # Given
        chat_uuid = "test-chat-uuid"
        user_content = "Hello, how are you?"
        
        # ストリーミング応答のモック
        async def mock_stream_generator(chat_history):
            for chunk in sample_streaming_chunks:
                yield chunk
        
        mock_llm_client.complete_message_stream = mock_stream_generator
        
        # メッセージプロセッサーのモック（最終メッセージ保存用）
        final_saved_message = MessageEntity(
            id=10, uuid="final-msg-uuid", role=Role.ASSISTANT, 
            content="I'm doing well, thank you!"
        )
        mock_message_processor.process_message.side_effect = [
            # ユーザーメッセージ保存の戻り値は不要（テストでは使わない）
            None,
            # アシスタントメッセージ保存の戻り値
            final_saved_message
        ]
        
        # When
        streaming_chunks = []
        final_chunk = None
        async for message_chunk in service.stream_user_message_and_response(chat_uuid, user_content, sample_chat_history):
            if getattr(message_chunk, 'is_streaming', False):
                streaming_chunks.append(message_chunk)
            else:
                final_chunk = message_chunk
        
        # Then
        # ユーザーメッセージが保存されたか確認
        user_message_call = mock_message_processor.process_message.call_args_list[0]
        assert user_message_call[0][1].role == Role.USER
        assert user_message_call[0][1].content == user_content
        
        # ストリーミングチャンクが正しく生成されたか確認
        assert len(streaming_chunks) == 5
        
        # 最終メッセージが保存され、返されたか確認
        assert final_chunk == final_saved_message
        
        # アシスタントメッセージが保存されたか確認
        assistant_message_call = mock_message_processor.process_message.call_args_list[1]
        assert assistant_message_call[0][1].role == Role.ASSISTANT
        assert assistant_message_call[0][1].content == "I'm doing well, thank you!"
    
    @pytest.mark.asyncio
    async def test_stream_user_message_and_response_empty_user_content(self, service):
        """空のユーザーメッセージコンテンツのエラーハンドリング"""
        # Given
        chat_uuid = "test-chat-uuid"
        empty_content = ""
        chat_history = []
        
        # When & Then
        with pytest.raises(ValueError, match="Message content cannot be empty"):
            async for _ in service.stream_user_message_and_response(chat_uuid, empty_content, chat_history):
                pass
    
    @pytest.mark.asyncio
    async def test_stream_user_message_and_response_whitespace_content(self, service):
        """空白文字のみのユーザーメッセージのエラーハンドリング"""
        # Given
        chat_uuid = "test-chat-uuid"
        whitespace_content = "   \n\t   "
        chat_history = []
        
        # When & Then
        with pytest.raises(ValueError, match="Message content cannot be empty"):
            async for _ in service.stream_user_message_and_response(chat_uuid, whitespace_content, chat_history):
                pass

    # === エッジケースとエラーハンドリングテスト ===
    
    @pytest.mark.asyncio
    async def test_stream_response_malformed_chunks(self, service, mock_llm_client, sample_chat_history):
        """不正な形式のチャンクの処理"""
        # Given
        malformed_chunks = [
            {"invalid": "structure"},
            {"choices": []},  # 空のchoices
            {"choices": [{}]},  # deltaなし
            {"choices": [{"delta": {"content": "Valid content"}}]}  # 正常
        ]
        
        async def mock_stream_generator(chat_history):
            for chunk in malformed_chunks:
                yield chunk
        
        mock_llm_client.complete_message_stream = mock_stream_generator
        
        # When
        chunks = []
        async for message_chunk in service.stream_response(sample_chat_history):
            chunks.append(message_chunk)
        
        # Then
        # 正常なチャンクのみ処理される
        assert len(chunks) == 2  # 1つのストリーミング + 1つの最終メッセージ
        assert chunks[0].content == "Valid content"
        assert chunks[1].content == "Valid content"
    
    @pytest.mark.asyncio
    async def test_stream_response_single_chunk(self, service, mock_llm_client, sample_chat_history):
        """単一チャンクでの正常動作"""
        # Given
        single_chunk = [{"choices": [{"delta": {"content": "Single response"}}]}]
        
        async def mock_stream_generator(chat_history):
            for chunk in single_chunk:
                yield chunk
        
        mock_llm_client.complete_message_stream = mock_stream_generator
        
        # When
        chunks = []
        async for message_chunk in service.stream_response(sample_chat_history):
            chunks.append(message_chunk)
        
        # Then
        assert len(chunks) == 2  # 1つのストリーミング + 1つの最終メッセージ
        assert chunks[0].content == "Single response"
        assert chunks[1].content == "Single response"
    
    @pytest.mark.asyncio
    async def test_stream_response_very_long_response(self, service, mock_llm_client, sample_chat_history):
        """非常に長いレスポンスの処理"""
        # Given
        long_chunks = []
        for i in range(100):
            long_chunks.append({"choices": [{"delta": {"content": f"Part{i} "}}]})
        
        async def mock_stream_generator(chat_history):
            for chunk in long_chunks:
                yield chunk
        
        mock_llm_client.complete_message_stream = mock_stream_generator
        
        # When
        chunks = []
        async for message_chunk in service.stream_response(sample_chat_history):
            chunks.append(message_chunk)
        
        # Then
        assert len(chunks) == 101  # 100のストリーミング + 1つの最終メッセージ
        final_content = chunks[-1].content
        assert "Part0" in final_content
        assert "Part99" in final_content
        assert len(final_content) > 500  # 長いコンテンツであることを確認