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
from ...tortoise_client.template_repository_adapter import (
    TortoiseTemplateRepositoryAdapter, TortoisePresetRepositoryAdapter
)
from ...usecase.template_management.template_service import TemplateService, PresetService
from ...domain.exception.template_exceptions import (
    TemplateNotFoundError, TemplateAccessDeniedError, TemplateValidationError,
    PresetNotFoundError, PresetAccessDeniedError, PresetValidationError
)
from ...tortoise_client.models import PromptTemplate, ConversationPreset, User
from ...port.dto.template_dto import PromptTemplateDto, ConversationPresetDto

router = APIRouter()
template_repo = TortoiseTemplateRepositoryAdapter()
preset_repo = TortoisePresetRepositoryAdapter()
template_service = TemplateService(template_repo)
preset_service = PresetService(preset_repo)


async def get_current_user_id(current_user_uuid: str = Depends(get_current_user)) -> int:
    """Get current user's integer ID from UUID"""
    try:
        user = await User.get(uuid=current_user_uuid)
        return user.id
    except Exception:
        raise HTTPException(status_code=401, detail="User not found")


def template_dto_to_response(template_dto: PromptTemplateDto) -> TemplateResponse:
    """PromptTemplateDTOをレスポンススキーマに変換"""
    return TemplateResponse(
        uuid=template_dto.uuid,
        name=template_dto.name,
        description=template_dto.description,
        template_content=template_dto.template_content,
        category=template_dto.category,
        variables=template_dto.variables or {},
        is_public=template_dto.is_public,
        is_favorite=template_dto.is_favorite,
        usage_count=template_dto.usage_count,
        created_at=template_dto.created_at.isoformat() if template_dto.created_at else None,
        updated_at=template_dto.updated_at.isoformat() if template_dto.updated_at else None
    )


def preset_dto_to_response(preset_dto: ConversationPresetDto) -> PresetResponse:
    """ConversationPresetDTOをレスポンススキーマに変換"""
    return PresetResponse(
        uuid=preset_dto.uuid,
        name=preset_dto.name,
        description=preset_dto.description,
        model_id=preset_dto.model_id,
        temperature=float(preset_dto.temperature),
        max_tokens=preset_dto.max_tokens,
        system_prompt=preset_dto.system_prompt,
        is_favorite=preset_dto.is_favorite,
        usage_count=preset_dto.usage_count,
        created_at=preset_dto.created_at.isoformat() if preset_dto.created_at else None,
        updated_at=preset_dto.updated_at.isoformat() if preset_dto.updated_at else None
    )


# テンプレート関連のエンドポイント
@router.post("/templates", response_model=TemplateResponse)
async def create_template(
    request: TemplateCreateRequest,
    current_user_id: int = Depends(get_current_user_id)
):
    """新しいテンプレートを作成"""
    try:
        template = await template_service.create_template(
            name=request.name,
            template_content=request.template_content,
            user_id=current_user_id,
            description=request.description,
            category=request.category,
            variables=request.variables
        )
        
        # Make public if requested
        if request.is_public:
            template.make_public()
            await template_service.update_template(
                template.id, current_user_id, is_public=True
            )
        
        return template_dto_to_response(template_service._entity_to_dto(template))
    except TemplateValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/templates", response_model=PaginatedResponse)
async def get_templates(
    params: TemplateListParams = Depends(),
    current_user_id: int = Depends(get_current_user_id)
):
    """テンプレート一覧を取得"""
    templates = await template_service.search_templates(
        user_id=current_user_id,
        category=params.category,
        search_text=params.q,
        include_public=True,
        limit=params.limit,
        offset=(params.page - 1) * params.limit
    )
    
    items = [template_dto_to_response(template_service._entity_to_dto(t)).model_dump() for t in templates]
    total = len(items)  # Simplified for now
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
    current_user_id: int = Depends(get_current_user_id)
):
    """特定のテンプレートを取得"""
    try:
        template = await template_service.get_template_by_uuid(template_uuid, current_user_id)
        return template_dto_to_response(template_service._entity_to_dto(template))
    except TemplateNotFoundError:
        raise HTTPException(status_code=404, detail="Template not found")
    except TemplateAccessDeniedError:
        raise HTTPException(status_code=403, detail="Access denied")


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