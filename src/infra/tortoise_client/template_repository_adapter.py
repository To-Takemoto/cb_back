"""
Adapter to bridge the gap between old and new template repository interfaces
"""
from typing import List, Optional
import json
from datetime import datetime
from tortoise.exceptions import DoesNotExist

from .models import PromptTemplate, ConversationPreset, User
from src.port.template_repository import TemplateRepositoryPort, PresetRepositoryPort
from src.port.dto.template_dto import (
    PromptTemplateDto, ConversationPresetDto,
    TemplateSearchCriteria, PresetSearchCriteria
)


class TortoiseTemplateRepositoryAdapter(TemplateRepositoryPort):
    """Adapter for template repository following the new port interface"""

    def _orm_to_template_dto(self, orm_template: PromptTemplate) -> PromptTemplateDto:
        """Convert ORM model to DTO"""
        variables = {}
        if orm_template.variables:
            try:
                variables = json.loads(orm_template.variables)
            except json.JSONDecodeError:
                variables = {}
        
        return PromptTemplateDto(
            id=orm_template.id,
            uuid=orm_template.uuid,
            name=orm_template.name,
            template_content=orm_template.template_content,
            user_id=orm_template.user_id,
            description=orm_template.description,
            category=orm_template.category,
            variables=variables,
            is_public=orm_template.is_public,
            is_favorite=orm_template.is_favorite,
            usage_count=orm_template.usage_count,
            created_at=orm_template.created_at,
            updated_at=orm_template.updated_at
        )

    async def create_template(self, template: PromptTemplateDto) -> PromptTemplateDto:
        """Create a new prompt template"""
        variables_json = json.dumps(template.variables) if template.variables else None
        
        user = await User.get(id=template.user_id)
        
        orm_template = await PromptTemplate.create(
            user=user,
            uuid=template.uuid,
            name=template.name,
            description=template.description,
            template_content=template.template_content,
            category=template.category,
            variables=variables_json,
            is_public=template.is_public,
            is_favorite=template.is_favorite
        )
        return self._orm_to_template_dto(orm_template)

    async def get_template_by_id(self, template_id: int) -> Optional[PromptTemplateDto]:
        """Get template by ID"""
        try:
            orm_template = await PromptTemplate.get(id=template_id)
            return self._orm_to_template_dto(orm_template)
        except DoesNotExist:
            return None

    async def get_template_by_uuid(self, uuid: str) -> Optional[PromptTemplateDto]:
        """Get template by UUID"""
        try:
            orm_template = await PromptTemplate.get(uuid=uuid)
            return self._orm_to_template_dto(orm_template)
        except DoesNotExist:
            return None

    async def update_template(self, template: PromptTemplateDto) -> PromptTemplateDto:
        """Update existing template"""
        try:
            orm_template = await PromptTemplate.get(id=template.id)
            
            # Update fields
            orm_template.name = template.name
            orm_template.template_content = template.template_content
            orm_template.description = template.description
            orm_template.category = template.category
            orm_template.variables = json.dumps(template.variables) if template.variables else None
            orm_template.is_public = template.is_public
            orm_template.is_favorite = template.is_favorite
            orm_template.usage_count = template.usage_count
            orm_template.updated_at = datetime.utcnow()
            
            await orm_template.save()
            return self._orm_to_template_dto(orm_template)
        except DoesNotExist:
            raise ValueError(f"Template with ID {template.id} not found")

    async def delete_template(self, template_id: int) -> bool:
        """Delete template by ID"""
        try:
            orm_template = await PromptTemplate.get(id=template_id)
            await orm_template.delete()
            return True
        except DoesNotExist:
            return False

    async def search_templates(self, criteria: TemplateSearchCriteria) -> List[PromptTemplateDto]:
        """Search templates by criteria"""
        query = PromptTemplate.all()
        
        if criteria.user_id is not None:
            query = query.filter(user_id=criteria.user_id)
        
        if criteria.category is not None:
            query = query.filter(category=criteria.category)
        
        if criteria.is_public is not None:
            query = query.filter(is_public=criteria.is_public)
        
        if criteria.is_favorite is not None:
            query = query.filter(is_favorite=criteria.is_favorite)
        
        if criteria.search_text is not None:
            query = query.filter(
                name__icontains=criteria.search_text
            ) | query.filter(
                description__icontains=criteria.search_text
            ) | query.filter(
                template_content__icontains=criteria.search_text
            )
        
        query = query.order_by("-updated_at")
        
        if criteria.offset is not None:
            query = query.offset(criteria.offset)
        
        if criteria.limit is not None:
            query = query.limit(criteria.limit)
        
        orm_templates = await query
        return [self._orm_to_template_dto(t) for t in orm_templates]

    async def get_templates_by_user(self, user_id: int) -> List[PromptTemplateDto]:
        """Get all templates for a user"""
        orm_templates = await PromptTemplate.filter(user_id=user_id).order_by("-updated_at")
        return [self._orm_to_template_dto(t) for t in orm_templates]

    async def get_public_templates(self) -> List[PromptTemplateDto]:
        """Get all public templates"""
        orm_templates = await PromptTemplate.filter(is_public=True).order_by("-updated_at")
        return [self._orm_to_template_dto(t) for t in orm_templates]

    async def get_template_categories(self, user_id: Optional[int] = None) -> List[str]:
        """Get available template categories"""
        if user_id is not None:
            user_categories = await PromptTemplate.filter(
                user_id=user_id,
                category__not_isnull=True
            ).distinct().values_list('category', flat=True)
            
            public_categories = await PromptTemplate.filter(
                is_public=True,
                category__not_isnull=True
            ).distinct().values_list('category', flat=True)
            
            categories = sorted(set(user_categories + public_categories))
        else:
            categories = await PromptTemplate.filter(
                category__not_isnull=True
            ).distinct().values_list('category', flat=True)
            categories = sorted(set(categories))
        
        return categories

    async def increment_template_usage(self, template_id: int) -> bool:
        """Increment template usage count"""
        from tortoise.transactions import in_transaction
        try:
            async with in_transaction():
                template = await PromptTemplate.get(id=template_id)
                template.usage_count += 1
                template.updated_at = datetime.utcnow()
                await template.save()
                return True
        except DoesNotExist:
            return False


class TortoisePresetRepositoryAdapter(PresetRepositoryPort):
    """Adapter for preset repository following the new port interface"""

    def _orm_to_preset_dto(self, orm_preset: ConversationPreset) -> ConversationPresetDto:
        """Convert ORM model to DTO"""
        return ConversationPresetDto(
            id=orm_preset.id,
            uuid=orm_preset.uuid,
            name=orm_preset.name,
            model_id=orm_preset.model_id,
            user_id=orm_preset.user_id,
            description=orm_preset.description,
            temperature=orm_preset.temperature,
            max_tokens=orm_preset.max_tokens,
            system_prompt=orm_preset.system_prompt,
            is_favorite=orm_preset.is_favorite,
            usage_count=orm_preset.usage_count,
            created_at=orm_preset.created_at,
            updated_at=orm_preset.updated_at
        )

    async def create_preset(self, preset: ConversationPresetDto) -> ConversationPresetDto:
        """Create a new conversation preset"""
        user = await User.get(id=preset.user_id)
        
        orm_preset = await ConversationPreset.create(
            user=user,
            uuid=preset.uuid,
            name=preset.name,
            description=preset.description,
            model_id=preset.model_id,
            temperature=preset.temperature,
            max_tokens=preset.max_tokens,
            system_prompt=preset.system_prompt,
            is_favorite=preset.is_favorite
        )
        return self._orm_to_preset_dto(orm_preset)

    async def get_preset_by_id(self, preset_id: int) -> Optional[ConversationPresetDto]:
        """Get preset by ID"""
        try:
            orm_preset = await ConversationPreset.get(id=preset_id)
            return self._orm_to_preset_dto(orm_preset)
        except DoesNotExist:
            return None

    async def get_preset_by_uuid(self, uuid: str) -> Optional[ConversationPresetDto]:
        """Get preset by UUID"""
        try:
            orm_preset = await ConversationPreset.get(uuid=uuid)
            return self._orm_to_preset_dto(orm_preset)
        except DoesNotExist:
            return None

    async def update_preset(self, preset: ConversationPresetDto) -> ConversationPresetDto:
        """Update existing preset"""
        try:
            orm_preset = await ConversationPreset.get(id=preset.id)
            
            # Update fields
            orm_preset.name = preset.name
            orm_preset.model_id = preset.model_id
            orm_preset.description = preset.description
            orm_preset.temperature = preset.temperature
            orm_preset.max_tokens = preset.max_tokens
            orm_preset.system_prompt = preset.system_prompt
            orm_preset.is_favorite = preset.is_favorite
            orm_preset.usage_count = preset.usage_count
            orm_preset.updated_at = datetime.utcnow()
            
            await orm_preset.save()
            return self._orm_to_preset_dto(orm_preset)
        except DoesNotExist:
            raise ValueError(f"Preset with ID {preset.id} not found")

    async def delete_preset(self, preset_id: int) -> bool:
        """Delete preset by ID"""
        try:
            orm_preset = await ConversationPreset.get(id=preset_id)
            await orm_preset.delete()
            return True
        except DoesNotExist:
            return False

    async def search_presets(self, criteria: PresetSearchCriteria) -> List[ConversationPresetDto]:
        """Search presets by criteria"""
        query = ConversationPreset.all()
        
        if criteria.user_id is not None:
            query = query.filter(user_id=criteria.user_id)
        
        if criteria.model_id is not None:
            query = query.filter(model_id=criteria.model_id)
        
        if criteria.is_favorite is not None:
            query = query.filter(is_favorite=criteria.is_favorite)
        
        if criteria.search_text is not None:
            query = query.filter(
                name__icontains=criteria.search_text
            ) | query.filter(
                description__icontains=criteria.search_text
            )
        
        query = query.order_by("-updated_at")
        
        if criteria.offset is not None:
            query = query.offset(criteria.offset)
        
        if criteria.limit is not None:
            query = query.limit(criteria.limit)
        
        orm_presets = await query
        return [self._orm_to_preset_dto(p) for p in orm_presets]

    async def get_presets_by_user(self, user_id: int) -> List[ConversationPresetDto]:
        """Get all presets for a user"""
        orm_presets = await ConversationPreset.filter(user_id=user_id).order_by("-updated_at")
        return [self._orm_to_preset_dto(p) for p in orm_presets]

    async def increment_preset_usage(self, preset_id: int) -> bool:
        """Increment preset usage count"""
        from tortoise.transactions import in_transaction
        try:
            async with in_transaction():
                preset = await ConversationPreset.get(id=preset_id)
                preset.usage_count += 1
                preset.updated_at = datetime.utcnow()
                await preset.save()
                return True
        except DoesNotExist:
            return False