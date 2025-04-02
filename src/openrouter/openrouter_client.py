from .entities import LLMMessage
from openrouter_api import OpenRouterAPI

class OpenRouterClient:
    """
    OpenRouter API クライアントクラス
    ユーザーに公開されるインターフェース
    """
    
    def __init__(self, api_key: str | None = None, default_model: str = "anthropic/claude-3-haiku"):
        """
        OpenRouterClient のコンストラクタ
        
        Args:
            api_key: OpenRouter API キー（Noneの場合は環境変数から取得）
            default_model: デフォルトで使用するモデル名
        """
        # APIインスタンスの初期化
        self.api = OpenRouterAPI(api_key=api_key, default_model=default_model)
    
    async def completion(
        self,
        messages: list[dict[str, str] | LLMMessage],
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 1000,
        stream: bool = False,
        **kwargs
    ) -> dict:
        """
        LLM補完リクエストを非同期で送信する
        
        Args:
            messages: メッセージのリスト（辞書またはLLMMessageオブジェクト）
            model: 使用するモデル名
            temperature: 生成される応答のランダム性
            max_tokens: 生成するトークンの最大数
            stream: ストリーミングレスポンスを使用するか
            **kwargs: その他のパラメータ
            
        Returns:
            dict: APIレスポンス
        """
        # 辞書形式のメッセージをLLMMessageオブジェクトに変換
        message_objects = []
        for msg in messages:
            if isinstance(msg, dict):
                message_objects.append(LLMMessage(role=msg["role"], content=msg["content"]))
            else:
                message_objects.append(msg)
        
        return await self.api.request_completion(
            messages=message_objects,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=stream,
            **kwargs
        )
    
    async def list_models(self) -> dict:
        """
        利用可能なモデルのリストを非同期で取得する
        
        Returns:
            dict: 利用可能なモデルのリスト
        """
        return await self.api.get_available_models()
    
    def set_default_model(self, model: str) -> None:
        """デフォルトモデルを設定する"""
        self.api.set_default_model(model)
    
    def update_headers(self, new_headers: dict[str, str]) -> None:
        """ヘッダー情報を更新する"""
        self.api.update_headers(new_headers)
        
    def set_base_url(self, base_url: str) -> None:
        """ベースURLを変更する"""
        self.api.set_base_url(base_url)
        
    def set_endpoint(self, endpoint_name: str, endpoint_path: str) -> None:
        """エンドポイントのパスを変更する"""
        self.api.set_endpoint(endpoint_name, endpoint_path)