"""
Template management service - use case layer
"""
from typing import List, Optional, Dict, Any
from datetime import datetime

from src.domain.entity.template_entity import PromptTemplate, ConversationPreset
from src.domain.exception.template_exceptions import (
    TemplateNotFoundError, TemplateAccessDeniedError, TemplateValidationError,
    PresetNotFoundError, PresetAccessDeniedError, PresetValidationError
)
from src.port.template_repository import TemplateRepositoryPort, PresetRepositoryPort
from src.port.dto.template_dto import (
    PromptTemplateDto, ConversationPresetDto,
    TemplateSearchCriteria, PresetSearchCriteria
)


class TemplateService:
    """Service for template management operations"""

    def __init__(self, template_repository: TemplateRepositoryPort):
        self._template_repository = template_repository

    async def create_template(self, name: str, template_content: str, user_id: int,
                            description: Optional[str] = None, category: Optional[str] = None,
                            variables: Optional[Dict[str, Any]] = None) -> PromptTemplate:
        """Create a new prompt template"""
        if not name.strip():
            raise TemplateValidationError("Template name cannot be empty")
        if not template_content.strip():
            raise TemplateValidationError("Template content cannot be empty")

        # Create domain entity
        template = PromptTemplate(
            name=name.strip(),
            template_content=template_content,
            user_id=user_id,
            description=description,
            category=category,
            variables=variables or {}
        )
        
        # Convert to DTO and save
        template_dto = self._entity_to_dto(template)
        saved_dto = await self._template_repository.create_template(template_dto)
        
        return self._dto_to_entity(saved_dto)

    async def get_template(self, template_id: int, user_id: int) -> PromptTemplate:
        """Get template by ID with access control"""
        template_dto = await self._template_repository.get_template_by_id(template_id)
        if not template_dto:
            raise TemplateNotFoundError(str(template_id))
        
        # Check access - user can access their own templates or public templates
        if template_dto.user_id != user_id and not template_dto.is_public:
            raise TemplateAccessDeniedError(str(template_id), user_id)
        
        return self._dto_to_entity(template_dto)

    async def get_template_by_uuid(self, uuid: str, user_id: int) -> PromptTemplate:
        """Get template by UUID with access control"""
        template_dto = await self._template_repository.get_template_by_uuid(uuid)
        if not template_dto:
            raise TemplateNotFoundError(uuid)
        
        # Check access
        if template_dto.user_id != user_id and not template_dto.is_public:
            raise TemplateAccessDeniedError(uuid, user_id)
        
        return self._dto_to_entity(template_dto)

    async def update_template(self, template_id: int, user_id: int,
                            name: Optional[str] = None, template_content: Optional[str] = None,
                            description: Optional[str] = None, category: Optional[str] = None,
                            variables: Optional[Dict[str, Any]] = None) -> PromptTemplate:
        """Update template with access control"""
        # Get existing template and check ownership
        template_dto = await self._template_repository.get_template_by_id(template_id)
        if not template_dto:
            raise TemplateNotFoundError(str(template_id))
        
        if template_dto.user_id != user_id:
            raise TemplateAccessDeniedError(str(template_id), user_id)
        
        # Convert to entity and update
        template = self._dto_to_entity(template_dto)
        
        if name is not None or description is not None or category is not None or variables is not None:
            template.update_metadata(name, description, category, variables)
        
        if template_content is not None:
            if not template_content.strip():
                raise TemplateValidationError("Template content cannot be empty")
            template.update_content(template_content)
        
        # Save changes
        updated_dto = self._entity_to_dto(template)
        saved_dto = await self._template_repository.update_template(updated_dto)
        
        return self._dto_to_entity(saved_dto)

    async def delete_template(self, template_id: int, user_id: int) -> bool:
        """Delete template with access control"""
        template_dto = await self._template_repository.get_template_by_id(template_id)
        if not template_dto:
            raise TemplateNotFoundError(str(template_id))
        
        if template_dto.user_id != user_id:
            raise TemplateAccessDeniedError(str(template_id), user_id)
        
        return await self._template_repository.delete_template(template_id)

    async def get_user_templates(self, user_id: int) -> List[PromptTemplate]:
        """Get all templates for a user"""
        template_dtos = await self._template_repository.get_templates_by_user(user_id)
        return [self._dto_to_entity(dto) for dto in template_dtos]

    async def get_public_templates(self) -> List[PromptTemplate]:
        """Get all public templates"""
        template_dtos = await self._template_repository.get_public_templates()
        return [self._dto_to_entity(dto) for dto in template_dtos]

    async def search_templates(self, user_id: int, category: Optional[str] = None,
                             search_text: Optional[str] = None, include_public: bool = True,
                             limit: Optional[int] = None, offset: Optional[int] = None) -> List[PromptTemplate]:
        """Search templates with various criteria"""
        criteria = TemplateSearchCriteria(
            user_id=user_id,
            category=category,
            search_text=search_text,
            limit=limit,
            offset=offset
        )
        
        template_dtos = await self._template_repository.search_templates(criteria)
        
        # Add public templates if requested
        if include_public:
            public_criteria = TemplateSearchCriteria(
                is_public=True,
                category=category,
                search_text=search_text,
                limit=limit,
                offset=offset
            )
            public_dtos = await self._template_repository.search_templates(public_criteria)
            # Remove duplicates and templates already owned by user
            for dto in public_dtos:
                if dto.user_id != user_id and dto not in template_dtos:
                    template_dtos.append(dto)
        
        return [self._dto_to_entity(dto) for dto in template_dtos]

    async def toggle_favorite(self, template_id: int, user_id: int) -> PromptTemplate:
        """Toggle template favorite status"""
        template = await self.get_template(template_id, user_id)
        
        if template.is_favorite:
            template.unmark_as_favorite()
        else:
            template.mark_as_favorite()
        
        updated_dto = self._entity_to_dto(template)
        saved_dto = await self._template_repository.update_template(updated_dto)
        
        return self._dto_to_entity(saved_dto)

    async def use_template(self, template_id: int, user_id: int) -> PromptTemplate:
        """Use template (increment usage count)"""
        template = await self.get_template(template_id, user_id)
        template.increment_usage()
        
        await self._template_repository.increment_template_usage(template_id)
        
        return template

    def _entity_to_dto(self, entity: PromptTemplate) -> PromptTemplateDto:
        """Convert entity to DTO"""
        return PromptTemplateDto(
            id=entity.id,
            uuid=entity.uuid,
            name=entity.name,
            template_content=entity.template_content,
            user_id=entity.user_id,
            description=entity.description,
            category=entity.category,
            variables=entity.variables,
            is_public=entity.is_public,
            is_favorite=entity.is_favorite,
            usage_count=entity.usage_count,
            created_at=entity.created_at,
            updated_at=entity.updated_at
        )

    def _dto_to_entity(self, dto: PromptTemplateDto) -> PromptTemplate:
        """Convert DTO to entity"""
        return PromptTemplate(
            id=dto.id,
            uuid=dto.uuid,
            name=dto.name,
            template_content=dto.template_content,
            user_id=dto.user_id,
            description=dto.description,
            category=dto.category,
            variables=dto.variables,
            is_public=dto.is_public,
            is_favorite=dto.is_favorite,
            usage_count=dto.usage_count,
            created_at=dto.created_at,
            updated_at=dto.updated_at
        )


class PresetService:
    """Service for conversation preset management operations"""

    def __init__(self, preset_repository: PresetRepositoryPort):
        self._preset_repository = preset_repository

    async def create_preset(self, name: str, model_id: str, user_id: int,
                          description: Optional[str] = None, temperature: str = "0.7",
                          max_tokens: int = 1000, system_prompt: Optional[str] = None) -> ConversationPreset:
        """Create a new conversation preset"""
        if not name.strip():
            raise PresetValidationError("Preset name cannot be empty")
        if not model_id.strip():
            raise PresetValidationError("Model ID cannot be empty")

        # Create domain entity
        preset = ConversationPreset(
            name=name.strip(),
            model_id=model_id,
            user_id=user_id,
            description=description,
            temperature=temperature,
            max_tokens=max_tokens,
            system_prompt=system_prompt
        )
        
        # Convert to DTO and save
        preset_dto = self._entity_to_dto(preset)
        saved_dto = await self._preset_repository.create_preset(preset_dto)
        
        return self._dto_to_entity(saved_dto)

    async def get_preset(self, preset_id: int, user_id: int) -> ConversationPreset:
        """Get preset by ID with access control"""
        preset_dto = await self._preset_repository.get_preset_by_id(preset_id)
        if not preset_dto:
            raise PresetNotFoundError(str(preset_id))
        
        if preset_dto.user_id != user_id:
            raise PresetAccessDeniedError(str(preset_id), user_id)
        
        return self._dto_to_entity(preset_dto)

    async def get_preset_by_uuid(self, uuid: str, user_id: int) -> ConversationPreset:
        """Get preset by UUID with access control"""
        preset_dto = await self._preset_repository.get_preset_by_uuid(uuid)
        if not preset_dto:
            raise PresetNotFoundError(uuid)
        
        if preset_dto.user_id != user_id:
            raise PresetAccessDeniedError(uuid, user_id)
        
        return self._dto_to_entity(preset_dto)

    async def update_preset(self, preset_id: int, user_id: int,
                          name: Optional[str] = None, model_id: Optional[str] = None,
                          description: Optional[str] = None, temperature: Optional[str] = None,
                          max_tokens: Optional[int] = None, system_prompt: Optional[str] = None) -> ConversationPreset:
        """Update preset with access control"""
        preset_dto = await self._preset_repository.get_preset_by_id(preset_id)
        if not preset_dto:
            raise PresetNotFoundError(str(preset_id))
        
        if preset_dto.user_id != user_id:
            raise PresetAccessDeniedError(str(preset_id), user_id)
        
        # Convert to entity and update
        preset = self._dto_to_entity(preset_dto)
        
        if name is not None or description is not None:
            preset.update_metadata(name, description)
        
        if model_id is not None or temperature is not None or max_tokens is not None:
            preset.update_model_settings(model_id, temperature, max_tokens)
        
        if system_prompt is not None:
            preset.update_system_prompt(system_prompt)
        
        # Save changes
        updated_dto = self._entity_to_dto(preset)
        saved_dto = await self._preset_repository.update_preset(updated_dto)
        
        return self._dto_to_entity(saved_dto)

    async def delete_preset(self, preset_id: int, user_id: int) -> bool:
        """Delete preset with access control"""
        preset_dto = await self._preset_repository.get_preset_by_id(preset_id)
        if not preset_dto:
            raise PresetNotFoundError(str(preset_id))
        
        if preset_dto.user_id != user_id:
            raise PresetAccessDeniedError(str(preset_id), user_id)
        
        return await self._preset_repository.delete_preset(preset_id)

    async def get_user_presets(self, user_id: int) -> List[ConversationPreset]:
        """Get all presets for a user"""
        preset_dtos = await self._preset_repository.get_presets_by_user(user_id)
        return [self._dto_to_entity(dto) for dto in preset_dtos]

    async def search_presets(self, user_id: int, model_id: Optional[str] = None,
                           search_text: Optional[str] = None,
                           limit: Optional[int] = None, offset: Optional[int] = None) -> List[ConversationPreset]:
        """Search presets with various criteria"""
        criteria = PresetSearchCriteria(
            user_id=user_id,
            model_id=model_id,
            search_text=search_text,
            limit=limit,
            offset=offset
        )
        
        preset_dtos = await self._preset_repository.search_presets(criteria)
        return [self._dto_to_entity(dto) for dto in preset_dtos]

    async def toggle_favorite(self, preset_id: int, user_id: int) -> ConversationPreset:
        """Toggle preset favorite status"""
        preset = await self.get_preset(preset_id, user_id)
        
        if preset.is_favorite:
            preset.unmark_as_favorite()
        else:
            preset.mark_as_favorite()
        
        updated_dto = self._entity_to_dto(preset)
        saved_dto = await self._preset_repository.update_preset(updated_dto)
        
        return self._dto_to_entity(saved_dto)

    async def use_preset(self, preset_id: int, user_id: int) -> ConversationPreset:
        """Use preset (increment usage count)"""
        preset = await self.get_preset(preset_id, user_id)
        preset.increment_usage()
        
        await self._preset_repository.increment_preset_usage(preset_id)
        
        return preset

    def _entity_to_dto(self, entity: ConversationPreset) -> ConversationPresetDto:
        """Convert entity to DTO"""
        return ConversationPresetDto(
            id=entity.id,
            uuid=entity.uuid,
            name=entity.name,
            model_id=entity.model_id,
            user_id=entity.user_id,
            description=entity.description,
            temperature=entity.temperature,
            max_tokens=entity.max_tokens,
            system_prompt=entity.system_prompt,
            is_favorite=entity.is_favorite,
            usage_count=entity.usage_count,
            created_at=entity.created_at,
            updated_at=entity.updated_at
        )

    def _dto_to_entity(self, dto: ConversationPresetDto) -> ConversationPreset:
        """Convert DTO to entity"""
        return ConversationPreset(
            id=dto.id,
            uuid=dto.uuid,
            name=dto.name,
            model_id=dto.model_id,
            user_id=dto.user_id,
            description=dto.description,
            temperature=dto.temperature,
            max_tokens=dto.max_tokens,
            system_prompt=dto.system_prompt,
            is_favorite=dto.is_favorite,
            usage_count=dto.usage_count,
            created_at=dto.created_at,
            updated_at=dto.updated_at
        )