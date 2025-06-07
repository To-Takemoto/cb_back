"""
API統合テスト - データベース初期化の問題を検証・修正
"""
import pytest
from fastapi.testclient import TestClient
import tempfile
import os
from tortoise import Tortoise
from src.infra.tortoise_client.models import User, DiscussionStructure, Message
from src.infra.auth import create_access_token


@pytest.fixture(scope="function")
async def test_db():
    """テスト用データベースを作成"""
    from src.infra.tortoise_client.config import TORTOISE_ORM
    
    # テスト用のインメモリデータベース設定
    test_config = {
        "connections": {"default": "sqlite://:memory:"},
        "apps": TORTOISE_ORM["apps"]
    }
    
    await Tortoise.init(config=test_config)
    await Tortoise.generate_schemas()
    
    # テストユーザーを作成（パスワードは"password"）
    from src.infra.auth import get_password_hash
    user = await User.create(
        uuid="test-user-uuid",
        name="testuser",
        password=get_password_hash("password")
    )
    
    yield
    
    # クリーンアップ
    await Tortoise.close_connections()


@pytest.fixture
def client(test_db):
    """テストクライアントを作成"""
    from src.infra.rest_api.main import app
    
    with TestClient(app) as client:
        yield client


@pytest.fixture
def auth_token():
    """認証トークンを生成"""
    return create_access_token(data={"sub": "test-user-uuid"})


@pytest.mark.asyncio
async def test_user_created(test_db):
    """テストユーザーが正しく作成されているかテスト"""
    users = await User.all()
    assert len(users) == 1
    user = users[0]
    assert user.name == "testuser"
    assert user.uuid == "test-user-uuid"
    assert user.password  # パスワードがハッシュ化されていることを確認


def test_health_check(client):
    """ヘルスチェックエンドポイントのテスト"""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy", "version": "0.1.0"}


def test_create_chat_unauthorized(client):
    """認証なしでのチャット作成テスト"""
    response = client.post("/api/v1/chats/", json={"initial_message": "Hello"})
    assert response.status_code == 401


def test_create_chat_authorized(client, auth_token):
    """認証ありでのチャット作成テスト"""
    headers = {"Authorization": f"Bearer {auth_token}"}
    response = client.post("/api/v1/chats/", json={"initial_message": "Hello"}, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert "chat_uuid" in data
    

@pytest.mark.asyncio
async def test_user_repository_integration(client):
    """ユーザーリポジトリとの統合テスト"""
    from src.infra.di import get_user_repository
    user_repo = get_user_repository()
    user = await user_repo.get_user_by_name("testuser")
    assert user is not None
    assert user.name == "testuser"
    assert user.uuid == "test-user-uuid"


def test_auth_login(client):
    """ログインエンドポイントのテスト"""
    response = client.post("/api/v1/auth/login", data={
        "username": "testuser",
        "password": "password"
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_auth_me(client, auth_token):
    """ユーザー情報取得エンドポイントのテスト"""
    headers = {"Authorization": f"Bearer {auth_token}"}
    response = client.get("/api/v1/auth/me", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["uuid"] == "test-user-uuid"
    assert data["username"] == "testuser"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])