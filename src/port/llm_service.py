from typing import Protocol#, AsyncIterable
from ..entity.message import Message

class LLMService(Protocol):
    """LLMサービスとの通信を抽象化するインターフェース"""
    
    async def send_message(self, messages: list[Message]) -> Message:
        """
        メッセージリストをLLMに送信し、応答テキストを取得する
        
        Args:
            messages: 送信するメッセージのリスト
            
        Returns:
            LLMからの応答メッセージ
        """
    
    # ストリーミング関連のメソッド (必要に応じて実装)
    # async def stream_messages(self, messages: list[Message]) -> AsyncIterator[str]:
    #     """
    #     メッセージリストをLLMに送信し、応答をストリーミングで取得する
        
    #     Args:
    #         messages: 送信するメッセージのリスト
            
    #     Returns:
    #         応答のチャンクを返すAsyncイテレータ
    #     """
    #     ...
        
    # モデル設定のメソッド
    def set_model(self, model_name: str) -> None:
        """
        使用するモデルを設定する
        
        Args:
            model_name: 使用するモデル名
        """