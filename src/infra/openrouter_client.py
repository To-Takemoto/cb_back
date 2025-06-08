import os
import json
import httpx
import asyncio
from typing import AsyncGenerator
from dotenv import load_dotenv

from .presentators import format_api_response, format_api_input
from ..domain.entity.message_entity import MessageEntity, Role
from ..domain.entity.model_entity import ModelEntity, ModelArchitecture, ModelPricing

class OpenRouterLLMService:
    """OpenRouter APIと連携するLLMサービスの実装"""
    
    # 基本URL定義
    BASE_URL = "https://openrouter.ai/api/v1"
    CHAT_ENDPOINT = "/chat/completions"
    MODELS_ENDPOINT = "/models"
    
    def __init__(
        self,
        api_key: str|None = None,
        default_model: str = "openai/gpt-3.5-turbo"
    ):
        """
        OpenRouterLLMService のコンストラクタ
        
        Args:
            api_key: OpenRouter API キー（Noneの場合は環境変数から取得）
            default_model: デフォルトで使用するモデル名
        """
        # APIキーの取得: 引数 → 環境変数 → .envファイル の優先順
        self.api_key = api_key or os.environ.get("OPENROUTER_API_KEY")
        if not self.api_key:
            # .envファイルからの読み込みを試みる
            load_dotenv()
            self.api_key = os.environ.get("OPENROUTER_API_KEY")
            if not self.api_key:
                raise ValueError("API キーが指定されていません。引数、環境変数、または.envファイルで指定してください。")
        
        self.model = default_model
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": "null_po",
            "X-Title": "cb_back_local"
        }
        self._client = None
        self._client_lock = asyncio.Lock()
            
    async def _ensure_client(self) -> httpx.AsyncClient:
        """スレッドセーフなクライアント取得"""
        if self._client is None:
            async with self._client_lock:
                if self._client is None:  # ダブルチェックロッキング
                    self._client = httpx.AsyncClient(timeout=30.0)
        return self._client

    def set_model(self, model_name: str) -> None:
        """
        使用するモデルを設定する
        
        Args:
            model_name: 使用するモデル名
        """
        self.model = model_name
        
    async def complete_message(self, messages: list[MessageEntity]) -> dict:
        """
        メッセージリストをLLMに送信し、応答テキストとメタデータを含む生のレスポンスを取得する
        
        Args:
            messages: 送信するメッセージのリスト
            
        Returns:
            (LLMからの応答メッセージ, 生のレスポンスデータ)のタプル
        
        注意:
            この実装では、返却するMessageオブジェクトのid, uuidフィールドには
            値が設定されません。これらの値はアプリケーション層または
            サービス層で設定する必要があります。
        """
        client = await self._ensure_client()

        message_dict_list = format_api_input.format_entity_list_to_dict_list(messages)
        
        #urlの作成
        url = f"{self.BASE_URL}{self.CHAT_ENDPOINT}"
        # リクエストデータの構築
        data = {
            "model": self.model,
            "messages": message_dict_list,
            "temperature": 0.7,  # デフォルト値
            "max_tokens": 1000   # デフォルト値
        }
        try:
            response = await client.post(
                url, 
                headers=self.headers, 
                json=data,
            )
            response.raise_for_status()
            response_data = response.json()
            
            flatten_response_data = format_api_response.flatten_api_response(response_data)
            return flatten_response_data
            
        except httpx.TimeoutException:
            raise TimeoutError("LLM API request timed out")
        except httpx.HTTPStatusError as e:
            raise ConnectionError(f"LLM API error: {e.response.status_code}")
        except Exception as e:
            raise e
    
    async def complete_message_stream(self, messages: list[MessageEntity]) -> AsyncGenerator[dict, None]:
        """
        メッセージリストをLLMに送信し、ストリーミング形式で応答を取得する
        
        Args:
            messages: 送信するメッセージのリスト
            
        Yields:
            LLMからのストリーミング応答チャンク
        """
        client = await self._ensure_client()

        message_dict_list = format_api_input.format_entity_list_to_dict_list(messages)
        
        # URLの作成
        url = f"{self.BASE_URL}{self.CHAT_ENDPOINT}"
        # リクエストデータの構築（ストリーミング用）
        data = {
            "model": self.model,
            "messages": message_dict_list,
            "temperature": 0.7,
            "max_tokens": 1000,
            "stream": True  # ストリーミングを有効化
        }
        
        try:
            async with client.stream(
                "POST",
                url,
                headers=self.headers,
                json=data
            ) as response:
                response.raise_for_status()
                
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        if line == "data: [DONE]":
                            break
                        
                        try:
                            chunk_data = json.loads(line[6:])  # "data: " を除去
                            # チャンクにコンテンツが含まれている場合のみyield
                            if (chunk_data.get("choices") and 
                                chunk_data["choices"][0].get("delta") and
                                chunk_data["choices"][0]["delta"].get("content")):
                                yield chunk_data
                        except json.JSONDecodeError:
                            # 無効なJSONは無視
                            continue
                            
        except httpx.TimeoutException:
            raise TimeoutError("LLM API streaming request timed out")
        except httpx.HTTPStatusError as e:
            raise ConnectionError(f"LLM API streaming error: {e.response.status_code}")
        except Exception as e:
            raise e
    
    async def get_available_models(self, category: str = None) -> list[ModelEntity]:
        """
        利用可能なモデル一覧を取得する
        
        Args:
            category: モデルのカテゴリでフィルタリング（オプション）
            
        Returns:
            利用可能なモデルのリスト
        """
        client = await self._ensure_client()
            
        url = f"{self.BASE_URL}{self.MODELS_ENDPOINT}"
        params = {}
        if category:
            params["category"] = category
            
        try:
            response = await client.get(
                url,
                headers=self.headers,
                params=params
            )
            response.raise_for_status()
            response_data = response.json()
            
            models = []
            for model_data in response_data.get("data", []):
                architecture = None
                if "architecture" in model_data:
                    arch_data = model_data["architecture"]
                    architecture = ModelArchitecture(
                        input_modalities=arch_data.get("input_modalities", []),
                        output_modalities=arch_data.get("output_modalities", []),
                        tokenizer=arch_data.get("tokenizer", "")
                    )
                
                pricing = None
                if "pricing" in model_data:
                    price_data = model_data["pricing"]
                    pricing = ModelPricing(
                        prompt=price_data.get("prompt", "0"),
                        completion=price_data.get("completion", "0")
                    )
                
                model = ModelEntity(
                    id=model_data["id"],
                    name=model_data["name"],
                    created=model_data["created"],
                    description=model_data.get("description"),
                    architecture=architecture,
                    pricing=pricing,
                    context_length=model_data.get("context_length")
                )
                models.append(model)
                
            return models
            
        except httpx.TimeoutException:
            raise TimeoutError("Models API request timed out")
        except httpx.HTTPStatusError as e:
            raise ConnectionError(f"Models API error: {e.response.status_code}")
        except Exception as e:
            raise e

    async def aclose(self):
        """HTTPクライアントを閉じる"""
        if self._client is not None:
            await self._client.aclose()
            self._client = None
    
    async def __aenter__(self):
        """非同期コンテキストマネージャーのエントリー"""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """非同期コンテキストマネージャーの終了時にリソースをクリーンアップ"""
        await self.aclose()