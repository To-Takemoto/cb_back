from typing import Protocol, Optional

from .dto.message_dto import MessageDTO
from ..domain.entity.message_entity import MessageEntity
from ..domain.entity.chat_tree import ChatTree

class ChatRepository(Protocol):
    """
    チャットデータを永続化するためのリポジトリインターフェース。
    メッセージの保存、チャット構造の初期化、更新、読み込みなどの機能を提供します。
    """
    
    def __init__(self, user_id):
        """
        リポジトリインスタンスを初期化します。
        
        Args:
            user_id: リポジトリを利用するユーザーのID
        """
        pass

    async def save_message(
            self,
            discussion_structure_uuid: str,
            message_dto: MessageDTO,
            llm_details: dict = None
            ) -> MessageEntity:
        """
        指定されたディスカッション構造に新しいメッセージを保存します。
        
        Args:
            discussion_structure_uuid: メッセージを保存するディスカッション構造のUUID
            message: 保存するメッセージエンティティ
            
        Returns:
            MessageEntity: 保存されたメッセージエンティティ（IDやUUIDなどが設定された状態）
        """
        pass

    async def init_structure(self, initial_message: MessageEntity) -> tuple[ChatTree, MessageEntity]:
        """
        新しいチャット構造を初期化し、指定された初期メッセージを保存します。
        
        Args:
            initial_message: チャット構造の初期メッセージとなるメッセージエンティティ
            
        Returns:
            ChatTree: 作成されたチャットツリー構造
        """
        pass

    async def load_tree(self, uuid: str) -> ChatTree:
        """
        指定されたUUIDのチャットツリー構造を読み込みます。
        
        Args:
            uuid: 読み込むチャットツリー構造のUUID
            
        Returns:
            ChatTree: 読み込まれたチャットツリー構造
        """
        pass

    async def update_tree(self, new_tree: ChatTree) -> None:
        """
        チャットツリー構造を更新します。
        
        Args:
            new_tree: 更新するチャットツリー構造
        """
        pass
    
    async def get_latest_message_by_discussion(self, discussion_uuid: str) -> MessageEntity:
        """
        指定されたディスカッションの最新メッセージを取得します。
        
        Args:
            discussion_uuid: 取得対象となるディスカッションのUUID
            
        Returns:
            MessageEntity: 最新のメッセージエンティティ
            
        Raises:
            DoesNotExist: 該当するディスカッションが存在しない場合や、
                        メッセージが存在しない場合に発生します。
        """
        pass

    async def get_history(self, uuid_list: list[str]) -> list[MessageEntity]:
        """
        指定されたUUIDリストに対応するメッセージ履歴を取得します。
        
        Args:
            uuid_list: 取得対象となるメッセージUUIDのリスト
            
        Returns:
            list[MessageEntity]: MessageEntityのリスト（UUIDリストと同じ順序で返される）
            
        Note:
            存在しないUUIDが含まれる場合、そのメッセージはスキップされます。
        """
        pass
    
    
    async def get_recent_chats(self, user_uuid: str, limit: int = 10) -> list[dict]:
        """
        ユーザーの最近のチャット一覧を取得します。
        
        Args:
            user_uuid: ユーザーのUUID
            limit: 取得する件数の上限
            
        Returns:
            list[dict]: チャット情報のリスト
        """
        pass
    
    async def delete_chat(self, chat_uuid: str, user_uuid: str) -> bool:
        """
        チャットを削除します。
        
        Args:
            chat_uuid: チャットのUUID
            user_uuid: ユーザーのUUID（権限確認用）
            
        Returns:
            bool: 削除成功時True、失敗時False
        """
        pass
    
    async def search_messages(self, chat_uuid: str, query: str) -> list[dict]:
        """
        チャット内のメッセージを検索します。
        
        Args:
            chat_uuid: チャットのUUID
            query: 検索クエリ
            
        Returns:
            list[dict]: 検索結果のメッセージリスト
        """
        pass
    
    async def get_chats_by_date(self, user_uuid: str, date_filter: str) -> list[dict]:
        """
        日付でフィルタリングしたチャット一覧を取得します。
        
        Args:
            user_uuid: ユーザーのUUID
            date_filter: フィルタ条件（today, yesterday, week, month）
            
        Returns:
            list[dict]: フィルタリングされたチャット情報のリスト
        """
        pass
    
    async def get_user_chat_count(self, user_uuid: str) -> int:
        """
        ユーザーの全チャット数を取得します。
        
        Args:
            user_uuid: ユーザーのUUID
            
        Returns:
            int: チャットの総数
        """
        pass
    
    async def get_recent_chats_paginated(self, user_uuid: str, limit: int, offset: int) -> list[dict]:
        """
        ユーザーの最近のチャット一覧をページネーションで取得します。
        
        Args:
            user_uuid: ユーザーのUUID
            limit: 取得する件数
            offset: スキップする件数
            
        Returns:
            list[dict]: チャット情報のリスト
        """
        pass
    
    async def get_chat_metadata(self, chat_uuid: str, user_uuid: str) -> Optional[dict]:
        """
        チャットのメタデータを取得します。
        
        Args:
            chat_uuid: チャットのUUID
            user_uuid: ユーザーのUUID（権限確認用）
            
        Returns:
            Optional[dict]: チャットのメタデータ、存在しない場合はNone
        """
        pass
    
    async def update_chat(self, chat_uuid: str, user_uuid: str, title: Optional[str], system_prompt: Optional[str]) -> bool:
        """
        チャットのタイトルやシステムプロンプトを更新します。
        
        Args:
            chat_uuid: チャットのUUID
            user_uuid: ユーザーのUUID（権限確認用）
            title: 新しいタイトル（Noneの場合は更新しない）
            system_prompt: 新しいシステムプロンプト（Noneの場合は更新しない）
            
        Returns:
            bool: 更新成功時True、失敗時False
        """
        pass
    
    async def edit_message(self, chat_uuid: str, message_id: str, user_uuid: str, content: str) -> bool:
        """
        メッセージの内容を編集します。
        
        Args:
            chat_uuid: チャットのUUID
            message_id: メッセージのUUID
            user_uuid: ユーザーのUUID（権限確認用）
            content: 新しいメッセージ内容
            
        Returns:
            bool: 編集成功時True、失敗時False
        """
        pass
    
    async def delete_message(self, chat_uuid: str, message_id: str, user_uuid: str) -> bool:
        """
        メッセージを削除します。
        
        Args:
            chat_uuid: チャットのUUID
            message_id: メッセージのUUID
            user_uuid: ユーザーのUUID（権限確認用）
            
        Returns:
            bool: 削除成功時True、失敗時False
        """
        pass
    
    async def search_and_paginate_chats(self, user_uuid: str, query: Optional[str], sort: Optional[str], limit: int, offset: int) -> dict:
        """
        チャットを検索・ソート・ページネーションで取得します。
        
        Args:
            user_uuid: ユーザーのUUID
            query: 検索クエリ（Noneの場合は全件取得）
            sort: ソート条件（例: "updated_at.desc", "created_at.asc"）
            limit: 取得する件数
            offset: スキップする件数
            
        Returns:
            dict: {"items": list[dict], "total": int} 形式の結果
        """
        pass