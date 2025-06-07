import pytest
from uuid import uuid4
from fastapi.testclient import TestClient


class TestSessionRecovery:
    @pytest.fixture
    def client(self, monkeypatch):
        from src.infra.rest_api.main import app
        
        # Mock authentication function
        def mock_get_current_user():
            return "test-user-uuid"
        
        # Mock chat repo function
        class MockChatRepo:
            def __init__(self):
                self.last_positions = {}
                self.chat_structures = {}
            
            def update_last_position(self, chat_uuid: str, user_uuid: str, node_id: str):
                self.last_positions[f"{chat_uuid}:{user_uuid}"] = node_id
            
            def get_last_position(self, chat_uuid: str, user_uuid: str):
                return self.last_positions.get(f"{chat_uuid}:{user_uuid}")
        
        mock_repo = MockChatRepo()
        
        def mock_get_chat_repo():
            return mock_repo
        
        # Override dependencies
        app.dependency_overrides = {
            app.router.routes[0].endpoint.__code__.co_varnames[0]: mock_get_current_user
        }
        
        from src.infra.auth import get_current_user
        from src.infra.di import get_chat_repo_client
        
        app.dependency_overrides[get_current_user] = mock_get_current_user
        app.dependency_overrides[get_chat_repo_client] = mock_get_chat_repo
        
        self.mock_repo = mock_repo
        
        return TestClient(app)
    
    @pytest.fixture
    def auth_headers(self, monkeypatch):
        """Mock authentication headers"""
        def mock_get_current_user(token=None):
            return "test-user-uuid"
        
        # Mock all auth-related imports
        monkeypatch.setattr("src.infra.auth.get_current_user", mock_get_current_user)
        monkeypatch.setattr("src.infra.rest_api.routers.chats.get_current_user", mock_get_current_user)
        return {"Authorization": "Bearer test-token"}
    
    @pytest.fixture
    def mock_chat_repo(self, monkeypatch):
        """Mock chat repository for testing"""
        class MockChatRepo:
            def __init__(self):
                self.last_positions = {}
                self.chat_structures = {}
            
            def update_last_position(self, chat_uuid: str, user_uuid: str, node_id: str):
                self.last_positions[f"{chat_uuid}:{user_uuid}"] = node_id
            
            def get_last_position(self, chat_uuid: str, user_uuid: str):
                return self.last_positions.get(f"{chat_uuid}:{user_uuid}")
            
            def load_structure(self, chat_uuid: str):
                from src.domain.entity.chat_tree import DiscussionTree
                tree = DiscussionTree()
                tree.uuid = chat_uuid
                return tree
        
        mock_repo = MockChatRepo()
        monkeypatch.setattr("src.infra.di.get_chat_repo_client", lambda: mock_repo)
        monkeypatch.setattr("src.infra.rest_api.routers.chats.get_chat_repo_client", lambda: mock_repo)
        return mock_repo
    
    def test_get_last_position(self, client, auth_headers, mock_chat_repo):
        # Arrange
        chat_uuid = str(uuid4())
        node_id = "test-node-123"
        mock_chat_repo.update_last_position(chat_uuid, "test-user-uuid", node_id)
        
        # Act
        response = client.get(
            f"/api/v1/chats/{chat_uuid}/last-position",
            headers=auth_headers
        )
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["node_id"] == node_id
        assert data["chat_uuid"] == chat_uuid
    
    def test_get_last_position_not_found(self, client, auth_headers, mock_chat_repo):
        # Arrange
        chat_uuid = str(uuid4())
        
        # Act
        response = client.get(
            f"/api/v1/chats/{chat_uuid}/last-position",
            headers=auth_headers
        )
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["node_id"] is None
        assert data["chat_uuid"] == chat_uuid
    
    def test_update_last_position_on_message(self, client, auth_headers, mock_chat_repo, monkeypatch):
        # Mock chat interaction
        class MockChatInteraction:
            def add_message(self, chat_uuid, message_content, user_id):
                return {
                    "role": "user",
                    "content": message_content,
                    "uuid": "msg-123",
                    "children": ["assistant-msg-123"]
                }, {
                    "role": "assistant",
                    "content": "Test response",
                    "uuid": "assistant-msg-123"
                }
        
        monkeypatch.setattr("src.infra.rest_api.dependencies.get_chat_interaction", 
                          lambda *args: MockChatInteraction())
        
        # Arrange
        chat_uuid = str(uuid4())
        
        # Act
        response = client.post(
            f"/api/v1/chats/{chat_uuid}/messages",
            json={"content": "Test message"},
            headers=auth_headers
        )
        
        # Assert
        assert response.status_code == 200
        # Check that last position was updated
        last_pos = mock_chat_repo.get_last_position(chat_uuid, "test-user-uuid")
        assert last_pos == "assistant-msg-123"