"""
Template API Endpoints Tests

テンプレートとプリセットのAPIエンドポイントテスト
FastAPI TestClientを使用したエンドポイント動作検証
"""

import pytest
import sys
import os
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch
from datetime import datetime
import json
import uuid

# Add path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from src.infra.rest_api.main import app
from src.port.dto.template_dto import PromptTemplateDto, ConversationPresetDto


class TestTemplateAPIEndpoints:
    """テンプレートAPIエンドポイントテスト"""
    
    @pytest.fixture
    def client(self):
        """FastAPI TestClient"""
        return TestClient(app)
    
    @pytest.fixture
    def sample_template_dto(self):
        """サンプルテンプレートDTO"""
        return PromptTemplateDto(
            id=1,
            uuid=str(uuid.uuid4()),
            name="Test Template",
            template_content="Hello {name}!",
            user_id=1,
            description="Test description",
            category="greeting",
            variables={"name": "string"},
            is_public=False,
            is_favorite=False,
            usage_count=0,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
    
    @pytest.fixture
    def auth_headers(self):
        """認証ヘッダー（モック）"""
        return {"Authorization": "Bearer test-token"}

    # === テンプレート作成エンドポイント ===
    
    @patch('src.infra.rest_api.routers.templates.template_service')
    def test_create_template_success(self, mock_service, client, sample_template_dto, auth_headers):
        """テンプレート作成成功テスト"""
        # Given
        mock_service.create_template.return_value = sample_template_dto
        
        request_data = {
            "name": "Test Template",
            "template_content": "Hello {name}!",
            "description": "Test description",
            "category": "greeting",
            "variables": {"name": "string"}
        }
        
        # When
        with patch('src.infra.rest_api.dependencies.get_current_user_id', return_value=1):
            response = client.post("/api/v1/templates/", json=request_data, headers=auth_headers)
        
        # Then
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Test Template"
        assert data["template_content"] == "Hello {name}!"
        assert data["user_id"] == 1
        assert data["description"] == "Test description"
        assert data["category"] == "greeting"
        assert data["variables"] == {"name": "string"}
    
    @patch('src.infra.rest_api.routers.templates.template_service')
    def test_create_template_validation_error(self, mock_service, client, auth_headers):
        """テンプレート作成バリデーションエラーテスト"""
        # Given
        request_data = {
            "name": "",  # 空の名前
            "template_content": "Hello {name}!"
        }
        
        # When
        with patch('src.infra.rest_api.dependencies.get_current_user_id', return_value=1):
            response = client.post("/api/v1/templates/", json=request_data, headers=auth_headers)
        
        # Then
        assert response.status_code == 422  # Validation Error
    
    def test_create_template_unauthorized(self, client):
        """テンプレート作成未認証エラーテスト"""
        # Given
        request_data = {
            "name": "Test Template",
            "template_content": "Hello {name}!"
        }
        
        # When
        response = client.post("/api/v1/templates/", json=request_data)
        
        # Then
        assert response.status_code == 401

    # === テンプレート取得エンドポイント ===
    
    @patch('src.infra.rest_api.routers.templates.template_service')
    def test_get_template_success(self, mock_service, client, sample_template_dto, auth_headers):
        """テンプレート取得成功テスト"""
        # Given
        template_uuid = sample_template_dto.uuid
        mock_service.get_template.return_value = sample_template_dto
        
        # When
        with patch('src.infra.rest_api.dependencies.get_current_user_id', return_value=1):
            response = client.get(f"/api/v1/templates/{template_uuid}", headers=auth_headers)
        
        # Then
        assert response.status_code == 200
        data = response.json()
        assert data["uuid"] == template_uuid
        assert data["name"] == "Test Template"
    
    @patch('src.infra.rest_api.routers.templates.template_service')
    def test_get_template_not_found(self, mock_service, client, auth_headers):
        """テンプレート取得失敗テスト"""
        # Given
        from src.domain.exception.template_exceptions import TemplateNotFoundError
        mock_service.get_template.side_effect = TemplateNotFoundError("Template not found")
        
        # When
        with patch('src.infra.rest_api.dependencies.get_current_user_id', return_value=1):
            response = client.get("/api/v1/templates/non-existent-uuid", headers=auth_headers)
        
        # Then
        assert response.status_code == 404

    # === テンプレート一覧取得エンドポイント ===
    
    @patch('src.infra.rest_api.routers.templates.template_service')
    def test_list_templates_success(self, mock_service, client, auth_headers):
        """テンプレート一覧取得成功テスト"""
        # Given
        templates = [
            PromptTemplateDto(
                id=1, uuid="uuid1", name="Template 1", template_content="Content 1",
                user_id=1, is_public=False, is_favorite=True, usage_count=5,
                created_at=datetime.utcnow(), updated_at=datetime.utcnow()
            ),
            PromptTemplateDto(
                id=2, uuid="uuid2", name="Template 2", template_content="Content 2",
                user_id=1, is_public=True, is_favorite=False, usage_count=3,
                created_at=datetime.utcnow(), updated_at=datetime.utcnow()
            )
        ]
        mock_service.search_templates.return_value = (templates, 2)
        
        # When
        with patch('src.infra.rest_api.dependencies.get_current_user_id', return_value=1):
            response = client.get("/api/v1/templates/?offset=0&limit=10", headers=auth_headers)
        
        # Then
        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 2
        assert len(data["templates"]) == 2
        assert data["templates"][0]["name"] == "Template 1"
        assert data["templates"][1]["name"] == "Template 2"
    
    @patch('src.infra.rest_api.routers.templates.template_service')
    def test_list_templates_with_filters(self, mock_service, client, auth_headers):
        """フィルター付きテンプレート一覧取得テスト"""
        # Given
        templates = []
        mock_service.search_templates.return_value = (templates, 0)
        
        # When
        with patch('src.infra.rest_api.dependencies.get_current_user_id', return_value=1):
            response = client.get(
                "/api/v1/templates/?category=greeting&is_favorite=true&search=hello",
                headers=auth_headers
            )
        
        # Then
        assert response.status_code == 200
        # サービスが正しいパラメータで呼ばれたか確認
        mock_service.search_templates.assert_called_once()

    # === テンプレート更新エンドポイント ===
    
    @patch('src.infra.rest_api.routers.templates.template_service')
    def test_update_template_success(self, mock_service, client, sample_template_dto, auth_headers):
        """テンプレート更新成功テスト"""
        # Given
        template_uuid = sample_template_dto.uuid
        updated_dto = PromptTemplateDto(
            **{**sample_template_dto.__dict__, 'name': 'Updated Template'}
        )
        mock_service.update_template.return_value = updated_dto
        
        request_data = {
            "name": "Updated Template",
            "template_content": "Updated content"
        }
        
        # When
        with patch('src.infra.rest_api.dependencies.get_current_user_id', return_value=1):
            response = client.put(f"/api/v1/templates/{template_uuid}", json=request_data, headers=auth_headers)
        
        # Then
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Template"
    
    @patch('src.infra.rest_api.routers.templates.template_service')
    def test_update_template_access_denied(self, mock_service, client, auth_headers):
        """テンプレート更新アクセス拒否テスト"""
        # Given
        from src.domain.exception.template_exceptions import TemplateAccessDeniedError
        mock_service.update_template.side_effect = TemplateAccessDeniedError("Access denied")
        
        request_data = {"name": "New Name"}
        
        # When
        with patch('src.infra.rest_api.dependencies.get_current_user_id', return_value=1):
            response = client.put("/api/v1/templates/test-uuid", json=request_data, headers=auth_headers)
        
        # Then
        assert response.status_code == 403

    # === テンプレート削除エンドポイント ===
    
    @patch('src.infra.rest_api.routers.templates.template_service')
    def test_delete_template_success(self, mock_service, client, auth_headers):
        """テンプレート削除成功テスト"""
        # Given
        template_uuid = "test-uuid"
        mock_service.delete_template.return_value = None
        
        # When
        with patch('src.infra.rest_api.dependencies.get_current_user_id', return_value=1):
            response = client.delete(f"/api/v1/templates/{template_uuid}", headers=auth_headers)
        
        # Then
        assert response.status_code == 204
    
    @patch('src.infra.rest_api.routers.templates.template_service')
    def test_delete_template_not_found(self, mock_service, client, auth_headers):
        """テンプレート削除失敗テスト"""
        # Given
        from src.domain.exception.template_exceptions import TemplateNotFoundError
        mock_service.delete_template.side_effect = TemplateNotFoundError("Template not found")
        
        # When
        with patch('src.infra.rest_api.dependencies.get_current_user_id', return_value=1):
            response = client.delete("/api/v1/templates/non-existent-uuid", headers=auth_headers)
        
        # Then
        assert response.status_code == 404

    # === テンプレート使用エンドポイント ===
    
    @patch('src.infra.rest_api.routers.templates.template_service')
    def test_use_template_success(self, mock_service, client, auth_headers):
        """テンプレート使用成功テスト"""
        # Given
        template_uuid = "test-uuid"
        mock_service.use_template.return_value = None
        
        # When
        with patch('src.infra.rest_api.dependencies.get_current_user_id', return_value=1):
            response = client.post(f"/api/v1/templates/{template_uuid}/use", headers=auth_headers)
        
        # Then
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Template usage incremented"

    # === カテゴリ取得エンドポイント ===
    
    @patch('src.infra.rest_api.routers.templates.template_service')
    def test_get_categories_success(self, mock_service, client, auth_headers):
        """カテゴリ一覧取得成功テスト"""
        # Given
        categories = ["greeting", "farewell", "business", "casual"]
        mock_service.get_categories.return_value = categories
        
        # When
        with patch('src.infra.rest_api.dependencies.get_current_user_id', return_value=1):
            response = client.get("/api/v1/templates/categories", headers=auth_headers)
        
        # Then
        assert response.status_code == 200
        data = response.json()
        assert data["categories"] == categories


class TestPresetAPIEndpoints:
    """プリセットAPIエンドポイントテスト"""
    
    @pytest.fixture
    def client(self):
        """FastAPI TestClient"""
        return TestClient(app)
    
    @pytest.fixture
    def sample_preset_dto(self):
        """サンプルプリセットDTO"""
        return ConversationPresetDto(
            id=1,
            uuid=str(uuid.uuid4()),
            name="Test Preset",
            model_id="gpt-3.5-turbo",
            user_id=1,
            description="Test preset",
            temperature="0.7",
            max_tokens=1000,
            system_prompt="You are a helpful assistant",
            is_favorite=False,
            usage_count=0,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
    
    @pytest.fixture
    def auth_headers(self):
        """認証ヘッダー（モック）"""
        return {"Authorization": "Bearer test-token"}

    # === プリセット作成エンドポイント ===
    
    @patch('src.infra.rest_api.routers.templates.preset_service')
    def test_create_preset_success(self, mock_service, client, sample_preset_dto, auth_headers):
        """プリセット作成成功テスト"""
        # Given
        mock_service.create_preset.return_value = sample_preset_dto
        
        request_data = {
            "name": "Test Preset",
            "model_id": "gpt-3.5-turbo",
            "description": "Test preset",
            "temperature": "0.7",
            "max_tokens": 1000,
            "system_prompt": "You are a helpful assistant"
        }
        
        # When
        with patch('src.infra.rest_api.dependencies.get_current_user_id', return_value=1):
            response = client.post("/api/v1/templates/presets", json=request_data, headers=auth_headers)
        
        # Then
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Test Preset"
        assert data["model_id"] == "gpt-3.5-turbo"
        assert data["temperature"] == "0.7"
        assert data["max_tokens"] == 1000
    
    @patch('src.infra.rest_api.routers.templates.preset_service')
    def test_create_preset_validation_error(self, mock_service, client, auth_headers):
        """プリセット作成バリデーションエラーテスト"""
        # Given
        request_data = {
            "name": "",  # 空の名前
            "model_id": "gpt-3.5-turbo"
        }
        
        # When
        with patch('src.infra.rest_api.dependencies.get_current_user_id', return_value=1):
            response = client.post("/api/v1/templates/presets", json=request_data, headers=auth_headers)
        
        # Then
        assert response.status_code == 422  # Validation Error

    # === プリセット取得エンドポイント ===
    
    @patch('src.infra.rest_api.routers.templates.preset_service')
    def test_get_preset_success(self, mock_service, client, sample_preset_dto, auth_headers):
        """プリセット取得成功テスト"""
        # Given
        preset_uuid = sample_preset_dto.uuid
        mock_service.get_preset.return_value = sample_preset_dto
        
        # When
        with patch('src.infra.rest_api.dependencies.get_current_user_id', return_value=1):
            response = client.get(f"/api/v1/templates/presets/{preset_uuid}", headers=auth_headers)
        
        # Then
        assert response.status_code == 200
        data = response.json()
        assert data["uuid"] == preset_uuid
        assert data["name"] == "Test Preset"
    
    @patch('src.infra.rest_api.routers.templates.preset_service')
    def test_get_preset_not_found(self, mock_service, client, auth_headers):
        """プリセット取得失敗テスト"""
        # Given
        from src.domain.exception.template_exceptions import PresetNotFoundError
        mock_service.get_preset.side_effect = PresetNotFoundError("Preset not found")
        
        # When
        with patch('src.infra.rest_api.dependencies.get_current_user_id', return_value=1):
            response = client.get("/api/v1/templates/presets/non-existent-uuid", headers=auth_headers)
        
        # Then
        assert response.status_code == 404

    # === プリセット一覧取得エンドポイント ===
    
    @patch('src.infra.rest_api.routers.templates.preset_service')
    def test_list_presets_success(self, mock_service, client, auth_headers):
        """プリセット一覧取得成功テスト"""
        # Given
        presets = [
            ConversationPresetDto(
                id=1, uuid="uuid1", name="Preset 1", model_id="gpt-3.5-turbo",
                user_id=1, temperature="0.7", max_tokens=1000, is_favorite=True,
                usage_count=5, created_at=datetime.utcnow(), updated_at=datetime.utcnow()
            ),
            ConversationPresetDto(
                id=2, uuid="uuid2", name="Preset 2", model_id="gpt-4",
                user_id=1, temperature="0.8", max_tokens=2000, is_favorite=False,
                usage_count=3, created_at=datetime.utcnow(), updated_at=datetime.utcnow()
            )
        ]
        mock_service.search_presets.return_value = (presets, 2)
        
        # When
        with patch('src.infra.rest_api.dependencies.get_current_user_id', return_value=1):
            response = client.get("/api/v1/templates/presets?offset=0&limit=10", headers=auth_headers)
        
        # Then
        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 2
        assert len(data["presets"]) == 2
        assert data["presets"][0]["name"] == "Preset 1"

    # === プリセット更新エンドポイント ===
    
    @patch('src.infra.rest_api.routers.templates.preset_service')
    def test_update_preset_success(self, mock_service, client, sample_preset_dto, auth_headers):
        """プリセット更新成功テスト"""
        # Given
        preset_uuid = sample_preset_dto.uuid
        updated_dto = ConversationPresetDto(
            **{**sample_preset_dto.__dict__, 'name': 'Updated Preset'}
        )
        mock_service.update_preset.return_value = updated_dto
        
        request_data = {
            "name": "Updated Preset",
            "temperature": "0.8"
        }
        
        # When
        with patch('src.infra.rest_api.dependencies.get_current_user_id', return_value=1):
            response = client.put(f"/api/v1/templates/presets/{preset_uuid}", json=request_data, headers=auth_headers)
        
        # Then
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Preset"

    # === プリセット削除エンドポイント ===
    
    @patch('src.infra.rest_api.routers.templates.preset_service')
    def test_delete_preset_success(self, mock_service, client, auth_headers):
        """プリセット削除成功テスト"""
        # Given
        preset_uuid = "test-uuid"
        mock_service.delete_preset.return_value = None
        
        # When
        with patch('src.infra.rest_api.dependencies.get_current_user_id', return_value=1):
            response = client.delete(f"/api/v1/templates/presets/{preset_uuid}", headers=auth_headers)
        
        # Then
        assert response.status_code == 204

    # === プリセット使用エンドポイント ===
    
    @patch('src.infra.rest_api.routers.templates.preset_service')
    def test_use_preset_success(self, mock_service, client, auth_headers):
        """プリセット使用成功テスト"""
        # Given
        preset_uuid = "test-uuid"
        mock_service.use_preset.return_value = None
        
        # When
        with patch('src.infra.rest_api.dependencies.get_current_user_id', return_value=1):
            response = client.post(f"/api/v1/templates/presets/{preset_uuid}/use", headers=auth_headers)
        
        # Then
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Preset usage incremented"