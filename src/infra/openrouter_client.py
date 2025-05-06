import os
import httpx
from dotenv import load_dotenv

from ..entity.message_entity import MessageEntity, Role

class OpenRouterLLMService:
    """OpenRouter APIと連携するLLMサービスの実装"""
    
    # 基本URL定義
    BASE_URL = "https://openrouter.ai/api/v1"
    CHAT_ENDPOINT = "/chat/completions"
    
    def __init__(
        self,
        api_key: str = None,
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
        self.client = None
        
    async def __aenter__(self):
        """非同期コンテキストマネージャとしての初期化"""
        self.client = httpx.AsyncClient()
        return self

    async def __aexit__(self, exc_type, exc_value, traceback) -> None:
        """非同期コンテキストマネージャとしての終了処理"""
        if self.client:
            await self.client.aclose()
        if exc_type:
            raise exc_type
            
    def set_model(self, model_name: str) -> None:
        """
        使用するモデルを設定する
        
        Args:
            model_name: 使用するモデル名
        """
        self.model = model_name
    
    @staticmethod
    def _convert_to_api_messages(messages: list[MessageEntity]) -> list[dict]:
        """
        Message型からOpenRouter APIが期待する形式に変換する
        
        Args:
            messages: Message型のリスト
            
        Returns:
            OpenRouter APIフォーマットのメッセージリスト
        """
        return [
            {
                "role": message.role.value,  # Role列挙型から文字列値を取得
                "content": message.content
            }
            for message in messages
        ]
        
    async def complete_message(self, messages: list[MessageEntity]) -> tuple[MessageEntity, dict]:
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
        url = f"{self.BASE_URL}{self.CHAT_ENDPOINT}"
        
        # Message型からOpenRouter APIが期待する形式に変換
        formatted_messages = self._convert_to_api_messages(messages)
        # リクエストデータの構築
        data = {
            "model": self.model,
            "messages": formatted_messages,
            "temperature": 0.7,  # デフォルト値
            "max_tokens": 1000   # デフォルト値
        }
        # クライアントの存在確認
        if not self.client:
            raise RuntimeError("このクラスはコンテキストマネージャとしてのみ使用できます。'async with'構文を使用してください。")
        try:
            response = await self.client.post(
                url, 
                headers=self.headers, 
                json=data,
            )
            response.raise_for_status()  # エラーが発生した場合は例外を発生させる
            response_data = response.json()
            # 応答からコンテンツを抽出
            try:
                content = response_data["choices"][0]["message"]["content"]
            except (KeyError, IndexError) as e:
                raise ValueError(f"OpenRouter API レスポンスの解析に失敗しました: {e}, レスポンス: {response_data}")
            
            message = MessageEntity(
                id=-1,  # ダミー値、上位層で適切に設定される必要がある
                uuid=None,  # ダミー値、上位層で適切に設定される必要がある
                role=Role.ASSISTANT,
                content=content
            )
            return message, response_data
            
        except Exception as e:
            raise e