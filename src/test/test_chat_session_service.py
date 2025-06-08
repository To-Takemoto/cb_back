"""
ChatSessionService Unit Tests

チャットセッション管理サービスの包括的なユニットテスト
新しいチャット開始、既存チャット再開、セッション状態管理をテスト
"""

import pytest
import uuid
import sys
import os
from unittest.mock import AsyncMock, Mock

# Add path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from src.domain.entity.message_entity import MessageEntity, Role
from src.domain.entity.chat_tree import ChatTree, ChatStructure
from src.usecase.chat_interaction.chat_session_service import ChatSessionService
from src.usecase.chat_interaction.message_cache import MessageCache
from src.port.chat_repo import ChatRepository


class TestChatSessionService:
    """ChatSessionServiceの包括的テスト"""
    
    @pytest.fixture
    def mock_chat_repo(self):
        """モックChatRepositoryフィクスチャ"""
        return AsyncMock(spec=ChatRepository)
    
    @pytest.fixture  
    def mock_cache(self):
        """モックMessageCacheフィクスチャ"""
        return Mock(spec=MessageCache)
    
    @pytest.fixture
    def service(self, mock_chat_repo, mock_cache):
        """ChatSessionServiceインスタンス"""
        return ChatSessionService(mock_chat_repo, mock_cache)
    
    @pytest.fixture
    def sample_message(self):
        """サンプルメッセージエンティティ"""
        return MessageEntity(
            id=1,
            uuid="test-message-uuid",
            role=Role.SYSTEM,
            content="Test system message"
        )
    
    @pytest.fixture
    def sample_chat_tree(self):
        """サンプルチャットツリー"""
        root_node = ChatStructure(message_uuid="test-message-uuid")
        return ChatTree(id=1, uuid="test-chat-uuid", tree=root_node)

    # === 新しいチャット開始テスト ===
    
    @pytest.mark.asyncio
    async def test_start_new_chat_with_initial_message(self, service, mock_chat_repo, mock_cache, sample_message, sample_chat_tree):
        """初期メッセージ付きで新しいチャットを開始"""
        # Given
        initial_content = "Welcome to the chat"
        mock_chat_repo.init_structure.return_value = (sample_chat_tree, sample_message)
        
        # When
        result_uuid = await service.start_new_chat(initial_content)
        
        # Then
        assert result_uuid == sample_chat_tree.uuid
        assert service.get_current_chat_uuid() == sample_chat_tree.uuid
        assert service.is_chat_active()
        
        # リポジトリが正しく呼ばれたかチェック
        mock_chat_repo.init_structure.assert_called_once()
        created_message = mock_chat_repo.init_structure.call_args[0][0]
        assert created_message.role == Role.SYSTEM
        assert created_message.content == initial_content
        
        # キャッシュが更新されたかチェック
        mock_cache.set.assert_called_once_with(sample_message)
    
    @pytest.mark.asyncio
    async def test_start_new_chat_without_initial_message(self, service, mock_chat_repo, mock_cache, sample_message, sample_chat_tree):
        """初期メッセージなしで新しいチャットを開始"""
        # Given
        mock_chat_repo.init_structure.return_value = (sample_chat_tree, sample_message)
        
        # When
        result_uuid = await service.start_new_chat()
        
        # Then
        assert result_uuid == sample_chat_tree.uuid
        created_message = mock_chat_repo.init_structure.call_args[0][0]
        assert created_message.content == ""  # 空文字列になるべき
    
    @pytest.mark.asyncio
    async def test_start_new_chat_with_none_message(self, service, mock_chat_repo, mock_cache, sample_message, sample_chat_tree):
        """None初期メッセージで新しいチャットを開始"""
        # Given
        mock_chat_repo.init_structure.return_value = (sample_chat_tree, sample_message)
        
        # When
        result_uuid = await service.start_new_chat(None)
        
        # Then
        created_message = mock_chat_repo.init_structure.call_args[0][0]
        assert created_message.content == ""

    # === 既存チャット再開テスト ===
    
    @pytest.mark.asyncio
    async def test_restart_existing_chat(self, service, mock_chat_repo, sample_chat_tree):
        """既存のチャットを正常に再開"""
        # Given
        chat_uuid = "existing-chat-uuid"
        mock_chat_repo.load_tree.return_value = sample_chat_tree
        
        # When
        await service.restart_chat(chat_uuid)
        
        # Then
        assert service.get_current_chat_uuid() == chat_uuid
        assert service.is_chat_active()
        mock_chat_repo.load_tree.assert_called_once_with(chat_uuid)
    
    @pytest.mark.asyncio
    async def test_restart_chat_repo_error(self, service, mock_chat_repo):
        """チャットリポジトリエラー時の例外伝播"""
        # Given
        chat_uuid = "non-existent-chat-uuid"
        mock_chat_repo.load_tree.side_effect = Exception("Chat not found")
        
        # When & Then
        with pytest.raises(Exception, match="Chat not found"):
            await service.restart_chat(chat_uuid)
        
        # サービス状態が変更されていないことを確認
        assert service.get_current_chat_uuid() is None
        assert not service.is_chat_active()

    # === セッション状態管理テスト ===
    
    def test_initial_state(self, service):
        """初期状態が正しく設定されている"""
        assert service.get_current_chat_uuid() is None
        assert service.get_structure_handler() is None
        assert not service.is_chat_active()
    
    @pytest.mark.asyncio
    async def test_chat_session_state_transitions(self, service, mock_chat_repo, mock_cache, sample_message, sample_chat_tree):
        """チャットセッション状態の遷移"""
        # Given
        mock_chat_repo.init_structure.return_value = (sample_chat_tree, sample_message)
        mock_chat_repo.load_tree.return_value = sample_chat_tree
        
        # 初期状態
        assert not service.is_chat_active()
        
        # 新しいチャット開始
        await service.start_new_chat("Hello")
        assert service.is_chat_active()
        first_uuid = service.get_current_chat_uuid()
        
        # 別のチャットに切り替え
        await service.restart_chat("another-uuid")
        assert service.is_chat_active()
        assert service.get_current_chat_uuid() == "another-uuid"
        assert service.get_current_chat_uuid() != first_uuid

    # === エラーハンドリングテスト ===
    
    @pytest.mark.asyncio
    async def test_start_chat_repo_failure(self, service, mock_chat_repo):
        """チャット開始時のリポジトリエラー"""
        # Given
        mock_chat_repo.init_structure.side_effect = Exception("Database error")
        
        # When & Then
        with pytest.raises(Exception, match="Database error"):
            await service.start_new_chat("Test")
        
        # 状態が変更されていないことを確認
        assert not service.is_chat_active()

    # === 境界値テスト ===
    
    @pytest.mark.asyncio
    async def test_start_chat_with_empty_string(self, service, mock_chat_repo, mock_cache, sample_message, sample_chat_tree):
        """空文字列の初期メッセージ"""
        # Given
        mock_chat_repo.init_structure.return_value = (sample_chat_tree, sample_message)
        
        # When
        await service.start_new_chat("")
        
        # Then
        created_message = mock_chat_repo.init_structure.call_args[0][0]
        assert created_message.content == ""
    
    @pytest.mark.asyncio
    async def test_start_chat_with_whitespace_message(self, service, mock_chat_repo, mock_cache, sample_message, sample_chat_tree):
        """空白文字のみの初期メッセージ"""
        # Given
        mock_chat_repo.init_structure.return_value = (sample_chat_tree, sample_message)
        
        # When
        await service.start_new_chat("   \n\t   ")
        
        # Then
        created_message = mock_chat_repo.init_structure.call_args[0][0]
        assert created_message.content == "   \n\t   "  # そのまま保持される