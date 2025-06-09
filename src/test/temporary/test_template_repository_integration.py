"""
Template Repository Integration Tests

テンプレートリポジトリの統合テスト
Tortoise ORMを使用した実際のデータベース操作をテスト
"""

import pytest
import sys
import os
import asyncio
from datetime import datetime
from typing import List
import uuid

# Add path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from tortoise import Tortoise
from tortoise.contrib.test import TestCase
from src.infra.tortoise_client.models import PromptTemplate as PromptTemplateModel, ConversationPreset as ConversationPresetModel, User
from src.infra.tortoise_client.template_repository_adapter import TortoiseTemplateRepositoryAdapter, TortoisePresetRepositoryAdapter
from src.domain.entity.template_entity import PromptTemplate, ConversationPreset
from src.port.dto.template_dto import TemplateSearchCriteria, PresetSearchCriteria


class TestTemplateRepositoryIntegration(TestCase):
    """テンプレートリポジトリ統合テスト"""
    
    async def asyncSetUp(self):
        """テストセットアップ"""
        await super().asyncSetUp()
        self.template_repo = TortoiseTemplateRepositoryAdapter()
        
        # テスト用ユーザー作成
        self.test_user = await User.create(
            username="testuser",
            email="test@example.com",
            hashed_password="hashedpassword"
        )
        self.test_user_id = self.test_user.id
        
        # 別のユーザーも作成（アクセス権限テスト用）
        self.other_user = await User.create(
            username="otheruser", 
            email="other@example.com",
            hashed_password="hashedpassword"
        )
        self.other_user_id = self.other_user.id

    # === テンプレート作成テスト ===
    
    async def test_create_template_success(self):
        """テンプレート作成成功テスト"""
        # Given
        template_entity = PromptTemplate(
            name="Integration Test Template",
            template_content="Hello {name}! Welcome to {place}.",
            user_id=self.test_user_id,
            description="Integration test template",
            category="greeting",
            variables={"name": "string", "place": "string"}
        )
        
        # When
        result = await self.template_repo.create_template(template_entity)
        
        # Then
        assert result is not None
        assert result.name == "Integration Test Template"
        assert result.template_content == "Hello {name}! Welcome to {place}."
        assert result.user_id == self.test_user_id
        assert result.description == "Integration test template"
        assert result.category == "greeting"
        assert result.variables == {"name": "string", "place": "string"}
        assert result.uuid is not None
        assert not result.is_public
        assert not result.is_favorite
        assert result.usage_count == 0
        
        # DBに実際に保存されているか確認
        db_template = await PromptTemplateModel.get(uuid=result.uuid)
        assert db_template.name == "Integration Test Template"
        assert db_template.user_id == self.test_user_id
    
    async def test_create_template_minimal_data(self):
        """最小データでのテンプレート作成テスト"""
        # Given
        template_entity = PromptTemplate(
            name="Minimal Template",
            template_content="Simple content",
            user_id=self.test_user_id
        )
        
        # When
        result = await self.template_repo.create_template(template_entity)
        
        # Then
        assert result.name == "Minimal Template"
        assert result.template_content == "Simple content"
        assert result.description is None
        assert result.category is None
        assert result.variables is None

    # === テンプレート取得テスト ===
    
    async def test_get_template_by_uuid_success(self):
        """UUID によるテンプレート取得成功テスト"""
        # Given - DBに直接テンプレートを作成
        db_template = await PromptTemplateModel.create(
            uuid=str(uuid.uuid4()),
            name="DB Test Template",
            template_content="DB content",
            user_id=self.test_user_id,
            category="test",
            variables='{"param": "string"}',
            is_public=False,
            is_favorite=True,
            usage_count=5
        )
        
        # When
        result = await self.template_repo.get_template_by_uuid(db_template.uuid)
        
        # Then
        assert result is not None
        assert result.uuid == db_template.uuid
        assert result.name == "DB Test Template"
        assert result.template_content == "DB content"
        assert result.user_id == self.test_user_id
        assert result.category == "test"
        assert result.variables == {"param": "string"}
        assert not result.is_public
        assert result.is_favorite
        assert result.usage_count == 5
    
    async def test_get_template_by_uuid_not_found(self):
        """存在しないUUIDでの取得テスト"""
        # When
        result = await self.template_repo.get_template_by_uuid("non-existent-uuid")
        
        # Then
        assert result is None

    # === テンプレート更新テスト ===
    
    async def test_update_template_success(self):
        """テンプレート更新成功テスト"""
        # Given - 既存テンプレート作成
        template_entity = PromptTemplate(
            name="Original Template",
            template_content="Original content",
            user_id=self.test_user_id
        )
        created = await self.template_repo.create_template(template_entity)
        
        # When - 更新
        updated_entity = PromptTemplate(
            name="Updated Template",
            template_content="Updated content",
            user_id=self.test_user_id,
            uuid=created.uuid,
            description="Updated description",
            category="updated"
        )
        result = await self.template_repo.update_template(created.uuid, updated_entity)
        
        # Then
        assert result.name == "Updated Template"
        assert result.template_content == "Updated content"
        assert result.description == "Updated description"
        assert result.category == "updated"
        assert result.uuid == created.uuid  # UUIDは変わらない
        
        # DBからも確認
        db_template = await PromptTemplateModel.get(uuid=created.uuid)
        assert db_template.name == "Updated Template"

    # === テンプレート削除テスト ===
    
    async def test_delete_template_success(self):
        """テンプレート削除成功テスト"""
        # Given
        template_entity = PromptTemplate(
            name="To Delete Template",
            template_content="Content to delete",
            user_id=self.test_user_id
        )
        created = await self.template_repo.create_template(template_entity)
        
        # When
        await self.template_repo.delete_template(created.uuid)
        
        # Then - テンプレートが削除されていることを確認
        deleted_template = await PromptTemplateModel.filter(uuid=created.uuid).first()
        assert deleted_template is None
        
        # リポジトリからも取得できないことを確認
        result = await self.template_repo.get_template_by_uuid(created.uuid)
        assert result is None

    # === テンプレート検索テスト ===
    
    async def test_search_templates_by_user(self):
        """ユーザー別テンプレート検索テスト"""
        # Given - 複数のテンプレートを作成
        template1 = await self.template_repo.create_template(PromptTemplate(
            name="User1 Template 1", template_content="Content 1", user_id=self.test_user_id,
            category="greeting", is_favorite=True
        ))
        template2 = await self.template_repo.create_template(PromptTemplate(
            name="User1 Template 2", template_content="Content 2", user_id=self.test_user_id,
            category="farewell"
        ))
        # 他のユーザーのテンプレート
        await self.template_repo.create_template(PromptTemplate(
            name="User2 Template", template_content="Content", user_id=self.other_user_id
        ))
        
        # When
        criteria = TemplateSearchCriteria(user_id=self.test_user_id)
        templates, total = await self.template_repo.search_templates(criteria)
        
        # Then
        assert total == 2
        assert len(templates) == 2
        template_names = [t.name for t in templates]
        assert "User1 Template 1" in template_names
        assert "User1 Template 2" in template_names
        assert "User2 Template" not in template_names
    
    async def test_search_templates_with_filters(self):
        """フィルター付きテンプレート検索テスト"""
        # Given - 様々な条件のテンプレートを作成
        await self.template_repo.create_template(PromptTemplate(
            name="Greeting Favorite", template_content="Hello content", user_id=self.test_user_id,
            category="greeting", is_favorite=True
        ))
        await self.template_repo.create_template(PromptTemplate(
            name="Greeting Normal", template_content="Hi content", user_id=self.test_user_id,
            category="greeting", is_favorite=False
        ))
        await self.template_repo.create_template(PromptTemplate(
            name="Farewell Favorite", template_content="Bye content", user_id=self.test_user_id,
            category="farewell", is_favorite=True
        ))
        
        # When - カテゴリとお気に入りで絞り込み
        criteria = TemplateSearchCriteria(
            user_id=self.test_user_id,
            category="greeting",
            is_favorite=True
        )
        templates, total = await self.template_repo.search_templates(criteria)
        
        # Then
        assert total == 1
        assert len(templates) == 1
        assert templates[0].name == "Greeting Favorite"
        assert templates[0].category == "greeting"
        assert templates[0].is_favorite == True
    
    async def test_search_templates_with_text_search(self):
        """テキスト検索テスト"""
        # Given
        await self.template_repo.create_template(PromptTemplate(
            name="Customer Support Template", template_content="Help customer with issue", 
            user_id=self.test_user_id
        ))
        await self.template_repo.create_template(PromptTemplate(
            name="Sales Template", template_content="Sell product to customer", 
            user_id=self.test_user_id
        ))
        await self.template_repo.create_template(PromptTemplate(
            name="Meeting Template", template_content="Schedule a meeting", 
            user_id=self.test_user_id
        ))
        
        # When - "customer"で検索
        criteria = TemplateSearchCriteria(
            user_id=self.test_user_id,
            search_query="customer"
        )
        templates, total = await self.template_repo.search_templates(criteria)
        
        # Then
        assert total == 2
        template_names = [t.name for t in templates]
        assert "Customer Support Template" in template_names
        assert "Sales Template" in template_names
        assert "Meeting Template" not in template_names
    
    async def test_search_templates_pagination(self):
        """ページネーションテスト"""
        # Given - 5つのテンプレートを作成
        for i in range(5):
            await self.template_repo.create_template(PromptTemplate(
                name=f"Template {i+1}", template_content=f"Content {i+1}", 
                user_id=self.test_user_id
            ))
        
        # When - 最初の2件を取得
        criteria = TemplateSearchCriteria(
            user_id=self.test_user_id,
            offset=0,
            limit=2
        )
        templates, total = await self.template_repo.search_templates(criteria)
        
        # Then
        assert total == 5
        assert len(templates) == 2
        
        # When - 次の2件を取得
        criteria.offset = 2
        templates, total = await self.template_repo.search_templates(criteria)
        
        # Then
        assert total == 5
        assert len(templates) == 2

    # === 使用回数増加テスト ===
    
    async def test_increment_usage_success(self):
        """使用回数増加成功テスト"""
        # Given
        template_entity = PromptTemplate(
            name="Usage Test Template",
            template_content="Content",
            user_id=self.test_user_id
        )
        created = await self.template_repo.create_template(template_entity)
        initial_usage = created.usage_count
        
        # When
        await self.template_repo.increment_usage(created.uuid)
        
        # Then
        updated_template = await self.template_repo.get_template_by_uuid(created.uuid)
        assert updated_template.usage_count == initial_usage + 1
        
        # もう一度増加
        await self.template_repo.increment_usage(created.uuid)
        updated_template = await self.template_repo.get_template_by_uuid(created.uuid)
        assert updated_template.usage_count == initial_usage + 2

    # === お気に入り切り替えテスト ===
    
    async def test_toggle_favorite_success(self):
        """お気に入り切り替え成功テスト"""
        # Given
        template_entity = PromptTemplate(
            name="Favorite Test Template",
            template_content="Content",
            user_id=self.test_user_id
        )
        created = await self.template_repo.create_template(template_entity)
        assert not created.is_favorite
        
        # When - お気に入りにする
        result = await self.template_repo.toggle_favorite(created.uuid)
        
        # Then
        assert result.is_favorite == True
        
        # When - お気に入りを解除
        result = await self.template_repo.toggle_favorite(created.uuid)
        
        # Then
        assert result.is_favorite == False

    # === カテゴリ取得テスト ===
    
    async def test_get_categories_success(self):
        """カテゴリ一覧取得成功テスト"""
        # Given - 様々なカテゴリのテンプレートを作成
        categories_to_create = ["greeting", "farewell", "business", "greeting", "casual"]
        for category in categories_to_create:
            await self.template_repo.create_template(PromptTemplate(
                name=f"Template for {category}",
                template_content="Content",
                user_id=self.test_user_id,
                category=category
            ))
        
        # 他のユーザーのカテゴリ（除外されるべき）
        await self.template_repo.create_template(PromptTemplate(
            name="Other user template",
            template_content="Content",
            user_id=self.other_user_id,
            category="other_category"
        ))
        
        # When
        categories = await self.template_repo.get_categories(self.test_user_id)
        
        # Then
        assert len(categories) == 4  # 重複除去されている
        assert "greeting" in categories
        assert "farewell" in categories
        assert "business" in categories
        assert "casual" in categories
        assert "other_category" not in categories


class TestPresetRepositoryIntegration(TestCase):
    """プリセットリポジトリ統合テスト"""
    
    async def asyncSetUp(self):
        """テストセットアップ"""
        await super().asyncSetUp()
        self.preset_repo = TortoisePresetRepositoryAdapter()
        
        # テスト用ユーザー作成
        self.test_user = await User.create(
            username="testuser",
            email="test@example.com", 
            hashed_password="hashedpassword"
        )
        self.test_user_id = self.test_user.id

    # === プリセット作成テスト ===
    
    async def test_create_preset_success(self):
        """プリセット作成成功テスト"""
        # Given
        preset_entity = ConversationPreset(
            name="Integration Test Preset",
            model_id="gpt-3.5-turbo",
            user_id=self.test_user_id,
            description="Integration test preset",
            temperature="0.8",
            max_tokens=2000,
            system_prompt="You are a helpful integration test assistant"
        )
        
        # When
        result = await self.preset_repo.create_preset(preset_entity)
        
        # Then
        assert result is not None
        assert result.name == "Integration Test Preset"
        assert result.model_id == "gpt-3.5-turbo"
        assert result.user_id == self.test_user_id
        assert result.description == "Integration test preset"
        assert result.temperature == "0.8"
        assert result.max_tokens == 2000
        assert result.system_prompt == "You are a helpful integration test assistant"
        assert result.uuid is not None
        assert not result.is_favorite
        assert result.usage_count == 0
        
        # DBに実際に保存されているか確認
        db_preset = await ConversationPresetModel.get(uuid=result.uuid)
        assert db_preset.name == "Integration Test Preset"
        assert db_preset.user_id == self.test_user_id

    # === プリセット取得テスト ===
    
    async def test_get_preset_by_uuid_success(self):
        """UUID によるプリセット取得成功テスト"""
        # Given
        preset_entity = ConversationPreset(
            name="Get Test Preset",
            model_id="gpt-4",
            user_id=self.test_user_id,
            temperature="0.9",
            max_tokens=3000
        )
        created = await self.preset_repo.create_preset(preset_entity)
        
        # When
        result = await self.preset_repo.get_preset_by_uuid(created.uuid)
        
        # Then
        assert result is not None
        assert result.uuid == created.uuid
        assert result.name == "Get Test Preset"
        assert result.model_id == "gpt-4"
        assert result.temperature == "0.9"
        assert result.max_tokens == 3000

    # === プリセット検索テスト ===
    
    async def test_search_presets_by_model(self):
        """モデル別プリセット検索テスト"""
        # Given
        await self.preset_repo.create_preset(ConversationPreset(
            name="GPT-3.5 Preset", model_id="gpt-3.5-turbo", user_id=self.test_user_id
        ))
        await self.preset_repo.create_preset(ConversationPreset(
            name="GPT-4 Preset", model_id="gpt-4", user_id=self.test_user_id
        ))
        await self.preset_repo.create_preset(ConversationPreset(
            name="Another GPT-4 Preset", model_id="gpt-4", user_id=self.test_user_id
        ))
        
        # When
        criteria = PresetSearchCriteria(
            user_id=self.test_user_id,
            model_id="gpt-4"
        )
        presets, total = await self.preset_repo.search_presets(criteria)
        
        # Then
        assert total == 2
        assert len(presets) == 2
        for preset in presets:
            assert preset.model_id == "gpt-4"

    # === プリセット使用回数増加テスト ===
    
    async def test_increment_preset_usage_success(self):
        """プリセット使用回数増加成功テスト"""
        # Given
        preset_entity = ConversationPreset(
            name="Usage Test Preset",
            model_id="gpt-3.5-turbo",
            user_id=self.test_user_id
        )
        created = await self.preset_repo.create_preset(preset_entity)
        initial_usage = created.usage_count
        
        # When
        await self.preset_repo.increment_usage(created.uuid)
        
        # Then
        updated_preset = await self.preset_repo.get_preset_by_uuid(created.uuid)
        assert updated_preset.usage_count == initial_usage + 1