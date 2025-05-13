from ...entity.message_entity import MessageEntity, Role
from ...port.chat_repo import ChatRepository
from ...port.llm_client import LLMClient
from ...port.dto.message_dto import MessageDTO
from .structure_handler import StructureHandle

class ChatInteraction:
    def __init__(
        self,
        chat_repo: ChatRepository,
        llm_client: LLMClient,
        ) -> None:
        """ """
        self.chat_repo = chat_repo
        self.llm_client = llm_client
        self.structure = StructureHandle(self.chat_repo)
        self.message_store:list[MessageEntity] = []

    def start_new_chat(self, initial_strings: str = None) -> None:
        initial_message_dto = MessageDTO(Role.SYSTEM, initial_strings)
        new_tree = self.chat_repo.init_structure(initial_message_dto)
        self.structure.store_tree(new_tree)

    async def continue_chat(self, user_message_strings: str) -> MessageEntity:
        user_message_dto = MessageDTO(Role.USER, user_message_strings)
        self._process_message(user_message_dto)
        chat_history = self._get_chat_history()
        llm_response = await self.llm_client.complete_message(chat_history)
        llm_message_dict = self._format_llm_response(llm_response)
        llm_message = self._process_message(llm_message_dict)
        return llm_message
    
    def restart_chat(self, chat_uuid: str) -> None:
        chat_tree = self.chat_repo.load_tree(chat_uuid)
        self.structure.store_tree(chat_tree)

    def select_message(self, message_uuid: str) -> None:
        self.structure.select_node(message_uuid)

    def find_message_from_cache(self, message_uuid: str) -> MessageEntity:
        for message in self.message_store:
            if str(message.uuid) == message_uuid:
                return message
        else:
            raise ValueError("uuidを持つmessageなし。")
        
    def _get_chat_history(self) -> list[MessageEntity]:
        chat_history_uuid_list = self.structure.get_current_path()
        chat_history = self.chat_repo.get_history(chat_history_uuid_list)
        return chat_history
        
    def _process_message(self, message_dto: MessageDTO) -> MessageEntity:
        message_entity = self.chat_repo.save_message(
            discussion_structure_uuid = self.structure.get_uuid(),
            message_dto = message_dto
            )
        self._cache_messsage(message_entity)
        self.structure.append_message(message_entity)
        new_tree = self.structure.get_chat_tree()
        self.chat_repo.update_tree(new_tree)
        return message_entity

    def _cache_messsage(self, message: MessageEntity) -> None:
        self.message_store.append(message)

    # @staticmethod
    # def _convert_message_list(message_list: list[MessageEntity]) -> list[dict]:
    #     message_dict_list = []
    #     for message in message_list:
    #         role = str(message.role.value)
    #         content = str(message.content)
    #         message_dict = {"role":role, "content": content}
    #         message_dict_list.append(message_dict)
    #     return message_dict_list
    
    @staticmethod
    def _format_llm_response(llm_response: dict) -> dict:
        return MessageDTO(Role.ASSISTANT, llm_response["choices"][0]["message"]["content"])