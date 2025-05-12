from typing import Protocol#, AsyncIterable

class LLMClient(Protocol):
    """LLMサービスとの通信を抽象化するインターフェース"""
    
    async def complete_message(self, messages: list[dict]) -> dict:
        """
        メッセージリストをLLMに送信し、応答テキストを取得する
        
        Args:
            messages: 送信するメッセージのリスト
            
        Returns:
            LLMからの応答メッセージ
        """

    def set_model(self, model_name: str) -> None:
        """
        使用するモデルを設定する
        
        Args:
            model_name: 使用するモデル名
        """