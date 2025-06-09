"""
Simple Template Service Tests

実際の実装に合わせたシンプルなテンプレートサービステスト
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


class TestTemplateServiceSimple:
    """実装済みTemplateServiceのシンプルテスト"""
    
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
            created_at=datetime.now(),
            updated_at=datetime.now()
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
        assert isinstance(result, PromptTemplate)
        assert result.name == "Test Template"
        assert result.template_content == "Hello {name}!"
        assert result.user_id == 1
        assert result.description == "Test description"
        assert result.category == "greeting"
        assert result.variables == {"name": "string"}
        
        # リポジトリが正しく呼ばれたか確認
        mock_template_repo.create_template.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_create_template_validation_errors(self, template_service):
        """テンプレート作成のバリデーションエラーテスト"""
        # 名前が空
        with pytest.raises(TemplateValidationError, match="Template name cannot be empty"):
            await template_service.create_template("", "content", 1)
        
        # 名前が空白のみ
        with pytest.raises(TemplateValidationError, match="Template name cannot be empty"):
            await template_service.create_template("   ", "content", 1)
        
        # コンテンツが空
        with pytest.raises(TemplateValidationError, match="Template content cannot be empty"):
            await template_service.create_template("name", "", 1)
        
        # コンテンツが空白のみ
        with pytest.raises(TemplateValidationError, match="Template content cannot be empty"):
            await template_service.create_template("name", "   ", 1)

    # === テンプレート取得テスト ===
    
    @pytest.mark.asyncio
    async def test_get_template_by_id_success(self, template_service, mock_template_repo, sample_template_dto):
        """ID によるテンプレート取得成功テスト"""
        # Given
        template_id = 1
        mock_template_repo.get_template_by_id.return_value = sample_template_dto
        
        # When
        result = await template_service.get_template(template_id, user_id=1)
        
        # Then
        assert isinstance(result, PromptTemplate)
        assert result.name == "Test Template"
        mock_template_repo.get_template_by_id.assert_called_once_with(template_id)
    
    @pytest.mark.asyncio
    async def test_get_template_by_uuid_success(self, template_service, mock_template_repo, sample_template_dto):
        """UUID によるテンプレート取得成功テスト"""
        # Given
        template_uuid = sample_template_dto.uuid
        mock_template_repo.get_template_by_uuid.return_value = sample_template_dto
        
        # When
        result = await template_service.get_template_by_uuid(template_uuid, user_id=1)
        
        # Then
        assert isinstance(result, PromptTemplate)
        assert result.uuid == template_uuid
        mock_template_repo.get_template_by_uuid.assert_called_once_with(template_uuid)
    
    @pytest.mark.asyncio
    async def test_get_template_not_found(self, template_service, mock_template_repo):
        """テンプレートが見つからない場合のテスト"""
        # Given
        template_id = 999
        mock_template_repo.get_template_by_id.return_value = None
        
        # When & Then
        with pytest.raises(TemplateNotFoundError):
            await template_service.get_template(template_id, user_id=1)
    
    @pytest.mark.asyncio
    async def test_get_template_access_denied(self, template_service, mock_template_repo):
        """アクセス権限がない場合のテスト"""
        # Given - 他のユーザーのプライベートテンプレート
        template_dto = PromptTemplateDto(
            id=1, uuid="test-uuid", name="Private Template", 
            template_content="Content", user_id=999,  # 異なるユーザー
            is_public=False,  # プライベート
            is_favorite=False, usage_count=0,
            created_at=datetime.now(), updated_at=datetime.now()
        )
        mock_template_repo.get_template_by_id.return_value = template_dto
        
        # When & Then
        with pytest.raises(TemplateAccessDeniedError):
            await template_service.get_template(1, user_id=1)
    
    @pytest.mark.asyncio
    async def test_get_public_template_access_allowed(self, template_service, mock_template_repo):
        """公開テンプレートへのアクセス許可テスト"""
        # Given - 他のユーザーの公開テンプレート
        template_dto = PromptTemplateDto(
            id=1, uuid="test-uuid", name="Public Template", 
            template_content="Content", user_id=999,  # 異なるユーザー
            is_public=True,  # 公開
            is_favorite=False, usage_count=0,
            created_at=datetime.now(), updated_at=datetime.now()
        )
        mock_template_repo.get_template_by_id.return_value = template_dto
        
        # When
        result = await template_service.get_template(1, user_id=1)
        
        # Then
        assert result.name == "Public Template"
        assert result.is_public == True

    # === テンプレート削除テスト ===
    
    @pytest.mark.asyncio
    async def test_delete_template_success(self, template_service, mock_template_repo, sample_template_dto):
        """テンプレート削除成功テスト"""
        # Given
        template_id = 1
        mock_template_repo.get_template_by_id.return_value = sample_template_dto
        mock_template_repo.delete_template.return_value = True
        
        # When
        result = await template_service.delete_template(template_id, user_id=1)
        
        # Then
        assert result == True
        mock_template_repo.delete_template.assert_called_once_with(template_id)
    
    @pytest.mark.asyncio
    async def test_delete_template_access_denied(self, template_service, mock_template_repo):
        """テンプレート削除のアクセス拒否テスト"""
        # Given - 他のユーザーのテンプレート
        template_dto = PromptTemplateDto(
            id=1, uuid="test-uuid", name="Template", 
            template_content="Content", user_id=999,  # 異なるユーザー
            is_public=False, is_favorite=False, usage_count=0,
            created_at=datetime.now(), updated_at=datetime.now()
        )
        mock_template_repo.get_template_by_id.return_value = template_dto
        
        # When & Then
        with pytest.raises(TemplateAccessDeniedError):
            await template_service.delete_template(1, user_id=1)

    # === テンプレート検索テスト ===
    
    @pytest.mark.asyncio
    async def test_search_templates_success(self, template_service, mock_template_repo):
        """テンプレート検索成功テスト"""
        # Given
        template_dtos = [
            PromptTemplateDto(
                id=1, uuid="uuid1", name="Template 1", template_content="Content 1",
                user_id=1, category="greeting", is_public=False, is_favorite=True,
                usage_count=5, created_at=datetime.now(), updated_at=datetime.now()
            ),
            PromptTemplateDto(
                id=2, uuid="uuid2", name="Template 2", template_content="Content 2",
                user_id=1, category="farewell", is_public=True, is_favorite=False,
                usage_count=3, created_at=datetime.now(), updated_at=datetime.now()
            )
        ]
        mock_template_repo.search_templates.return_value = template_dtos
        
        # When
        result = await template_service.search_templates(
            user_id=1,
            category="greeting",
            search_text="Template"
        )
        
        # Then
        assert len(result) == 2
        assert all(isinstance(template, PromptTemplate) for template in result)
        assert result[0].name == "Template 1"
        assert result[1].name == "Template 2"

    # === テンプレート使用テスト ===
    
    @pytest.mark.asyncio
    async def test_use_template_success(self, template_service, mock_template_repo, sample_template_dto):
        """テンプレート使用成功テスト"""
        # Given
        template_id = 1
        mock_template_repo.get_template_by_id.return_value = sample_template_dto
        mock_template_repo.increment_template_usage.return_value = None
        
        # When
        result = await template_service.use_template(template_id, user_id=1)
        
        # Then
        assert isinstance(result, PromptTemplate)
        assert result.usage_count == sample_template_dto.usage_count + 1  # エンティティで増加
        mock_template_repo.increment_template_usage.assert_called_once_with(template_id)

    # === お気に入り機能テスト ===
    
    @pytest.mark.asyncio
    async def test_toggle_favorite_success(self, template_service, mock_template_repo, sample_template_dto):
        """お気に入り切り替え成功テスト"""
        # Given
        template_id = 1
        mock_template_repo.get_template_by_id.return_value = sample_template_dto
        
        # お気に入り状態を変更したDTOを返すモック
        favorited_dto = PromptTemplateDto(
            **{k: v for k, v in sample_template_dto.__dict__.items() if k != 'is_favorite'},
            is_favorite=True
        )
        mock_template_repo.update_template.return_value = favorited_dto
        
        # When
        result = await template_service.toggle_favorite(template_id, user_id=1)
        
        # Then
        assert isinstance(result, PromptTemplate)
        assert result.is_favorite == True
        mock_template_repo.update_template.assert_called_once()


class TestPresetServiceSimple:
    """実装済みPresetServiceのシンプルテスト"""
    
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
            created_at=datetime.now(),
            updated_at=datetime.now()
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
        assert isinstance(result, ConversationPreset)
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

    # === プリセット取得テスト ===
    
    @pytest.mark.asyncio
    async def test_get_preset_by_id_success(self, preset_service, mock_preset_repo, sample_preset_dto):
        """ID によるプリセット取得成功テスト"""
        # Given
        preset_id = 1
        mock_preset_repo.get_preset_by_id.return_value = sample_preset_dto
        
        # When
        result = await preset_service.get_preset(preset_id, user_id=1)
        
        # Then
        assert isinstance(result, ConversationPreset)
        assert result.name == "Test Preset"
        mock_preset_repo.get_preset_by_id.assert_called_once_with(preset_id)
    
    @pytest.mark.asyncio
    async def test_get_preset_by_uuid_success(self, preset_service, mock_preset_repo, sample_preset_dto):
        """UUID によるプリセット取得成功テスト"""
        # Given
        preset_uuid = sample_preset_dto.uuid
        mock_preset_repo.get_preset_by_uuid.return_value = sample_preset_dto
        
        # When
        result = await preset_service.get_preset_by_uuid(preset_uuid, user_id=1)
        
        # Then
        assert isinstance(result, ConversationPreset)
        assert result.uuid == preset_uuid
        mock_preset_repo.get_preset_by_uuid.assert_called_once_with(preset_uuid)
    
    @pytest.mark.asyncio
    async def test_get_preset_not_found(self, preset_service, mock_preset_repo):
        """プリセットが見つからない場合のテスト"""
        # Given
        mock_preset_repo.get_preset_by_id.return_value = None
        
        # When & Then
        with pytest.raises(PresetNotFoundError):
            await preset_service.get_preset(999, user_id=1)
    
    @pytest.mark.asyncio
    async def test_get_preset_access_denied(self, preset_service, mock_preset_repo):
        """プリセットアクセス拒否テスト"""
        # Given - 他のユーザーのプリセット
        preset_dto = ConversationPresetDto(
            id=1, uuid="test-uuid", name="Preset", model_id="gpt-3.5-turbo",
            user_id=999,  # 異なるユーザー
            temperature="0.7", max_tokens=1000, is_favorite=False, usage_count=0,
            created_at=datetime.now(), updated_at=datetime.now()
        )
        mock_preset_repo.get_preset_by_id.return_value = preset_dto
        
        # When & Then
        with pytest.raises(PresetAccessDeniedError):
            await preset_service.get_preset(1, user_id=1)

    # === プリセット削除テスト ===
    
    @pytest.mark.asyncio
    async def test_delete_preset_success(self, preset_service, mock_preset_repo, sample_preset_dto):
        """プリセット削除成功テスト"""
        # Given
        preset_id = 1
        mock_preset_repo.get_preset_by_id.return_value = sample_preset_dto
        mock_preset_repo.delete_preset.return_value = True
        
        # When
        result = await preset_service.delete_preset(preset_id, user_id=1)
        
        # Then
        assert result == True
        mock_preset_repo.delete_preset.assert_called_once_with(preset_id)

    # === プリセット使用テスト ===
    
    @pytest.mark.asyncio
    async def test_use_preset_success(self, preset_service, mock_preset_repo, sample_preset_dto):
        """プリセット使用成功テスト"""
        # Given
        preset_id = 1
        mock_preset_repo.get_preset_by_id.return_value = sample_preset_dto
        mock_preset_repo.increment_preset_usage.return_value = None
        
        # When
        result = await preset_service.use_preset(preset_id, user_id=1)
        
        # Then
        assert isinstance(result, ConversationPreset)
        assert result.usage_count == sample_preset_dto.usage_count + 1
        mock_preset_repo.increment_preset_usage.assert_called_once_with(preset_id)

    # === プリセット検索テスト ===
    
    @pytest.mark.asyncio
    async def test_search_presets_success(self, preset_service, mock_preset_repo):
        """プリセット検索成功テスト"""
        # Given
        preset_dtos = [
            ConversationPresetDto(
                id=1, uuid="uuid1", name="Preset 1", model_id="gpt-3.5-turbo",
                user_id=1, temperature="0.7", max_tokens=1000, is_favorite=True,
                usage_count=5, created_at=datetime.now(), updated_at=datetime.now()
            ),
            ConversationPresetDto(
                id=2, uuid="uuid2", name="Preset 2", model_id="gpt-4",
                user_id=1, temperature="0.8", max_tokens=2000, is_favorite=False,
                usage_count=3, created_at=datetime.now(), updated_at=datetime.now()
            )
        ]
        mock_preset_repo.search_presets.return_value = preset_dtos
        
        # When
        result = await preset_service.search_presets(
            user_id=1,
            model_id="gpt-3.5-turbo",
            search_text="Preset"
        )
        
        # Then
        assert len(result) == 2
        assert all(isinstance(preset, ConversationPreset) for preset in result)
        assert result[0].name == "Preset 1"