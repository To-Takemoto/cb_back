import os
import httpx
from dotenv import load_dotenv

from .presentators import format_api_response, format_api_input
from ..domain.entity.message_entity import MessageEntity, Role

class OpenRouterLLMService:
    """OpenRouter APIと連携するLLMサービスの実装"""
    
    # 基本URL定義
    BASE_URL = "https://openrouter.ai/api/v1"
    CHAT_ENDPOINT = "/chat/completions"
    
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
        self.client = None
            
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
        self.client = httpx.AsyncClient()

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
            response = await self.client.post(
                url, 
                headers=self.headers, 
                json=data,
            )
            response.raise_for_status()  # エラーが発生した場合は例外を発生させる
            response_data = response.json()
            # 応答からコンテンツを抽出

            flatten_response_data = format_api_response.flatten_api_response(response_data)

            return flatten_response_data
            
        except Exception as e:
            raise e
        
        finally:
            await self.client.aclose()