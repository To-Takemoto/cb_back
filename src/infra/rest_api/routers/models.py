from fastapi import APIRouter, Depends, HTTPException
from typing import Optional

from ...auth import get_current_user
from ..dependencies import get_llm_client_dependency
from ....usecase.model_management.model_service import ModelManagementService
from ....port.dto.model_dto import ModelListResponseDto, ModelDto, ModelSelectionRequestDto, ModelArchitectureDto, ModelPricingDto
from ....infra.logging_config import get_logger

router = APIRouter(
    prefix="/api/v1/models",
    tags=["models"]
)

logger = get_logger("api.models")

def get_model_service(llm_client = Depends(get_llm_client_dependency)) -> ModelManagementService:
    """モデル管理サービスの依存性注入"""
    return ModelManagementService(llm_client)

@router.get("/", response_model=ModelListResponseDto)
async def get_available_models(
    category: Optional[str] = None,
    current_user_id: str = Depends(get_current_user),
    model_service: ModelManagementService = Depends(get_model_service)
):
    """
    利用可能なモデル一覧を取得する
    
    Args:
        category: モデルのカテゴリでフィルタリング（オプション）
        
    Returns:
        利用可能なモデルのリスト
    """
    try:
        models = await model_service.get_available_models(category)
        
        # EntityをDTOに変換
        model_dtos = []
        for model in models:
            architecture_dto = None
            if model.architecture:
                architecture_dto = ModelArchitectureDto(
                    input_modalities=model.architecture.input_modalities,
                    output_modalities=model.architecture.output_modalities,
                    tokenizer=model.architecture.tokenizer
                )
            
            pricing_dto = None
            if model.pricing:
                pricing_dto = ModelPricingDto(
                    prompt=model.pricing.prompt,
                    completion=model.pricing.completion
                )
            
            model_dto = ModelDto(
                id=model.id,
                name=model.name,
                created=model.created,
                description=model.description,
                architecture=architecture_dto,
                pricing=pricing_dto,
                context_length=model.context_length
            )
            model_dtos.append(model_dto)
        
        logger.info(f"Retrieved {len(model_dtos)} models for user {current_user_id}")
        return ModelListResponseDto(data=model_dtos)
        
    except Exception as e:
        logger.error(f"Failed to get available models for user {current_user_id}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve models")

@router.post("/select")
async def select_model(
    req: ModelSelectionRequestDto,
    current_user_id: str = Depends(get_current_user),
    model_service: ModelManagementService = Depends(get_model_service)
):
    """
    使用するモデルを選択・設定する
    
    Args:
        req: モデル選択リクエスト
        
    Returns:
        選択結果のメッセージ
    """
    try:
        # 利用可能なモデル一覧を取得してバリデーション
        available_models = await model_service.get_available_models()
        
        if not model_service.validate_model_id(req.model_id, available_models):
            raise HTTPException(
                status_code=400, 
                detail=f"Model '{req.model_id}' is not available"
            )
        
        # モデルを設定
        model_service.set_model(req.model_id)
        
        logger.info(f"User {current_user_id} selected model: {req.model_id}")
        return {
            "detail": f"Model '{req.model_id}' selected successfully",
            "model_id": req.model_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to select model {req.model_id} for user {current_user_id}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to select model")

@router.get("/current")
async def get_current_model(
    current_user_id: str = Depends(get_current_user),
    model_service: ModelManagementService = Depends(get_model_service)
):
    """
    現在選択されているモデルを取得する
    
    Returns:
        現在のモデル情報
    """
    try:
        current_model_id = model_service.get_current_model()
        
        logger.info(f"Current model for user {current_user_id}: {current_model_id}")
        return {
            "model_id": current_model_id
        }
        
    except Exception as e:
        logger.error(f"Failed to get current model for user {current_user_id}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to get current model")