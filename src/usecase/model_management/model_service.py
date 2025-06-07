from typing import List, Optional
import logging

from src.domain.entity.model_entity import ModelEntity
from src.infra.openrouter_client import OpenRouterLLMService
from src.infra.tortoise_client.model_cache_repo import TortoiseModelCacheRepository as ModelCacheRepository


class ModelManagementService:
    """モデル管理に関するビジネスロジックを担当するサービス"""
    
    def __init__(self, llm_service: OpenRouterLLMService):
        self.llm_service = llm_service
        self.cache_repo = ModelCacheRepository()
        self.logger = logging.getLogger(__name__)
    
    async def get_available_models(self, category: Optional[str] = None) -> List[ModelEntity]:
        """
        利用可能なモデル一覧を取得する（キャッシュ機能付き）
        
        Args:
            category: モデルのカテゴリでフィルタリング（オプション）
            
        Returns:
            利用可能なモデルのリスト
        """
        try:
            # キャッシュが有効かチェック
            if await self.cache_repo.is_cache_valid():
                self.logger.info("Using cached models data")
                cached_models = await self.cache_repo.get_cached_models()
                if cached_models:
                    return self._filter_by_category(cached_models, category)
            
            # キャッシュが無効またはデータがない場合、APIから取得
            self.logger.info("Fetching fresh models data from OpenRouter API")
            try:
                fresh_models = await self.llm_service.get_available_models(category)
                
                # キャッシュを更新
                await self.cache_repo.update_cache(fresh_models)
                self.logger.info(f"Updated models cache with {len(fresh_models)} models")
                
                return fresh_models
                
            except Exception as api_error:
                # API呼び出しが失敗した場合、古いキャッシュデータを返す
                self.logger.warning(f"OpenRouter API failed, falling back to cached data: {api_error}")
                cached_models = await self.cache_repo.get_cached_models()
                if cached_models:
                    self.logger.info(f"Using stale cached data: {len(cached_models)} models")
                    return self._filter_by_category(cached_models, category)
                else:
                    # キャッシュもない場合は例外を再発生
                    self.logger.error("No cached data available and API failed")
                    raise api_error
                    
        except Exception as e:
            self.logger.error(f"Error in get_available_models: {e}")
            raise
    
    def _filter_by_category(self, models: List[ModelEntity], category: Optional[str]) -> List[ModelEntity]:
        """
        モデルリストをカテゴリでフィルタリング
        
        Args:
            models: フィルタリング対象のモデルリスト
            category: フィルタリングカテゴリ（Noneの場合はフィルタリングしない）
            
        Returns:
            フィルタリングされたモデルリスト
        """
        if not category:
            return models
        
        # 実際のカテゴリフィルタリングロジックは必要に応じて実装
        # OpenRouterのAPIがカテゴリをサポートしている場合の実装
        return models
    
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
    
    async def validate_model_id_with_cache_refresh(self, model_id: str) -> bool:
        """
        モデルIDを検証し、キャッシュにない場合は自動的にAPI再取得する
        
        Args:
            model_id: 検証するモデルID
            
        Returns:
            モデルIDが有効な場合True、そうでなければFalse
        """
        try:
            # まずキャッシュで確認
            if await self.cache_repo.model_exists_in_cache(model_id):
                return True
            
            # キャッシュにない場合、API再取得して確認
            self.logger.info(f"Model {model_id} not found in cache, refreshing from API")
            fresh_models = await self.get_available_models()
            return self.validate_model_id(model_id, fresh_models)
            
        except Exception as e:
            self.logger.error(f"Error validating model ID {model_id}: {e}")
            return False
    
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