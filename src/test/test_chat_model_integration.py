import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, AsyncMock, patch
import sys
import os

# パッケージパスを追加
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from src.infra.rest_api.main import app
from src.domain.entity.model_entity import ModelEntity, ModelPricing


class TestChatModelIntegration:
    """チャット機能とモデル選択の統合テスト"""
    
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
                pricing=ModelPricing(prompt="0.0000015", completion="0.000002"),
                context_length=4096
            ),
            ModelEntity(
                id="openai/gpt-4",
                name="GPT-4",
                created=1687882411,
                description="OpenAI's GPT-4 model",
                pricing=ModelPricing(prompt="0.00003", completion="0.00006"),
                context_length=8192
            )
        ]
    
    @patch('src.infra.rest_api.routers.chats.get_current_user')
    @patch('src.infra.rest_api.routers.chats.get_model_service')
    @patch('src.infra.rest_api.routers.chats.get_llm_client_dependency')
    @patch('src.infra.rest_api.routers.chats.get_message_cache_dependency')
    @patch('src.infra.rest_api.routers.chats.create_chat_repo_for_user')
    @patch('src.infra.rest_api.routers.chats.ChatInteraction')
    def test_create_chat_with_model_selection(
        self, 
        mock_chat_interaction,
        mock_create_chat_repo,
        mock_get_cache,
        mock_get_llm_client,
        mock_get_model_service,
        mock_get_current_user,
        client,
        sample_models
    ):
        """モデル指定でのチャット作成テスト"""
        # 認証をモック
        mock_get_current_user.return_value = "user123"
        
        # モデルサービスをモック
        mock_model_service = Mock()
        mock_model_service.get_available_models = AsyncMock(return_value=sample_models)
        mock_model_service.validate_model_id.return_value = True
        mock_model_service.set_model = Mock()
        mock_get_model_service.return_value = mock_model_service
        
        # チャットインタラクションをモック
        mock_interaction_instance = Mock()
        mock_interaction_instance.structure.get_uuid.return_value = "test-chat-uuid"
        mock_interaction_instance.start_new_chat = Mock()
        mock_chat_interaction.return_value = mock_interaction_instance
        
        # 他の依存関係をモック
        mock_get_llm_client.return_value = Mock()
        mock_get_cache.return_value = Mock()
        mock_create_chat_repo.return_value = Mock()
        
        # テスト実行
        response = client.post("/api/v1/chats/", json={
            "initial_message": "Hello, world!",
            "model_id": "openai/gpt-4"
        })
        
        # 検証
        assert response.status_code == 200
        data = response.json()
        assert data["chat_uuid"] == "test-chat-uuid"
        
        # モデル関連のメソッドが呼び出されたことを確認
        mock_model_service.get_available_models.assert_called_once()
        mock_model_service.validate_model_id.assert_called_once_with("openai/gpt-4", sample_models)
        mock_model_service.set_model.assert_called_once_with("openai/gpt-4")
        
        # チャット作成が呼び出されたことを確認
        mock_interaction_instance.start_new_chat.assert_called_once_with("Hello, world!")
    
    @patch('src.infra.rest_api.routers.chats.get_current_user')
    @patch('src.infra.rest_api.routers.chats.get_model_service')
    @patch('src.infra.rest_api.routers.chats.get_llm_client_dependency')
    @patch('src.infra.rest_api.routers.chats.get_message_cache_dependency')
    @patch('src.infra.rest_api.routers.chats.create_chat_repo_for_user')
    @patch('src.infra.rest_api.routers.chats.ChatInteraction')
    def test_create_chat_without_model_selection(
        self, 
        mock_chat_interaction,
        mock_create_chat_repo,
        mock_get_cache,
        mock_get_llm_client,
        mock_get_model_service,
        mock_get_current_user,
        client
    ):
        """モデル指定なしでのチャット作成テスト"""
        # 認証をモック
        mock_get_current_user.return_value = "user123"
        
        # モデルサービスをモック（呼び出されないはず）
        mock_model_service = Mock()
        mock_get_model_service.return_value = mock_model_service
        
        # チャットインタラクションをモック
        mock_interaction_instance = Mock()
        mock_interaction_instance.structure.get_uuid.return_value = "test-chat-uuid"
        mock_interaction_instance.start_new_chat = Mock()
        mock_chat_interaction.return_value = mock_interaction_instance
        
        # 他の依存関係をモック
        mock_get_llm_client.return_value = Mock()
        mock_get_cache.return_value = Mock()
        mock_create_chat_repo.return_value = Mock()
        
        # テスト実行
        response = client.post("/api/v1/chats/", json={
            "initial_message": "Hello, world!"
        })
        
        # 検証
        assert response.status_code == 200
        data = response.json()
        assert data["chat_uuid"] == "test-chat-uuid"
        
        # モデル関連のメソッドが呼び出されていないことを確認
        assert not mock_model_service.get_available_models.called
        assert not mock_model_service.validate_model_id.called
        assert not mock_model_service.set_model.called
    
    @patch('src.infra.rest_api.routers.chats.get_current_user')
    @patch('src.infra.rest_api.routers.chats.get_model_service')
    @patch('src.infra.rest_api.routers.chats.get_llm_client_dependency')
    @patch('src.infra.rest_api.routers.chats.get_message_cache_dependency')
    @patch('src.infra.rest_api.routers.chats.create_chat_repo_for_user')
    def test_create_chat_with_invalid_model(
        self, 
        mock_create_chat_repo,
        mock_get_cache,
        mock_get_llm_client,
        mock_get_model_service,
        mock_get_current_user,
        client,
        sample_models
    ):
        """無効なモデル指定でのチャット作成テスト"""
        # 認証をモック
        mock_get_current_user.return_value = "user123"
        
        # モデルサービスをモック
        mock_model_service = Mock()
        mock_model_service.get_available_models = AsyncMock(return_value=sample_models)
        mock_model_service.validate_model_id.return_value = False
        mock_get_model_service.return_value = mock_model_service
        
        # 他の依存関係をモック
        mock_get_llm_client.return_value = Mock()
        mock_get_cache.return_value = Mock()
        mock_create_chat_repo.return_value = Mock()
        
        # テスト実行
        response = client.post("/api/v1/chats/", json={
            "initial_message": "Hello, world!",
            "model_id": "invalid/model"
        })
        
        # 検証
        assert response.status_code == 400
        assert response.json()["detail"] == "Model 'invalid/model' is not available"
    
    @patch('src.infra.rest_api.routers.chats.get_current_user')
    @patch('src.infra.rest_api.routers.chats.get_model_service')
    @patch('src.infra.rest_api.routers.chats.get_llm_client_dependency')
    @patch('src.infra.rest_api.routers.chats.get_message_cache_dependency')
    @patch('src.infra.rest_api.routers.chats.create_chat_repo_for_user')
    @patch('src.infra.rest_api.routers.chats.ChatInteraction')
    def test_send_message_with_model_selection(
        self, 
        mock_chat_interaction,
        mock_create_chat_repo,
        mock_get_cache,
        mock_get_llm_client,
        mock_get_model_service,
        mock_get_current_user,
        client,
        sample_models
    ):
        """モデル指定でのメッセージ送信テスト"""
        # 認証をモック
        mock_get_current_user.return_value = "user123"
        
        # モデルサービスをモック
        mock_model_service = Mock()
        mock_model_service.get_available_models = AsyncMock(return_value=sample_models)
        mock_model_service.validate_model_id.return_value = True
        mock_model_service.set_model = Mock()
        mock_get_model_service.return_value = mock_model_service
        
        # チャットインタラクションをモック
        mock_interaction_instance = Mock()
        mock_message = Mock()
        mock_message.uuid = "message-uuid"
        mock_message.content = "AI response"
        mock_interaction_instance.continue_chat = AsyncMock(return_value=mock_message)
        mock_interaction_instance.restart_chat = Mock()
        mock_interaction_instance.select_message = Mock()
        mock_interaction_instance.structure.current_node = Mock()
        mock_interaction_instance.structure.current_node.parent = None
        mock_interaction_instance.structure.get_current_path.return_value = ["path1", "path2"]
        mock_chat_interaction.return_value = mock_interaction_instance
        
        # 他の依存関係をモック
        mock_get_llm_client.return_value = Mock()
        mock_get_cache.return_value = Mock()
        mock_create_chat_repo.return_value = Mock()
        
        # テスト実行
        response = client.post("/api/v1/chats/test-chat-uuid/messages", json={
            "content": "Hello AI!",
            "model_id": "openai/gpt-4"
        })
        
        # 検証
        assert response.status_code == 200
        data = response.json()
        assert data["message_uuid"] == "message-uuid"
        assert data["content"] == "AI response"
        
        # モデル関連のメソッドが呼び出されたことを確認
        mock_model_service.get_available_models.assert_called_once()
        mock_model_service.validate_model_id.assert_called_once_with("openai/gpt-4", sample_models)
        mock_model_service.set_model.assert_called_once_with("openai/gpt-4")
        
        # チャット関連のメソッドが呼び出されたことを確認
        mock_interaction_instance.restart_chat.assert_called_once_with("test-chat-uuid")
        mock_interaction_instance.continue_chat.assert_called_once_with("Hello AI!")
    
    @patch('src.infra.rest_api.routers.chats.get_current_user')
    @patch('src.infra.rest_api.routers.chats.get_model_service')
    @patch('src.infra.rest_api.routers.chats.get_llm_client_dependency')
    @patch('src.infra.rest_api.routers.chats.get_message_cache_dependency')
    @patch('src.infra.rest_api.routers.chats.create_chat_repo_for_user')
    @patch('src.infra.rest_api.routers.chats.ChatInteraction')
    def test_send_message_without_model_selection(
        self, 
        mock_chat_interaction,
        mock_create_chat_repo,
        mock_get_cache,
        mock_get_llm_client,
        mock_get_model_service,
        mock_get_current_user,
        client
    ):
        """モデル指定なしでのメッセージ送信テスト"""
        # 認証をモック
        mock_get_current_user.return_value = "user123"
        
        # モデルサービスをモック（呼び出されないはず）
        mock_model_service = Mock()
        mock_get_model_service.return_value = mock_model_service
        
        # チャットインタラクションをモック
        mock_interaction_instance = Mock()
        mock_message = Mock()
        mock_message.uuid = "message-uuid"
        mock_message.content = "AI response"
        mock_interaction_instance.continue_chat = AsyncMock(return_value=mock_message)
        mock_interaction_instance.restart_chat = Mock()
        mock_interaction_instance.structure.current_node = Mock()
        mock_interaction_instance.structure.current_node.parent = None
        mock_interaction_instance.structure.get_current_path.return_value = ["path1", "path2"]
        mock_chat_interaction.return_value = mock_interaction_instance
        
        # 他の依存関係をモック
        mock_get_llm_client.return_value = Mock()
        mock_get_cache.return_value = Mock()
        mock_create_chat_repo.return_value = Mock()
        
        # テスト実行
        response = client.post("/api/v1/chats/test-chat-uuid/messages", json={
            "content": "Hello AI!"
        })
        
        # 検証
        assert response.status_code == 200
        data = response.json()
        assert data["message_uuid"] == "message-uuid"
        assert data["content"] == "AI response"
        
        # モデル関連のメソッドが呼び出されていないことを確認
        assert not mock_model_service.get_available_models.called
        assert not mock_model_service.validate_model_id.called
        assert not mock_model_service.set_model.called
    
    @patch('src.infra.rest_api.routers.chats.get_current_user')
    @patch('src.infra.rest_api.routers.chats.get_model_service')
    @patch('src.infra.rest_api.routers.chats.get_llm_client_dependency')
    @patch('src.infra.rest_api.routers.chats.get_message_cache_dependency')
    @patch('src.infra.rest_api.routers.chats.create_chat_repo_for_user')
    def test_send_message_with_invalid_model(
        self, 
        mock_create_chat_repo,
        mock_get_cache,
        mock_get_llm_client,
        mock_get_model_service,
        mock_get_current_user,
        client,
        sample_models
    ):
        """無効なモデル指定でのメッセージ送信テスト"""
        # 認証をモック
        mock_get_current_user.return_value = "user123"
        
        # モデルサービスをモック
        mock_model_service = Mock()
        mock_model_service.get_available_models = AsyncMock(return_value=sample_models)
        mock_model_service.validate_model_id.return_value = False
        mock_get_model_service.return_value = mock_model_service
        
        # 他の依存関係をモック
        mock_get_llm_client.return_value = Mock()
        mock_get_cache.return_value = Mock()
        mock_create_chat_repo.return_value = Mock()
        
        # テスト実行
        response = client.post("/api/v1/chats/test-chat-uuid/messages", json={
            "content": "Hello AI!",
            "model_id": "invalid/model"
        })
        
        # 検証
        assert response.status_code == 400
        assert response.json()["detail"] == "Model 'invalid/model' is not available"