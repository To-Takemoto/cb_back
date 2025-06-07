"""
モデルキャッシュ用のTortoise ORMリポジトリ実装
"""
import json
from datetime import datetime, timedelta, timezone
from typing import List, Optional
from tortoise.exceptions import DoesNotExist

from .models import AvailableModelCache
from src.domain.entity.model_entity import ModelEntity, ModelArchitecture, ModelPricing


class TortoiseModelCacheRepository:
    """モデルキャッシュのCRUD操作を提供するTortoise ORMリポジトリ"""
    
    def __init__(self):
        self.cache_ttl_hours = 24
    
    async def get_cached_models(self) -> List[ModelEntity]:
        """
        キャッシュされたモデル一覧を取得
        
        Returns:
            キャッシュされたモデルのリスト
        """
        try:
            cached_models = await AvailableModelCache.filter(
                is_active=True
            ).order_by('name')
            
            models = []
            for cached_model in cached_models:
                # アーキテクチャ情報の復元
                architecture = None
                if cached_model.architecture_data:
                    try:
                        arch_data = json.loads(cached_model.architecture_data)
                        architecture = ModelArchitecture(
                            input_modalities=arch_data.get("input_modalities", []),
                            output_modalities=arch_data.get("output_modalities", []),
                            tokenizer=arch_data.get("tokenizer", "")
                        )
                    except json.JSONDecodeError:
                        pass
                
                # 価格情報の復元
                pricing = None
                if cached_model.pricing_prompt or cached_model.pricing_completion:
                    pricing = ModelPricing(
                        prompt=cached_model.pricing_prompt or "0",
                        completion=cached_model.pricing_completion or "0"
                    )
                
                model = ModelEntity(
                    id=cached_model.id,
                    name=cached_model.name,
                    created=cached_model.created,
                    description=cached_model.description,
                    architecture=architecture,
                    pricing=pricing,
                    context_length=cached_model.context_length
                )
                models.append(model)
            
            return models
            
        except Exception as e:
            # テーブルが存在しない場合など
            return []
    
    async def is_cache_valid(self) -> bool:
        """
        キャッシュが有効かどうかを判定
        
        Returns:
            True: キャッシュが有効（24時間以内に更新されている）
            False: キャッシュが無効（更新が必要）
        """
        try:
            # 最新の更新時刻を取得
            latest_update = await AvailableModelCache.filter(
                is_active=True
            ).order_by('-last_updated').first()
            
            if not latest_update:
                return False
            
            # 24時間以内かチェック
            now = datetime.now(timezone.utc)
            time_diff = now - latest_update.last_updated.replace(tzinfo=timezone.utc)
            
            return time_diff.total_seconds() < (self.cache_ttl_hours * 3600)
            
        except Exception:
            return False
    
    async def update_cache(self, models: List[ModelEntity]) -> None:
        """
        キャッシュを新しいモデル一覧で更新
        
        Args:
            models: 新しいモデル一覧
        """
        try:
            current_time = datetime.now(timezone.utc)
            
            # 既存のデータを無効化
            await AvailableModelCache.filter(is_active=True).update(is_active=False)
            
            # 新しいデータを挿入
            cache_data = []
            for model in models:
                # アーキテクチャ情報をJSON化
                architecture_json = None
                if model.architecture:
                    architecture_json = json.dumps({
                        "input_modalities": model.architecture.input_modalities,
                        "output_modalities": model.architecture.output_modalities,
                        "tokenizer": model.architecture.tokenizer
                    })
                
                cache_data.append(AvailableModelCache(
                    id=model.id,
                    name=model.name,
                    description=model.description,
                    context_length=model.context_length,
                    pricing_prompt=model.pricing.prompt if model.pricing else None,
                    pricing_completion=model.pricing.completion if model.pricing else None,
                    architecture_data=architecture_json,
                    created=model.created,
                    last_updated=current_time,
                    is_active=True
                ))
            
            if cache_data:
                # バッチ挿入
                await AvailableModelCache.bulk_create(cache_data)
                
        except Exception as e:
            # エラーが発生した場合はログを出力（ここでは pass）
            pass
    
    async def model_exists_in_cache(self, model_id: str) -> bool:
        """
        指定されたモデルIDがキャッシュに存在するかチェック
        
        Args:
            model_id: チェックするモデルID
            
        Returns:
            True: モデルが存在する
            False: モデルが存在しない
        """
        try:
            exists = await AvailableModelCache.filter(
                id=model_id,
                is_active=True
            ).exists()
            return exists
        except Exception:
            return False
    
    async def clear_cache(self) -> None:
        """
        キャッシュをクリア（すべてのエントリを無効化）
        """
        try:
            await AvailableModelCache.filter(is_active=True).update(is_active=False)
        except Exception:
            pass