from typing import Optional, Callable, List
from ...domain.entity.chat_tree import ChatTree, ChatStructure
from ...domain.entity.message_entity import MessageEntity
from ...domain.exception.chat_exceptions import ChatNotFoundError, MessageNotFoundError, InvalidTreeStructureError
from ...port.chat_repo import ChatRepository

class StructureHandle:
    def __init__(self, chat_repo: ChatRepository) -> None:
        self.chat_repo = chat_repo
        self.chat_tree: Optional[ChatTree] = None
        self.current_node: Optional[ChatStructure] = None

    def store_tree(self, tree: ChatTree) -> None:
        if tree is None:
            raise InvalidTreeStructureError("Cannot store None tree")
        self.chat_tree = tree
        self._set_latest()

    def append_message(self, message: MessageEntity) -> None:
        if self.current_node is None:
            raise InvalidTreeStructureError("No current node set")
        new_structure = ChatStructure(message.uuid, self.current_node)
        self.current_node = new_structure

    def get_current_path(self) -> List[str]:
        if self.current_node is None:
            return []
        return [node.uuid for node in self.current_node.path]
    
    def select_node(self, message_uuid: str) -> None:
        if self.chat_tree is None or self.chat_tree.tree is None:
            raise InvalidTreeStructureError("No tree loaded")
            
        try:
            target_node = self._pick_nodes_with_descendants(
                self.chat_tree.tree,
                lambda node: str(getattr(node, "uuid", None)) == str(message_uuid)
            )
            self.current_node = target_node
        except ValueError:
            raise MessageNotFoundError(message_uuid)
        
    def get_uuid(self) -> str:
        return self.chat_tree.uuid
    
    def get_chat_tree(self) -> ChatStructure:
        return self.chat_tree
    
    def get_all_node_uuids(self) -> list[str]:
        """ツリー内の全ノードのUUIDを取得"""
        all_uuids = []
        def recurse(node):
            all_uuids.append(str(node.uuid))
            for child in node.children:
                recurse(child)
        recurse(self.chat_tree.tree)
        return all_uuids
        
    def _set_latest(self) -> None:
        latest_message = self.chat_repo.get_latest_message_by_discussion(self.chat_tree.uuid)
        latest_node = self._pick_nodes_with_descendants(
            self.chat_tree.tree,
            lambda node: str(getattr(node, "uuid", None)) == str(latest_message.uuid))
        self.current_node = latest_node

    def _pick_nodes_with_descendants(self, root: ChatStructure, condition: Callable[[ChatStructure], bool]) -> ChatStructure:
        """指定した条件に一致するノードを検索する"""
        matched = []
        
        def recurse(node: ChatStructure) -> None:
            if condition(node):
                matched.append(node)
            for child in node.children:
                recurse(child)
        
        recurse(root)
        
        if len(matched) > 1:
            raise ValueError("Multiple nodes match the condition")
        elif not matched:
            raise ValueError("No nodes match the condition")
        
        return matched[0]