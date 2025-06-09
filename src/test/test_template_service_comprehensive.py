"""
Comprehensive Template Service Tests

テンプレート機能の包括的なテスト
TemplateServiceとPresetServiceの全機能をカバー
"""

import pytest
import sys
import os
from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch
from typing import List, Optional
import uuid

# Add path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from src.domain.entity.template_entity import PromptTemplate, ConversationPreset
from src.domain.exception.template_exceptions import (
    TemplateNotFoundError, TemplateAccessDeniedError, TemplateValidationError,
    PresetNotFoundError, PresetAccessDeniedError, PresetValidationError
)
from src.port.dto.template_dto import (
    PromptTemplateDto, ConversationPresetDto, 
    TemplateSearchCriteria, PresetSearchCriteria
)
from src.usecase.template_management.template_service import TemplateService, PresetService


class TestTemplateServiceComprehensive:
    """TemplateServiceの包括的テスト"""
    
    @pytest.fixture
    def mock_template_repo(self):
        """モックテンプレートリポジトリ"""
        return AsyncMock()
    
    @pytest.fixture
    def template_service(self, mock_template_repo):
        """TemplateServiceインスタンス"""
        return TemplateService(mock_template_repo)
    
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

    # === テンプレート作成テスト ===
    
    @pytest.mark.asyncio
    async def test_create_template_success(self, template_service, mock_template_repo, sample_template_dto):
        """テンプレート作成成功テスト"""
        # Given
        mock_template_repo.create_template.return_value = sample_template_dto
        
        # When
        result = await template_service.create_template(
            name="Test Template",
            template_content="Hello {name}!",
            user_id=1,
            description="Test description",
            category="greeting",
            variables={"name": "string"}
        )
        
        # Then
        assert result.name == "Test Template"
        assert result.template_content == "Hello {name}!"
        assert result.user_id == 1
        assert result.description == "Test description"
        assert result.category == "greeting"
        assert result.variables == {"name": "string"}
        assert not result.is_public
        assert not result.is_favorite
        assert result.usage_count == 0
        
        # リポジトリが正しく呼ばれたか確認
        mock_template_repo.create_template.assert_called_once()
        call_args = mock_template_repo.create_template.call_args[0][0]
        assert isinstance(call_args, PromptTemplate)
        assert call_args.name == "Test Template"
        assert call_args.template_content == "Hello {name}!"
    
    @pytest.mark.asyncio
    async def test_create_template_validation_errors(self, template_service):
        """テンプレート作成のバリデーションエラーテスト"""
        # 名前が空
        with pytest.raises(TemplateValidationError, match="Template name cannot be empty"):
            await template_service.create_template("", "content", 1)
        
        # 名前がNone
        with pytest.raises(TemplateValidationError, match="Template name cannot be empty"):
            await template_service.create_template(None, "content", 1)
        
        # 名前が空白のみ
        with pytest.raises(TemplateValidationError, match="Template name cannot be empty"):
            await template_service.create_template("   ", "content", 1)
        
        # コンテンツが空
        with pytest.raises(TemplateValidationError, match="Template content cannot be empty"):
            await template_service.create_template("name", "", 1)
        
        # コンテンツがNone
        with pytest.raises(TemplateValidationError, match="Template content cannot be empty"):
            await template_service.create_template("name", None, 1)
        
        # ユーザーIDが無効
        with pytest.raises(TemplateValidationError, match="User ID must be positive"):
            await template_service.create_template("name", "content", 0)
        
        with pytest.raises(TemplateValidationError, match="User ID must be positive"):
            await template_service.create_template("name", "content", -1)

    # === テンプレート取得テスト ===
    
    @pytest.mark.asyncio
    async def test_get_template_success(self, template_service, mock_template_repo, sample_template_dto):
        """テンプレート取得成功テスト"""
        # Given
        template_uuid = sample_template_dto.uuid
        mock_template_repo.get_template_by_uuid.return_value = sample_template_dto
        
        # When
        result = await template_service.get_template(template_uuid, user_id=1)
        
        # Then
        assert result.uuid == template_uuid
        assert result.name == "Test Template"
        mock_template_repo.get_template_by_uuid.assert_called_once_with(template_uuid)
    
    @pytest.mark.asyncio
    async def test_get_template_not_found(self, template_service, mock_template_repo):
        """テンプレートが見つからない場合のテスト"""
        # Given
        template_uuid = "non-existent-uuid"
        mock_template_repo.get_template_by_uuid.return_value = None
        
        # When & Then
        with pytest.raises(TemplateNotFoundError, match="Template not found"):
            await template_service.get_template(template_uuid, user_id=1)
    
    @pytest.mark.asyncio
    async def test_get_template_access_denied(self, template_service, mock_template_repo):
        """アクセス権限がない場合のテスト"""
        # Given
        template_dto = PromptTemplateDto(
            id=1, uuid="test-uuid", name="Private Template", 
            template_content="Content", user_id=999,  # 異なるユーザー
            is_public=False,  # プライベート
            is_favorite=False, usage_count=0,
            created_at=datetime.utcnow(), updated_at=datetime.utcnow()
        )
        mock_template_repo.get_template_by_uuid.return_value = template_dto
        
        # When & Then
        with pytest.raises(TemplateAccessDeniedError, match="Access denied"):
            await template_service.get_template("test-uuid", user_id=1)
    
    @pytest.mark.asyncio
    async def test_get_public_template_access_allowed(self, template_service, mock_template_repo):
        """公開テンプレートへのアクセス許可テスト"""
        # Given
        template_dto = PromptTemplateDto(
            id=1, uuid="test-uuid", name="Public Template", 
            template_content="Content", user_id=999,  # 異なるユーザー
            is_public=True,  # 公開
            is_favorite=False, usage_count=0,
            created_at=datetime.utcnow(), updated_at=datetime.utcnow()
        )
        mock_template_repo.get_template_by_uuid.return_value = template_dto
        
        # When
        result = await template_service.get_template("test-uuid", user_id=1)
        
        # Then
        assert result.name == "Public Template"
        assert result.is_public == True

    # === テンプレート更新テスト ===
    
    @pytest.mark.asyncio
    async def test_update_template_success(self, template_service, mock_template_repo, sample_template_dto):
        """テンプレート更新成功テスト"""
        # Given
        template_uuid = sample_template_dto.uuid
        mock_template_repo.get_template_by_uuid.return_value = sample_template_dto
        
        updated_dto = PromptTemplateDto(
            **{**sample_template_dto.__dict__, 
               'name': 'Updated Template', 
               'template_content': 'Updated content'}
        )
        mock_template_repo.update_template.return_value = updated_dto
        
        # When
        result = await template_service.update_template(
            template_uuid=template_uuid,
            user_id=1,
            name="Updated Template",
            template_content="Updated content"
        )
        
        # Then
        assert result.name == "Updated Template"
        assert result.template_content == "Updated content"
        mock_template_repo.update_template.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_update_template_access_denied(self, template_service, mock_template_repo):
        """テンプレート更新のアクセス拒否テスト"""
        # Given
        template_dto = PromptTemplateDto(
            id=1, uuid="test-uuid", name="Template", 
            template_content="Content", user_id=999,  # 異なるユーザー
            is_public=True, is_favorite=False, usage_count=0,
            created_at=datetime.utcnow(), updated_at=datetime.utcnow()
        )
        mock_template_repo.get_template_by_uuid.return_value = template_dto
        
        # When & Then
        with pytest.raises(TemplateAccessDeniedError, match="Only template owner can update"):
            await template_service.update_template("test-uuid", user_id=1, name="New Name")

    # === テンプレート削除テスト ===
    
    @pytest.mark.asyncio
    async def test_delete_template_success(self, template_service, mock_template_repo, sample_template_dto):
        """テンプレート削除成功テスト"""
        # Given
        template_uuid = sample_template_dto.uuid
        mock_template_repo.get_template_by_uuid.return_value = sample_template_dto
        
        # When
        await template_service.delete_template(template_uuid, user_id=1)
        
        # Then
        mock_template_repo.delete_template.assert_called_once_with(template_uuid)
    
    @pytest.mark.asyncio
    async def test_delete_template_access_denied(self, template_service, mock_template_repo):
        """テンプレート削除のアクセス拒否テスト"""
        # Given
        template_dto = PromptTemplateDto(
            id=1, uuid="test-uuid", name="Template", 
            template_content="Content", user_id=999,  # 異なるユーザー
            is_public=False, is_favorite=False, usage_count=0,
            created_at=datetime.utcnow(), updated_at=datetime.utcnow()
        )
        mock_template_repo.get_template_by_uuid.return_value = template_dto
        
        # When & Then
        with pytest.raises(TemplateAccessDeniedError, match="Only template owner can delete"):
            await template_service.delete_template("test-uuid", user_id=1)

    # === テンプレート検索テスト ===
    
    @pytest.mark.asyncio
    async def test_search_templates_success(self, template_service, mock_template_repo):
        """テンプレート検索成功テスト"""
        # Given
        templates = [
            PromptTemplateDto(
                id=1, uuid="uuid1", name="Template 1", template_content="Content 1",
                user_id=1, category="greeting", is_public=False, is_favorite=True,
                usage_count=5, created_at=datetime.utcnow(), updated_at=datetime.utcnow()
            ),
            PromptTemplateDto(
                id=2, uuid="uuid2", name="Template 2", template_content="Content 2",
                user_id=1, category="farewell", is_public=True, is_favorite=False,
                usage_count=3, created_at=datetime.utcnow(), updated_at=datetime.utcnow()
            )
        ]
        mock_template_repo.search_templates.return_value = (templates, 2)
        
        # When
        result_templates, total_count = await template_service.search_templates(
            user_id=1,
            category="greeting",
            is_favorite=True,
            search_query="Template",
            offset=0,
            limit=10
        )
        
        # Then
        assert len(result_templates) == 2
        assert total_count == 2
        assert result_templates[0].name == "Template 1"
        assert result_templates[1].name == "Template 2"
        
        # 検索条件が正しく渡されたか確認
        mock_template_repo.search_templates.assert_called_once()
        call_args = mock_template_repo.search_templates.call_args[0][0]
        assert isinstance(call_args, TemplateSearchCriteria)
        assert call_args.user_id == 1
        assert call_args.category == "greeting"
        assert call_args.is_favorite == True
        assert call_args.search_query == "Template"

    # === テンプレート使用テスト ===
    
    @pytest.mark.asyncio
    async def test_use_template_success(self, template_service, mock_template_repo, sample_template_dto):
        """テンプレート使用成功テスト"""
        # Given
        template_uuid = sample_template_dto.uuid
        mock_template_repo.get_template_by_uuid.return_value = sample_template_dto
        
        # When
        await template_service.use_template(template_uuid, user_id=1)
        
        # Then
        mock_template_repo.increment_usage.assert_called_once_with(template_uuid)
    
    @pytest.mark.asyncio
    async def test_use_template_access_denied(self, template_service, mock_template_repo):
        """プライベートテンプレートの使用アクセス拒否テスト"""
        # Given
        template_dto = PromptTemplateDto(
            id=1, uuid="test-uuid", name="Private Template", 
            template_content="Content", user_id=999,  # 異なるユーザー
            is_public=False,  # プライベート
            is_favorite=False, usage_count=0,
            created_at=datetime.utcnow(), updated_at=datetime.utcnow()
        )
        mock_template_repo.get_template_by_uuid.return_value = template_dto
        
        # When & Then
        with pytest.raises(TemplateAccessDeniedError, match="Access denied"):
            await template_service.use_template("test-uuid", user_id=1)

    # === お気に入り機能テスト ===
    
    @pytest.mark.asyncio
    async def test_toggle_favorite_success(self, template_service, mock_template_repo, sample_template_dto):
        """お気に入り切り替え成功テスト"""
        # Given
        template_uuid = sample_template_dto.uuid
        mock_template_repo.get_template_by_uuid.return_value = sample_template_dto
        
        updated_dto = PromptTemplateDto(
            **{**sample_template_dto.__dict__, 'is_favorite': True}
        )
        mock_template_repo.toggle_favorite.return_value = updated_dto
        
        # When
        result = await template_service.toggle_favorite(template_uuid, user_id=1)
        
        # Then
        assert result.is_favorite == True
        mock_template_repo.toggle_favorite.assert_called_once_with(template_uuid)

    # === カテゴリ取得テスト ===
    
    @pytest.mark.asyncio
    async def test_get_categories_success(self, template_service, mock_template_repo):
        """カテゴリ一覧取得成功テスト"""
        # Given
        categories = ["greeting", "farewell", "business", "casual"]
        mock_template_repo.get_categories.return_value = categories
        
        # When
        result = await template_service.get_categories(user_id=1)
        
        # Then
        assert result == categories
        mock_template_repo.get_categories.assert_called_once_with(user_id=1)


class TestPresetServiceComprehensive:
    """PresetServiceの包括的テスト"""
    
    @pytest.fixture
    def mock_preset_repo(self):
        """モックプリセットリポジトリ"""
        return AsyncMock()
    
    @pytest.fixture
    def preset_service(self, mock_preset_repo):
        """PresetServiceインスタンス"""
        return PresetService(mock_preset_repo)
    
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

    # === プリセット作成テスト ===
    
    @pytest.mark.asyncio
    async def test_create_preset_success(self, preset_service, mock_preset_repo, sample_preset_dto):
        """プリセット作成成功テスト"""
        # Given
        mock_preset_repo.create_preset.return_value = sample_preset_dto
        
        # When
        result = await preset_service.create_preset(
            name="Test Preset",
            model_id="gpt-3.5-turbo",
            user_id=1,
            description="Test preset",
            temperature="0.7",
            max_tokens=1000,
            system_prompt="You are a helpful assistant"
        )
        
        # Then
        assert result.name == "Test Preset"
        assert result.model_id == "gpt-3.5-turbo"
        assert result.user_id == 1
        assert result.temperature == "0.7"
        assert result.max_tokens == 1000
        assert result.system_prompt == "You are a helpful assistant"
    
    @pytest.mark.asyncio
    async def test_create_preset_validation_errors(self, preset_service):
        """プリセット作成のバリデーションエラーテスト"""
        # 名前が空
        with pytest.raises(PresetValidationError, match="Preset name cannot be empty"):
            await preset_service.create_preset("", "gpt-3.5-turbo", 1)
        
        # モデルIDが空
        with pytest.raises(PresetValidationError, match="Model ID cannot be empty"):
            await preset_service.create_preset("name", "", 1)
        
        # ユーザーIDが無効
        with pytest.raises(PresetValidationError, match="User ID must be positive"):
            await preset_service.create_preset("name", "gpt-3.5-turbo", 0)
        
        # 無効な温度値
        with pytest.raises(PresetValidationError, match="Temperature must be between 0.0 and 2.0"):
            await preset_service.create_preset("name", "gpt-3.5-turbo", 1, temperature="3.0")
        
        with pytest.raises(PresetValidationError, match="Temperature must be between 0.0 and 2.0"):
            await preset_service.create_preset("name", "gpt-3.5-turbo", 1, temperature="-1.0")
        
        # 無効なmax_tokens値
        with pytest.raises(PresetValidationError, match="Max tokens must be positive"):
            await preset_service.create_preset("name", "gpt-3.5-turbo", 1, max_tokens=0)
        
        with pytest.raises(PresetValidationError, match="Max tokens must be positive"):
            await preset_service.create_preset("name", "gpt-3.5-turbo", 1, max_tokens=-100)

    # === プリセット取得テスト ===
    
    @pytest.mark.asyncio
    async def test_get_preset_success(self, preset_service, mock_preset_repo, sample_preset_dto):
        """プリセット取得成功テスト"""
        # Given
        preset_uuid = sample_preset_dto.uuid
        mock_preset_repo.get_preset_by_uuid.return_value = sample_preset_dto
        
        # When
        result = await preset_service.get_preset(preset_uuid, user_id=1)
        
        # Then
        assert result.uuid == preset_uuid
        assert result.name == "Test Preset"
    
    @pytest.mark.asyncio
    async def test_get_preset_not_found(self, preset_service, mock_preset_repo):
        """プリセットが見つからない場合のテスト"""
        # Given
        mock_preset_repo.get_preset_by_uuid.return_value = None
        
        # When & Then
        with pytest.raises(PresetNotFoundError, match="Preset not found"):
            await preset_service.get_preset("non-existent-uuid", user_id=1)
    
    @pytest.mark.asyncio
    async def test_get_preset_access_denied(self, preset_service, mock_preset_repo):
        """プリセットアクセス拒否テスト"""
        # Given
        preset_dto = ConversationPresetDto(
            id=1, uuid="test-uuid", name="Preset", model_id="gpt-3.5-turbo",
            user_id=999,  # 異なるユーザー
            temperature="0.7", max_tokens=1000, is_favorite=False, usage_count=0,
            created_at=datetime.utcnow(), updated_at=datetime.utcnow()
        )
        mock_preset_repo.get_preset_by_uuid.return_value = preset_dto
        
        # When & Then
        with pytest.raises(PresetAccessDeniedError, match="Access denied"):
            await preset_service.get_preset("test-uuid", user_id=1)

    # === プリセット検索テスト ===
    
    @pytest.mark.asyncio
    async def test_search_presets_success(self, preset_service, mock_preset_repo):
        """プリセット検索成功テスト"""
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
        mock_preset_repo.search_presets.return_value = (presets, 2)
        
        # When
        result_presets, total_count = await preset_service.search_presets(
            user_id=1,
            model_id="gpt-3.5-turbo",
            is_favorite=True,
            search_query="Preset",
            offset=0,
            limit=10
        )
        
        # Then
        assert len(result_presets) == 2
        assert total_count == 2
        assert result_presets[0].name == "Preset 1"

    # === プリセット使用テスト ===
    
    @pytest.mark.asyncio
    async def test_use_preset_success(self, preset_service, mock_preset_repo, sample_preset_dto):
        """プリセット使用成功テスト"""
        # Given
        preset_uuid = sample_preset_dto.uuid
        mock_preset_repo.get_preset_by_uuid.return_value = sample_preset_dto
        
        # When
        await preset_service.use_preset(preset_uuid, user_id=1)
        
        # Then
        mock_preset_repo.increment_usage.assert_called_once_with(preset_uuid)

    # === プリセット更新・削除テスト ===
    
    @pytest.mark.asyncio
    async def test_update_preset_success(self, preset_service, mock_preset_repo, sample_preset_dto):
        """プリセット更新成功テスト"""
        # Given
        preset_uuid = sample_preset_dto.uuid
        mock_preset_repo.get_preset_by_uuid.return_value = sample_preset_dto
        
        updated_dto = ConversationPresetDto(
            **{**sample_preset_dto.__dict__, 'name': 'Updated Preset'}
        )
        mock_preset_repo.update_preset.return_value = updated_dto
        
        # When
        result = await preset_service.update_preset(
            preset_uuid=preset_uuid,
            user_id=1,
            name="Updated Preset"
        )
        
        # Then
        assert result.name == "Updated Preset"
    
    @pytest.mark.asyncio
    async def test_delete_preset_success(self, preset_service, mock_preset_repo, sample_preset_dto):
        """プリセット削除成功テスト"""
        # Given
        preset_uuid = sample_preset_dto.uuid
        mock_preset_repo.get_preset_by_uuid.return_value = sample_preset_dto
        
        # When
        await preset_service.delete_preset(preset_uuid, user_id=1)
        
        # Then
        mock_preset_repo.delete_preset.assert_called_once_with(preset_uuid)