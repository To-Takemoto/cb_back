import pytest
import asyncio
import json
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from fastapi.testclient import TestClient
from src.infra.rest_api.main import app
from src.infra.sqlite_client.peewee_models import (
    db_proxy, User, PromptTemplate, ConversationPreset
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
    test_db.create_tables([User, PromptTemplate, ConversationPreset])
    
    yield test_db
    
    # クリーンアップ
    test_db.drop_tables([User, PromptTemplate, ConversationPreset])
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
    # 実際のJWT認証をモック（簡単化）
    from src.infra.rest_api.dependencies import get_current_user
    
    def mock_get_current_user():
        return test_user.uuid
    
    app.dependency_overrides[get_current_user] = mock_get_current_user
    
    yield {"Authorization": "Bearer mock-token"}
    
    # クリーンアップ
    app.dependency_overrides.clear()


class TestTemplateAPI:
    """テンプレートAPI関連のテスト"""
    
    def test_create_template(self, setup_test_db, auth_headers):
        """テンプレート作成のテスト"""
        with TestClient(app) as client:
            template_data = {
                "name": "Python Code Explainer",
                "description": "Explains Python code step by step",
                "template_content": "Please explain this Python code: {code}",
                "category": "programming",
                "variables": ["code"],
                "is_public": False
            }
            
            response = client.post(
                "/api/v1/templates",
                json=template_data,
                headers=auth_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["name"] == "Python Code Explainer"
            assert data["category"] == "programming"
            assert data["variables"] == ["code"]
            assert data["usage_count"] == 0
    
    def test_get_templates_list(self, setup_test_db, auth_headers, test_user):
        """テンプレート一覧取得のテスト"""
        # テストデータを事前作成
        PromptTemplate.create(
            user=test_user.id,
            name="Test Template 1",
            template_content="Template content 1",
            category="test"
        )
        PromptTemplate.create(
            user=test_user.id,
            name="Test Template 2",
            template_content="Template content 2",
            category="test",
            is_favorite=True
        )
        
        with TestClient(app) as client:
            response = client.get(
                "/api/v1/templates",
                headers=auth_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["total"] == 2
            assert len(data["items"]) == 2
            assert data["items"][0]["name"] in ["Test Template 1", "Test Template 2"]
    
    def test_get_templates_with_filters(self, setup_test_db, auth_headers, test_user):
        """フィルター付きテンプレート一覧取得のテスト"""
        # テストデータを事前作成
        PromptTemplate.create(
            user=test_user.id,
            name="Favorite Template",
            template_content="Favorite content",
            category="favorite",
            is_favorite=True
        )
        PromptTemplate.create(
            user=test_user.id,
            name="Regular Template",
            template_content="Regular content",
            category="regular",
            is_favorite=False
        )
        
        with TestClient(app) as client:
            # お気に入りのみフィルター
            response = client.get(
                "/api/v1/templates?is_favorite=true",
                headers=auth_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["total"] == 1
            assert data["items"][0]["name"] == "Favorite Template"
            
            # カテゴリフィルター
            response = client.get(
                "/api/v1/templates?category=regular",
                headers=auth_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["total"] == 1
            assert data["items"][0]["name"] == "Regular Template"
    
    def test_update_template(self, setup_test_db, auth_headers, test_user):
        """テンプレート更新のテスト"""
        # テストデータを事前作成
        template = PromptTemplate.create(
            user=test_user.id,
            name="Original Template",
            template_content="Original content",
            category="original"
        )
        
        with TestClient(app) as client:
            update_data = {
                "name": "Updated Template",
                "template_content": "Updated content",
                "is_favorite": True
            }
            
            response = client.put(
                f"/api/v1/templates/{template.uuid}",
                json=update_data,
                headers=auth_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["name"] == "Updated Template"
            assert data["template_content"] == "Updated content"
            assert data["is_favorite"] == True
    
    def test_delete_template(self, setup_test_db, auth_headers, test_user):
        """テンプレート削除のテスト"""
        # テストデータを事前作成
        template = PromptTemplate.create(
            user=test_user.id,
            name="To Be Deleted",
            template_content="Delete me"
        )
        
        with TestClient(app) as client:
            response = client.delete(
                f"/api/v1/templates/{template.uuid}",
                headers=auth_headers
            )
            
            assert response.status_code == 200
            assert response.json()["message"] == "Template deleted successfully"
            
            # 削除確認
            response = client.get(
                f"/api/v1/templates/{template.uuid}",
                headers=auth_headers
            )
            assert response.status_code == 404
    
    def test_template_usage_increment(self, setup_test_db, auth_headers, test_user):
        """テンプレート使用回数増加のテスト"""
        # テストデータを事前作成
        template = PromptTemplate.create(
            user=test_user.id,
            name="Usage Test Template",
            template_content="Test content",
            usage_count=0
        )
        
        with TestClient(app) as client:
            response = client.post(
                f"/api/v1/templates/{template.uuid}/use",
                headers=auth_headers
            )
            
            assert response.status_code == 200
            
            # 使用回数が増加したか確認
            response = client.get(
                f"/api/v1/templates/{template.uuid}",
                headers=auth_headers
            )
            assert response.status_code == 200
            data = response.json()
            assert data["usage_count"] == 1


class TestPresetAPI:
    """プリセットAPI関連のテスト"""
    
    def test_create_preset(self, setup_test_db, auth_headers):
        """プリセット作成のテスト"""
        with TestClient(app) as client:
            preset_data = {
                "name": "Python Developer Setup",
                "description": "Optimized for Python development",
                "model_id": "gpt-4",
                "temperature": 0.3,
                "max_tokens": 2000,
                "system_prompt": "You are a Python expert."
            }
            
            response = client.post(
                "/api/v1/presets",
                json=preset_data,
                headers=auth_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["name"] == "Python Developer Setup"
            assert data["model_id"] == "gpt-4"
            assert data["temperature"] == 0.3
            assert data["max_tokens"] == 2000
    
    def test_get_presets_list(self, setup_test_db, auth_headers, test_user):
        """プリセット一覧取得のテスト"""
        # テストデータを事前作成
        ConversationPreset.create(
            user=test_user.id,
            name="Preset 1",
            model_id="gpt-3.5-turbo",
            temperature="0.7",
            max_tokens=1000
        )
        ConversationPreset.create(
            user=test_user.id,
            name="Preset 2",
            model_id="gpt-4",
            temperature="0.5",
            max_tokens=2000,
            is_favorite=True
        )
        
        with TestClient(app) as client:
            response = client.get(
                "/api/v1/presets",
                headers=auth_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["total"] == 2
            assert len(data["items"]) == 2
    
    def test_update_preset(self, setup_test_db, auth_headers, test_user):
        """プリセット更新のテスト"""
        # テストデータを事前作成
        preset = ConversationPreset.create(
            user=test_user.id,
            name="Original Preset",
            model_id="gpt-3.5-turbo",
            temperature="0.7",
            max_tokens=1000
        )
        
        with TestClient(app) as client:
            update_data = {
                "name": "Updated Preset",
                "temperature": 0.3,
                "is_favorite": True
            }
            
            response = client.put(
                f"/api/v1/presets/{preset.uuid}",
                json=update_data,
                headers=auth_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["name"] == "Updated Preset"
            assert data["temperature"] == 0.3
            assert data["is_favorite"] == True


class TestTemplateValidation:
    """テンプレートバリデーションのテスト"""
    
    def test_template_name_required(self, setup_test_db, auth_headers):
        """テンプレート名が必須であることのテスト"""
        with TestClient(app) as client:
            template_data = {
                "template_content": "Test content"
                # nameが不足
            }
            
            response = client.post(
                "/api/v1/templates",
                json=template_data,
                headers=auth_headers
            )
            
            assert response.status_code == 422
    
    def test_template_content_required(self, setup_test_db, auth_headers):
        """テンプレートコンテンツが必須であることのテスト"""
        with TestClient(app) as client:
            template_data = {
                "name": "Test Template"
                # template_contentが不足
            }
            
            response = client.post(
                "/api/v1/templates",
                json=template_data,
                headers=auth_headers
            )
            
            assert response.status_code == 422
    
    def test_preset_model_id_required(self, setup_test_db, auth_headers):
        """プリセットのモデルIDが必須であることのテスト"""
        with TestClient(app) as client:
            preset_data = {
                "name": "Test Preset"
                # model_idが不足
            }
            
            response = client.post(
                "/api/v1/presets",
                json=preset_data,
                headers=auth_headers
            )
            
            assert response.status_code == 422


if __name__ == "__main__":
    pytest.main([__file__, "-v"])