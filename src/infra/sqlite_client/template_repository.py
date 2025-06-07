from typing import List, Optional
import json
import datetime
from peewee import DoesNotExist

from .peewee_models import PromptTemplate, ConversationPreset, User


class TemplateRepository:
    """プロンプトテンプレートのリポジトリ"""
    
    async def create_template(
        self,
        user_id: str,
        name: str,
        template_content: str,
        description: Optional[str] = None,
        category: Optional[str] = None,
        variables: Optional[List[str]] = None,
        is_public: bool = False
    ) -> PromptTemplate:
        """テンプレートを新規作成"""
        variables_json = json.dumps(variables) if variables else None
        
        template = PromptTemplate.create(
            user=user_id,
            name=name,
            description=description,
            template_content=template_content,
            category=category,
            variables=variables_json,
            is_public=is_public
        )
        return template
    
    async def get_template_by_uuid(self, template_uuid: str, user_id: str) -> Optional[PromptTemplate]:
        """UUIDでテンプレートを取得（ユーザー所有またはパブリック）"""
        try:
            return PromptTemplate.get(
                (PromptTemplate.uuid == template_uuid) &
                ((PromptTemplate.user == user_id) | (PromptTemplate.is_public == True))
            )
        except DoesNotExist:
            return None
    
    async def get_user_templates(
        self,
        user_id: str,
        page: int = 1,
        limit: int = 20,
        category: Optional[str] = None,
        is_favorite: Optional[bool] = None,
        search_query: Optional[str] = None
    ) -> tuple[List[PromptTemplate], int]:
        """ユーザーのテンプレート一覧を取得"""
        query = PromptTemplate.select().where(
            (PromptTemplate.user == user_id) | (PromptTemplate.is_public == True)
        )
        
        if category:
            query = query.where(PromptTemplate.category == category)
        
        if is_favorite is not None:
            query = query.where(PromptTemplate.is_favorite == is_favorite)
        
        if search_query:
            query = query.where(
                (PromptTemplate.name.contains(search_query)) |
                (PromptTemplate.description.contains(search_query)) |
                (PromptTemplate.template_content.contains(search_query))
            )
        
        total = query.count()
        
        templates = list(query.order_by(PromptTemplate.updated_at.desc())
                        .paginate(page, limit))
        
        return templates, total
    
    async def update_template(
        self,
        template_uuid: str,
        user_id: str,
        **update_data
    ) -> Optional[PromptTemplate]:
        """テンプレートを更新"""
        try:
            template = PromptTemplate.get(
                (PromptTemplate.uuid == template_uuid) &
                (PromptTemplate.user == user_id)
            )
            
            # variablesがある場合はJSON化
            if 'variables' in update_data and update_data['variables']:
                update_data['variables'] = json.dumps(update_data['variables'])
            
            update_data['updated_at'] = datetime.datetime.now()
            
            for key, value in update_data.items():
                if hasattr(template, key) and value is not None:
                    setattr(template, key, value)
            
            template.save()
            return template
        except DoesNotExist:
            return None
    
    async def delete_template(self, template_uuid: str, user_id: str) -> bool:
        """テンプレートを削除"""
        try:
            template = PromptTemplate.get(
                (PromptTemplate.uuid == template_uuid) &
                (PromptTemplate.user == user_id)
            )
            template.delete_instance()
            return True
        except DoesNotExist:
            return False
    
    async def increment_usage_count(self, template_uuid: str) -> bool:
        """使用回数をインクリメント"""
        try:
            template = PromptTemplate.get(PromptTemplate.uuid == template_uuid)
            template.usage_count += 1
            template.updated_at = datetime.datetime.now()
            template.save()
            return True
        except DoesNotExist:
            return False
    
    async def get_categories(self, user_id: str) -> List[str]:
        """ユーザーのテンプレートカテゴリ一覧を取得"""
        categories = (PromptTemplate
                     .select(PromptTemplate.category)
                     .where(
                         ((PromptTemplate.user == user_id) | (PromptTemplate.is_public == True)) &
                         (PromptTemplate.category.is_null(False))
                     )
                     .distinct()
                     .order_by(PromptTemplate.category))
        
        return [cat.category for cat in categories]


class PresetRepository:
    """会話プリセットのリポジトリ"""
    
    async def create_preset(
        self,
        user_id: str,
        name: str,
        model_id: str,
        temperature: float = 0.7,
        max_tokens: int = 1000,
        system_prompt: Optional[str] = None,
        description: Optional[str] = None
    ) -> ConversationPreset:
        """プリセットを新規作成"""
        preset = ConversationPreset.create(
            user=user_id,
            name=name,
            description=description,
            model_id=model_id,
            temperature=str(temperature),
            max_tokens=max_tokens,
            system_prompt=system_prompt
        )
        return preset
    
    async def get_preset_by_uuid(self, preset_uuid: str, user_id: str) -> Optional[ConversationPreset]:
        """UUIDでプリセットを取得"""
        try:
            return ConversationPreset.get(
                (ConversationPreset.uuid == preset_uuid) &
                (ConversationPreset.user == user_id)
            )
        except DoesNotExist:
            return None
    
    async def get_user_presets(
        self,
        user_id: str,
        page: int = 1,
        limit: int = 20,
        is_favorite: Optional[bool] = None,
        search_query: Optional[str] = None
    ) -> tuple[List[ConversationPreset], int]:
        """ユーザーのプリセット一覧を取得"""
        query = ConversationPreset.select().where(ConversationPreset.user == user_id)
        
        if is_favorite is not None:
            query = query.where(ConversationPreset.is_favorite == is_favorite)
        
        if search_query:
            query = query.where(
                (ConversationPreset.name.contains(search_query)) |
                (ConversationPreset.description.contains(search_query))
            )
        
        total = query.count()
        
        presets = list(query.order_by(ConversationPreset.updated_at.desc())
                      .paginate(page, limit))
        
        return presets, total
    
    async def update_preset(
        self,
        preset_uuid: str,
        user_id: str,
        **update_data
    ) -> Optional[ConversationPreset]:
        """プリセットを更新"""
        try:
            preset = ConversationPreset.get(
                (ConversationPreset.uuid == preset_uuid) &
                (ConversationPreset.user == user_id)
            )
            
            # temperatureを文字列として保存
            if 'temperature' in update_data:
                update_data['temperature'] = str(update_data['temperature'])
            
            update_data['updated_at'] = datetime.datetime.now()
            
            for key, value in update_data.items():
                if hasattr(preset, key) and value is not None:
                    setattr(preset, key, value)
            
            preset.save()
            return preset
        except DoesNotExist:
            return None
    
    async def delete_preset(self, preset_uuid: str, user_id: str) -> bool:
        """プリセットを削除"""
        try:
            preset = ConversationPreset.get(
                (ConversationPreset.uuid == preset_uuid) &
                (ConversationPreset.user == user_id)
            )
            preset.delete_instance()
            return True
        except DoesNotExist:
            return False
    
    async def increment_usage_count(self, preset_uuid: str) -> bool:
        """使用回数をインクリメント"""
        try:
            preset = ConversationPreset.get(ConversationPreset.uuid == preset_uuid)
            preset.usage_count += 1
            preset.updated_at = datetime.datetime.now()
            preset.save()
            return True
        except DoesNotExist:
            return False