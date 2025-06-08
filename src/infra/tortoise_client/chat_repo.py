import uuid as uuidGen
import pickle
from typing import Optional, Tuple, List, Dict, Any
from datetime import datetime

from ...domain.entity.chat_tree import ChatTree, ChatStructure
from ...domain.entity.message_entity import MessageEntity, Role
from ...port.dto.message_dto import MessageDTO
from ...port.chat_repo import ChatRepository
from ...port.llm_client import LLMClient
from ...usecase.chat_interaction.title_generation import TitleGenerationService
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
        try:
            # ユーザーを取得
            user = await User.get(uuid=user_uuid)
            
            # 最近のディスカッションを取得
            discussions = await DiscussionStructure.filter(user=user).order_by('-updated_at').limit(limit)
            
            result = []
            for discussion in discussions:
                # 各チャットのメッセージ数を取得
                message_count = await Message.filter(discussion=discussion).count()
                
                # 最初のメッセージを取得してプレビューとして使用
                first_message = await Message.filter(discussion=discussion).order_by('created_at').first()
                preview = first_message.content[:100] if first_message else ""
                
                result.append({
                    "uuid": discussion.uuid,
                    "title": discussion.title or "Untitled Chat",
                    "preview": preview,
                    "message_count": message_count,
                    "created_at": discussion.created_at.isoformat(),
                    "updated_at": discussion.updated_at.isoformat()
                })
            
            return result
        except Exception:
            return []

    async def delete_chat(self, chat_uuid: str, user_uuid: str) -> bool:
        """チャットを削除"""
        try:
            # ユーザーを取得
            user = await User.get(uuid=user_uuid)
            
            # 指定されたユーザーのチャットを取得
            discussion = await DiscussionStructure.get(uuid=chat_uuid, user=user)
            
            # 関連するメッセージとLLM詳細を削除（カスケード削除）
            await Message.filter(discussion=discussion).delete()
            
            # ディスカッション構造を削除
            await discussion.delete()
            
            return True
        except Exception:
            return False

    async def search_messages(self, chat_uuid: str, query: str) -> list[dict]:
        """メッセージを検索"""
        try:
            # ディスカッションを取得
            discussion = await DiscussionStructure.get(uuid=chat_uuid)
            
            # メッセージを大文字小文字を区別せずに検索
            messages = await Message.filter(
                discussion=discussion,
                content__icontains=query
            ).order_by('created_at')
            
            result = []
            for message in messages:
                result.append({
                    "uuid": message.uuid,
                    "role": message.role,
                    "content": message.content,
                    "created_at": message.created_at.isoformat()
                })
            
            return result
        except Exception:
            return []

    async def get_chats_by_date(self, user_uuid: str, date_filter: str) -> list[dict]:
        """日付でフィルタリングしたチャット一覧を取得"""
        try:
            # ユーザーを取得
            user = await User.get(uuid=user_uuid)
            
            # 日付フィルターに基づいて期間を決定
            from datetime import date, timedelta
            today = date.today()
            
            if date_filter == "today":
                start_date = datetime.combine(today, datetime.min.time())
                end_date = datetime.combine(today, datetime.max.time())
            elif date_filter == "yesterday":
                yesterday = today - timedelta(days=1)
                start_date = datetime.combine(yesterday, datetime.min.time())
                end_date = datetime.combine(yesterday, datetime.max.time())
            elif date_filter == "week":
                week_ago = today - timedelta(days=7)
                start_date = datetime.combine(week_ago, datetime.min.time())
                end_date = datetime.combine(today, datetime.max.time())
            elif date_filter == "month":
                month_ago = today - timedelta(days=30)
                start_date = datetime.combine(month_ago, datetime.min.time())
                end_date = datetime.combine(today, datetime.max.time())
            else:
                # 不明なフィルターの場合は今日のデータを返す
                start_date = datetime.combine(today, datetime.min.time())
                end_date = datetime.combine(today, datetime.max.time())
            
            # 指定期間のディスカッションを取得
            discussions = await DiscussionStructure.filter(
                user=user,
                created_at__gte=start_date,
                created_at__lte=end_date
            ).order_by('-created_at')
            
            result = []
            for discussion in discussions:
                # 各チャットのメッセージ数を取得
                message_count = await Message.filter(discussion=discussion).count()
                
                # 最初のメッセージを取得してプレビューとして使用
                first_message = await Message.filter(discussion=discussion).order_by('created_at').first()
                preview = first_message.content[:100] if first_message else ""
                
                result.append({
                    "uuid": discussion.uuid,
                    "title": discussion.title or "Untitled Chat",
                    "preview": preview,
                    "message_count": message_count,
                    "created_at": discussion.created_at.isoformat(),
                    "updated_at": discussion.updated_at.isoformat()
                })
            
            return result
        except Exception:
            return []

    async def get_user_chat_count(self, user_uuid: str) -> int:
        """ユーザーの全チャット数を取得"""
        try:
            user = await User.get(uuid=user_uuid)
            count = await DiscussionStructure.filter(user=user).count()
            return count
        except Exception:
            return 0
    
    async def generate_chat_title(self, chat_uuid: str, messages: List[MessageEntity], llm_client: LLMClient) -> Optional[str]:
        """
        Generate and save a title for the specified chat using LLM.
        
        Args:
            chat_uuid: UUID of the chat to generate title for
            messages: List of messages in the conversation
            llm_client: LLM client for title generation
            
        Returns:
            Generated title or None if generation fails
        """
        try:
            # Create title generation service
            title_service = TitleGenerationService(llm_client)
            
            # Generate title using LLM
            generated_title = await title_service.generate_title(messages)
            
            if generated_title:
                # Update the discussion with the generated title
                await DiscussionStructure.filter(uuid=chat_uuid).update(title=generated_title)
                return generated_title
            
            return None
            
        except Exception as e:
            # Log error but don't raise - title generation failure shouldn't break chat
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Failed to generate title for chat {chat_uuid}: {e}")
            return None

    async def get_recent_chats_paginated(self, user_uuid: str, limit: int, offset: int) -> list[dict]:
        """ページネーションでチャット一覧を取得"""
        try:
            user = await User.get(uuid=user_uuid)
            discussions = await DiscussionStructure.filter(user=user).order_by('-updated_at').offset(offset).limit(limit)
            
            result = []
            for discussion in discussions:
                # 各チャットのメッセージ数を取得
                message_count = await Message.filter(discussion=discussion).count()
                
                # 最初のメッセージを取得してプレビューとして使用
                first_message = await Message.filter(discussion=discussion).order_by('created_at').first()
                preview = first_message.content[:100] if first_message else ""
                
                result.append({
                    "uuid": discussion.uuid,
                    "title": discussion.title or "Untitled Chat",
                    "preview": preview,
                    "message_count": message_count,
                    "created_at": discussion.created_at.isoformat(),
                    "updated_at": discussion.updated_at.isoformat()
                })
            
            return result
        except Exception:
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
        try:
            # ユーザーを取得
            user = await User.get(uuid=user_uuid)
            
            # 指定されたユーザーのチャットを取得
            discussion = await DiscussionStructure.get(uuid=chat_uuid, user=user)
            
            # フィールドを更新
            if title is not None:
                discussion.title = title
            if system_prompt is not None:
                discussion.system_prompt = system_prompt
            
            # 更新日時を設定
            discussion.updated_at = datetime.utcnow()
            
            # 保存
            await discussion.save()
            
            return True
        except Exception:
            return False

    async def edit_message(self, chat_uuid: str, message_id: str, user_uuid: str, content: str) -> bool:
        """メッセージの内容を編集"""
        try:
            # ユーザーを取得
            user = await User.get(uuid=user_uuid)
            
            # ディスカッションを取得（ユーザー権限チェック）
            discussion = await DiscussionStructure.get(uuid=chat_uuid, user=user)
            
            # メッセージを取得
            message = await Message.get(uuid=message_id, discussion=discussion)
            
            # 内容を更新
            message.content = content
            await message.save()
            
            return True
        except Exception:
            return False

    async def delete_message(self, chat_uuid: str, message_id: str, user_uuid: str) -> bool:
        """メッセージを削除"""
        try:
            # ユーザーを取得
            user = await User.get(uuid=user_uuid)
            
            # ディスカッションを取得（ユーザー権限チェック）
            discussion = await DiscussionStructure.get(uuid=chat_uuid, user=user)
            
            # メッセージを取得
            message = await Message.get(uuid=message_id, discussion=discussion)
            
            # メッセージを削除
            await message.delete()
            
            return True
        except Exception:
            return False

    async def search_and_paginate_chats(self, user_uuid: str, query: Optional[str], sort: Optional[str], limit: int, offset: int) -> dict:
        """チャットを検索・ソート・ページネーションで取得"""
        try:
            # ユーザーを取得
            user = await User.get(uuid=user_uuid)
            
            # ベースクエリを構築
            base_query = DiscussionStructure.filter(user=user)
            
            # 検索クエリが指定されている場合
            if query:
                base_query = base_query.filter(title__icontains=query)
            
            # ソート順を決定（デフォルトは更新日時の降順）
            sort_field = "-updated_at"  # デフォルト
            if sort == "created_at":
                sort_field = "-created_at"
            elif sort == "title":
                sort_field = "title"
            elif sort == "-title":
                sort_field = "-title"
            
            # 総数を取得
            total = await base_query.count()
            
            # ページネーションを適用してディスカッションを取得
            discussions = await base_query.order_by(sort_field).offset(offset).limit(limit)
            
            result = []
            for discussion in discussions:
                # 各チャットのメッセージ数を取得
                message_count = await Message.filter(discussion=discussion).count()
                
                # 最初のメッセージを取得してプレビューとして使用
                first_message = await Message.filter(discussion=discussion).order_by('created_at').first()
                preview = first_message.content[:100] if first_message else ""
                
                result.append({
                    "uuid": discussion.uuid,
                    "title": discussion.title or "Untitled Chat",
                    "preview": preview,
                    "message_count": message_count,
                    "created_at": discussion.created_at.isoformat(),
                    "updated_at": discussion.updated_at.isoformat()
                })
            
            return {"items": result, "total": total}
        except Exception:
            return {"items": [], "total": 0}

    async def get_tree_structure(self, chat_uuid: str) -> dict:
        """
        チャットツリー構造を取得し、フロントエンド用の辞書形式で返す
        """
        tree = await self.load_tree(chat_uuid)
        
        # 全ノードのUUIDを抽出
        all_uuids = []
        def extract_uuids(node):
            all_uuids.append(str(node.uuid))
            for child in node.children:
                extract_uuids(child)
        extract_uuids(tree.tree)
        
        # 全メッセージを一括取得
        messages = await Message.filter(uuid__in=all_uuids)
        message_map = {msg.uuid: msg for msg in messages}
        
        def convert_node_to_dict(node):
            node_uuid = str(node.uuid)
            message = message_map.get(node_uuid)
            
            if message:
                role = message.role
                content = message.content
            else:
                # メッセージが見つからない場合のデフォルト値
                role = "unknown"
                content = ""
            
            return {
                "uuid": node_uuid,
                "role": role,
                "content": content,
                "children": [convert_node_to_dict(child) for child in node.children]
            }
        
        return convert_node_to_dict(tree.tree)