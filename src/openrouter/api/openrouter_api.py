import httpx
import os
from dotenv import load_dotenv
import json

from ..domain.entities import LLMMessage

class OpenRouterAPI:
    """OpenRouter APIとの通信を担当するクラス"""
    
    # 基本URL定義
    BASE_URL = "https://openrouter.ai/api/v1"
    COMPLETION_ENDPOINT = "/chat/completions"
    MODELS_ENDPOINT = "/models"
    
    def __init__(self, api_key: str | None = None, default_model: str = "anthropic/claude-3-haiku"):
        """
        OpenRouterAPI のコンストラクタ
        
        Args:
            api_key: OpenRouter API キー
            default_model: デフォルトで使用するモデル名
        """
        # APIキーの取得
        self.api_key = api_key or self._get_api_key()
        self.default_model = default_model
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": "null_po",  # ご自身のサイトURLに変更してください
            "X-Title": "cb_back_local"  # アプリケーション名に変更してください
        }
    
    def _get_api_key(self) -> str:
        """
        APIキーを環境変数または.envファイルから取得する
        
        Returns:
            str: APIキー
            
        Raises:
            ValueError: APIキーが見つからない場合
        """
        # 環境変数から取得を試みる
        api_key = os.environ.get("OPENROUTER_API_KEY")
        if not api_key:
            # .envファイルからの読み込みを試みる
            load_dotenv()
            api_key = os.environ.get("OPENROUTER_API_KEY")
            if not api_key:
                raise ValueError("API キーが指定されていません。環境変数または.envファイルで指定してください。")
        return api_key
    
    async def request_completion(
        self,
        messages: list[LLMMessage],
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 1000,
        stream: bool = False,
        **kwargs
    ) -> dict:
        """LLM補完リクエストを送信するメソッド"""
        url = f"{self.BASE_URL}{self.COMPLETION_ENDPOINT}"
        
        # メッセージを辞書形式に変換
        message_dicts = [msg.to_dict() for msg in messages]
        
        # リクエストデータの構築
        data = {
            "model": model or self.default_model,
            "messages": message_dicts,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": stream,
            **kwargs
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=self.headers, json=data)
            response.raise_for_status()
            
            if stream:
                return await self._handle_streaming_response(response)
            else:
                return response.json()
    
    async def _handle_streaming_response(self, response: httpx.Response) -> dict:
        """ストリーミングレスポンスを処理する内部メソッド"""
        # 実際のストリーミング処理はアプリケーションの要件に応じて実装
        raise NotImplementedError("ストリーミングレスポンスの処理は実装されていません")
    
    async def get_available_models(self) -> dict:
        """利用可能なモデルを取得するメソッド"""
        url = f"{self.BASE_URL}{self.MODELS_ENDPOINT}"
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=self.headers)
            response.raise_for_status()
            return response.json()
    
    def set_default_model(self, model: str) -> None:
        """デフォルトモデルを設定するメソッド"""
        self.default_model = model
    
    def update_headers(self, new_headers: dict[str, str]) -> None:
        """ヘッダー情報を更新するメソッド"""
        self.headers.update(new_headers)
        
    def set_base_url(self, base_url: str) -> None:
        """ベースURLを変更するメソッド"""
        self.BASE_URL = base_url
        
    def set_endpoint(self, endpoint_name: str, endpoint_path: str) -> None:
        """エンドポイントのパスを変更するメソッド"""
        if endpoint_name == "COMPLETION_ENDPOINT":
            self.COMPLETION_ENDPOINT = endpoint_path
        elif endpoint_name == "MODELS_ENDPOINT":
            self.MODELS_ENDPOINT = endpoint_path
        else:
            raise ValueError(f"不明なエンドポイント名: {endpoint_name}")