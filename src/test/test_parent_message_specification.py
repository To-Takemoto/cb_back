"""
TDD: 親メッセージ指定機能のテスト
POST /api/v1/chats/{chat_uuid}/messages にparent_message_uuidパラメータを追加
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch
from src.infra.rest_api.main import app
from src.infra.rest_api.schemas import MessageRequest, MessageResponse


class TestParentMessageSpecification:
    """親メッセージ指定機能のテストクラス"""
    
    def test_message_request_schema_accepts_parent_message_uuid(self):
        """MessageRequestスキーマがparent_message_uuidを受け入れることをテスト"""
        # 既存のリクエスト（parent_message_uuid なし）
        request_without_parent = MessageRequest(content="Hello")
        assert request_without_parent.content == "Hello"
        assert request_without_parent.parent_message_uuid is None
        
        # 新しいリクエスト（parent_message_uuid あり）
        request_with_parent = MessageRequest(
            content="Hello", 
            parent_message_uuid="some-uuid"
        )
        assert request_with_parent.content == "Hello"
        assert request_with_parent.parent_message_uuid == "some-uuid"
    
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

    @patch('src.infra.rest_api.routers.chats.get_current_user')
    @patch('src.infra.rest_api.routers.chats.create_chat_repo_for_user')
    @patch('src.infra.di.get_llm_client')
    @patch('src.infra.rest_api.dependencies.get_message_cache')
    @patch('src.infra.rest_api.routers.chats.ChatInteraction')
    def test_send_message_without_parent_uuid_maintains_current_behavior(
        self, mock_chat_interaction, mock_cache, mock_llm_client, mock_chat_repo, mock_get_current_user
    ):
        """parent_message_uuidなしの場合、現在の動作を維持することをテスト"""
        # Mock setup
        mock_interaction_instance = Mock()
        mock_chat_interaction.return_value = mock_interaction_instance
        
        mock_message = Mock()
        mock_message.uuid = "new-message-uuid"
        mock_message.content = "AI response"
        mock_interaction_instance.continue_chat.return_value = mock_message
        
        # Mock parent node and path for response
        mock_parent = Mock()
        mock_parent.uuid = "parent-uuid"
        mock_interaction_instance.structure.current_node.parent = mock_parent
        mock_interaction_instance.structure.get_current_path.return_value = ["root", "parent-uuid", "new-message-uuid"]
        
        # Mock authentication
        mock_get_current_user.return_value = "test-user-id"
        
        client = TestClient(app)
        
        # parent_message_uuidなしでメッセージ送信
        response = client.post(
            "/api/v1/chats/test-chat-uuid/messages",
            json={"content": "Hello without parent"}
        )
        
        # select_messageが呼ばれないことを確認
        mock_interaction_instance.select_message.assert_not_called()
        # continue_chatが呼ばれることを確認
        mock_interaction_instance.continue_chat.assert_called_once_with("Hello without parent")

    @patch('src.infra.rest_api.routers.chats.get_current_user')
    @patch('src.infra.rest_api.routers.chats.create_chat_repo_for_user')
    @patch('src.infra.di.get_llm_client')
    @patch('src.infra.rest_api.dependencies.get_message_cache')
    @patch('src.infra.rest_api.routers.chats.ChatInteraction')
    def test_send_message_with_parent_uuid_selects_parent_first(
        self, mock_chat_interaction, mock_cache, mock_llm_client, mock_chat_repo, mock_get_current_user
    ):
        """parent_message_uuidありの場合、select_messageが先に呼ばれることをテスト"""
        # Mock setup
        mock_interaction_instance = Mock()
        mock_chat_interaction.return_value = mock_interaction_instance
        
        mock_message = Mock()
        mock_message.uuid = "new-message-uuid"
        mock_message.content = "AI response"
        mock_interaction_instance.continue_chat.return_value = mock_message
        
        # Mock parent node and path for response
        mock_parent = Mock()
        mock_parent.uuid = "specified-parent-uuid"
        mock_interaction_instance.structure.current_node.parent = mock_parent
        mock_interaction_instance.structure.get_current_path.return_value = ["root", "specified-parent-uuid", "new-message-uuid"]
        
        # Mock authentication
        mock_get_current_user.return_value = "test-user-id"
        
        client = TestClient(app)
        
        # parent_message_uuidありでメッセージ送信
        response = client.post(
            "/api/v1/chats/test-chat-uuid/messages",
            json={
                "content": "Hello with parent",
                "parent_message_uuid": "specified-parent-uuid"
            }
        )
        
        # select_messageが指定されたUUIDで呼ばれることを確認
        mock_interaction_instance.select_message.assert_called_once_with("specified-parent-uuid")
        # continue_chatが呼ばれることを確認
        mock_interaction_instance.continue_chat.assert_called_once_with("Hello with parent")

    @patch('src.infra.rest_api.routers.chats.create_chat_repo_for_user')
    @patch('src.infra.di.get_llm_client')
    @patch('src.infra.rest_api.dependencies.get_message_cache')
    @patch('src.infra.rest_api.routers.chats.ChatInteraction')
    def test_send_message_with_invalid_parent_uuid_returns_400(
        self, mock_chat_interaction, mock_cache, mock_llm_client, mock_chat_repo
    ):
        """無効なparent_message_uuidの場合、400エラーを返すことをテスト"""
        # Mock setup
        mock_interaction_instance = Mock()
        mock_chat_interaction.return_value = mock_interaction_instance
        
        # select_messageでValueErrorを発生させる
        mock_interaction_instance.select_message.side_effect = ValueError("Invalid parent UUID")
        
        client = TestClient(app)
        
        # 無効なparent_message_uuidでメッセージ送信
        response = client.post(
            "/api/v1/chats/test-chat-uuid/messages",
            json={
                "content": "Hello with invalid parent",
                "parent_message_uuid": "invalid-uuid"
            },
            headers={"Authorization": "Bearer fake-token"}
        )
        
        # 400エラーが返されることを確認
        assert response.status_code == 400
        assert "Invalid parent message UUID" in response.json()["detail"]

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

    @patch('src.infra.rest_api.routers.chats.create_chat_repo_for_user')
    @patch('src.infra.rest_api.routers.chats.get_llm_client')  
    @patch('src.infra.rest_api.routers.chats.get_message_cache')
    @patch('src.infra.rest_api.routers.chats.ChatInteraction')
    def test_response_includes_parent_and_path_information(
        self, mock_chat_interaction, mock_cache, mock_llm_client, mock_chat_repo
    ):
        """レスポンスに親ノードとパス情報が含まれることをテスト"""
        # Mock setup
        mock_interaction_instance = Mock()
        mock_chat_interaction.return_value = mock_interaction_instance
        
        mock_message = Mock()
        mock_message.uuid = "new-message-uuid"
        mock_message.content = "AI response"
        mock_interaction_instance.continue_chat.return_value = mock_message
        
        # Mock parent node and path
        mock_parent = Mock()
        mock_parent.uuid = "parent-uuid"
        mock_interaction_instance.structure.current_node.parent = mock_parent
        mock_interaction_instance.structure.get_current_path.return_value = ["root", "parent-uuid", "new-message-uuid"]
        
        client = TestClient(app)
        
        response = client.post(
            "/api/v1/chats/test-chat-uuid/messages",
            json={"content": "Hello"},
            headers={"Authorization": "Bearer fake-token"}
        )
        
        # レスポンスに追加情報が含まれることを確認
        response_data = response.json()
        assert "parent_message_uuid" in response_data
        assert "current_path" in response_data
        assert response_data["parent_message_uuid"] == "parent-uuid"
        assert response_data["current_path"] == ["root", "parent-uuid", "new-message-uuid"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])