from fastapi import APIRouter, Depends, HTTPException
from typing import List
import json

from ..dependencies import get_current_user
from ..schemas import (
    TemplateCreateRequest, TemplateUpdateRequest, TemplateResponse,
    TemplateListParams, PaginatedResponse,
    PresetCreateRequest, PresetUpdateRequest, PresetResponse,
    PresetListParams
)
from ...sqlite_client.template_repository import TemplateRepository, PresetRepository
from ...sqlite_client.peewee_models import PromptTemplate, ConversationPreset

router = APIRouter()
template_repo = TemplateRepository()
preset_repo = PresetRepository()


def template_to_response(template: PromptTemplate) -> TemplateResponse:
    """PromptTemplateモデルをレスポンススキーマに変換"""
    variables = []
    if template.variables:
        try:
            variables = json.loads(template.variables)
        except json.JSONDecodeError:
            variables = []
    
    return TemplateResponse(
        uuid=template.uuid,
        name=template.name,
        description=template.description,
        template_content=template.template_content,
        category=template.category,
        variables=variables,
        is_public=template.is_public,
        is_favorite=template.is_favorite,
        usage_count=template.usage_count,
        created_at=template.created_at.isoformat(),
        updated_at=template.updated_at.isoformat()
    )


def preset_to_response(preset: ConversationPreset) -> PresetResponse:
    """ConversationPresetモデルをレスポンススキーマに変換"""
    return PresetResponse(
        uuid=preset.uuid,
        name=preset.name,
        description=preset.description,
        model_id=preset.model_id,
        temperature=float(preset.temperature),
        max_tokens=preset.max_tokens,
        system_prompt=preset.system_prompt,
        is_favorite=preset.is_favorite,
        usage_count=preset.usage_count,
        created_at=preset.created_at.isoformat(),
        updated_at=preset.updated_at.isoformat()
    )


# テンプレート関連のエンドポイント
@router.post("/templates", response_model=TemplateResponse)
async def create_template(
    request: TemplateCreateRequest,
    current_user_id: str = Depends(get_current_user)
):
    """新しいテンプレートを作成"""
    template = await template_repo.create_template(
        user_id=current_user_id,
        name=request.name,
        template_content=request.template_content,
        description=request.description,
        category=request.category,
        variables=request.variables,
        is_public=request.is_public
    )
    return template_to_response(template)


@router.get("/templates", response_model=PaginatedResponse)
async def get_templates(
    params: TemplateListParams = Depends(),
    current_user_id: str = Depends(get_current_user)
):
    """テンプレート一覧を取得"""
    templates, total = await template_repo.get_user_templates(
        user_id=current_user_id,
        page=params.page,
        limit=params.limit,
        category=params.category,
        is_favorite=params.is_favorite,
        search_query=params.q
    )
    
    items = [template_to_response(template).model_dump() for template in templates]
    pages = (total + params.limit - 1) // params.limit
    
    return PaginatedResponse(
        items=items,
        total=total,
        page=params.page,
        limit=params.limit,
        pages=pages
    )


@router.get("/templates/{template_uuid}", response_model=TemplateResponse)
async def get_template(
    template_uuid: str,
    current_user_id: str = Depends(get_current_user)
):
    """特定のテンプレートを取得"""
    template = await template_repo.get_template_by_uuid(template_uuid, current_user_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    return template_to_response(template)


@router.put("/templates/{template_uuid}", response_model=TemplateResponse)
async def update_template(
    template_uuid: str,
    request: TemplateUpdateRequest,
    current_user_id: str = Depends(get_current_user)
):
    """テンプレートを更新"""
    update_data = {k: v for k, v in request.model_dump().items() if v is not None}
    
    template = await template_repo.update_template(
        template_uuid=template_uuid,
        user_id=current_user_id,
        **update_data
    )
    
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    return template_to_response(template)


@router.delete("/templates/{template_uuid}")
async def delete_template(
    template_uuid: str,
    current_user_id: str = Depends(get_current_user)
):
    """テンプレートを削除"""
    success = await template_repo.delete_template(template_uuid, current_user_id)
    if not success:
        raise HTTPException(status_code=404, detail="Template not found")
    
    return {"message": "Template deleted successfully"}


@router.post("/templates/{template_uuid}/use")
async def use_template(
    template_uuid: str,
    current_user_id: str = Depends(get_current_user)
):
    """テンプレートの使用回数をインクリメント"""
    success = await template_repo.increment_usage_count(template_uuid)
    if not success:
        raise HTTPException(status_code=404, detail="Template not found")
    
    return {"message": "Usage count incremented"}


@router.get("/templates/categories", response_model=List[str])
async def get_template_categories(
    current_user_id: str = Depends(get_current_user)
):
    """テンプレートカテゴリ一覧を取得"""
    categories = await template_repo.get_categories(current_user_id)
    return categories


# プリセット関連のエンドポイント
@router.post("/presets", response_model=PresetResponse)
async def create_preset(
    request: PresetCreateRequest,
    current_user_id: str = Depends(get_current_user)
):
    """新しいプリセットを作成"""
    preset = await preset_repo.create_preset(
        user_id=current_user_id,
        name=request.name,
        model_id=request.model_id,
        temperature=request.temperature,
        max_tokens=request.max_tokens,
        system_prompt=request.system_prompt,
        description=request.description
    )
    return preset_to_response(preset)


@router.get("/presets", response_model=PaginatedResponse)
async def get_presets(
    params: PresetListParams = Depends(),
    current_user_id: str = Depends(get_current_user)
):
    """プリセット一覧を取得"""
    presets, total = await preset_repo.get_user_presets(
        user_id=current_user_id,
        page=params.page,
        limit=params.limit,
        is_favorite=params.is_favorite,
        search_query=params.q
    )
    
    items = [preset_to_response(preset).model_dump() for preset in presets]
    pages = (total + params.limit - 1) // params.limit
    
    return PaginatedResponse(
        items=items,
        total=total,
        page=params.page,
        limit=params.limit,
        pages=pages
    )


@router.get("/presets/{preset_uuid}", response_model=PresetResponse)
async def get_preset(
    preset_uuid: str,
    current_user_id: str = Depends(get_current_user)
):
    """特定のプリセットを取得"""
    preset = await preset_repo.get_preset_by_uuid(preset_uuid, current_user_id)
    if not preset:
        raise HTTPException(status_code=404, detail="Preset not found")
    
    return preset_to_response(preset)


@router.put("/presets/{preset_uuid}", response_model=PresetResponse)
async def update_preset(
    preset_uuid: str,
    request: PresetUpdateRequest,
    current_user_id: str = Depends(get_current_user)
):
    """プリセットを更新"""
    update_data = {k: v for k, v in request.model_dump().items() if v is not None}
    
    preset = await preset_repo.update_preset(
        preset_uuid=preset_uuid,
        user_id=current_user_id,
        **update_data
    )
    
    if not preset:
        raise HTTPException(status_code=404, detail="Preset not found")
    
    return preset_to_response(preset)


@router.delete("/presets/{preset_uuid}")
async def delete_preset(
    preset_uuid: str,
    current_user_id: str = Depends(get_current_user)
):
    """プリセットを削除"""
    success = await preset_repo.delete_preset(preset_uuid, current_user_id)
    if not success:
        raise HTTPException(status_code=404, detail="Preset not found")
    
    return {"message": "Preset deleted successfully"}


@router.post("/presets/{preset_uuid}/use")
async def use_preset(
    preset_uuid: str,
    current_user_id: str = Depends(get_current_user)
):
    """プリセットの使用回数をインクリメント"""
    success = await preset_repo.increment_usage_count(preset_uuid)
    if not success:
        raise HTTPException(status_code=404, detail="Preset not found")
    
    return {"message": "Usage count incremented"}