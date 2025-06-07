from typing import List, Optional

from ...domain.entity.model_entity import ModelEntity
from ...infra.openrouter_client import OpenRouterLLMService


class ModelManagementService:
    """モデル管理に関するビジネスロジックを担当するサービス"""
    
    def __init__(self, llm_service: OpenRouterLLMService):
        self.llm_service = llm_service
    
    async def get_available_models(self, category: Optional[str] = None) -> List[ModelEntity]:
        """
        利用可能なモデル一覧を取得する
        
        Args:
            category: モデルのカテゴリでフィルタリング（オプション）
            
        Returns:
            利用可能なモデルのリスト
        """
        return await self.llm_service.get_available_models(category)
    
    def validate_model_id(self, model_id: str, available_models: List[ModelEntity]) -> bool:
        """
        指定されたモデルIDが利用可能なモデルに含まれているかを検証する
        
        Args:
            model_id: 検証するモデルID
            available_models: 利用可能なモデルのリスト
            
        Returns:
            モデルIDが有効な場合True、そうでなければFalse
        """
        return any(model.id == model_id for model in available_models)
    
    def set_model(self, model_id: str) -> None:
        """
        使用するモデルを設定する
        
        Args:
            model_id: 設定するモデルID
        """
        self.llm_service.set_model(model_id)
    
    def get_current_model(self) -> str:
        """
        現在設定されているモデルIDを取得する
        
        Returns:
            現在のモデルID
        """
        return self.llm_service.model