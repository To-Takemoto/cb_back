import uuid as uuidGen
from peewee import SqliteDatabase, DoesNotExist, fn, JOIN
from typing import Optional, Tuple, List, Dict, Any
import datetime

from ...domain.entity.chat_tree import ChatTree, ChatStructure
from ...domain.entity.message_entity import MessageEntity, Role
from ...port.dto.message_dto import MessageDTO
from .peewee_models import User, LLMDetails, DiscussionStructure, db_proxy
from .peewee_models import Message as mm

class ChatRepo:
    def __init__(self, user_id: int):
        # データベースプロキシが既に初期化されていない場合のみ初期化
        if not db_proxy.obj:
            from ...infra.config import Settings
            import os
            settings = Settings()
            db_path = settings.database_url.replace("sqlite:///", "")
            
            # データベースディレクトリが存在しない場合は作成
            db_dir = os.path.dirname(db_path)
            if db_dir and not os.path.exists(db_dir):
                os.makedirs(db_dir, exist_ok=True)
            
            db = SqliteDatabase(db_path)
            db_proxy.initialize(db)
            if not db.is_closed():
                db.connect()
        
        self.user_id = user_id
        self._user_cache = None

    def save_message(
        self,
        discussion_structure_uuid: str,
        message_dto: MessageDTO,
        llm_details: Optional[dict] = None
    ) -> MessageEntity:
        """
        メッセージを保存し、MessageEntityを返却
        """
        try:
            target_structure = DiscussionStructure.get(
                DiscussionStructure.uuid == discussion_structure_uuid
            )
        except DoesNotExist:
            raise ValueError(f"Discussion structure not found: {discussion_structure_uuid}")
        
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
        
        # LLM詳細情報の保存（アシスタントメッセージのみ）
        if llm_details and message_dto.role == Role.ASSISTANT:
            LLMDetails.create(
                message=inserted,
                model=llm_details.get('model'),
                provider=llm_details.get('provider', 'openrouter'),
                prompt_tokens=llm_details.get('prompt_tokens', 0),
                completion_tokens=llm_details.get('completion_tokens', 0),
                total_tokens=llm_details.get('total_tokens', 0)
            )
        
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

    def init_structure(self, initial_message_dto: MessageDTO, system_prompt: Optional[str] = None) -> Tuple[ChatTree, MessageEntity]:
        """
        新規チャット構造を作成し、初期メッセージを保存
        """
        # DiscussionStructureを作成
        user = self._get_user()
        base = DiscussionStructure.create(
            user=user,
            uuid=uuidGen.uuid4(),
            serialized_structure=b"",
            system_prompt=system_prompt
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

    def get_history(self, message_uuids: List[str]) -> List[MessageEntity]:
        results: List[MessageEntity] = []
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
    
    def _get_user(self) -> User:
        """ユーザー情報をキャッシュして取得"""
        if self._user_cache is None:
            try:
                self._user_cache = User.get(User.id == self.user_id)
            except DoesNotExist:
                raise ValueError(f"User not found: {self.user_id}")
        return self._user_cache
    
    async def generate_chat_title(self, chat_uuid: str, messages: List, llm_client) -> str:
        """
        チャットのメッセージからLLMを使ってタイトルを生成
        
        Args:
            chat_uuid (str): チャットUUID
            messages (List): メッセージリスト
            llm_client: LLMクライアント
            
        Returns:
            str: 生成されたタイトル（最大50文字）
        """
        # メッセージが空の場合はデフォルトタイトル
        if not messages:
            return "New Chat"
        
        # 最初の3-5メッセージを取得してタイトル生成に使用
        context_messages = messages[:5]
        
        try:
            # タイトル生成用のプロンプトを作成
            prompt_message = {
                "role": "system",
                "content": "以下の会話を15文字以内で要約してタイトルを生成してください。タイトルのみを返してください。"
            }
            
            # 会話履歴をLLM用のフォーマットに変換
            conversation = [prompt_message]
            for msg in context_messages:
                conversation.append({
                    "role": msg.role.value if hasattr(msg.role, 'value') else str(msg.role).lower(),
                    "content": msg.content
                })
            
            # LLMにタイトル生成を依頼
            response = await llm_client.complete_message(conversation)
            title = response.get("content", "").strip()
            
            # タイトルが生成された場合は長さを制限
            if title:
                return title[:50]
            else:
                # フォールバック: 最初のメッセージから生成
                return self._generate_fallback_title(context_messages)
                
        except Exception as e:
            # LLMエラー時のフォールバック処理
            return self._generate_fallback_title(context_messages)
    
    def _generate_fallback_title(self, messages: List) -> str:
        """
        LLMが使用できない場合のフォールバックタイトル生成
        
        Args:
            messages (List): メッセージリスト
            
        Returns:
            str: フォールバックタイトル
        """
        if not messages:
            return "New Chat"
        
        # 最初のユーザーメッセージを使用
        for msg in messages:
            if hasattr(msg, 'role') and str(msg.role).lower() == 'user':
                content = msg.content.strip()
                if content:
                    return content[:50]
        
        # ユーザーメッセージがない場合は最初のメッセージを使用
        first_message = messages[0]
        content = first_message.content.strip()
        return content[:50] if content else "New Chat"
    
    def get_recent_chats(self, user_uuid: str, limit: int = 10) -> List[Dict[str, Any]]:
        """ユーザーの最近のチャット一覧を取得（最適化版）"""
        try:
            user = User.get(User.uuid == user_uuid)
            
            # JOINを使用してN+1問題を解決
            discussions_with_counts = (DiscussionStructure
                .select(
                    DiscussionStructure,
                    fn.COUNT(mm.id).alias('message_count'),
                    fn.MIN(mm.content).alias('first_message_content')
                )
                .join(mm, JOIN.LEFT_OUTER)
                .where(DiscussionStructure.user == user)
                .group_by(DiscussionStructure.id)
                .order_by(DiscussionStructure.created_at.desc())
                .limit(limit))
            
            result = []
            for disc in discussions_with_counts:
                # タイトル生成
                first_content = getattr(disc, 'first_message_content', None)
                if disc.title:
                    title = disc.title
                elif first_content:
                    title = first_content[:50] + "..." if len(first_content) > 50 else first_content
                else:
                    title = "New Chat"
                
                result.append({
                    "uuid": disc.uuid,
                    "title": title,
                    "created_at": disc.created_at.isoformat(),
                    "updated_at": getattr(disc, 'updated_at', disc.created_at).isoformat(),
                    "message_count": getattr(disc, 'message_count', 0)
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
