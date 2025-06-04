import pytest
from uuid import uuid4
from datetime import datetime, timedelta
from fastapi.testclient import TestClient


class TestNavigation:
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
    
    @pytest.fixture
    def mock_chat_repo(self, monkeypatch):
        """Mock chat repository"""
        class MockChatRepo:
            def __init__(self):
                self.chats = [
                    {
                        "uuid": str(uuid4()),
                        "title": "Chat about Python",
                        "created_at": datetime.now() - timedelta(days=1),
                        "updated_at": datetime.now() - timedelta(hours=2),
                        "message_count": 5
                    },
                    {
                        "uuid": str(uuid4()),
                        "title": "Chat about AI",
                        "created_at": datetime.now() - timedelta(days=2),
                        "updated_at": datetime.now() - timedelta(hours=12),
                        "message_count": 10
                    }
                ]
            
            def get_recent_chats(self, user_uuid: str, limit: int = 10):
                return self.chats[:limit]
            
            def delete_chat(self, chat_uuid: str, user_uuid: str):
                self.chats = [c for c in self.chats if c["uuid"] != chat_uuid]
                return True
            
            def get_chat_title(self, chat_uuid: str):
                for chat in self.chats:
                    if chat["uuid"] == chat_uuid:
                        return chat["title"]
                return None
        
        mock_repo = MockChatRepo()
        monkeypatch.setattr("src.infra.di.get_chat_repo_client", lambda: mock_repo)
        return mock_repo
    
    def test_get_recent_chats(self, client, auth_headers, mock_chat_repo):
        # Act
        response = client.get(
            "/api/v1/chats/recent",
            headers=auth_headers
        )
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data["chats"]) == 2
        assert data["chats"][0]["title"] == "Chat about Python"
        assert "uuid" in data["chats"][0]
        assert "created_at" in data["chats"][0]
        assert "message_count" in data["chats"][0]
    
    def test_get_recent_chats_with_limit(self, client, auth_headers, mock_chat_repo):
        # Act
        response = client.get(
            "/api/v1/chats/recent?limit=1",
            headers=auth_headers
        )
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data["chats"]) == 1
    
    def test_delete_chat(self, client, auth_headers, mock_chat_repo):
        # Arrange
        chat_uuid = mock_chat_repo.chats[0]["uuid"]
        
        # Act
        response = client.delete(
            f"/api/v1/chats/{chat_uuid}",
            headers=auth_headers
        )
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["detail"] == f"Chat {chat_uuid} deleted successfully"
        assert len(mock_chat_repo.chats) == 1
    
    def test_delete_nonexistent_chat(self, client, auth_headers, mock_chat_repo):
        # Arrange
        fake_uuid = str(uuid4())
        
        # Act
        response = client.delete(
            f"/api/v1/chats/{fake_uuid}",
            headers=auth_headers
        )
        
        # Assert
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()
    
    def test_get_current_node(self, client, auth_headers, monkeypatch):
        # Mock chat interaction
        chat_uuid = str(uuid4())
        
        class MockChatInteraction:
            def restart_chat(self, uuid):
                pass
            
            @property
            def structure(self):
                class MockStructure:
                    def get_current_node_id(self):
                        return "current-node-123"
                return MockStructure()
        
        monkeypatch.setattr("src.infra.rest_api.dependencies.get_chat_interaction",
                          lambda *args: MockChatInteraction())
        
        # Act
        response = client.get(
            f"/api/v1/chats/{chat_uuid}/current-node",
            headers=auth_headers
        )
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["node_id"] == "current-node-123"
        assert data["chat_uuid"] == chat_uuid