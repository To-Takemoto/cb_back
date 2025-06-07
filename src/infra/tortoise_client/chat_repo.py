import uuid as uuidGen
import pickle
from typing import Optional, Tuple, List, Dict, Any
from datetime import datetime

from ...domain.entity.chat_tree import ChatTree, ChatStructure
from ...domain.entity.message_entity import MessageEntity, Role
from ...port.dto.message_dto import MessageDTO
from ...port.chat_repo import ChatRepository
from .models import User, DiscussionStructure, Message, LLMDetails


class TortoiseChatRepository(ChatRepository):
    """
    Tortoise ORM を用いた ChatRepository の実装
    """
    
    def __init__(self, user_id: int):
        self.user_id = user_id
        self._user_cache = None

    async def save_message(
        self,
        discussion_structure_uuid: str,
        message_dto: MessageDTO,
        llm_details: Optional[dict] = None
    ) -> MessageEntity:
        """メッセージを保存し、MessageEntityを返却"""
        try:
            target_structure = await DiscussionStructure.get(uuid=discussion_structure_uuid)
        except:
            raise ValueError(f"Discussion structure not found: {discussion_structure_uuid}")
        
        # メッセージを作成
        message_uuid = str(uuidGen.uuid4())
        message = await Message.create(
            discussion=target_structure,
            uuid=message_uuid,
            role=message_dto.role.value,
            content=message_dto.content,
            created_at=datetime.utcnow()
        )
        
        # LLM詳細が提供されている場合は保存
        if llm_details:
            await LLMDetails.create(
                message=message,
                model=llm_details.get('model'),
                provider=llm_details.get('provider'),
                prompt_tokens=llm_details.get('prompt_tokens'),
                completion_tokens=llm_details.get('completion_tokens'),
                total_tokens=llm_details.get('total_tokens')
            )
        
        return MessageEntity(
            id=message.id,
            uuid=message.uuid,
            role=Role(message.role),
            content=message.content
        )

    async def init_structure(self, initial_message: MessageEntity) -> Tuple[ChatTree, MessageEntity]:
        """新しいチャット構造を初期化し、指定された初期メッセージを保存"""
        user = await User.get(id=self.user_id)
        
        # 新しいディスカッション構造を作成
        discussion_uuid = str(uuidGen.uuid4())
        
        # 初期のチャット構造を作成
        root_node = ChatStructure(message_uuid=initial_message.uuid)
        chat_tree = ChatTree(
            id=0,  # Will be set after creation
            uuid=discussion_uuid,
            tree=root_node
        )
        
        # ディスカッション構造をDBに保存
        discussion = await DiscussionStructure.create(
            user=user,
            uuid=discussion_uuid,
            title=None,
            system_prompt=None,
            serialized_structure=chat_tree.get_tree_bin(),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        # 初期メッセージを保存
        message = await Message.create(
            discussion=discussion,
            uuid=initial_message.uuid,
            role=initial_message.role.value,
            content=initial_message.content,
            created_at=datetime.utcnow()
        )
        
        saved_message = MessageEntity(
            id=message.id,
            uuid=message.uuid,
            role=Role(message.role),
            content=message.content
        )
        
        return chat_tree, saved_message

    async def load_tree(self, uuid: str) -> ChatTree:
        """指定されたUUIDのチャットツリー構造を読み込み"""
        try:
            discussion = await DiscussionStructure.get(uuid=uuid)
            chat_tree = ChatTree(
                id=discussion.id,
                uuid=discussion.uuid,
                tree=None
            )
            chat_tree.revert_tree_from_bin(discussion.serialized_structure)
            return chat_tree
        except:
            raise ValueError(f"Chat tree not found: {uuid}")

    async def update_tree(self, new_tree: ChatTree) -> None:
        """チャットツリー構造を更新"""
        try:
            discussion = await DiscussionStructure.get(uuid=new_tree.uuid)
            discussion.serialized_structure = new_tree.get_tree_bin()
            discussion.updated_at = datetime.utcnow()
            await discussion.save()
        except:
            raise ValueError(f"Failed to update tree: {new_tree.uuid}")

    async def get_latest_message_by_discussion(self, discussion_uuid: str) -> MessageEntity:
        """指定されたディスカッションの最新メッセージを取得"""
        try:
            discussion = await DiscussionStructure.get(uuid=discussion_uuid)
            message = await Message.filter(discussion=discussion).order_by('-created_at').first()
            
            if not message:
                raise ValueError(f"No messages found for discussion: {discussion_uuid}")
                
            return MessageEntity(
                id=message.id,
                uuid=message.uuid,
                role=Role(message.role),
                content=message.content
            )
        except:
            raise ValueError(f"Discussion not found: {discussion_uuid}")

    async def get_history(self, uuid_list: list[str]) -> list[MessageEntity]:
        """指定されたUUIDリストに対応するメッセージ履歴を取得"""
        messages = await Message.filter(uuid__in=uuid_list).order_by('created_at')
        
        return [
            MessageEntity(
                id=msg.id,
                uuid=msg.uuid,
                role=Role(msg.role),
                content=msg.content
            )
            for msg in messages
        ]

    # 以下のメソッドは最小限の実装（今回は省略）
    async def get_recent_chats(self, user_uuid: str, limit: int = 10) -> list[dict]:
        """最近のチャット一覧を取得"""
        return []

    async def delete_chat(self, chat_uuid: str, user_uuid: str) -> bool:
        """チャットを削除"""
        return False

    async def search_messages(self, chat_uuid: str, query: str) -> list[dict]:
        """メッセージを検索"""
        return []

    async def get_chats_by_date(self, user_uuid: str, date_filter: str) -> list[dict]:
        """日付でフィルタリングしたチャット一覧を取得"""
        return []

    async def get_user_chat_count(self, user_uuid: str) -> int:
        """ユーザーの全チャット数を取得"""
        return 0

    async def get_recent_chats_paginated(self, user_uuid: str, limit: int, offset: int) -> list[dict]:
        """ページネーションでチャット一覧を取得"""
        return []

    async def get_chat_metadata(self, chat_uuid: str, user_uuid: str) -> Optional[dict]:
        """チャットのメタデータを取得"""
        try:
            user = await User.get(uuid=user_uuid)
            discussion = await DiscussionStructure.get(uuid=chat_uuid, user=user)
            
            # メッセージ数を取得
            message_count = await Message.filter(discussion=discussion).count()
            
            return {
                "uuid": discussion.uuid,
                "title": discussion.title or "Untitled Chat",
                "system_prompt": discussion.system_prompt,
                "created_at": discussion.created_at.isoformat(),
                "updated_at": discussion.updated_at.isoformat(),
                "message_count": message_count
            }
        except Exception:
            return None

    async def update_chat(self, chat_uuid: str, user_uuid: str, title: Optional[str], system_prompt: Optional[str]) -> bool:
        """チャットのタイトルやシステムプロンプトを更新"""
        return False

    async def edit_message(self, chat_uuid: str, message_id: str, user_uuid: str, content: str) -> bool:
        """メッセージの内容を編集"""
        return False

    async def delete_message(self, chat_uuid: str, message_id: str, user_uuid: str) -> bool:
        """メッセージを削除"""
        return False

    async def search_and_paginate_chats(self, user_uuid: str, query: Optional[str], sort: Optional[str], limit: int, offset: int) -> dict:
        """チャットを検索・ソート・ページネーションで取得"""
        return {"items": [], "total": 0}

    async def get_tree_structure(self, chat_uuid: str) -> dict:
        """
        チャットツリー構造を取得し、フロントエンド用の辞書形式で返す
        """
        tree = await self.load_tree(chat_uuid)
        
        def convert_node_to_dict(node):
            # ノードからメッセージUUIDを取得
            node_uuid = str(node.uuid)
            
            # メッセージの詳細情報を取得（同期的にアクセスする必要があるため、デフォルト値を使用）
            return {
                "uuid": node_uuid,
                "role": "user",  # デフォルト値、実際の実装では非同期でメッセージを取得する必要がある
                "content": "",   # デフォルト値、実際の実装では非同期でメッセージを取得する必要がある
                "children": [convert_node_to_dict(child) for child in node.children]
            }
        
        return convert_node_to_dict(tree.tree)