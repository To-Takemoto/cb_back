"""
メッセージエンティティとロール定義

このモジュールは、チャット内の個別メッセージを表現するドメインエンティティを提供します。
メッセージには役割（ユーザー、アシスタント、システム）があり、
LLMとの会話において重要な意味を持ちます。

主要要素:
- Role: メッセージの送信者役割を定義する列挙型
- MessageEntity: 個別メッセージの完全な情報を保持

設計原則:
- ドメインエンティティとして、外部依存性を持たない
- 不変性を保ち、データの整合性を確保
- LLM APIの標準的な役割分類に準拠
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

class Role(str, Enum):
    """
    メッセージの送信者役割を表す列挙型
    
    LLM（Large Language Model）との会話における標準的な役割分類に従います。
    各役割は特定の意味と用途を持ち、会話フローに重要な影響を与えます。
    
    Values:
        USER: ユーザーからのメッセージ（質問、指示等）
        ASSISTANT: AIアシスタントからの応答メッセージ
        SYSTEM: システムからの制御メッセージ（プロンプト、設定等）
    """
    USER = "user"          # ユーザーメッセージ：会話の開始、質問、指示
    ASSISTANT = "assistant"  # アシスタントメッセージ：AIからの応答、回答
    SYSTEM = "system"      # システムメッセージ：プロンプト、動作指示、設定

@dataclass
class MessageEntity:
    """
    チャット内の個別メッセージを表現するドメインエンティティ
    
    会話履歴の一部として保存・管理される単一のメッセージの
    完全な情報を保持します。ストリーミング中の一時的なメッセージと
    確定されたメッセージの両方を表現できます。
    
    Attributes:
        id (int): データベース内での一意識別子
        uuid (str): グローバル一意識別子（UUID形式）
        role (Role): メッセージの送信者役割
        content (str): メッセージの実際の内容テキスト
        is_streaming (bool): ストリーミング中かどうかのフラグ
        temp_id (Optional[str]): ストリーミング中の一時識別子
        
    Usage:
        # 通常のメッセージ
        message = MessageEntity(
            id=123,
            uuid="550e8400-e29b-41d4-a716-446655440000",
            role=Role.USER,
            content="こんにちは"
        )
        
        # ストリーミング中のメッセージ
        streaming_message = MessageEntity(
            id=0,  # 一時的
            uuid="",  # 一時的
            role=Role.ASSISTANT,
            content="部分的な応答...",
            is_streaming=True,
            temp_id="temp-123"
        )
        
    Note:
        - idはデータベース固有の識別子
        - uuidは外部システムとの連携やURLパラメータ等で使用
        - is_streamingがTrueの場合、id/uuidは一時的な値
        - temp_idはストリーミング中のフロントエンド識別に使用
    """
    id: int
    uuid: str
    role: Role
    content: str
    is_streaming: bool = field(default=False)
    temp_id: Optional[str] = field(default=None)