from typing import Protocol

from .dto.message_dto import MessageDTO
from ..entity.message_entity import MessageEntity
from ..entity.chat_tree import ChatTree

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

    def save_message(
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

    def init_structure(self, initial_message: MessageEntity) -> ChatTree:
        """
        新しいチャット構造を初期化し、指定された初期メッセージを保存します。
        
        Args:
            initial_message: チャット構造の初期メッセージとなるメッセージエンティティ
            
        Returns:
            ChatTree: 作成されたチャットツリー構造
        """
        pass

    def load_tree(self, uuid: str) -> ChatTree:
        """
        指定されたUUIDのチャットツリー構造を読み込みます。
        
        Args:
            uuid: 読み込むチャットツリー構造のUUID
            
        Returns:
            ChatTree: 読み込まれたチャットツリー構造
        """
        pass

    def update_tree(self, new_tree: ChatTree) -> None:
        """
        チャットツリー構造を更新します。
        
        Args:
            new_tree: 更新するチャットツリー構造
        """
        pass
    
    def get_latest_message_by_discussion(self, discussion_uuid: str) -> MessageEntity:
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

    def get_history(self, uuid_list: list[str]) -> list[MessageEntity]:
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