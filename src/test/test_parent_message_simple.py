"""
親メッセージ指定機能の簡単な動作テスト
"""
import pytest
from src.infra.rest_api.schemas import MessageRequest, MessageResponse


def test_schema_compatibility():
    """スキーマの互換性テスト"""
    # 既存のリクエスト（後方互換性）
    old_request = MessageRequest(content="Hello")
    assert old_request.content == "Hello"
    assert old_request.parent_message_uuid is None
    
    # 新しいリクエスト
    new_request = MessageRequest(content="Hello", parent_message_uuid="some-uuid")
    assert new_request.content == "Hello"
    assert new_request.parent_message_uuid == "some-uuid"
    
    # 既存のレスポンス（後方互換性）
    old_response = MessageResponse(message_uuid="msg-1", content="Response")
    assert old_response.message_uuid == "msg-1"
    assert old_response.content == "Response"
    assert old_response.parent_message_uuid is None
    assert old_response.current_path is None
    
    # 新しいレスポンス
    new_response = MessageResponse(
        message_uuid="msg-1", 
        content="Response",
        parent_message_uuid="parent-1",
        current_path=["root", "parent-1", "msg-1"]
    )
    assert new_response.message_uuid == "msg-1"
    assert new_response.content == "Response"
    assert new_response.parent_message_uuid == "parent-1"
    assert new_response.current_path == ["root", "parent-1", "msg-1"]


if __name__ == "__main__":
    test_schema_compatibility()
    print("✅ All schema compatibility tests passed!")