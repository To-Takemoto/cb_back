"""
チャットツリー構造を表現するドメインエンティティ

このモジュールは、分岐可能な会話履歴を木構造で管理するためのエンティティを提供します。
各メッセージはノードとして表現され、親子関係によって会話の流れを追跡できます。

主要クラス:
- ChatStructure: 個別のメッセージノードを表現
- ChatTree: チャット全体のメタデータとルートノードを含む

データ永続化:
- JSONシリアライゼーションによる安全なデータ保存
- pickleからの移行により、セキュリティリスクを軽減
"""

from anytree import NodeMixin
from dataclasses import dataclass
from typing import Optional, Dict, Any
import json

class ChatStructure(NodeMixin):
    """
    チャット内の個別メッセージを表現するノード
    
    anytreeのNodeMixinを継承し、親子関係の管理、
    ツリー操作、パス検索等の機能を提供します。
    
    Attributes:
        uuid (str): メッセージの一意識別子
        parent (Optional[ChatStructure]): 親ノード（Noneの場合はルート）
        children: 子ノード一覧（anytreeが自動管理）
    """
    
    def __init__(self, message_uuid: str, parent: Optional['ChatStructure'] = None):
        """
        新しいチャット構造ノードを初期化
        
        Args:
            message_uuid (str): このノードが表すメッセージのUUID
            parent (Optional[ChatStructure]): 親ノード。Noneの場合はルートノード
        """
        self.uuid = message_uuid
        self.parent = parent

    def to_dict(self) -> Dict[str, Any]:
        """
        ノードとその子ノードを辞書形式に変換
        
        再帰的に全ての子ノードを辞書形式に変換し、
        JSON シリアライゼーション可能な形式にします。
        
        Returns:
            Dict[str, Any]: ノードの辞書表現
                - uuid: このノードのメッセージUUID
                - children: 子ノードの辞書リスト
        """
        return {
            "uuid": self.uuid,
            "children": [child.to_dict() for child in self.children]
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any], parent: Optional['ChatStructure'] = None) -> 'ChatStructure':
        """
        辞書からノードツリーを復元
        
        to_dict()で生成された辞書データから、
        完全なノードツリーを再構築します。
        
        Args:
            data (Dict[str, Any]): ノードの辞書表現
                - uuid: メッセージUUID（必須）
                - children: 子ノードリスト（オプション）
            parent (Optional[ChatStructure]): このノードの親ノード
        
        Returns:
            ChatStructure: 復元されたノード（子ノードも含む）
            
        Raises:
            KeyError: 必須フィールド 'uuid' が存在しない場合
        """
        node = cls(data["uuid"], parent)
        for child_data in data.get("children", []):
            cls.from_dict(child_data, node)
        return node

@dataclass
class ChatTree:
    """
    チャット全体のメタデータとツリー構造を管理するエンティティ
    
    データベースのディスカッション構造レコードと対応し、
    チャット全体の識別情報とルートノードを保持します。
    
    Attributes:
        id (int): データベース内でのチャットID
        uuid (str): チャットの一意識別子（UUID）
        tree (Optional[ChatStructure]): チャットのルートノード
    """
    id: int
    uuid: str
    tree: Optional[ChatStructure]

    def get_tree_json(self) -> str:
        """
        ツリー構造をJSON文字列として取得
        
        チャット全体のツリー構造を、データベースへの保存や
        外部システムとの連携に適したJSON形式に変換します。
        
        Returns:
            str: ツリー構造のJSON文字列表現
                 ツリーがNoneの場合は 'null' を返す
        """
        if self.tree is None:
            return json.dumps(None)
        
        def convert_to_json_serializable(obj):
            """UUIDを文字列に変換するカスタムシリアライザー"""
            from uuid import UUID
            if isinstance(obj, UUID):
                return str(obj)
            elif isinstance(obj, dict):
                return {k: convert_to_json_serializable(v) for k, v in obj.items()}
            elif isinstance(obj, (list, tuple)):
                return [convert_to_json_serializable(item) for item in obj]
            else:
                return obj
        
        tree_dict = self.tree.to_dict()
        serializable_dict = convert_to_json_serializable(tree_dict)
        return json.dumps(serializable_dict)
    
    def get_tree_bin(self) -> bytes:
        """
        ツリー構造をバイナリ形式で取得（後方互換性用）
        
        既存のデータベースインターフェースとの互換性を保つため、
        JSON文字列をUTF-8バイト列にエンコードして返します。
        
        Returns:
            bytes: UTF-8エンコードされたJSON文字列
            
        Note:
            新しいコードではget_tree_json()を使用することを推奨
        """
        return self.get_tree_json().encode('utf-8')
    
    def revert_tree_from_json(self, tree_json: str) -> None:
        """
        JSON文字列からツリー構造を復元
        
        JSON形式で保存されたツリーデータから、
        完全なChatStructureオブジェクトツリーを再構築します。
        
        Args:
            tree_json (str): JSON形式のツリーデータ
                            'null'の場合はツリーをNoneに設定
        
        Raises:
            json.JSONDecodeError: 無効なJSON形式の場合
            KeyError: 必須フィールドが不足している場合
        """
        data = json.loads(tree_json)
        if data is None:
            self.tree = None
        else:
            self.tree = ChatStructure.from_dict(data)
    
    def revert_tree_from_bin(self, tree_bin: bytes) -> None:
        """
        バイナリデータからツリー構造を復元（後方互換性用）
        
        データベースから取得したバイナリデータを解釈し、
        ツリー構造を復元します。新形式（JSON）と旧形式（pickle）
        の両方に対応していますが、pickleは非推奨です。
        
        Args:
            tree_bin (bytes): ツリーデータのバイナリ表現
        
        Raises:
            ValueError: 旧形式（pickle）のデータが渡された場合
            UnicodeDecodeError: バイナリデータがUTF-8として無効な場合
            json.JSONDecodeError: JSONとして無効な場合
            
        Note:
            新しいコードではrevert_tree_from_json()を使用することを推奨
        """
        try:
            # 新しい形式（JSON）として試行
            self.revert_tree_from_json(tree_bin.decode('utf-8'))
        except (UnicodeDecodeError, json.JSONDecodeError):
            # 古い形式（pickle）の場合は例外を発生
            raise ValueError("Legacy pickle format is no longer supported. Please migrate data.")
        