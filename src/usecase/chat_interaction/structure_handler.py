from ...domain.entity.chat_tree import ChatTree, ChatStructure
from ...domain.entity.message_entity import MessageEntity
from ...port.chat_repo import ChatRepository

class StructureHandle:
    def __init__(self, chat_repo: ChatRepository) -> None:
        self.chat_repo = chat_repo

    def store_tree(self, tree: ChatTree) -> None:
        self.chat_tree = tree
        self._set_latest()

    def append_message(self, message: MessageEntity) -> None:
        new_structure = ChatStructure(message.uuid, self.current_node)
        self.current_node = new_structure

    def get_current_path(self) -> list[str]:
        return [node.uuid for node in self.current_node.path]
    
    def select_node(self, message_uuid: str) -> None:
        try:
            target_node = self._pick_nodes_with_descendants(
            self.chat_tree.tree,
            lambda node: str(getattr(node, "uuid", None)) == str(message_uuid))
            self.current_node = target_node
        except ValueError as e:
            raise e
        
    def get_uuid(self) -> str:
        return self.chat_tree.uuid
    
    def get_chat_tree(self) -> ChatStructure:
        return self.chat_tree
        
    def _set_latest(self) -> None:
        latest_message = self.chat_repo.get_latest_message_by_discussion(self.chat_tree.uuid)
        latest_node = self._pick_nodes_with_descendants(
            self.chat_tree.tree,
            lambda node: str(getattr(node, "uuid", None)) == str(latest_message.uuid))
        self.current_node = latest_node

    def _pick_nodes_with_descendants(self, root: ChatStructure, condition) -> list[ChatStructure]:
        matched = []
        def recurse(node):
            if condition(node):
                matched.append(node)
            for child in node.children:
                recurse(child)
        recurse(root)
        if len(matched) > 1:
            raise ValueError("条件に一致するノードが複数見つかりました。")
        elif not matched:
            raise ValueError("条件に一致するノードが一つも見つかりませんでした。")
        else:
            return matched[0]