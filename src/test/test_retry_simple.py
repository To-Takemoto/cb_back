import pytest
from fastapi.testclient import TestClient
from uuid import uuid4


def test_retry_endpoint_exists():
    """リトライエンドポイントが存在することを確認"""
    from src.infra.rest_api.main import app
    
    def mock_get_current_user():
        return "test-user-uuid"
    
    class MockChatInteraction:
        def restart_chat(self, uuid):
            pass
        def select_message(self, message_id):
            pass
        async def retry_last_message(self):
            class MockMessage:
                def __init__(self):
                    self.uuid = "retried-msg-123"
                    self.content = "Retried response"
            return MockMessage()
    
    class MockChatRepo:
        pass
    
    def mock_get_chat_interaction():
        return MockChatInteraction()
    
    def mock_get_chat_repo():
        return MockChatRepo()
    
    from src.infra.auth import get_current_user
    from src.infra.rest_api.dependencies import get_chat_interaction
    from src.infra.di import get_chat_repo_client
    
    app.dependency_overrides[get_current_user] = mock_get_current_user
    app.dependency_overrides[get_chat_interaction] = mock_get_chat_interaction
    app.dependency_overrides[get_chat_repo_client] = mock_get_chat_repo
    
    client = TestClient(app)
    
    chat_uuid = str(uuid4())
    message_id = "test-msg-123"
    
    response = client.post(f"/api/v1/chats/{chat_uuid}/messages/{message_id}/retry")
    
    assert response.status_code == 200
    data = response.json()
    assert data["message_uuid"] == "retried-msg-123"
    assert data["content"] == "Retried response"
    
    app.dependency_overrides.clear()


def test_error_handlers_registered():
    """エラーハンドラーが登録されていることを確認"""
    from src.infra.rest_api.main import app
    import asyncio
    
    # Check that exception handlers are registered
    assert asyncio.TimeoutError in app.exception_handlers
    assert ConnectionError in app.exception_handlers
    assert ValueError in app.exception_handlers
    assert PermissionError in app.exception_handlers
    assert Exception in app.exception_handlers


def test_error_response_format():
    """エラーレスポンス形式が統一されていることを確認"""
    from src.infra.rest_api.error_handlers import create_error_response
    
    response = create_error_response(
        error_type="test_error",
        user_message="Test error message",
        status_code=400,
        retry_available=True
    )
    
    content = response.body.decode()
    import json
    data = json.loads(content)
    
    assert data["error_type"] == "test_error"
    assert data["user_message"] == "Test error message"
    assert data["retry_available"] is True
    assert response.status_code == 400


if __name__ == "__main__":
    test_retry_endpoint_exists()
    test_error_handlers_registered()
    test_error_response_format()
    print("✅ All retry and error handling tests passed!")