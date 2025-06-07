import pytest
import json
import asyncio
import sys
import os
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from fastapi import FastAPI
import httpx

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from src.infra.rest_api.main import app
from src.domain.entity.message_entity import MessageEntity, Role
from src.usecase.chat_interaction.main import ChatInteraction
from src.infra.openrouter_client import OpenRouterLLMService


class TestStreamingEndpoint:
    """Test for streaming message endpoint"""
    
    @pytest.fixture
    def client(self):
        return TestClient(app)
    
    @pytest.fixture
    def mock_chat_interaction(self):
        return AsyncMock(spec=ChatInteraction)
    
    @pytest.fixture
    def mock_dependencies(self, mock_chat_interaction):
        """Mock all dependencies for streaming endpoint"""
        patches = [
            patch('src.infra.rest_api.routers.chats.get_current_user', return_value="test_user_id"),
            patch('src.infra.rest_api.routers.chats.create_chat_repo_for_user'),
            patch('src.infra.rest_api.routers.chats.get_llm_client_dependency'),
            patch('src.infra.rest_api.routers.chats.get_message_cache_dependency'),
            patch('src.infra.rest_api.routers.chats.ChatInteraction', return_value=mock_chat_interaction)
        ]
        
        for p in patches:
            p.start()
        
        yield mock_chat_interaction
        
        for p in patches:
            p.stop()
    
    def test_streaming_endpoint_success(self, client, mock_dependencies):
        """Test successful streaming response"""
        # Setup mock streaming messages
        temp_message_1 = MessageEntity(
            id=0,
            uuid="",
            content="Hello",
            role=Role.ASSISTANT,
            is_streaming=True,
            temp_id="temp-123"
        )
        
        temp_message_2 = MessageEntity(
            id=0,
            uuid="",
            content="Hello world",
            role=Role.ASSISTANT,
            is_streaming=True,
            temp_id="temp-123"
        )
        
        final_message = MessageEntity(
            id=3,
            uuid="final-msg-uuid",
            content="Hello world!",
            role=Role.ASSISTANT,
            is_streaming=False
        )
        
        async def mock_stream():
            yield temp_message_1
            yield temp_message_2
            yield final_message
        
        mock_dependencies.continue_chat_stream.return_value = mock_stream()
        
        # Make streaming request
        response = client.post(
            "/api/v1/chats/test-chat-uuid/messages/stream",
            json={"content": "Test message"},
            headers={"Authorization": "Bearer test-token"}
        )
        
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/event-stream; charset=utf-8"
        
        # Parse SSE stream
        lines = response.text.strip().split('\n\n')
        
        # Check chunk data
        chunk_1 = json.loads(lines[0].replace('data: ', ''))
        assert chunk_1["type"] == "chunk"
        assert chunk_1["content"] == "Hello"
        assert chunk_1["temp_id"] == "temp-123"
        
        chunk_2 = json.loads(lines[1].replace('data: ', ''))
        assert chunk_2["type"] == "chunk"
        assert chunk_2["content"] == "Hello world"
        
        # Check final data
        final_chunk = json.loads(lines[2].replace('data: ', ''))
        assert final_chunk["type"] == "final"
        assert final_chunk["content"] == "Hello world!"
        assert "message_uuid" in final_chunk
        
        # Verify interaction calls
        mock_dependencies.restart_chat.assert_called_once_with("test-chat-uuid")
        mock_dependencies.continue_chat_stream.assert_called_once_with("Test message")
    
    def test_streaming_endpoint_with_parent_message(self, client, mock_dependencies):
        """Test streaming with parent message branching"""
        final_message = MessageEntity(
            id=4,
            uuid="branched-msg-uuid",
            content="Branched response",
            role=Role.ASSISTANT,
            is_streaming=False
        )
        
        async def mock_stream():
            yield final_message
        
        mock_dependencies.continue_chat_stream.return_value = mock_stream()
        
        response = client.post(
            "/api/v1/chats/test-chat-uuid/messages/stream",
            json={
                "content": "Test message",
                "parent_message_uuid": "parent-uuid"
            },
            headers={"Authorization": "Bearer test-token"}
        )
        
        assert response.status_code == 200
        mock_dependencies.select_message.assert_called_once_with("parent-uuid")
    
    def test_streaming_endpoint_chat_not_found(self, client, mock_dependencies):
        """Test streaming when chat is not found"""
        mock_dependencies.restart_chat.side_effect = Exception("Chat not found")
        
        response = client.post(
            "/api/v1/chats/nonexistent-chat/messages/stream",
            json={"content": "Test message"},
            headers={"Authorization": "Bearer test-token"}
        )
        
        assert response.status_code == 200  # Still returns 200 for SSE
        
        # Should contain error in stream
        lines = response.text.strip().split('\n\n')
        error_chunk = json.loads(lines[0].replace('data: ', ''))
        assert error_chunk["type"] == "error"
        assert "Chat not found" in error_chunk["message"]


class TestOpenRouterStreaming:
    """Test for OpenRouter streaming client"""
    
    @pytest.fixture
    def openrouter_client(self):
        return OpenRouterLLMService("test-model")
    
    @pytest.fixture
    def mock_messages(self):
        return [
            MessageEntity(id=1, uuid="user-msg-uuid", content="Hello", role=Role.USER),
            MessageEntity(id=2, uuid="assistant-msg-uuid", content="Hi there!", role=Role.ASSISTANT)
        ]
    
    @pytest.mark.asyncio
    async def test_complete_message_stream_success(self, openrouter_client, mock_messages):
        """Test successful streaming from OpenRouter"""
        # Mock SSE response chunks
        mock_chunks = [
            'data: {"choices":[{"delta":{"content":"Hello"}}]}\n\n',
            'data: {"choices":[{"delta":{"content":" world"}}]}\n\n',
            'data: {"choices":[{"delta":{"content":"!"}}]}\n\n',
            'data: [DONE]\n\n'
        ]
        
        mock_response = AsyncMock()
        async def mock_aiter_lines():
            for line in mock_chunks:
                yield line
        mock_response.aiter_lines = mock_aiter_lines
        mock_response.raise_for_status = MagicMock()
        
        # Mock the httpx client and async context manager
        mock_client = AsyncMock()
        mock_stream_context = AsyncMock()
        mock_stream_context.__aenter__ = AsyncMock(return_value=mock_response)
        mock_stream_context.__aexit__ = AsyncMock(return_value=None)
        mock_client.stream = MagicMock(return_value=mock_stream_context)
        
        # Set the client on openrouter_client
        openrouter_client._client = mock_client
        
        chunks = []
        async for chunk in openrouter_client.complete_message_stream(mock_messages):
            chunks.append(chunk)
        
        assert len(chunks) == 3
        assert chunks[0]["choices"][0]["delta"]["content"] == "Hello"
        assert chunks[1]["choices"][0]["delta"]["content"] == " world"
        assert chunks[2]["choices"][0]["delta"]["content"] == "!"
    
    @pytest.mark.asyncio
    async def test_complete_message_stream_json_error(self, openrouter_client, mock_messages):
        """Test handling of malformed JSON in stream"""
        mock_chunks = [
            'data: {"choices":[{"delta":{"content":"Hello"}}]}\n\n',
            'data: invalid-json\n\n',  # This should be skipped
            'data: {"choices":[{"delta":{"content":" world"}}]}\n\n',
            'data: [DONE]\n\n'
        ]
        
        mock_response = AsyncMock()
        async def mock_aiter_lines():
            for line in mock_chunks:
                yield line
        mock_response.aiter_lines = mock_aiter_lines
        mock_response.raise_for_status = MagicMock()
        
        # Mock the httpx client and async context manager
        mock_client = AsyncMock()
        mock_stream_context = AsyncMock()
        mock_stream_context.__aenter__ = AsyncMock(return_value=mock_response)
        mock_stream_context.__aexit__ = AsyncMock(return_value=None)
        mock_client.stream = MagicMock(return_value=mock_stream_context)
        
        # Set the client on openrouter_client
        openrouter_client._client = mock_client
        
        chunks = []
        async for chunk in openrouter_client.complete_message_stream(mock_messages):
            chunks.append(chunk)
        
        # Should only get valid chunks, invalid JSON skipped
        assert len(chunks) == 2
        assert chunks[0]["choices"][0]["delta"]["content"] == "Hello"
        assert chunks[1]["choices"][0]["delta"]["content"] == " world"


class TestChatInteractionStreaming:
    """Test for ChatInteraction streaming functionality"""
    
    @pytest.fixture
    def mock_chat_repo(self):
        return MagicMock()
    
    @pytest.fixture
    def mock_llm_client(self):
        return AsyncMock()
    
    @pytest.fixture
    def mock_cache(self):
        return MagicMock()
    
    @pytest.fixture
    def chat_interaction(self, mock_chat_repo, mock_llm_client, mock_cache):
        return ChatInteraction(mock_chat_repo, mock_llm_client, mock_cache)
    
    @pytest.mark.asyncio
    async def test_continue_chat_stream_success(self, chat_interaction, mock_llm_client):
        """Test successful chat streaming"""
        # Mock LLM streaming response
        mock_chunks = [
            {"choices": [{"delta": {"content": "Hello"}}]},
            {"choices": [{"delta": {"content": " there"}}]},
            {"choices": [{"delta": {"content": "!"}}]}
        ]
        
        async def mock_stream(messages):
            for chunk in mock_chunks:
                yield chunk
        
        mock_llm_client.complete_message_stream = mock_stream
        
        # Mock other methods
        final_message_mock = MessageEntity(
            id=5,
            uuid="final-msg-uuid",
            content="Hello there!",
            role=Role.ASSISTANT,
            is_streaming=False
        )
        chat_interaction._process_message = MagicMock(return_value=final_message_mock)
        chat_interaction._get_chat_history = MagicMock(return_value=[])
        
        # Execute streaming
        messages = []
        async for message in chat_interaction.continue_chat_stream("Test input"):
            messages.append(message)
        
        # Should get 3 streaming messages + 1 final
        assert len(messages) == 4
        
        # Check streaming messages
        assert messages[0].content == "Hello"
        assert messages[0].is_streaming == True
        assert messages[1].content == "Hello there"
        assert messages[1].is_streaming == True
        assert messages[2].content == "Hello there!"
        assert messages[2].is_streaming == True
        
        # Check final message
        assert messages[3].is_streaming == False
        
        # Verify user message was processed
        chat_interaction._process_message.assert_called()
    
    @pytest.mark.asyncio
    async def test_continue_chat_stream_empty_message(self, chat_interaction):
        """Test streaming with empty message raises error"""
        with pytest.raises(ValueError, match="Message content cannot be empty"):
            async for _ in chat_interaction.continue_chat_stream(""):
                pass
    
    @pytest.mark.asyncio
    async def test_continue_chat_stream_llm_error(self, chat_interaction, mock_llm_client):
        """Test streaming when LLM fails"""
        mock_llm_client.complete_message_stream.side_effect = Exception("LLM failed")
        
        chat_interaction._process_message = MagicMock()
        chat_interaction._get_chat_history = MagicMock(return_value=[])
        
        with pytest.raises(Exception, match="Failed to stream chat"):
            async for _ in chat_interaction.continue_chat_stream("Test input"):
                pass