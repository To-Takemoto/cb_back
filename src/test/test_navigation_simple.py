import pytest
from fastapi.testclient import TestClient
from uuid import uuid4


def test_navigation_endpoints_exist():
    """ナビゲーションエンドポイントが存在することを確認"""
    from src.infra.rest_api.main import app
    
    def mock_get_current_user():
        return "test-user-uuid"
    
    class MockChatRepo:
        def get_recent_chats(self, user_uuid: str, limit: int = 10):
            return [
                {
                    "uuid": str(uuid4()),
                    "title": "Test Chat",
                    "created_at": "2024-01-01T00:00:00",
                    "message_count": 5
                }
            ]
        
        def delete_chat(self, chat_uuid: str, user_uuid: str):
            return True
    
    def mock_get_chat_repo():
        return MockChatRepo()
    
    from src.infra.auth import get_current_user
    from src.infra.di import get_chat_repo_client
    
    app.dependency_overrides[get_current_user] = mock_get_current_user
    app.dependency_overrides[get_chat_repo_client] = mock_get_chat_repo
    
    client = TestClient(app)
    
    # Test recent chats endpoint
    response = client.get("/api/v1/chats/recent")
    assert response.status_code == 200
    data = response.json()
    assert "chats" in data
    assert len(data["chats"]) == 1
    assert data["chats"][0]["title"] == "Test Chat"
    
    # Test delete chat endpoint
    test_uuid = str(uuid4())
    response = client.delete(f"/api/v1/chats/{test_uuid}")
    assert response.status_code == 200
    data = response.json()
    assert f"Chat {test_uuid} deleted successfully" in data["detail"]
    
    app.dependency_overrides.clear()


def test_current_node_endpoint_exists():
    """現在ノード取得エンドポイントが存在することを確認"""
    from src.infra.rest_api.main import app
    
    class MockChatInteraction:
        def restart_chat(self, uuid):
            pass
        
        @property
        def structure(self):
            class MockStructure:
                def get_current_node_id(self):
                    return "current-node-123"
            return MockStructure()
    
    def mock_get_chat_interaction():
        return MockChatInteraction()
    
    from src.infra.rest_api.dependencies import get_chat_interaction
    
    app.dependency_overrides[get_chat_interaction] = mock_get_chat_interaction
    
    client = TestClient(app)
    
    chat_uuid = str(uuid4())
    response = client.get(f"/api/v1/chats/{chat_uuid}/current-node")
    
    assert response.status_code == 200
    data = response.json()
    assert data["chat_uuid"] == chat_uuid
    assert data["node_id"] == "current-node-123"
    
    app.dependency_overrides.clear()


def test_navigation_repo_methods():
    """ナビゲーション用のリポジトリメソッドが実装されていることを確認"""
    from src.infra.sqlite_client.chat_repo import ChatRepo
    
    # Check methods exist
    assert hasattr(ChatRepo, 'get_recent_chats')
    assert hasattr(ChatRepo, 'delete_chat')
    
    # Check method signatures
    import inspect
    recent_sig = inspect.signature(ChatRepo.get_recent_chats)
    delete_sig = inspect.signature(ChatRepo.delete_chat)
    
    assert 'user_uuid' in recent_sig.parameters
    assert 'limit' in recent_sig.parameters
    
    assert 'chat_uuid' in delete_sig.parameters
    assert 'user_uuid' in delete_sig.parameters


if __name__ == "__main__":
    test_navigation_endpoints_exist()
    test_current_node_endpoint_exists()
    test_navigation_repo_methods()
    print("✅ All navigation tests passed!")