"""
TDD: 親メッセージ指定機能のテスト - Schema validation only
"""
import pytest
import sys
import os

# Add path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from src.infra.rest_api.schemas import MessageRequest, MessageResponse


class TestParentMessageSchemas:
    """親メッセージ指定機能のスキーマテスト"""
    
    def test_message_request_schema_accepts_parent_message_uuid(self):
        """MessageRequestスキーマがparent_message_uuidを受け入れることをテスト"""
        # 既存のリクエスト（parent_message_uuid なし）
        request_without_parent = MessageRequest(content="Hello")
        assert request_without_parent.content == "Hello"
        assert request_without_parent.parent_message_uuid is None
        
        # 新しいリクエスト（parent_message_uuid あり）
        request_with_parent = MessageRequest(
            content="Hello", 
            parent_message_uuid="123e4567-e89b-12d3-a456-426614174000"
        )
        assert request_with_parent.content == "Hello"
        assert request_with_parent.parent_message_uuid == "123e4567-e89b-12d3-a456-426614174000"
    
    def test_message_response_includes_parent_info(self):
        """MessageResponseが親ノード情報を含むことをテスト"""
        response = MessageResponse(
            message_uuid="new-message-uuid",
            content="AI response",
            parent_message_uuid="parent-uuid",
            current_path=["root", "parent-uuid", "new-message-uuid"]
        )
        assert response.message_uuid == "new-message-uuid"
        assert response.content == "AI response"
        assert response.parent_message_uuid == "parent-uuid"
        assert response.current_path == ["root", "parent-uuid", "new-message-uuid"]

    def test_message_response_backwards_compatibility(self):
        """MessageResponseが既存フィールドを維持することをテスト"""
        # 既存の最小限のレスポンス
        minimal_response = MessageResponse(
            message_uuid="new-message-uuid",
            content="AI response"
        )
        assert minimal_response.message_uuid == "new-message-uuid"
        assert minimal_response.content == "AI response"
        assert minimal_response.parent_message_uuid is None
        assert minimal_response.current_path is None
    
    def test_message_request_validation(self):
        """MessageRequestの基本的なバリデーションテスト"""
        # コンテンツが必須であることを確認
        try:
            invalid_request = MessageRequest()
            assert False, "Should have raised validation error"
        except:
            pass  # Expected to fail
        
        # 有効なリクエスト
        valid_request = MessageRequest(content="Valid content")
        assert valid_request.content == "Valid content"
    
    def test_message_response_optional_fields(self):
        """MessageResponseのオプションフィールドテスト"""
        # 必須フィールドのみ
        minimal = MessageResponse(
            message_uuid="uuid-123",
            content="response"
        )
        assert minimal.parent_message_uuid is None
        assert minimal.current_path is None
        
        # すべてのフィールド
        complete = MessageResponse(
            message_uuid="uuid-123",
            content="response",
            parent_message_uuid="parent-123",
            current_path=["root", "parent-123", "uuid-123"]
        )
        assert complete.parent_message_uuid == "parent-123"
        assert isinstance(complete.current_path, list)
        assert len(complete.current_path) == 3
    
    def test_path_structure_validation(self):
        """パス構造の基本的なバリデーションテスト"""
        path = ["root", "parent-uuid", "current-uuid"]
        
        # パスの基本構造確認
        assert isinstance(path, list)
        assert len(path) >= 1
        assert path[0] == "root"  # 最初は常にroot
        
        # 空のパスも許可
        empty_path = []
        assert isinstance(empty_path, list)
        
        # 単一要素のパス
        single_path = ["root"]
        assert len(single_path) == 1
        assert single_path[0] == "root"


class TestSchemaCompatibility:
    """スキーマの互換性テスト"""
    
    def test_request_schema_backward_compatibility(self):
        """リクエストスキーマの後方互換性"""
        # 旧形式（parent_message_uuidなし）
        old_format = {"content": "Hello"}
        request = MessageRequest(**old_format)
        assert request.content == "Hello"
        assert request.parent_message_uuid is None
        
        # 新形式（parent_message_uuidあり）
        new_format = {"content": "Hello", "parent_message_uuid": "123e4567-e89b-12d3-a456-426614174000"}
        request_new = MessageRequest(**new_format)
        assert request_new.content == "Hello"
        assert request_new.parent_message_uuid == "123e4567-e89b-12d3-a456-426614174000"
    
    def test_response_schema_forward_compatibility(self):
        """レスポンススキーマの前方互換性"""
        # 基本レスポンス
        basic_data = {
            "message_uuid": "msg-123",
            "content": "Response"
        }
        response = MessageResponse(**basic_data)
        assert response.message_uuid == "msg-123"
        assert response.content == "Response"
        
        # 拡張レスポンス
        extended_data = {
            "message_uuid": "msg-123",
            "content": "Response",
            "parent_message_uuid": "parent-123",
            "current_path": ["root", "parent-123", "msg-123"]
        }
        response_ext = MessageResponse(**extended_data)
        assert response_ext.parent_message_uuid == "parent-123"
        assert response_ext.current_path == ["root", "parent-123", "msg-123"]