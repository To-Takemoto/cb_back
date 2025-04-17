from ..entity.message import Message, Role
from ..port.message_repo import MessageRepository
from ..port.llm_service import LLMService

class LLMInteractionUC:
    def __init__(
        self,
        llm_service: LLMService,
        message_repository: MessageRepository|None = None,
        ) -> None:
        self.llm_service = llm_service
        self.message_repository = message_repository
    
    async def send_and_receive_message(
        self,
        prompt_message: str,
        conversation_id: str|None = None,
        ) -> Message:
        """
        メッセージを送信し、LLMからの返答を取得する。
        
        Args:
            prompt_message: 送信するメッセージ
            conversation_id: 会話ID（Noneの場合は履歴を使用しない）
            
        Returns:
            LLMからの応答メッセージ
        """
        # メッセージの保存とリポジトリからの会話履歴取得
        history: list[Message] = []
        message = Message(None, None, Role.USER, prompt_message)
        if self.message_repository and conversation_id:
            try:
                saved_message = await self.message_repository.save(message, conversation_id)
                history = await self.message_repository.get_conversation_history(conversation_id)
                history.append(saved_message)
            except Exception as e:
                raise e
        else:
            # リポジトリがない場合は単一メッセージのみ使用
            history = [message]
            
        # LLMとの通信
        try:
            async with self.llm_service:
                completed_message = await self.llm_service.send_message(history)
            
            # レスポンスの保存
            if self.message_repository and conversation_id:
                saved_completed_message = await self.message_repository.save(completed_message, conversation_id)
                return saved_completed_message
            return completed_message
        except Exception as e:
            # LLM通信エラーの処理
            print(f"Error communicating with LLM: {e}")
            raise  # 必要に応じて適切な例外に変換