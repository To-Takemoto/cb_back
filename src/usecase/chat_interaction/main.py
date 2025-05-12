from ...entity.message_entity import MessageEntity, Role
from ...port.chat_repo import ChatRepository
from ...port.llm_client import LLMClient
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
        self.structure_handler = StructureHandle(self.chat_repo)
        self.message_store:list[MessageEntity] = []

    def start_new_chat(self, initial_strings: str = None) -> None:
        initial_message_dict = {"role":"system", "content":initial_strings}
        new_tree = self.chat_repo.init_structure(initial_message_dict)
        self.structure_handler.store_tree(new_tree)
        self.structure_handler.set_latest()

    async def continue_chat(self, user_message_strings: str) -> MessageEntity:
        user_message = {"role":"user", "content": user_message_strings}
        filled_user_message = self.chat_repo.save_message(self.structure_handler.chat_tree.uuid, user_message)
        self._cache_messsage(filled_user_message)
        self.structure_handler.append_message(filled_user_message)
        self.chat_repo.update_tree(self.structure_handler.chat_tree)
        fllatten_chat_history_uuid = self.structure_handler.get_current_path()
        flatten_chat_history = self.chat_repo.get_history(fllatten_chat_history_uuid)
        chat_history = self._convert_message_list(flatten_chat_history)
        async with self.llm_client:
            llm_response = await self.llm_client.complete_message(chat_history)
        llm_message_dict = self._format_llm_response(llm_response)
        filled_llm_message = self.chat_repo.save_message(self.structure_handler.chat_tree.uuid, llm_message_dict)
        self._cache_messsage(filled_llm_message)
        self.structure_handler.append_message(filled_llm_message)
        self.chat_repo.update_tree(self.structure_handler.chat_tree)
        return filled_llm_message
    
    def restart_chat(self, chat_uuid: str) -> None:
        #print(self.chat_repo.load_tree(chat_uuid))
        self.structure_handler.store_tree(self.chat_repo.load_tree(chat_uuid))
        self.structure_handler.set_latest()

    def select_message(self, message_uuid: str) -> None:
        self.structure_handler.select_node(message_uuid)

    def find_message_from_cache(self, message_uuid: str) -> MessageEntity:
        for message in self.message_store:
            if str(message.uuid) == message_uuid:
                return message
        else:
            raise ValueError("uuidを持つmessageなし。")

    def _cache_messsage(self, message: MessageEntity) -> None:
        self.message_store.append(message)

    @staticmethod
    def _convert_message_list(message_list: list[MessageEntity]) -> list[dict]:
        message_dict_list = []
        for message in message_list:
            role = str(message.role.value)
            content = str(message.content)
            message_dict = {"role":role, "content": content}
            message_dict_list.append(message_dict)
        return message_dict_list
    
    @staticmethod
    def _format_llm_response(llm_response: dict) -> dict:
        return {"role":"assistant", "content":llm_response["choices"][0]["message"]["content"]}