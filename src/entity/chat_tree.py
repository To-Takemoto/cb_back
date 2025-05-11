from anytree import NodeMixin

from dataclasses import dataclass
import pickle

#from .message_entity import MessageEntity

class ChatStructure(NodeMixin):
    def __init__(self, message_uuid: str, parent):
        self.uuid = message_uuid
        self.parent = parent

@dataclass
class ChatTree:
    id: int
    uuid: str
    tree: ChatStructure

    def get_tree_bin(self) -> bytes:
        return pickle.dumps(self.tree)
    
    def revert_tree_from_bin(self, tree_bin: bytes) -> None:
        self.tree = pickle.loads(tree_bin)
        