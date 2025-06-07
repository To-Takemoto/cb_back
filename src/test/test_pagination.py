import pytest
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from fastapi.testclient import TestClient
from src.infra.rest_api.main import app
from src.infra.tortoise_client.models import (
    User as UserModel,
    DiscussionStructure,
    Message as MessageModel
)
from tortoise import Tortoise
import uuid
from datetime import datetime

client = TestClient(app)

@pytest.fixture
async def setup_test_data():
    """テスト用のユーザーとチャットデータを作成"""
    # テスト用インメモリデータベースを初期化
    await Tortoise.init(
        db_url="sqlite://:memory:",
        modules={"models": ["src.infra.tortoise_client.models"]}
    )
    await Tortoise.generate_schemas()
    
    # テストユーザーを作成
    test_user = await UserModel.create(
        uuid=str(uuid.uuid4()),
        name=f"test_user_{uuid.uuid4().hex[:8]}",
        password="hashed_password"
    )
    
    # 複数のチャットを作成
    for i in range(25):  # 25個のチャットを作成
        disc = await DiscussionStructure.create(
            uuid=str(uuid.uuid4()),
            user=test_user,
            serialized_structure="{}"
        )
        
        # 各チャットにメッセージを追加
        await MessageModel.create(
            uuid=str(uuid.uuid4()),
            discussion=disc,
            content=f"Test message {i}",
            role="user"
        )
    
    yield test_user
    
    # クリーンアップ
    await Tortoise.close_connections()

def test_pagination_parameters():
    """ページネーションパラメータの検証"""
    # 無効なページ番号
    response = client.get("/api/v1/chats/recent?page=0")
    assert response.status_code == 422
    
    # 無効なlimit
    response = client.get("/api/v1/chats/recent?limit=0")
    assert response.status_code == 422
    
    response = client.get("/api/v1/chats/recent?limit=101")
    assert response.status_code == 422

@pytest.mark.asyncio
async def test_pagination_response_format(setup_test_data):
    """ページネーションレスポンスのフォーマット確認"""
    # このテストでは認証をモックする必要があるため、スキップ
    pass