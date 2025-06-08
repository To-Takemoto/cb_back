"""
HistoryService Unit Tests

履歴管理サービスの包括的なユニットテスト
履歴取得、データ変換、パスベースアクセスをテスト
"""

import pytest
import sys
import os
from unittest.mock import AsyncMock

# Add path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from src.domain.entity.message_entity import MessageEntity, Role
from src.usecase.chat_interaction.history_service import HistoryService
from src.port.chat_repo import ChatRepository


class TestHistoryService:
    """HistoryServiceの包括的テスト"""
    
    @pytest.fixture
    def mock_chat_repo(self):
        """モックChatRepositoryフィクスチャ"""
        return AsyncMock(spec=ChatRepository)
    
    @pytest.fixture
    def service(self, mock_chat_repo):
        """HistoryServiceインスタンス"""
        return HistoryService(mock_chat_repo)
    
    @pytest.fixture
    def sample_mixed_history(self):
        """ユーザーとアシスタントメッセージが混在した履歴"""
        return [
            MessageEntity(id=1, uuid="msg-1", role=Role.SYSTEM, content="System prompt"),
            MessageEntity(id=2, uuid="msg-2", role=Role.USER, content="Hello"),
            MessageEntity(id=3, uuid="msg-3", role=Role.ASSISTANT, content="Hi there!"),
            MessageEntity(id=4, uuid="msg-4", role=Role.USER, content="How are you?"),
            MessageEntity(id=5, uuid="msg-5", role=Role.ASSISTANT, content="I'm doing well, thanks!")
        ]
    
    @pytest.fixture
    def user_only_history(self):
        """ユーザーメッセージのみの履歴"""
        return [
            MessageEntity(id=1, uuid="msg-1", role=Role.USER, content="First message"),
            MessageEntity(id=2, uuid="msg-2", role=Role.USER, content="Second message")
        ]
    
    @pytest.fixture
    def assistant_ending_history(self):
        """アシスタントメッセージで終わる履歴"""
        return [
            MessageEntity(id=1, uuid="msg-1", role=Role.USER, content="Hello"),
            MessageEntity(id=2, uuid="msg-2", role=Role.ASSISTANT, content="Hi!")
        ]
    
    @pytest.fixture
    def user_ending_history(self):
        """ユーザーメッセージで終わる履歴"""
        return [
            MessageEntity(id=1, uuid="msg-1", role=Role.USER, content="Hello"),
            MessageEntity(id=2, uuid="msg-2", role=Role.ASSISTANT, content="Hi!"),
            MessageEntity(id=3, uuid="msg-3", role=Role.USER, content="How are you?")
        ]

    # === 履歴取得テスト ===
    
    @pytest.mark.asyncio
    async def test_get_chat_history_success(self, service, mock_chat_repo, sample_mixed_history):
        """正常な履歴取得"""
        # Given
        uuid_list = ["msg-1", "msg-2", "msg-3", "msg-4", "msg-5"]
        mock_chat_repo.get_history.return_value = sample_mixed_history
        
        # When
        result = await service.get_chat_history(uuid_list)
        
        # Then
        assert result == sample_mixed_history
        mock_chat_repo.get_history.assert_called_once_with(uuid_list)
    
    @pytest.mark.asyncio
    async def test_get_chat_history_empty_list(self, service, mock_chat_repo):
        """空のUUIDリストでの履歴取得"""
        # Given
        empty_uuid_list = []
        mock_chat_repo.get_history.return_value = []
        
        # When
        result = await service.get_chat_history(empty_uuid_list)
        
        # Then
        assert result == []
        mock_chat_repo.get_history.assert_called_once_with(empty_uuid_list)
    
    @pytest.mark.asyncio
    async def test_get_chat_history_repo_error(self, service, mock_chat_repo):
        """リポジトリエラー時の例外伝播"""
        # Given
        uuid_list = ["msg-1", "msg-2"]
        mock_chat_repo.get_history.side_effect = Exception("Database error")
        
        # When & Then
        with pytest.raises(Exception, match="Database error"):
            await service.get_chat_history(uuid_list)

    # === 最後のアシスタントメッセージ除外テスト ===
    
    def test_exclude_last_assistant_message_with_assistant_ending(self, service, assistant_ending_history):
        """最後がアシスタントメッセージの場合の除外"""
        # When
        result = service.exclude_last_assistant_message(assistant_ending_history)
        
        # Then
        assert len(result) == 1
        assert result[0].role == Role.USER
        assert result[0].content == "Hello"
    
    def test_exclude_last_assistant_message_with_user_ending(self, service, user_ending_history):
        """最後がユーザーメッセージの場合は除外されない"""
        # When
        result = service.exclude_last_assistant_message(user_ending_history)
        
        # Then
        assert result == user_ending_history  # 変更されない
        assert len(result) == 3
    
    def test_exclude_last_assistant_message_empty_history(self, service):
        """空の履歴の場合"""
        # Given
        empty_history = []
        
        # When
        result = service.exclude_last_assistant_message(empty_history)
        
        # Then
        assert result == []
    
    def test_exclude_last_assistant_message_single_user_message(self, service):
        """単一のユーザーメッセージの場合"""
        # Given
        single_user = [MessageEntity(id=1, uuid="msg-1", role=Role.USER, content="Hello")]
        
        # When
        result = service.exclude_last_assistant_message(single_user)
        
        # Then
        assert result == single_user
    
    def test_exclude_last_assistant_message_single_assistant_message(self, service):
        """単一のアシスタントメッセージの場合"""
        # Given
        single_assistant = [MessageEntity(id=1, uuid="msg-1", role=Role.ASSISTANT, content="Hello")]
        
        # When
        result = service.exclude_last_assistant_message(single_assistant)
        
        # Then
        assert result == []

    # === 最後のユーザーメッセージ検索テスト ===
    
    def test_find_last_user_message_success(self, service, sample_mixed_history):
        """正常な最後のユーザーメッセージ検索"""
        # When
        result = service.find_last_user_message(sample_mixed_history)
        
        # Then
        assert result.uuid == "msg-4"
        assert result.role == Role.USER
        assert result.content == "How are you?"
    
    def test_find_last_user_message_user_only(self, service, user_only_history):
        """ユーザーメッセージのみの履歴での検索"""
        # When
        result = service.find_last_user_message(user_only_history)
        
        # Then
        assert result.uuid == "msg-2"
        assert result.content == "Second message"
    
    def test_find_last_user_message_no_user_messages(self, service):
        """ユーザーメッセージが存在しない場合"""
        # Given
        assistant_only = [
            MessageEntity(id=1, uuid="msg-1", role=Role.ASSISTANT, content="Hello"),
            MessageEntity(id=2, uuid="msg-2", role=Role.SYSTEM, content="System")
        ]
        
        # When & Then
        with pytest.raises(ValueError, match="No user message found in chat history"):
            service.find_last_user_message(assistant_only)
    
    def test_find_last_user_message_empty_history(self, service):
        """空の履歴での検索"""
        # Given
        empty_history = []
        
        # When & Then
        with pytest.raises(ValueError, match="No user message found in chat history"):
            service.find_last_user_message(empty_history)

    # === 最後のユーザーメッセージまでの履歴取得テスト ===
    
    def test_get_messages_up_to_last_user_with_assistant_ending(self, service, sample_mixed_history):
        """アシスタントメッセージで終わる履歴から最後のユーザーメッセージまで取得"""
        # When
        result = service.get_messages_up_to_last_user(sample_mixed_history)
        
        # Then
        assert len(result) == 4
        assert result[-1].role == Role.USER
        assert result[-1].content == "How are you?"
    
    def test_get_messages_up_to_last_user_with_user_ending(self, service, user_ending_history):
        """ユーザーメッセージで終わる履歴の場合"""
        # When
        result = service.get_messages_up_to_last_user(user_ending_history)
        
        # Then
        assert result == user_ending_history
        assert len(result) == 3
    
    def test_get_messages_up_to_last_user_empty_after_exclusion(self, service):
        """アシスタントメッセージ除外後に空になる場合"""
        # Given
        single_assistant = [MessageEntity(id=1, uuid="msg-1", role=Role.ASSISTANT, content="Hello")]
        
        # When
        result = service.get_messages_up_to_last_user(single_assistant)
        
        # Then
        assert result == []
    
    def test_get_messages_up_to_last_user_no_user_after_exclusion(self, service):
        """アシスタントメッセージ除外後にユーザーメッセージが最後でない場合"""
        # Given
        system_ending = [
            MessageEntity(id=1, uuid="msg-1", role=Role.SYSTEM, content="System"),
            MessageEntity(id=2, uuid="msg-2", role=Role.ASSISTANT, content="Hello")
        ]
        
        # When & Then
        with pytest.raises(ValueError, match="Last message is not from user"):
            service.get_messages_up_to_last_user(system_ending)
    
    def test_get_messages_up_to_last_user_empty_history(self, service):
        """空の履歴の場合"""
        # Given
        empty_history = []
        
        # When
        result = service.get_messages_up_to_last_user(empty_history)
        
        # Then
        assert result == []

    # === 複雑なシナリオテスト ===
    
    def test_complex_conversation_flow(self, service):
        """複雑な会話フローのテスト"""
        # Given
        complex_history = [
            MessageEntity(id=1, uuid="msg-1", role=Role.SYSTEM, content="System prompt"),
            MessageEntity(id=2, uuid="msg-2", role=Role.USER, content="Question 1"),
            MessageEntity(id=3, uuid="msg-3", role=Role.ASSISTANT, content="Answer 1"),
            MessageEntity(id=4, uuid="msg-4", role=Role.USER, content="Question 2"),
            MessageEntity(id=5, uuid="msg-5", role=Role.ASSISTANT, content="Answer 2"),
            MessageEntity(id=6, uuid="msg-6", role=Role.USER, content="Final question"),
            MessageEntity(id=7, uuid="msg-7", role=Role.ASSISTANT, content="Final answer")
        ]
        
        # Test exclude last assistant message
        without_last = service.exclude_last_assistant_message(complex_history)
        assert len(without_last) == 6
        assert without_last[-1].content == "Final question"
        
        # Test find last user message
        last_user = service.find_last_user_message(complex_history)
        assert last_user.content == "Final question"
        
        # Test get messages up to last user
        up_to_user = service.get_messages_up_to_last_user(complex_history)
        assert len(up_to_user) == 6
        assert up_to_user[-1].content == "Final question"