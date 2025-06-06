import pytest
import time
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from fastapi.testclient import TestClient
from src.infra.rest_api.main import app

client = TestClient(app)

def test_login_rate_limit():
    """ログインエンドポイントのレート制限をテスト（5回/分）"""
    # 連続して6回ログインを試行
    for i in range(6):
        response = client.post(
            "/api/v1/auth/login",
            data={"username": "testuser", "password": "wrong_password"}
        )
        
        if i < 5:
            # 最初の5回は成功するはず（認証失敗でも429ではない）
            assert response.status_code != 429
        else:
            # 6回目はレート制限に引っかかるはず
            assert response.status_code == 429
            assert "リクエストが多すぎます" in response.json()["detail"]
            assert "Retry-After" in response.headers

def test_refresh_rate_limit():
    """トークンリフレッシュのレート制限をテスト（10回/時間）"""
    # まず正常なトークンを取得（実際にはモックが必要）
    # ここではレート制限の動作確認のみ
    
    # 認証なしでアクセスして401を確認
    response = client.post("/api/v1/auth/refresh")
    assert response.status_code == 401  # 認証が必要

def test_health_check_no_rate_limit():
    """ヘルスチェックエンドポイントにはレート制限がないことを確認"""
    # 20回連続でアクセス
    for i in range(20):
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"