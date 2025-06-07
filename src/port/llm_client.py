from typing import Protocol, AsyncGenerator

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

    async def complete_message_stream(self, messages: list[dict]) -> AsyncGenerator[dict, None]:
        """
        メッセージリストをLLMに送信し、ストリーミング形式で応答を取得する
        
        Args:
            messages: 送信するメッセージのリスト
            
        Yields:
            LLMからのストリーミング応答チャンク
        """

    def set_model(self, model_name: str) -> None:
        """
        使用するモデルを設定する
        
        Args:
            model_name: 使用するモデル名
        """