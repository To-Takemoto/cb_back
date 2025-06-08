"""
Tortoise ORM template and preset repositories
"""
from typing import List, Optional, Tuple
import json
from datetime import datetime
from tortoise.exceptions import DoesNotExist

from .models import PromptTemplate, ConversationPreset, User


class TortoiseTemplateRepository:
    """プロンプトテンプレートのTortoise ORMリポジトリ"""
    
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
        
        user = await User.get(uuid=user_id)
        
        template = await PromptTemplate.create(
            user=user,
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
            user = await User.get(uuid=user_id)
            # まず最初のクエリを試す（ユーザー所有のテンプレート）
            first_result = await PromptTemplate.filter(
                uuid=template_uuid,
                user=user
            ).first()

            if first_result:
                return first_result

            # パブリックテンプレートを検索
            return await PromptTemplate.filter(
                uuid=template_uuid,
                is_public=True
            ).first()
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
    ) -> Tuple[List[PromptTemplate], int]:
        """ユーザーのテンプレート一覧を取得"""
        user = await User.get(uuid=user_id)
        
        query = PromptTemplate.filter(
            PromptTemplate.user == user
        ).union(
            PromptTemplate.filter(PromptTemplate.is_public == True)
        )
        
        if category:
            query = query.filter(category=category)
        
        if is_favorite is not None:
            query = query.filter(is_favorite=is_favorite)
        
        if search_query:
            query = query.filter(
                name__icontains=search_query
            ) | query.filter(
                description__icontains=search_query
            ) | query.filter(
                template_content__icontains=search_query
            )
        
        total = await query.count()
        
        offset = (page - 1) * limit
        templates = await query.order_by("-updated_at").offset(offset).limit(limit)
        
        return templates, total
    
    async def update_template(
        self,
        template_uuid: str,
        user_id: str,
        **update_data
    ) -> Optional[PromptTemplate]:
        """テンプレートを更新"""
        try:
            user = await User.get(uuid=user_id)
            template = await PromptTemplate.get(
                uuid=template_uuid,
                user=user
            )
            
            # variablesがある場合はJSON化
            if 'variables' in update_data and update_data['variables']:
                update_data['variables'] = json.dumps(update_data['variables'])
            
            update_data['updated_at'] = datetime.utcnow()
            
            for key, value in update_data.items():
                if hasattr(template, key) and value is not None:
                    setattr(template, key, value)
            
            await template.save()
            return template
        except DoesNotExist:
            return None
    
    async def delete_template(self, template_uuid: str, user_id: str) -> bool:
        """テンプレートを削除"""
        try:
            user = await User.get(uuid=user_id)
            template = await PromptTemplate.get(
                uuid=template_uuid,
                user=user
            )
            await template.delete()
            return True
        except DoesNotExist:
            return False
    
    async def increment_usage_count(self, template_uuid: str) -> bool:
        """使用回数をインクリメント"""
        try:
            template = await PromptTemplate.get(uuid=template_uuid)
            template.usage_count += 1
            template.updated_at = datetime.utcnow()
            await template.save()
            return True
        except DoesNotExist:
            return False
    
    async def get_categories(self, user_id: str) -> List[str]:
        """ユーザーのテンプレートカテゴリ一覧を取得"""
        user = await User.get(uuid=user_id)
        
        user_templates = await PromptTemplate.filter(
            user=user,
            category__not_isnull=True
        ).distinct().values_list('category', flat=True)
        
        public_templates = await PromptTemplate.filter(
            is_public=True,
            category__not_isnull=True
        ).distinct().values_list('category', flat=True)
        
        categories = sorted(set(user_templates + public_templates))
        return categories


class TortoisePresetRepository:
    """会話プリセットのTortoise ORMリポジトリ"""
    
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
        user = await User.get(uuid=user_id)
        
        preset = await ConversationPreset.create(
            user=user,
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
            user = await User.get(uuid=user_id)
            return await ConversationPreset.get(
                uuid=preset_uuid,
                user=user
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
    ) -> Tuple[List[ConversationPreset], int]:
        """ユーザーのプリセット一覧を取得"""
        user = await User.get(uuid=user_id)
        query = ConversationPreset.filter(user=user)
        
        if is_favorite is not None:
            query = query.filter(is_favorite=is_favorite)
        
        if search_query:
            query = query.filter(
                name__icontains=search_query
            ) | query.filter(
                description__icontains=search_query
            )
        
        total = await query.count()
        
        offset = (page - 1) * limit
        presets = await query.order_by("-updated_at").offset(offset).limit(limit)
        
        return presets, total
    
    async def update_preset(
        self,
        preset_uuid: str,
        user_id: str,
        **update_data
    ) -> Optional[ConversationPreset]:
        """プリセットを更新"""
        try:
            user = await User.get(uuid=user_id)
            preset = await ConversationPreset.get(
                uuid=preset_uuid,
                user=user
            )
            
            # temperatureを文字列として保存
            if 'temperature' in update_data:
                update_data['temperature'] = str(update_data['temperature'])
            
            update_data['updated_at'] = datetime.utcnow()
            
            for key, value in update_data.items():
                if hasattr(preset, key) and value is not None:
                    setattr(preset, key, value)
            
            await preset.save()
            return preset
        except DoesNotExist:
            return None
    
    async def delete_preset(self, preset_uuid: str, user_id: str) -> bool:
        """プリセットを削除"""
        try:
            user = await User.get(uuid=user_id)
            preset = await ConversationPreset.get(
                uuid=preset_uuid,
                user=user
            )
            await preset.delete()
            return True
        except DoesNotExist:
            return False
    
    async def increment_usage_count(self, preset_uuid: str) -> bool:
        """使用回数をインクリメント"""
        try:
            preset = await ConversationPreset.get(uuid=preset_uuid)
            preset.usage_count += 1
            preset.updated_at = datetime.utcnow()
            await preset.save()
            return True
        except DoesNotExist:
            return False