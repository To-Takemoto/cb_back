import uuid as uuidGen
from peewee import SqliteDatabase, DoesNotExist

from ...domain.entity.chat_tree import ChatTree, ChatStructure
from ...domain.entity.message_entity import MessageEntity, Role
from ...port.dto.message_dto import MessageDTO
from .peewee_models import User, LLMDetails, DiscussionStructure, db_proxy
from .peewee_models import Message as mm

class ChatRepo:
    def __init__(self, user_id: int):
        # DB接続・初期化
        db = SqliteDatabase("data/sqlite.db")
        db_proxy.initialize(db)
        db.connect()
        self.user = User.get_by_id(user_id)

    def save_message(
        self,
        discussion_structure_uuid: str,
        message_dto: MessageDTO,
        llm_details: dict | None = None
    ) -> MessageEntity:
        """
        メッセージを保存し、MessageEntityを返却
        """
        target_structure = DiscussionStructure.get(
            DiscussionStructure.uuid == discussion_structure_uuid
        )
        # ForeignKeyはIDで指定
        inserted = mm.create(
            discussion_id=target_structure.id,
            owner_id=self.user.id,
            uuid=uuidGen.uuid4(),
            role=message_dto.role.value,
            content=message_dto.content,
        )
        message_entity = MessageEntity(
            id=inserted.id,
            uuid=inserted.uuid,
            role=self.evaluate_role(inserted.role),
            content=inserted.content
        )
        # LLM詳細保存ロジックは未実装
        return message_entity

    @staticmethod
    def evaluate_role(role: str) -> Role:
        if role == "user":
            return Role.USER
        if role == "assistant":
            return Role.ASSISTANT
        if role == "system":
            return Role.SYSTEM
        raise ValueError(f"想定外のrole; {role}")

    def init_structure(self, initial_message_dto: MessageDTO) -> tuple[ChatTree, MessageEntity]:
        """
        新規チャット構造を作成し、初期メッセージを保存
        """
        # DiscussionStructureを作成
        base = DiscussionStructure.create(
            owner_id=self.user.id,
            uuid=uuidGen.uuid4(),
            structure=b""
        )
        # 初期メッセージを保存
        saved_msg = self.save_message(base.uuid, initial_message_dto)

        # ChatTree生成と構造バイナリ化
        new_tree = ChatTree(
            id=base.id,
            uuid=base.uuid,
            tree=ChatStructure(saved_msg.uuid, None)
        )
        base.structure = new_tree.get_tree_bin()
        base.save()

        return new_tree, saved_msg

    def load_tree(self, uuid: str) -> ChatTree:
        record = DiscussionStructure.get(DiscussionStructure.uuid == uuid)
        tree = ChatTree(id=record.id, uuid=record.uuid, tree=None)
        tree.revert_tree_from_bin(record.structure)
        return tree

    def update_tree(self, new_tree: ChatTree) -> None:
        record = DiscussionStructure.get(DiscussionStructure.uuid == new_tree.uuid)
        record.structure = new_tree.get_tree_bin()
        record.save()

    def get_latest_message_by_discussion(self, discussion_uuid: str) -> MessageEntity:
        target = DiscussionStructure.get(DiscussionStructure.uuid == discussion_uuid)
        last = (mm
            .select()
            .where(mm.discussion == target)
            .order_by(mm.created_at.desc())
            .first()
        )
        if not last:
            raise DoesNotExist("指定ディスカッションにメッセージが存在しません。")
        return MessageEntity(
            id=last.id,
            uuid=last.uuid,
            role=self.evaluate_role(last.role),
            content=last.content
        )

    def get_history(self, message_uuids: list[str]) -> list[MessageEntity]:
        results: list[MessageEntity] = []
        for u in message_uuids:
            try:
                msg = mm.get(mm.uuid == u)
            except DoesNotExist:
                raise DoesNotExist(f"UUID {u} のメッセージが見つかりません。")
            results.append(
                MessageEntity(
                    id=msg.id,
                    uuid=msg.uuid,
                    role=self.evaluate_role(msg.role),
                    content=msg.content
                )
            )
        return results
