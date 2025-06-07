import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, AsyncMock, patch
import sys
import os

# パッケージパスを追加
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from src.infra.rest_api.main import app
from src.domain.entity.model_entity import ModelEntity, ModelArchitecture, ModelPricing


class TestModelsAPI:
    """モデルAPIエンドポイントの統合テスト"""
    
    @pytest.fixture
    def client(self):
        """テストクライアント"""
        return TestClient(app)
    
    @pytest.fixture
    def sample_models(self):
        """テスト用のサンプルモデル"""
        return [
            ModelEntity(
                id="openai/gpt-3.5-turbo",
                name="GPT-3.5 Turbo",
                created=1677649963,
                description="OpenAI's GPT-3.5 Turbo model",
                architecture=ModelArchitecture(
                    input_modalities=["text"],
                    output_modalities=["text"],
                    tokenizer="GPT"
                ),
                pricing=ModelPricing(
                    prompt="0.0000015",
                    completion="0.000002"
                ),
                context_length=4096
            ),
            ModelEntity(
                id="openai/gpt-4",
                name="GPT-4",
                created=1687882411,
                description="OpenAI's GPT-4 model",
                pricing=ModelPricing(
                    prompt="0.00003",
                    completion="0.00006"
                ),
                context_length=8192
            )
        ]
    
    @pytest.fixture
    def mock_auth_header(self):
        """認証ヘッダーのモック"""
        return {"Authorization": "Bearer test-token"}
    
    def test_get_models_unauthorized(self, client):
        """認証なしでのモデル一覧取得テスト"""
        response = client.get("/api/v1/models/")
        assert response.status_code == 401
        assert response.json()["detail"] == "Not authenticated"
    
    def test_get_models_success(self, client, sample_models):
        """モデル一覧取得成功テスト"""
        from src.infra.rest_api.routers.models import get_current_user, get_model_service
        
        # 認証をモック
        def mock_get_current_user():
            return "user123"
        
        # モデルサービスをモック
        mock_service = Mock()
        mock_service.get_available_models = AsyncMock(return_value=sample_models)
        def mock_get_model_service():
            return mock_service
        
        # 依存関係をオーバーライド
        app.dependency_overrides[get_current_user] = mock_get_current_user
        app.dependency_overrides[get_model_service] = mock_get_model_service
        
        try:
            # テスト実行
            response = client.get("/api/v1/models/")
        finally:
            # クリーンアップ
            app.dependency_overrides.clear()
        
        # 検証
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert len(data["data"]) == 2
        
        # 最初のモデルの検証
        first_model = data["data"][0]
        assert first_model["id"] == "openai/gpt-3.5-turbo"
        assert first_model["name"] == "GPT-3.5 Turbo"
        assert first_model["description"] == "OpenAI's GPT-3.5 Turbo model"
        assert first_model["context_length"] == 4096
        
        # アーキテクチャの検証
        assert first_model["architecture"] is not None
        assert first_model["architecture"]["input_modalities"] == ["text"]
        assert first_model["architecture"]["output_modalities"] == ["text"]
        assert first_model["architecture"]["tokenizer"] == "GPT"
        
        # 価格の検証
        assert first_model["pricing"] is not None
        assert first_model["pricing"]["prompt"] == "0.0000015"
        assert first_model["pricing"]["completion"] == "0.000002"
        
        # 2番目のモデルの検証
        second_model = data["data"][1]
        assert second_model["id"] == "openai/gpt-4"
        assert second_model["architecture"] is None
    
    @patch('src.infra.rest_api.routers.models.get_current_user')
    @patch('src.infra.rest_api.routers.models.get_model_service')
    def test_get_models_with_category(self, mock_get_model_service, mock_get_current_user, client, sample_models):
        """カテゴリ指定でのモデル一覧取得テスト"""
        # 認証をモック
        mock_get_current_user.return_value = "user123"
        
        # モデルサービスをモック
        mock_service = Mock()
        mock_service.get_available_models = AsyncMock(return_value=sample_models)
        mock_get_model_service.return_value = mock_service
        
        # テスト実行
        response = client.get("/api/v1/models/?category=programming")
        
        # 検証
        assert response.status_code == 200
        mock_service.get_available_models.assert_called_once_with("programming")
    
    @patch('src.infra.rest_api.routers.models.get_current_user')
    @patch('src.infra.rest_api.routers.models.get_model_service')
    def test_get_models_error(self, mock_get_model_service, mock_get_current_user, client):
        """モデル一覧取得エラーテスト"""
        # 認証をモック
        mock_get_current_user.return_value = "user123"
        
        # モデルサービスでエラーを発生させる
        mock_service = Mock()
        mock_service.get_available_models = AsyncMock(side_effect=Exception("API Error"))
        mock_get_model_service.return_value = mock_service
        
        # テスト実行
        response = client.get("/api/v1/models/")
        
        # 検証
        assert response.status_code == 500
        assert response.json()["detail"] == "Failed to retrieve models"
    
    def test_select_model_unauthorized(self, client):
        """認証なしでのモデル選択テスト"""
        response = client.post("/api/v1/models/select", json={"model_id": "openai/gpt-3.5-turbo"})
        assert response.status_code == 401
        assert response.json()["detail"] == "Not authenticated"
    
    @patch('src.infra.rest_api.routers.models.get_current_user')
    @patch('src.infra.rest_api.routers.models.get_model_service')
    def test_select_model_success(self, mock_get_model_service, mock_get_current_user, client, sample_models):
        """モデル選択成功テスト"""
        # 認証をモック
        mock_get_current_user.return_value = "user123"
        
        # モデルサービスをモック
        mock_service = Mock()
        mock_service.get_available_models = AsyncMock(return_value=sample_models)
        mock_service.validate_model_id.return_value = True
        mock_service.set_model = Mock()
        mock_get_model_service.return_value = mock_service
        
        # テスト実行
        response = client.post("/api/v1/models/select", json={"model_id": "openai/gpt-3.5-turbo"})
        
        # 検証
        assert response.status_code == 200
        data = response.json()
        assert data["detail"] == "Model 'openai/gpt-3.5-turbo' selected successfully"
        assert data["model_id"] == "openai/gpt-3.5-turbo"
        
        # サービスメソッドが呼び出されたことを確認
        mock_service.get_available_models.assert_called_once()
        mock_service.validate_model_id.assert_called_once_with("openai/gpt-3.5-turbo", sample_models)
        mock_service.set_model.assert_called_once_with("openai/gpt-3.5-turbo")
    
    @patch('src.infra.rest_api.routers.models.get_current_user')
    @patch('src.infra.rest_api.routers.models.get_model_service')
    def test_select_model_invalid(self, mock_get_model_service, mock_get_current_user, client, sample_models):
        """無効なモデル選択テスト"""
        # 認証をモック
        mock_get_current_user.return_value = "user123"
        
        # モデルサービスをモック
        mock_service = Mock()
        mock_service.get_available_models = AsyncMock(return_value=sample_models)
        mock_service.validate_model_id.return_value = False
        mock_get_model_service.return_value = mock_service
        
        # テスト実行
        response = client.post("/api/v1/models/select", json={"model_id": "invalid/model"})
        
        # 検証
        assert response.status_code == 400
        assert response.json()["detail"] == "Model 'invalid/model' is not available"
        
        # set_modelが呼び出されていないことを確認
        assert not hasattr(mock_service, 'set_model') or not mock_service.set_model.called
    
    @patch('src.infra.rest_api.routers.models.get_current_user')
    @patch('src.infra.rest_api.routers.models.get_model_service')
    def test_select_model_error(self, mock_get_model_service, mock_get_current_user, client):
        """モデル選択エラーテスト"""
        # 認証をモック
        mock_get_current_user.return_value = "user123"
        
        # モデルサービスでエラーを発生させる
        mock_service = Mock()
        mock_service.get_available_models = AsyncMock(side_effect=Exception("API Error"))
        mock_get_model_service.return_value = mock_service
        
        # テスト実行
        response = client.post("/api/v1/models/select", json={"model_id": "openai/gpt-3.5-turbo"})
        
        # 検証
        assert response.status_code == 500
        assert response.json()["detail"] == "Failed to select model"
    
    def test_get_current_model_unauthorized(self, client):
        """認証なしでの現在のモデル取得テスト"""
        response = client.get("/api/v1/models/current")
        assert response.status_code == 401
        assert response.json()["detail"] == "Not authenticated"
    
    @patch('src.infra.rest_api.routers.models.get_current_user')
    @patch('src.infra.rest_api.routers.models.get_model_service')
    def test_get_current_model_success(self, mock_get_model_service, mock_get_current_user, client):
        """現在のモデル取得成功テスト"""
        # 認証をモック
        mock_get_current_user.return_value = "user123"
        
        # モデルサービスをモック
        mock_service = Mock()
        mock_service.get_current_model.return_value = "openai/gpt-4"
        mock_get_model_service.return_value = mock_service
        
        # テスト実行
        response = client.get("/api/v1/models/current")
        
        # 検証
        assert response.status_code == 200
        data = response.json()
        assert data["model_id"] == "openai/gpt-4"
    
    @patch('src.infra.rest_api.routers.models.get_current_user')
    @patch('src.infra.rest_api.routers.models.get_model_service')
    def test_get_current_model_error(self, mock_get_model_service, mock_get_current_user, client):
        """現在のモデル取得エラーテスト"""
        # 認証をモック
        mock_get_current_user.return_value = "user123"
        
        # モデルサービスでエラーを発生させる
        mock_service = Mock()
        mock_service.get_current_model.side_effect = Exception("Service Error")
        mock_get_model_service.return_value = mock_service
        
        # テスト実行
        response = client.get("/api/v1/models/current")
        
        # 検証
        assert response.status_code == 500
        assert response.json()["detail"] == "Failed to get current model"