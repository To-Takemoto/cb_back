import pytest
from uuid import uuid4
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch
import asyncio


class TestRetryAndErrorHandling:
    @pytest.fixture
    def client(self):
        from src.infra.rest_api.main import app
        return TestClient(app)
    
    @pytest.fixture
    def auth_headers(self, monkeypatch):
        """Mock authentication headers"""
        def mock_get_current_user(token):
            return "test-user-uuid"
        
        monkeypatch.setattr("src.infra.auth.get_current_user", mock_get_current_user)
        return {"Authorization": "Bearer test-token"}
    
    def test_retry_message_endpoint(self, client, auth_headers, monkeypatch):
        # Mock dependencies
        chat_uuid = str(uuid4())
        message_id = "test-message-123"
        
        class MockChatInteraction:
            def restart_chat(self, uuid):
                pass
            
            async def retry_message(self, message_id):
                return Mock(uuid="new-msg-123", content="Retried response")
        
        monkeypatch.setattr("src.infra.rest_api.dependencies.get_chat_interaction",
                          lambda *args: MockChatInteraction())
        
        # Act
        response = client.post(
            f"/api/v1/chats/{chat_uuid}/messages/{message_id}/retry",
            headers=auth_headers
        )
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["message_uuid"] == "new-msg-123"
        assert data["content"] == "Retried response"
    
    def test_retry_with_timeout_handling(self, client, auth_headers, monkeypatch):
        # Mock with timeout error
        chat_uuid = str(uuid4())
        message_id = "test-message-123"
        
        class MockChatInteraction:
            def restart_chat(self, uuid):
                pass
            
            async def retry_message(self, message_id):
                raise asyncio.TimeoutError("LLM API timeout")
        
        monkeypatch.setattr("src.infra.rest_api.dependencies.get_chat_interaction",
                          lambda *args: MockChatInteraction())
        
        # Act
        response = client.post(
            f"/api/v1/chats/{chat_uuid}/messages/{message_id}/retry",
            headers=auth_headers
        )
        
        # Assert
        assert response.status_code == 504
        data = response.json()
        assert "timeout" in data["detail"].lower()
        assert data["error_type"] == "timeout"
        assert data["retry_available"] is True
    
    def test_user_friendly_error_messages(self, client, auth_headers, monkeypatch):
        # Test various error scenarios
        scenarios = [
            (ConnectionError("Network error"), 503, "connection_error", 
             "接続エラーが発生しました。しばらく待ってから再試行してください。"),
            (ValueError("Invalid input"), 400, "validation_error",
             "入力内容に問題があります。内容を確認してください。"),
            (PermissionError("Access denied"), 403, "permission_error",
             "このリソースへのアクセス権限がありません。"),
            (Exception("Unknown error"), 500, "internal_error",
             "予期しないエラーが発生しました。問題が続く場合はサポートにお問い合わせください。")
        ]
        
        for error, status_code, error_type, expected_message in scenarios:
            class MockChatInteraction:
                def restart_chat(self, uuid):
                    raise error
            
            monkeypatch.setattr("src.infra.rest_api.dependencies.get_chat_interaction",
                              lambda *args: MockChatInteraction())
            
            response = client.post(
                f"/api/v1/chats/{str(uuid4())}/messages",
                json={"content": "test"},
                headers=auth_headers
            )
            
            assert response.status_code == status_code
            data = response.json()
            assert data["error_type"] == error_type
            assert data["user_message"] == expected_message
    
    def test_partial_response_recovery(self, client, auth_headers, monkeypatch):
        # Mock streaming response that fails halfway
        chat_uuid = str(uuid4())
        
        class MockChatInteraction:
            def restart_chat(self, uuid):
                pass
            
            async def continue_chat_streaming(self, content):
                yield {"content": "This is ", "done": False}
                yield {"content": "a partial ", "done": False}
                raise ConnectionError("Connection lost")
        
        monkeypatch.setattr("src.infra.rest_api.dependencies.get_chat_interaction",
                          lambda *args: MockChatInteraction())
        
        # Act
        response = client.post(
            f"/api/v1/chats/{chat_uuid}/messages/stream",
            json={"content": "test", "stream": True},
            headers=auth_headers
        )
        
        # Assert
        assert response.status_code == 206  # Partial content
        data = response.json()
        assert data["partial_content"] == "This is a partial "
        assert data["error_occurred"] is True
        assert data["can_resume"] is True