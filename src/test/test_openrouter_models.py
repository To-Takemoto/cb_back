import pytest
from unittest.mock import Mock, AsyncMock, patch
import httpx
import sys
import os

# パッケージパスを追加
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from src.infra.openrouter_client import OpenRouterLLMService
from src.domain.entity.model_entity import ModelEntity


class TestOpenRouterModels:
    """OpenRouterクライアントのモデル関連機能テスト"""
    
    @pytest.fixture
    def mock_response_data(self):
        """モックレスポンスデータ"""
        return {
            "data": [
                {
                    "id": "openai/gpt-3.5-turbo",
                    "name": "GPT-3.5 Turbo",
                    "created": 1677649963,
                    "description": "OpenAI's GPT-3.5 Turbo model",
                    "architecture": {
                        "input_modalities": ["text"],
                        "output_modalities": ["text"],
                        "tokenizer": "GPT"
                    },
                    "pricing": {
                        "prompt": "0.0000015",
                        "completion": "0.000002"
                    },
                    "context_length": 4096
                },
                {
                    "id": "openai/gpt-4",
                    "name": "GPT-4",
                    "created": 1687882411,
                    "description": "OpenAI's GPT-4 model",
                    "pricing": {
                        "prompt": "0.00003",
                        "completion": "0.00006"
                    },
                    "context_length": 8192
                }
            ]
        }
    
    @pytest.fixture
    def openrouter_service(self):
        """テスト用OpenRouterサービス"""
        # 環境変数をモック
        with patch.dict(os.environ, {'OPENROUTER_API_KEY': 'test-api-key'}):
            return OpenRouterLLMService()
    
    @pytest.mark.asyncio
    async def test_get_available_models_success(self, openrouter_service, mock_response_data):
        """モデル一覧取得成功のテスト"""
        # HTTPクライアントをモック
        mock_client = AsyncMock()
        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_response.json.return_value = mock_response_data
        mock_client.get.return_value = mock_response
        
        openrouter_service._client = mock_client
        
        # テスト実行
        result = await openrouter_service.get_available_models()
        
        # 検証
        assert len(result) == 2
        
        # 最初のモデルの検証
        first_model = result[0]
        assert isinstance(first_model, ModelEntity)
        assert first_model.id == "openai/gpt-3.5-turbo"
        assert first_model.name == "GPT-3.5 Turbo"
        assert first_model.created == 1677649963
        assert first_model.description == "OpenAI's GPT-3.5 Turbo model"
        assert first_model.context_length == 4096
        
        # アーキテクチャの検証
        assert first_model.architecture is not None
        assert first_model.architecture.input_modalities == ["text"]
        assert first_model.architecture.output_modalities == ["text"]
        assert first_model.architecture.tokenizer == "GPT"
        
        # 価格の検証
        assert first_model.pricing is not None
        assert first_model.pricing.prompt == "0.0000015"
        assert first_model.pricing.completion == "0.000002"
        
        # 2番目のモデルの検証
        second_model = result[1]
        assert second_model.id == "openai/gpt-4"
        assert second_model.architecture is None  # アーキテクチャ情報がない
        assert second_model.pricing is not None
        
        # APIコールの検証
        mock_client.get.assert_called_once_with(
            "https://openrouter.ai/api/v1/models",
            headers=openrouter_service.headers,
            params={}
        )
    
    @pytest.mark.asyncio
    async def test_get_available_models_with_category(self, openrouter_service, mock_response_data):
        """カテゴリ指定でのモデル一覧取得テスト"""
        # HTTPクライアントをモック
        mock_client = AsyncMock()
        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_response.json.return_value = mock_response_data
        mock_client.get.return_value = mock_response
        
        openrouter_service._client = mock_client
        
        # テスト実行
        result = await openrouter_service.get_available_models("programming")
        
        # 検証
        assert len(result) == 2
        
        # APIコールの検証（カテゴリパラメータが含まれていることを確認）
        mock_client.get.assert_called_once_with(
            "https://openrouter.ai/api/v1/models",
            headers=openrouter_service.headers,
            params={"category": "programming"}
        )
    
    @pytest.mark.asyncio
    async def test_get_available_models_minimal_data(self, openrouter_service):
        """最小限のデータでのモデル一覧取得テスト"""
        minimal_response = {
            "data": [
                {
                    "id": "simple/model",
                    "name": "Simple Model",
                    "created": 1234567890
                }
            ]
        }
        
        # HTTPクライアントをモック
        mock_client = AsyncMock()
        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_response.json.return_value = minimal_response
        mock_client.get.return_value = mock_response
        
        openrouter_service._client = mock_client
        
        # テスト実行
        result = await openrouter_service.get_available_models()
        
        # 検証
        assert len(result) == 1
        model = result[0]
        assert model.id == "simple/model"
        assert model.name == "Simple Model"
        assert model.created == 1234567890
        assert model.description is None
        assert model.architecture is None
        assert model.pricing is None
        assert model.context_length is None
    
    @pytest.mark.asyncio
    async def test_get_available_models_timeout_error(self, openrouter_service):
        """タイムアウトエラーのテスト"""
        # HTTPクライアントをモック
        mock_client = AsyncMock()
        mock_client.get.side_effect = httpx.TimeoutException("Request timed out")
        
        openrouter_service._client = mock_client
        
        # テスト実行と検証
        with pytest.raises(TimeoutError, match="Models API request timed out"):
            await openrouter_service.get_available_models()
    
    @pytest.mark.asyncio
    async def test_get_available_models_http_error(self, openrouter_service):
        """HTTPエラーのテスト"""
        # HTTPクライアントをモック
        mock_client = AsyncMock()
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Unauthorized", request=Mock(), response=mock_response
        )
        mock_client.get.return_value = mock_response
        
        openrouter_service._client = mock_client
        
        # テスト実行と検証
        with pytest.raises(ConnectionError, match="Models API error: 401"):
            await openrouter_service.get_available_models()
    
    @pytest.mark.asyncio
    async def test_get_available_models_empty_response(self, openrouter_service):
        """空のレスポンスのテスト"""
        empty_response = {"data": []}
        
        # HTTPクライアントをモック
        mock_client = AsyncMock()
        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_response.json.return_value = empty_response
        mock_client.get.return_value = mock_response
        
        openrouter_service._client = mock_client
        
        # テスト実行
        result = await openrouter_service.get_available_models()
        
        # 検証
        assert len(result) == 0
        assert result == []
    
    @pytest.mark.asyncio
    async def test_client_initialization(self, openrouter_service):
        """クライアント初期化のテスト"""
        # 初期状態ではクライアントはNone
        assert openrouter_service._client is None
        
        # HTTPクライアントをモック
        mock_client = AsyncMock()
        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_response.json.return_value = {"data": []}
        mock_client.get.return_value = mock_response
        
        # httpx.AsyncClientをモック
        with patch('httpx.AsyncClient', return_value=mock_client):
            await openrouter_service.get_available_models()
        
        # クライアントが設定されていることを確認
        assert openrouter_service._client is not None