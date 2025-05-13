import uuid as uuidGen
from peewee import SqliteDatabase
from peewee import DoesNotExist

from ...entity.chat_tree import ChatTree, ChatStructure
from ...entity.message_entity import MessageEntity, Role
from ...port.dto.message_dto import MessageDTO
from ..presentators import format_api_input, format_api_response
from .peewee_models import User, LLMDetails, DiscussionStructure, db_proxy
from .peewee_models import Message as mm


class SqliteClient:
    def __init__(self, user_id: int):
        db = SqliteDatabase("data/sqlite.db")
        db_proxy.initialize(db)
        self.user = User.get_by_id(user_id)

    def save_message(
            self,
            discussion_structure_uuid: str,
            message_dto: MessageDTO,
            ) -> MessageEntity:
        "面倒で一部未実装。"
        target_structure = DiscussionStructure.get(DiscussionStructure.uuid == discussion_structure_uuid)
        query = {
            "discussion": target_structure,
            "owner": self.user,
            "uuid": uuidGen.uuid4(),
            "role": message_dto.role.value,
            "content": message_dto.content,
        }
        inserted_message:mm = mm.create(**query)
        filled_message_entity = MessageEntity(
            id = inserted_message.id,
            uuid = inserted_message.uuid,
            role = self.evaluate_role(inserted_message.role),
            content = inserted_message.content
            )
        if message_dto.role.value == "assistant":
            pass#ここにllmのメッセージの詳細を突っ込むロジックを用意すべき。
        return filled_message_entity
        
    @staticmethod
    def evaluate_role(role: str) -> Role:
        "これダメだろ、ほんとは。"
        if role == "user":
            return Role.USER
        elif role == "assistant":
            return Role.ASSISTANT
        elif role == "system":
            return Role.SYSTEM
        else:
            raise ValueError(f"想定外のrole;{role}が渡されました。")

    def init_structure(self, initial_message_dto: MessageDTO) -> ChatTree:
        query = {
            "owner": self.user,
            "uuid": uuidGen.uuid4(),
            "structure": "何もなし。"
        }
        null_strucuture:DiscussionStructure = DiscussionStructure.create(**query)
        saved_message = self.save_message(null_strucuture.uuid, initial_message_dto)
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

    def get_latest_message_by_discussion(self, discussion_uuid: str) -> MessageEntity:
        """
        指定されたdiscussion_uuidに属する最も作成日時が新しいメッセージを取得し、
        MessageEntityとして返します。
        
        Args:
            discussion_uuid: 取得対象となるディスカッションのUUID
            
        Returns:
            MessageEntity: 最新のメッセージエンティティ
            
        Raises:
            DoesNotExist: 該当するディスカッションが存在しない場合や、
                        メッセージが存在しない場合に発生します。
        """
        # 対象のディスカッション構造を取得
        target_structure = DiscussionStructure.get(DiscussionStructure.uuid == discussion_uuid)
        
        # 該当するディスカッションで最新のメッセージを取得
        latest_message = (mm
                        .select()
                        .where(mm.discussion == target_structure)
                        .order_by(mm.created_at.desc())
                        .first())
        
        if latest_message is None:
            raise DoesNotExist("指定されたディスカッションにメッセージが存在しません。")
        
        # MessageEntityに変換して返す
        return MessageEntity(
            id=latest_message.id,
            uuid=latest_message.uuid,
            role=self.evaluate_role(latest_message.role),
            content=latest_message.content
    )

    def get_history(self, message_uuids: list[str]) -> list[MessageEntity]:
        """
        指定されたUUIDのリストに対応するメッセージを取得し、
        MessageEntityのリストとして返します。
        
        Args:
            message_uuids: 取得対象となるメッセージUUIDのリスト
            
        Returns:
            list[MessageEntity]: MessageEntityのリスト（UUIDリストと同じ順序で返される）
        """
        # 結果格納用のリスト
        result_entities = []
        
        for uuid in message_uuids:
            try:
                # UUIDに対応するメッセージを取得
                message = mm.get(mm.uuid == uuid)
                
                # MessageEntityに変換
                message_entity = MessageEntity(
                    id=message.id,
                    uuid=message.uuid,
                    role=self.evaluate_role(message.role),
                    content=message.content
                )
                
                # 結果リストに追加
                result_entities.append(message_entity)
                
            except DoesNotExist:
                raise DoesNotExist("対象のuuidを持つメッセージがdbにないようで。")
        
        return result_entities