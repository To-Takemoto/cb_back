"""
Test for template implementation
"""
import pytest
from datetime import datetime
from src.domain.entity.template_entity import PromptTemplate, ConversationPreset
from src.domain.exception.template_exceptions import (
    TemplateValidationError, PresetValidationError
)
from src.port.dto.template_dto import PromptTemplateDto, ConversationPresetDto
from src.usecase.template_management.template_service import TemplateService, PresetService
from unittest.mock import AsyncMock, MagicMock


class TestPromptTemplateEntity:
    """Test PromptTemplate domain entity"""
    
    def test_create_template(self):
        """Test creating a new template"""
        template = PromptTemplate(
            name="Test Template",
            template_content="Hello {name}!",
            user_id=1,
            variables={"name": "string"}
        )
        
        assert template.name == "Test Template"
        assert template.template_content == "Hello {name}!"
        assert template.user_id == 1
        assert template.variables == {"name": "string"}
        assert not template.is_public
        assert not template.is_favorite
        assert template.usage_count == 0
    
    def test_increment_usage(self):
        """Test incrementing usage count"""
        template = PromptTemplate(
            name="Test",
            template_content="Content",
            user_id=1
        )
        
        initial_count = template.usage_count
        template.increment_usage()
        
        assert template.usage_count == initial_count + 1
    
    def test_toggle_favorite(self):
        """Test marking as favorite"""
        template = PromptTemplate(
            name="Test",
            template_content="Content",
            user_id=1
        )
        
        assert not template.is_favorite
        
        template.mark_as_favorite()
        assert template.is_favorite
        
        template.unmark_as_favorite()
        assert not template.is_favorite
    
    def test_toggle_public(self):
        """Test making public/private"""
        template = PromptTemplate(
            name="Test",
            template_content="Content",
            user_id=1
        )
        
        assert not template.is_public
        
        template.make_public()
        assert template.is_public
        
        template.make_private()
        assert not template.is_public


class TestConversationPresetEntity:
    """Test ConversationPreset domain entity"""
    
    def test_create_preset(self):
        """Test creating a new preset"""
        preset = ConversationPreset(
            name="Test Preset",
            model_id="gpt-3.5-turbo",
            user_id=1,
            temperature="0.8",
            max_tokens=2000
        )
        
        assert preset.name == "Test Preset"
        assert preset.model_id == "gpt-3.5-turbo"
        assert preset.user_id == 1
        assert preset.temperature == "0.8"
        assert preset.max_tokens == 2000
        assert not preset.is_favorite
        assert preset.usage_count == 0
    
    def test_update_model_settings(self):
        """Test updating model settings"""
        preset = ConversationPreset(
            name="Test",
            model_id="gpt-3.5-turbo",
            user_id=1
        )
        
        preset.update_model_settings(
            model_id="gpt-4",
            temperature="0.9",
            max_tokens=4000
        )
        
        assert preset.model_id == "gpt-4"
        assert preset.temperature == "0.9"
        assert preset.max_tokens == 4000


class TestTemplateService:
    """Test TemplateService use case"""
    
    @pytest.fixture
    def mock_template_repo(self):
        """Mock template repository"""
        repo = AsyncMock()
        return repo
    
    @pytest.fixture
    def template_service(self, mock_template_repo):
        """Template service with mocked repository"""
        return TemplateService(mock_template_repo)
    
    @pytest.mark.asyncio
    async def test_create_template_validation(self, template_service):
        """Test template creation validation"""
        # Test empty name
        with pytest.raises(TemplateValidationError, match="Template name cannot be empty"):
            await template_service.create_template("", "content", 1)
        
        # Test empty content
        with pytest.raises(TemplateValidationError, match="Template content cannot be empty"):
            await template_service.create_template("name", "", 1)
    
    @pytest.mark.asyncio
    async def test_create_template_success(self, template_service, mock_template_repo):
        """Test successful template creation"""
        # Mock repository response
        created_dto = PromptTemplateDto(
            id=1,
            uuid="test-uuid",
            name="Test Template",
            template_content="Hello {name}!",
            user_id=1,
            variables={"name": "string"},
            is_public=False,
            is_favorite=False,
            usage_count=0,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        mock_template_repo.create_template.return_value = created_dto
        
        # Call service
        result = await template_service.create_template(
            name="Test Template",
            template_content="Hello {name}!",
            user_id=1,
            variables={"name": "string"}
        )
        
        # Verify result
        assert result.name == "Test Template"
        assert result.template_content == "Hello {name}!"
        assert result.user_id == 1
        assert result.variables == {"name": "string"}
        
        # Verify repository was called
        mock_template_repo.create_template.assert_called_once()


class TestPresetService:
    """Test PresetService use case"""
    
    @pytest.fixture
    def mock_preset_repo(self):
        """Mock preset repository"""
        repo = AsyncMock()
        return repo
    
    @pytest.fixture
    def preset_service(self, mock_preset_repo):
        """Preset service with mocked repository"""
        return PresetService(mock_preset_repo)
    
    @pytest.mark.asyncio
    async def test_create_preset_validation(self, preset_service):
        """Test preset creation validation"""
        # Test empty name
        with pytest.raises(PresetValidationError, match="Preset name cannot be empty"):
            await preset_service.create_preset("", "gpt-3.5-turbo", 1)
        
        # Test empty model_id
        with pytest.raises(PresetValidationError, match="Model ID cannot be empty"):
            await preset_service.create_preset("name", "", 1)
    
    @pytest.mark.asyncio
    async def test_create_preset_success(self, preset_service, mock_preset_repo):
        """Test successful preset creation"""
        # Mock repository response
        created_dto = ConversationPresetDto(
            id=1,
            uuid="test-uuid",
            name="Test Preset",
            model_id="gpt-3.5-turbo",
            user_id=1,
            temperature="0.7",
            max_tokens=1000,
            is_favorite=False,
            usage_count=0,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        mock_preset_repo.create_preset.return_value = created_dto
        
        # Call service
        result = await preset_service.create_preset(
            name="Test Preset",
            model_id="gpt-3.5-turbo",
            user_id=1
        )
        
        # Verify result
        assert result.name == "Test Preset"
        assert result.model_id == "gpt-3.5-turbo"
        assert result.user_id == 1
        assert result.temperature == "0.7"
        assert result.max_tokens == 1000
        
        # Verify repository was called
        mock_preset_repo.create_preset.assert_called_once()