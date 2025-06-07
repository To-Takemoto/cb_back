import pytest
import datetime
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from fastapi.testclient import TestClient
from src.infra.rest_api.main import app
from src.infra.sqlite_client.peewee_models import (
    db_proxy, User, DiscussionStructure, Message, LLMDetails, AvailableModelCache
)
from src.infra.auth import get_password_hash
from peewee import SqliteDatabase


@pytest.fixture(scope="function")
def setup_test_db():
    """テスト用データベースをセットアップ"""
    # インメモリデータベースを使用
    test_db = SqliteDatabase(':memory:')
    db_proxy.initialize(test_db)
    
    # テーブルを作成
    test_db.create_tables([User, DiscussionStructure, Message, LLMDetails, AvailableModelCache])
    
    yield test_db
    
    # クリーンアップ
    test_db.drop_tables([User, DiscussionStructure, Message, LLMDetails, AvailableModelCache])
    test_db.close()


@pytest.fixture
def test_user(setup_test_db):
    """テスト用ユーザーを作成"""
    user = User.create(
        uuid="test-user-uuid",
        name="testuser",
        password=get_password_hash("testpass")
    )
    return user


@pytest.fixture
def auth_headers(test_user):
    """認証ヘッダーを取得"""
    from src.infra.rest_api.dependencies import get_current_user
    
    def mock_get_current_user():
        return test_user.uuid
    
    app.dependency_overrides[get_current_user] = mock_get_current_user
    
    yield {"Authorization": "Bearer mock-token"}
    
    # クリーンアップ
    app.dependency_overrides.clear()


@pytest.fixture
def test_data(setup_test_db, test_user):
    """テスト用のメッセージ・統計データを作成"""
    # モデルキャッシュを作成
    model1 = AvailableModelCache.create(
        id="gpt-3.5-turbo",
        name="GPT-3.5 Turbo",
        description="Fast and efficient",
        context_length=4096,
        pricing_prompt="0.001",
        pricing_completion="0.002",
        created=1640995200
    )
    
    model2 = AvailableModelCache.create(
        id="gpt-4",
        name="GPT-4",
        description="Advanced reasoning",
        context_length=8192,
        pricing_prompt="0.01",
        pricing_completion="0.03",
        created=1640995200
    )
    
    # ディスカッション（チャット）を作成
    discussion = DiscussionStructure.create(
        user=test_user.id,
        uuid="test-discussion-uuid",
        title="Test Chat",
        serialized_structure=b'test_data'
    )
    
    # 過去7日間のメッセージを作成
    now = datetime.datetime.now()
    for i in range(7):
        date = now - datetime.timedelta(days=i)
        
        # ユーザーメッセージ
        user_msg = Message.create(
            discussion=discussion.id,
            uuid=f"user-msg-{i}",
            role="user",
            content=f"User message {i}",
            created_at=date
        )
        
        # アシスタントメッセージ
        assistant_msg = Message.create(
            discussion=discussion.id,
            uuid=f"assistant-msg-{i}",
            role="assistant",
            content=f"Assistant response {i}",
            created_at=date + datetime.timedelta(minutes=1)
        )
        
        # LLM詳細（トークン使用量とコスト計算用）
        model_id = "gpt-3.5-turbo" if i % 2 == 0 else "gpt-4"
        LLMDetails.create(
            message=assistant_msg.id,
            model=model_id,
            provider="openrouter",
            prompt_tokens=100 + i * 10,
            completion_tokens=50 + i * 5,
            total_tokens=150 + i * 15
        )
    
    return {
        "user": test_user,
        "discussion": discussion,
        "models": [model1, model2]
    }


class TestAnalyticsAPI:
    """アナリティクスAPI関連のテスト"""
    
    def test_get_analytics_overview(self, setup_test_db, auth_headers, test_data):
        """使用統計概要取得のテスト"""
        with TestClient(app) as client:
            response = client.get(
                "/api/v1/analytics/overview?period=7d",
                headers=auth_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            
            # 基本統計の確認
            assert "total_messages" in data
            assert "total_tokens" in data
            assert "total_cost" in data
            assert "period_start" in data
            assert "period_end" in data
            
            # 7日間で7つのアシスタントメッセージがあることを確認
            assert data["total_messages"] >= 7
    
    def test_get_model_breakdown(self, setup_test_db, auth_headers, test_data):
        """モデル別使用統計のテスト"""
        with TestClient(app) as client:
            response = client.get(
                "/api/v1/analytics/models?period=7d",
                headers=auth_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            
            assert "models" in data
            models = data["models"]
            
            # 両方のモデルが使用されていることを確認
            model_ids = [model["model_id"] for model in models]
            assert "gpt-3.5-turbo" in model_ids
            assert "gpt-4" in model_ids
            
            # 各モデルの統計データが正しい形式であることを確認
            for model in models:
                assert "model_id" in model
                assert "model_name" in model
                assert "message_count" in model
                assert "token_count" in model
                assert "cost" in model
                assert "percentage" in model
                assert isinstance(model["message_count"], int)
                assert isinstance(model["token_count"], int)
                assert isinstance(model["cost"], (int, float))
    
    def test_get_daily_usage(self, setup_test_db, auth_headers, test_data):
        """日別使用統計のテスト"""
        with TestClient(app) as client:
            response = client.get(
                "/api/v1/analytics/daily?period=7d",
                headers=auth_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            
            assert "daily_usage" in data
            daily_usage = data["daily_usage"]
            
            # 7日間のデータが返されることを確認
            assert len(daily_usage) == 8  # 今日を含む8日間
            
            # 各日のデータ形式を確認
            for day in daily_usage:
                assert "date" in day
                assert "message_count" in day
                assert "token_count" in day
                assert "cost" in day
                assert isinstance(day["message_count"], int)
                assert isinstance(day["token_count"], int)
                assert isinstance(day["cost"], (int, float))
    
    def test_get_hourly_pattern(self, setup_test_db, auth_headers, test_data):
        """時間帯別使用パターンのテスト"""
        with TestClient(app) as client:
            response = client.get(
                "/api/v1/analytics/hourly?period=7d",
                headers=auth_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            
            assert "hourly_pattern" in data
            hourly_pattern = data["hourly_pattern"]
            
            # 24時間分のデータが返されることを確認
            assert len(hourly_pattern) == 24
            
            # 各時間のデータ形式を確認
            for hour_data in hourly_pattern:
                assert "hour" in hour_data
                assert "message_count" in hour_data
                assert "token_count" in hour_data
                assert 0 <= hour_data["hour"] <= 23
                assert isinstance(hour_data["message_count"], int)
                assert isinstance(hour_data["token_count"], int)
    
    def test_get_cost_analysis(self, setup_test_db, auth_headers, test_data):
        """コスト分析のテスト"""
        with TestClient(app) as client:
            response = client.get(
                "/api/v1/analytics/costs?period=7d",
                headers=auth_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            
            assert "cost_trends" in data
            assert "total_cost" in data
            assert "average_cost_per_message" in data
            assert "average_cost_per_token" in data
            
            # コストトレンドの形式確認
            cost_trends = data["cost_trends"]
            for trend in cost_trends:
                assert "date" in trend
                assert "daily_cost" in trend
                assert "cumulative_cost" in trend
                assert isinstance(trend["daily_cost"], (int, float))
                assert isinstance(trend["cumulative_cost"], (int, float))
    
    def test_get_full_analytics(self, setup_test_db, auth_headers, test_data):
        """総合アナリティクス取得のテスト"""
        with TestClient(app) as client:
            response = client.get(
                "/api/v1/analytics?period=7d",
                headers=auth_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            
            # 全ての主要セクションが含まれていることを確認
            assert "overview" in data
            assert "model_breakdown" in data
            assert "daily_usage" in data
            assert "hourly_pattern" in data
            assert "top_categories" in data
            assert "cost_trends" in data
            
            # 概要データの確認
            overview = data["overview"]
            assert "total_messages" in overview
            assert "total_tokens" in overview
            assert "total_cost" in overview
    
    def test_analytics_period_validation(self, setup_test_db, auth_headers, test_data):
        """期間パラメータのバリデーションテスト"""
        with TestClient(app) as client:
            # 有効な期間
            valid_periods = ["1d", "7d", "30d", "90d", "1y"]
            for period in valid_periods:
                response = client.get(
                    f"/api/v1/analytics/overview?period={period}",
                    headers=auth_headers
                )
                assert response.status_code == 200
            
            # 無効な期間
            response = client.get(
                "/api/v1/analytics/overview?period=invalid",
                headers=auth_headers
            )
            assert response.status_code == 422
    
    def test_analytics_with_model_filter(self, setup_test_db, auth_headers, test_data):
        """モデルフィルターのテスト"""
        with TestClient(app) as client:
            response = client.get(
                "/api/v1/analytics/overview?period=7d&model_filter=gpt-4",
                headers=auth_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            
            # フィルターされた結果であることを確認
            # GPT-4のみのメッセージ数は全体より少ないはず
            assert "total_messages" in data
            assert "total_tokens" in data


class TestAnalyticsRepository:
    """アナリティクスリポジトリのテスト"""
    
    def test_period_parsing(self, setup_test_db):
        """期間パースのテスト"""
        from src.infra.sqlite_client.analytics_repository import AnalyticsRepository
        
        repo = AnalyticsRepository()
        
        # 各期間の解析テスト
        start, end = repo._parse_period("1d")
        assert (end - start).days == 1
        
        start, end = repo._parse_period("7d")
        assert (end - start).days == 7
        
        start, end = repo._parse_period("30d")
        assert (end - start).days == 30
        
        start, end = repo._parse_period("invalid")
        assert (end - start).days == 7  # デフォルト値


if __name__ == "__main__":
    pytest.main([__file__, "-v"])