"""
Port interface for template repository
"""
from abc import ABC, abstractmethod
from typing import List, Optional
from src.port.dto.template_dto import (
    PromptTemplateDto, 
    ConversationPresetDto,
    TemplateSearchCriteria,
    PresetSearchCriteria
)


class TemplateRepositoryPort(ABC):
    """Port interface for template repository operations"""

    @abstractmethod
    async def create_template(self, template: PromptTemplateDto) -> PromptTemplateDto:
        """Create a new prompt template"""
        pass

    @abstractmethod
    async def get_template_by_id(self, template_id: int) -> Optional[PromptTemplateDto]:
        """Get template by ID"""
        pass

    @abstractmethod
    async def get_template_by_uuid(self, uuid: str) -> Optional[PromptTemplateDto]:
        """Get template by UUID"""
        pass

    @abstractmethod
    async def update_template(self, template: PromptTemplateDto) -> PromptTemplateDto:
        """Update existing template"""
        pass

    @abstractmethod
    async def delete_template(self, template_id: int) -> bool:
        """Delete template by ID"""
        pass

    @abstractmethod
    async def search_templates(self, criteria: TemplateSearchCriteria) -> List[PromptTemplateDto]:
        """Search templates by criteria"""
        pass

    @abstractmethod
    async def get_templates_by_user(self, user_id: int) -> List[PromptTemplateDto]:
        """Get all templates for a user"""
        pass

    @abstractmethod
    async def get_public_templates(self) -> List[PromptTemplateDto]:
        """Get all public templates"""
        pass

    @abstractmethod
    async def get_template_categories(self, user_id: Optional[int] = None) -> List[str]:
        """Get available template categories"""
        pass

    @abstractmethod
    async def increment_template_usage(self, template_id: int) -> bool:
        """Increment template usage count"""
        pass


class PresetRepositoryPort(ABC):
    """Port interface for conversation preset repository operations"""

    @abstractmethod
    async def create_preset(self, preset: ConversationPresetDto) -> ConversationPresetDto:
        """Create a new conversation preset"""
        pass

    @abstractmethod
    async def get_preset_by_id(self, preset_id: int) -> Optional[ConversationPresetDto]:
        """Get preset by ID"""
        pass

    @abstractmethod
    async def get_preset_by_uuid(self, uuid: str) -> Optional[ConversationPresetDto]:
        """Get preset by UUID"""
        pass

    @abstractmethod
    async def update_preset(self, preset: ConversationPresetDto) -> ConversationPresetDto:
        """Update existing preset"""
        pass

    @abstractmethod
    async def delete_preset(self, preset_id: int) -> bool:
        """Delete preset by ID"""
        pass

    @abstractmethod
    async def search_presets(self, criteria: PresetSearchCriteria) -> List[ConversationPresetDto]:
        """Search presets by criteria"""
        pass

    @abstractmethod
    async def get_presets_by_user(self, user_id: int) -> List[ConversationPresetDto]:
        """Get all presets for a user"""
        pass

    @abstractmethod
    async def increment_preset_usage(self, preset_id: int) -> bool:
        """Increment preset usage count"""
        pass