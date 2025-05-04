import uuid as uuidGen
from peewee import SqliteDatabase

from ...entity.chat_tree import ChatTree, ChatStructure
from ...entity.message_entity import MessageEntity, Role
from .peewee_models import User, LLMDetails, DiscussionStructure, db_proxy
from .peewee_models import Message as mm


class SqliteClient:
    def __init__(self, owner: User = None):
        db = SqliteDatabase("data/sqlite.db")
        db_proxy.initialize(db)
        if not owner:
            self.owner = User.get_by_id(1)
        else:
            self.owner = owner

    def save_message(
            self,
            discussion_structure: DiscussionStructure,
            message: MessageEntity
            ) -> MessageEntity:
        "面倒で一部未実装。"
        query = {
            "discussion": discussion_structure,
            "owner": self.owner,
            "uuid": uuidGen.uuid4(),
            "role": message.role.value,
            "content": message.content,
        }
        inserted_message = mm.create(**query)
        filled_message_entity = MessageEntity(
            id = inserted_message.id,
            uuid = inserted_message.uuid,
            role = self.evaluate_role(inserted_message.role),
            content = inserted_message.content
            )
        if message.role == Role.ASSISTANT:
            pass#ここにllmのメッセージの詳細を突っ込むロジックを用意すべき。
        return filled_message_entity
        
    @staticmethod
    def evaluate_role(role: str) -> Role:
        "これダメだろ、ほんとは。"
        if role == "user":
            return Role.USER
        if role == "assistant":
            return Role.ASSISTANT
        if role == "system":
            return Role.SYSTEM

    def init_structure(self, initial_message: MessageEntity) -> ChatTree:
        query = {
            "owner": self.owner,
            "uuid": uuidGen.uuid4(),
            "structure": "何もなし。"
        }
        null_strucuture:DiscussionStructure = DiscussionStructure.create(**query)
        saved_message = self.save_message(null_strucuture, initial_message)
        #pickleなんかを用いてORDBみたいに使い、nodemixinで作られたtreeをいい感じに保存する必要がある。
        new_tree = ChatTree(
            id = null_strucuture.id,
            uuid = null_strucuture.uuid,
            tree = ChatStructure(saved_message.uuid, None)
        )
        filled_tree: DiscussionStructure = null_strucuture.get_by_id(null_strucuture.id)
        filled_tree.structure = new_tree.get_tree_bin()
        filled_tree.save()

        return new_tree
        

    def load_tree(self, uuid: str) -> ChatTree:
        target_tree_record:DiscussionStructure = DiscussionStructure.get(DiscussionStructure.uuid == uuid)
        target_tree = ChatTree(
            id = target_tree_record.id,
            uuid = target_tree_record.uuid,
            tree = None
        )
        target_tree.revert_tree_from_bin(target_tree_record.structure)
        return target_tree

    def update_tree(self, new_tree: ChatTree) -> None:
        tree_uuid = new_tree.uuid
        tree_bin = new_tree.get_tree_bin()
        previous_tree: DiscussionStructure = DiscussionStructure.get(DiscussionStructure.uuid == tree_uuid)
        previous_tree.structure = tree_bin
        previous_tree.save()
