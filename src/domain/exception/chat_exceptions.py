"""チャット関連の例外クラス"""

from typing import Optional

class ChatException(Exception):
    """チャット関連の基底例外クラス"""
    def __init__(self, message: str, error_code: Optional[str] = None):
        super().__init__(message)
        self.error_code = error_code

class ChatNotFoundError(ChatException):
    """チャットが見つからない場合の例外"""
    def __init__(self, chat_uuid: str):
        super().__init__(f"Chat not found: {chat_uuid}", "CHAT_NOT_FOUND")
        self.chat_uuid = chat_uuid

class MessageNotFoundError(ChatException):
    """メッセージが見つからない場合の例外"""
    def __init__(self, message_uuid: str):
        super().__init__(f"Message not found: {message_uuid}", "MESSAGE_NOT_FOUND")
        self.message_uuid = message_uuid

class InvalidTreeStructureError(ChatException):
    """ツリー構造が不正な場合の例外"""
    def __init__(self, reason: str):
        super().__init__(f"Invalid tree structure: {reason}", "INVALID_TREE_STRUCTURE")

class LLMServiceError(ChatException):
    """LLMサービス関連の例外"""
    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(f"LLM service error: {message}", "LLM_SERVICE_ERROR")
        self.status_code = status_code

class AccessDeniedError(ChatException):
    """アクセス拒否の例外"""
    def __init__(self, resource: str):
        super().__init__(f"Access denied to resource: {resource}", "ACCESS_DENIED")
        self.resource = resource