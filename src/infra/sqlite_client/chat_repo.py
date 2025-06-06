import uuid as uuidGen
from peewee import SqliteDatabase, DoesNotExist
from typing import Optional
import datetime

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
            discussion=target_structure,
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
            user=self.user,
            uuid=uuidGen.uuid4(),
            serialized_structure=b""
        )
        # 初期メッセージを保存
        saved_msg = self.save_message(base.uuid, initial_message_dto)

        # ChatTree生成と構造バイナリ化
        new_tree = ChatTree(
            id=base.id,
            uuid=base.uuid,
            tree=ChatStructure(saved_msg.uuid, None)
        )
        base.serialized_structure = new_tree.get_tree_bin()
        base.save()

        return new_tree, saved_msg

    def load_tree(self, uuid: str) -> ChatTree:
        record = DiscussionStructure.get(DiscussionStructure.uuid == uuid)
        tree = ChatTree(id=record.id, uuid=record.uuid, tree=None)
        tree.revert_tree_from_bin(record.serialized_structure)
        return tree

    def update_tree(self, new_tree: ChatTree) -> None:
        record = DiscussionStructure.get(DiscussionStructure.uuid == new_tree.uuid)
        record.serialized_structure = new_tree.get_tree_bin()
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
    
    
    def get_recent_chats(self, user_uuid: str, limit: int = 10) -> list[dict]:
        """ユーザーの最近のチャット一覧を取得"""
        try:
            user = User.get(User.uuid == user_uuid)
            discussions = (DiscussionStructure
                         .select()
                         .where(DiscussionStructure.user == user)
                         .order_by(DiscussionStructure.created_at.desc())
                         .limit(limit))
            
            result = []
            for disc in discussions:
                # メッセージ数をカウント
                message_count = mm.select().where(mm.discussion == disc).count()
                
                # 最初のメッセージからタイトルを生成（または専用フィールドがあれば使用）
                first_message = mm.select().where(mm.discussion == disc).order_by(mm.created_at).first()
                title = first_message.content[:50] + "..." if first_message and len(first_message.content) > 50 else (first_message.content if first_message else "New Chat")
                
                result.append({
                    "uuid": disc.uuid,
                    "title": title,
                    "created_at": disc.created_at.isoformat(),
                    "updated_at": disc.created_at.isoformat(),  # TODO: 更新日時を別途管理する場合は修正
                    "message_count": message_count
                })
            
            return result
        except DoesNotExist:
            return []
    
    def delete_chat(self, chat_uuid: str, user_uuid: str) -> bool:
        """チャットを削除"""
        try:
            user = User.get(User.uuid == user_uuid)
            discussion = DiscussionStructure.get(
                DiscussionStructure.uuid == chat_uuid,
                DiscussionStructure.user == user
            )
            
            # 関連するメッセージとLLM詳細を削除
            messages = mm.select().where(mm.discussion == discussion)
            for message in messages:
                LLMDetails.delete().where(LLMDetails.message == message).execute()
            
            mm.delete().where(mm.discussion == discussion).execute()
            
            
            # ディスカッション構造を削除
            discussion.delete_instance()
            
            return True
        except DoesNotExist:
            return False
    
    def search_messages(self, chat_uuid: str, query: str) -> list[dict]:
        """チャット内のメッセージを検索"""
        try:
            discussion = DiscussionStructure.get(DiscussionStructure.uuid == chat_uuid)
            
            # SQLiteのLIKE演算子で検索
            messages = (mm.select()
                       .where(
                           (mm.discussion == discussion) & 
                           (mm.content.contains(query))
                       )
                       .order_by(mm.created_at.desc()))
            
            results = []
            for msg in messages:
                # ハイライト処理（簡易版）
                import re
                highlighted = re.sub(
                    f'({re.escape(query)})',
                    r'<mark>\1</mark>',
                    msg.content,
                    flags=re.IGNORECASE
                )
                
                results.append({
                    "uuid": msg.uuid,
                    "content": msg.content,
                    "role": msg.role,
                    "created_at": msg.created_at.isoformat(),
                    "highlight": highlighted
                })
            
            return results
        except DoesNotExist:
            return []
    
    def get_chats_by_date(self, user_uuid: str, date_filter: str) -> list[dict]:
        """日付でフィルタリングしたチャット一覧を取得"""
        try:
            user = User.get(User.uuid == user_uuid)
            
            # 日付フィルタの設定
            today = datetime.datetime.now().date()
            if date_filter == "today":
                start_date = today
            elif date_filter == "yesterday":
                start_date = today - datetime.timedelta(days=1)
                end_date = today
            elif date_filter == "week":
                start_date = today - datetime.timedelta(days=7)
            elif date_filter == "month":
                start_date = today - datetime.timedelta(days=30)
            else:
                return []
            
            # クエリの構築
            query = DiscussionStructure.select().where(
                DiscussionStructure.user == user
            )
            
            if date_filter == "today":
                query = query.where(
                    DiscussionStructure.created_at >= datetime.datetime.combine(start_date, datetime.time.min)
                )
            elif date_filter == "yesterday":
                query = query.where(
                    (DiscussionStructure.created_at >= datetime.datetime.combine(start_date, datetime.time.min)) &
                    (DiscussionStructure.created_at < datetime.datetime.combine(end_date, datetime.time.min))
                )
            else:
                query = query.where(
                    DiscussionStructure.created_at >= datetime.datetime.combine(start_date, datetime.time.min)
                )
            
            query = query.order_by(DiscussionStructure.created_at.desc())
            
            results = []
            for disc in query:
                # 最新メッセージを取得
                last_message = (mm.select()
                              .where(mm.discussion == disc)
                              .order_by(mm.created_at.desc())
                              .first())
                
                results.append({
                    "chat_uuid": disc.uuid,
                    "created_at": disc.created_at.isoformat(),
                    "last_message": last_message.content if last_message else "No messages"
                })
            
            return results
        except DoesNotExist:
            return []
    
    def get_chat_metadata(self, chat_uuid: str, user_uuid: str) -> Optional[dict]:
        """チャットのメタデータを取得"""
        try:
            user = User.get(User.uuid == user_uuid)
            discussion = DiscussionStructure.get(
                DiscussionStructure.uuid == chat_uuid,
                DiscussionStructure.user == user
            )
            
            # メッセージ数をカウント
            message_count = mm.select().where(mm.discussion == discussion).count()
            
            # タイトルを生成（専用フィールドがあればそれを使用、なければ最初のメッセージから）
            title = getattr(discussion, 'title', None)
            if not title:
                first_message = mm.select().where(mm.discussion == discussion).order_by(mm.created_at).first()
                title = first_message.content[:50] + "..." if first_message and len(first_message.content) > 50 else (first_message.content if first_message else "New Chat")
            
            # updated_atフィールドが存在するかチェック
            updated_at = getattr(discussion, 'updated_at', discussion.created_at)
            
            return {
                "chat_uuid": discussion.uuid,
                "title": title,
                "created_at": discussion.created_at.isoformat(),
                "updated_at": updated_at.isoformat(),
                "message_count": message_count,
                "owner_id": user.uuid
            }
        except DoesNotExist:
            return None
    
    def update_chat(self, chat_uuid: str, user_uuid: str, title: Optional[str], system_prompt: Optional[str]) -> bool:
        """チャットのタイトルやシステムプロンプトを更新"""
        try:
            user = User.get(User.uuid == user_uuid)
            discussion = DiscussionStructure.get(
                DiscussionStructure.uuid == chat_uuid,
                DiscussionStructure.user == user
            )
            
            updated = False
            if title is not None:
                discussion.title = title
                updated = True
            
            if system_prompt is not None:
                discussion.system_prompt = system_prompt
                updated = True
            
            if updated:
                discussion.updated_at = datetime.datetime.now()
                discussion.save()
            
            return True
        except DoesNotExist:
            return False
    
    def edit_message(self, chat_uuid: str, message_id: str, user_uuid: str, content: str) -> bool:
        """メッセージの内容を編集"""
        try:
            user = User.get(User.uuid == user_uuid)
            discussion = DiscussionStructure.get(
                DiscussionStructure.uuid == chat_uuid,
                DiscussionStructure.user == user
            )
            
            message = mm.get(
                mm.uuid == message_id,
                mm.discussion == discussion
            )
            
            message.content = content
            message.save()
            
            # チャットの更新日時も更新
            discussion.updated_at = datetime.datetime.now()
            discussion.save()
            
            return True
        except DoesNotExist:
            return False
    
    def delete_message(self, chat_uuid: str, message_id: str, user_uuid: str) -> bool:
        """メッセージを削除"""
        try:
            user = User.get(User.uuid == user_uuid)
            discussion = DiscussionStructure.get(
                DiscussionStructure.uuid == chat_uuid,
                DiscussionStructure.user == user
            )
            
            message = mm.get(
                mm.uuid == message_id,
                mm.discussion == discussion
            )
            
            # 関連するLLM詳細を削除
            LLMDetails.delete().where(LLMDetails.message == message).execute()
            
            # メッセージを削除
            message.delete_instance()
            
            # チャットの更新日時も更新
            discussion.updated_at = datetime.datetime.now()
            discussion.save()
            
            return True
        except DoesNotExist:
            return False
    
    def search_and_paginate_chats(self, user_uuid: str, query: Optional[str], sort: Optional[str], limit: int, offset: int) -> dict:
        """チャットを検索・ソート・ページネーションで取得"""
        try:
            user = User.get(User.uuid == user_uuid)
            
            # ベースクエリ
            base_query = DiscussionStructure.select().where(DiscussionStructure.user == user)
            
            # 検索条件を追加
            if query:
                # チャットタイトルまたはメッセージ内容で検索
                message_discussions = (mm.select(mm.discussion)
                                     .where(mm.content.contains(query))
                                     .distinct())
                
                base_query = base_query.where(
                    (DiscussionStructure.title.contains(query)) |
                    (DiscussionStructure.id.in_(message_discussions))
                )
            
            # ソート条件を追加
            if sort:
                if sort == "created_at.asc":
                    base_query = base_query.order_by(DiscussionStructure.created_at.asc())
                elif sort == "created_at.desc":
                    base_query = base_query.order_by(DiscussionStructure.created_at.desc())
                elif sort == "updated_at.asc":
                    base_query = base_query.order_by(DiscussionStructure.updated_at.asc())
                elif sort == "updated_at.desc":
                    base_query = base_query.order_by(DiscussionStructure.updated_at.desc())
                else:
                    # デフォルトソート
                    base_query = base_query.order_by(DiscussionStructure.updated_at.desc())
            else:
                base_query = base_query.order_by(DiscussionStructure.updated_at.desc())
            
            # 総数を取得
            total_count = base_query.count()
            
            # ページネーション適用
            paginated_query = base_query.limit(limit).offset(offset)
            
            # 結果を構築
            results = []
            for disc in paginated_query:
                # メッセージ数をカウント
                message_count = mm.select().where(mm.discussion == disc).count()
                
                # タイトルを取得
                title = disc.title
                if not title:
                    first_message = mm.select().where(mm.discussion == disc).order_by(mm.created_at).first()
                    title = first_message.content[:50] + "..." if first_message and len(first_message.content) > 50 else (first_message.content if first_message else "New Chat")
                
                results.append({
                    "chat_uuid": disc.uuid,
                    "title": title,
                    "created_at": disc.created_at.isoformat(),
                    "updated_at": disc.updated_at.isoformat(),
                    "message_count": message_count
                })
            
            return {
                "items": results,
                "total": total_count
            }
        except DoesNotExist:
            return {
                "items": [],
                "total": 0
            }
    
    def get_user_chat_count(self, user_uuid: str) -> int:
        """
        ユーザーの全チャット数を取得します。
        """
        try:
            user = User.get(User.uuid == user_uuid)
            return user.discussionstructure_set.count()
        except DoesNotExist:
            return 0
    
    def get_recent_chats_paginated(self, user_uuid: str, limit: int, offset: int) -> list[dict]:
        """
        ユーザーの最近のチャット一覧をページネーションで取得します。
        """
        try:
            user = User.get(User.uuid == user_uuid)
            query = (DiscussionStructure.select()
                    .where(DiscussionStructure.user == user)
                    .order_by(DiscussionStructure.created_at.desc())
                    .limit(limit)
                    .offset(offset))
            
            results = []
            for disc in query:
                # 最新メッセージを取得
                last_message = (mm.select()
                              .where(mm.discussion == disc)
                              .order_by(mm.created_at.desc())
                              .first())
                
                results.append({
                    "chat_uuid": disc.uuid,
                    "created_at": disc.created_at.isoformat(),
                    "last_message": last_message.content if last_message else "No messages"
                })
            
            return results
        except DoesNotExist:
            return []

    def get_tree_structure(self, chat_uuid: str) -> dict:
        """
        チャットツリー構造を取得し、フロントエンド用の辞書形式で返す
        """
        tree = self.load_tree(chat_uuid)
        
        def convert_node_to_dict(node):
            # メッセージの詳細情報を取得
            try:
                msg = mm.get(mm.uuid == str(node.uuid))
                role = msg.role
                content = msg.content
            except DoesNotExist:
                # メッセージが見つからない場合のデフォルト値
                role = "unknown"
                content = ""
            
            return {
                "uuid": str(node.uuid),
                "role": role,
                "content": content,
                "children": [convert_node_to_dict(child) for child in node.children]
            }
        
        return convert_node_to_dict(tree.tree)
