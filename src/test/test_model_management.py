import pytest
from unittest.mock import Mock, AsyncMock
import sys
import os

# パッケージパスを追加
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from src.usecase.model_management.model_service import ModelManagementService
from src.domain.entity.model_entity import ModelEntity, ModelArchitecture, ModelPricing
from src.infra.openrouter_client import OpenRouterLLMService


class TestModelManagementService:
    """モデル管理サービスのテスト"""
    
    @pytest.fixture
    def mock_llm_service(self):
        """モックLLMサービス"""
        mock_service = Mock(spec=OpenRouterLLMService)
        mock_service.model = "openai/gpt-3.5-turbo"
        return mock_service
    
    @pytest.fixture
    def model_service(self, mock_llm_service):
        """テスト対象のモデル管理サービス"""
        return ModelManagementService(mock_llm_service)
    
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
                architecture=ModelArchitecture(
                    input_modalities=["text"],
                    output_modalities=["text"],
                    tokenizer="GPT"
                ),
                pricing=ModelPricing(
                    prompt="0.00003",
                    completion="0.00006"
                ),
                context_length=8192
            )
        ]
    
    @pytest.mark.asyncio
    async def test_get_available_models(self, model_service, mock_llm_service, sample_models):
        """利用可能なモデル一覧取得のテスト"""
        # モックの設定
        mock_llm_service.get_available_models = AsyncMock(return_value=sample_models)
        
        # テスト実行
        result = await model_service.get_available_models()
        
        # 検証
        assert len(result) == 2
        assert result[0].id == "openai/gpt-3.5-turbo"
        assert result[1].id == "openai/gpt-4"
        mock_llm_service.get_available_models.assert_called_once_with(None)
    
    @pytest.mark.asyncio
    async def test_get_available_models_with_category(self, model_service, mock_llm_service, sample_models):
        """カテゴリ指定でのモデル一覧取得のテスト"""
        # モックの設定
        mock_llm_service.get_available_models = AsyncMock(return_value=sample_models)
        
        # テスト実行
        result = await model_service.get_available_models("programming")
        
        # 検証
        assert len(result) == 2
        mock_llm_service.get_available_models.assert_called_once_with("programming")
    
    def test_validate_model_id_valid(self, model_service, sample_models):
        """有効なモデルIDのバリデーションテスト"""
        # テスト実行
        result = model_service.validate_model_id("openai/gpt-3.5-turbo", sample_models)
        
        # 検証
        assert result is True
    
    def test_validate_model_id_invalid(self, model_service, sample_models):
        """無効なモデルIDのバリデーションテスト"""
        # テスト実行
        result = model_service.validate_model_id("invalid/model", sample_models)
        
        # 検証
        assert result is False
    
    def test_validate_model_id_empty_list(self, model_service):
        """空のモデルリストでのバリデーションテスト"""
        # テスト実行
        result = model_service.validate_model_id("openai/gpt-3.5-turbo", [])
        
        # 検証
        assert result is False
    
    def test_set_model(self, model_service, mock_llm_service):
        """モデル設定のテスト"""
        # テスト実行
        model_service.set_model("openai/gpt-4")
        
        # 検証
        mock_llm_service.set_model.assert_called_once_with("openai/gpt-4")
    
    def test_get_current_model(self, model_service, mock_llm_service):
        """現在のモデル取得のテスト"""
        # モックの設定
        mock_llm_service.model = "openai/gpt-4"
        
        # テスト実行
        result = model_service.get_current_model()
        
        # 検証
        assert result == "openai/gpt-4"


class TestModelEntity:
    """モデルエンティティのテスト"""
    
    def test_model_entity_creation(self):
        """モデルエンティティの作成テスト"""
        architecture = ModelArchitecture(
            input_modalities=["text"],
            output_modalities=["text"],
            tokenizer="GPT"
        )
        pricing = ModelPricing(prompt="0.001", completion="0.002")
        
        model = ModelEntity(
            id="test/model",
            name="Test Model",
            created=1234567890,
            description="A test model",
            architecture=architecture,
            pricing=pricing,
            context_length=4096
        )
        
        assert model.id == "test/model"
        assert model.name == "Test Model"
        assert model.created == 1234567890
        assert model.description == "A test model"
        assert model.architecture == architecture
        assert model.pricing == pricing
        assert model.context_length == 4096
    
    def test_model_entity_minimal(self):
        """最小構成でのモデルエンティティ作成テスト"""
        model = ModelEntity(
            id="test/model",
            name="Test Model",
            created=1234567890
        )
        
        assert model.id == "test/model"
        assert model.name == "Test Model"
        assert model.created == 1234567890
        assert model.description is None
        assert model.architecture is None
        assert model.pricing is None
        assert model.context_length is None