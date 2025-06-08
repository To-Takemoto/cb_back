import pytest
from fastapi.testclient import TestClient
from uuid import uuid4


def test_search_endpoints_exist():
    """検索エンドポイントが存在することを確認"""
    from src.infra.rest_api.main import app
    
    def mock_get_current_user():
        return "test-user-uuid"
    
    class MockChatRepo:
        def search_messages(self, chat_uuid: str, query: str):
            return [
                {
                    "uuid": str(uuid4()),
                    "content": "This is a Python tutorial",
                    "role": "user",
                    "created_at": "2024-01-01T00:00:00",
                    "highlight": "This is a <mark>Python</mark> tutorial"
                }
            ]
        
        def get_chats_by_date(self, user_uuid: str, date_filter: str):
            return [
                {
                    "chat_uuid": str(uuid4()),
                    "created_at": "2024-01-01T00:00:00",
                    "last_message": "Today's chat"
                }
            ]
        
        def get_recent_chats(self, user_uuid: str, limit: int = 10):
            return [
                {
                    "uuid": str(uuid4()),
                    "title": "Recent Chat",
                    "created_at": "2024-01-01T00:00:00",
                    "message_count": 3
                }
            ]
    
    def mock_get_chat_repo():
        return MockChatRepo()
    
    from src.infra.auth import get_current_user
    from src.infra.di import get_chat_repo_client
    
    app.dependency_overrides[get_current_user] = mock_get_current_user
    app.dependency_overrides[get_chat_repo_client] = mock_get_chat_repo
    
    client = TestClient(app)
    
    # Test search messages
    chat_uuid = str(uuid4())
    response = client.get(f"/api/v1/chats/{chat_uuid}/search?q=Python")
    assert response.status_code == 200
    data = response.json()
    assert "results" in data
    assert len(data["results"]) == 1
    assert "Python" in data["results"][0]["content"]
    assert "<mark>Python</mark>" in data["results"][0]["highlight"]
    
    # Test search with short query (should fail)
    response = client.get(f"/api/v1/chats/{chat_uuid}/search?q=a")
    assert response.status_code == 400
    
    # Test date filter
    response = client.get("/api/v1/chats?date=today")
    assert response.status_code == 200
    data = response.json()
    assert "chats" in data
    assert data["filter"] == "today"
    
    # Test invalid date filter
    response = client.get("/api/v1/chats?date=invalid")
    assert response.status_code == 400
    
    # Test default chat list (no date filter)
    response = client.get("/api/v1/chats")
    assert response.status_code == 200
    data = response.json()
    assert "chats" in data
    
    app.dependency_overrides.clear()


def test_search_repo_methods():
    """検索用のリポジトリメソッドが実装されていることを確認"""
    from src.infra.tortoise_client.chat_repo import TortoiseChatRepository as ChatRepo
    
    # Check methods exist
    assert hasattr(ChatRepo, 'search_messages')
    assert hasattr(ChatRepo, 'get_chats_by_date')
    
    # Check method signatures
    import inspect
    search_sig = inspect.signature(ChatRepo.search_messages)
    date_sig = inspect.signature(ChatRepo.get_chats_by_date)
    
    assert 'chat_uuid' in search_sig.parameters
    assert 'query' in search_sig.parameters
    
    assert 'user_uuid' in date_sig.parameters
    assert 'date_filter' in date_sig.parameters


if __name__ == "__main__":
    test_search_endpoints_exist()
    test_search_repo_methods()
    print("✅ All search and filter tests passed!")