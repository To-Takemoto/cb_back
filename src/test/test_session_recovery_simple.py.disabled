import pytest
from uuid import uuid4
from fastapi.testclient import TestClient


def test_get_last_position_endpoint_exists():
    """最後の位置取得エンドポイントが存在することを確認"""
    from src.infra.rest_api.main import app
    
    # Override dependencies to avoid authentication
    def mock_get_current_user():
        return "test-user-uuid"
    
    class MockChatRepo:
        def get_last_position(self, chat_uuid: str, user_uuid: str):
            return "test-node-123"
    
    def mock_get_chat_repo():
        return MockChatRepo()
    
    from src.infra.auth import get_current_user
    from src.infra.di import get_chat_repo_client
    
    app.dependency_overrides[get_current_user] = mock_get_current_user
    app.dependency_overrides[get_chat_repo_client] = mock_get_chat_repo
    
    client = TestClient(app)
    
    # Test the endpoint
    chat_uuid = str(uuid4())
    response = client.get(f"/api/v1/chats/{chat_uuid}/last-position")
    
    assert response.status_code == 200
    data = response.json()
    assert data["chat_uuid"] == chat_uuid
    assert data["node_id"] == "test-node-123"
    
    # Clean up
    app.dependency_overrides.clear()


def test_session_recovery_repo_methods():
    """ChatRepoのセッション復帰メソッドが実装されていることを確認"""
    from src.infra.sqlite_client.chat_repo import ChatRepo
    
    # Check methods exist
    assert hasattr(ChatRepo, 'update_last_position')
    assert hasattr(ChatRepo, 'get_last_position')
    
    # Check method signatures
    import inspect
    update_sig = inspect.signature(ChatRepo.update_last_position)
    get_sig = inspect.signature(ChatRepo.get_last_position)
    
    assert 'chat_uuid' in update_sig.parameters
    assert 'user_uuid' in update_sig.parameters
    assert 'node_id' in update_sig.parameters
    
    assert 'chat_uuid' in get_sig.parameters
    assert 'user_uuid' in get_sig.parameters


def test_database_model_exists():
    """UserChatPositionモデルが存在することを確認"""
    from src.infra.sqlite_client.peewee_models import UserChatPosition
    
    # Check model exists
    assert UserChatPosition is not None
    
    # Check fields exist
    assert hasattr(UserChatPosition, 'user')
    assert hasattr(UserChatPosition, 'discussion')
    assert hasattr(UserChatPosition, 'last_node_id')
    assert hasattr(UserChatPosition, 'updated_at')


if __name__ == "__main__":
    test_get_last_position_endpoint_exists()
    test_session_recovery_repo_methods()
    test_database_model_exists()
    print("✅ All session recovery tests passed!")