from ..entity.message import Message, Role
from ..api.message_repo import MessageRepository
from ..api.llm_service import LLMService

class LLMInteractionUC:
    def __init__(
        self,
        llm_service: LLMService,
        message_repository: MessageRepository,
        ):
        self.llm_service = llm_service
        self.message_repository = message_repository
    
    async def send_and_recieve_message(
        self,
        prompt_message: Message,
        conversation_id: str,
        ) -> Message:
        """
        メッセージを投げつつ、返答を戻り値にする。
        """
        saved_message = await self.message_repository.save(prompt_message, conversation_id)
        self.history = await self.message_repository.get_conversation_history(conversation_id)
        self.history.append(saved_message)
        complited_message = await self.llm_service.send_messages(self.history)
        saved_complited_message = await self.message_repository.save(complited_message)
        self.history.append(saved_complited_message)
        return saved_complited_message
