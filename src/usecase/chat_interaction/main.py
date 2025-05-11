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

    def start_new_chat(self, initial_strings: str = None) -> None:
        initial_message = MessageEntity(None, None, Role.SYSTEM, initial_strings)
        new_tree = self.chat_repo.init_structure(initial_message)
        self.structure_handler.store_tree(new_tree)
        self.structure_handler.set_latest()

    async def continue_chat(self, user_message_strings: str) -> MessageEntity:
        user_message = MessageEntity(None, None, Role.USER, user_message_strings)
        filled_user_message = self.chat_repo.save_message(self.structure_handler.chat_tree.uuid, user_message)
        self.structure_handler.append_message(filled_user_message)
        self.chat_repo.update_tree(self.structure_handler.chat_tree)
        fllatten_chat_history_uuid = self.structure_handler.get_current_path()
        flatten_chat_history = self.chat_repo.get_history(fllatten_chat_history_uuid)
        async with self.llm_client:
            llm_message, full_data = await self.llm_client.complete_message(flatten_chat_history)
        filled_llm_message = self.chat_repo.save_message(self.structure_handler.chat_tree.uuid, llm_message, full_data)
        self.structure_handler.append_message(filled_llm_message)
        self.chat_repo.update_tree(self.structure_handler.chat_tree)
        return filled_llm_message
    
    def restart_chat(self, chat_uuid: str):
        #print(self.chat_repo.load_tree(chat_uuid))
        self.structure_handler.store_tree(self.chat_repo.load_tree(chat_uuid))
        self.structure_handler.set_latest()

    def select_message(self, message_uuid):
        self.structure_handler.select_node(message_uuid)
