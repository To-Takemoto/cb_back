"""
API統合テスト - データベース初期化の問題を検証・修正
"""
import pytest
from fastapi.testclient import TestClient
import tempfile
import os
from src.infra.sqlite_client.peewee_models import db_proxy, User, DiscussionStructure, Message
from peewee import SqliteDatabase
from src.infra.auth import create_access_token


@pytest.fixture(scope="function")
def test_db():
    """テスト用データベースを作成"""
    with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as f:
        test_db_path = f.name
    
    # テスト用データベースを初期化
    db = SqliteDatabase(test_db_path)
    db_proxy.initialize(db)
    
    # テーブルを作成
    with db:
        db.create_tables([User, DiscussionStructure, Message])
        
        # テストユーザーを作成（パスワードは"password"）
        user = User.create(
            uuid="test-user-uuid",
            name="testuser",
            password="password"  # User.save()が自動的にハッシュ化する
        )
    
    yield db
    
    # クリーンアップ
    db.close()
    os.unlink(test_db_path)


@pytest.fixture
def client(test_db):
    """テストクライアントを作成"""
    from src.infra.rest_api.main import app
    
    # スタートアップイベントを無効化してテスト用データベースを使用
    app.router.on_startup.clear()
    
    # テスト用にデータベースプロキシをオーバーライド
    db_proxy.initialize(test_db)
    
    with TestClient(app) as client:
        yield client


@pytest.fixture
def auth_token():
    """認証トークンを生成"""
    return create_access_token(data={"sub": "test-user-uuid"})


def test_user_created(test_db):
    """テストユーザーが正しく作成されているかテスト"""
    users = User.select()
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
    

def test_user_repository_integration(client):
    """ユーザーリポジトリとの統合テスト"""
    from src.infra.di import get_user_repository
    user_repo = get_user_repository()
    user = user_repo.get_user_by_name("testuser")
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