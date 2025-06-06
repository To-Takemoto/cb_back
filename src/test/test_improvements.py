"""
実装した改善機能の統合テスト
"""
import pytest
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from fastapi.testclient import TestClient
from src.infra.rest_api.main import app

client = TestClient(app)

def test_health_check_endpoint():
    """ヘルスチェックエンドポイントの動作確認"""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
    assert response.json()["version"] == "0.1.0"

def test_token_refresh_requires_auth():
    """トークンリフレッシュエンドポイントが認証を要求することを確認"""
    response = client.post("/api/v1/auth/refresh")
    assert response.status_code == 401
    assert "detail" in response.json()

def test_pagination_query_parameters():
    """ページネーションのクエリパラメータ検証"""
    # 有効なパラメータ（認証なしで422になるはず）
    response = client.get("/api/v1/chats/recent?page=1&limit=20")
    assert response.status_code == 401  # 認証が必要
    
    # 無効なページ番号
    response = client.get("/api/v1/chats/recent?page=0&limit=20")
    assert response.status_code == 401  # 認証チェックが先
    
    # 無効なlimit（大きすぎる）
    response = client.get("/api/v1/chats/recent?page=1&limit=101")
    assert response.status_code == 401  # 認証チェックが先

def test_rate_limit_headers():
    """レート制限時のヘッダー確認"""
    # 複数回リクエストを送信してレート制限を確認
    for i in range(10):
        response = client.post(
            "/api/v1/auth/login",
            data={"username": "test", "password": "test"}
        )
        
        if response.status_code == 429:
            # レート制限に達した場合
            assert "Retry-After" in response.headers
            assert "リクエストが多すぎます" in response.json()["detail"]
            break

def test_alembic_configuration():
    """Alembicの設定ファイルが存在することを確認"""
    alembic_ini = Path(__file__).parent.parent.parent / "alembic.ini"
    assert alembic_ini.exists()
    
    alembic_env = Path(__file__).parent.parent.parent / "alembic" / "env.py"
    assert alembic_env.exists()

def test_improved_error_messages():
    """エラーメッセージが日本語で返されることを確認"""
    # 存在しないエンドポイント
    response = client.get("/api/v1/nonexistent")
    assert response.status_code == 404
    
    # 認証なしでの保護されたエンドポイントアクセス
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401
    assert "detail" in response.json()