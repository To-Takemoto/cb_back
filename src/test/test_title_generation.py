"""
チャットタイトル自動生成機能に関するテスト

このテストファイルは、最初のユーザー/アシスタント交換後に
LLMを使って自動的にチャットタイトルが生成されることを検証します。
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from src.infra.tortoise_client.models import (
    User, DiscussionStructure, Message as mm, LLMDetails
)
from tortoise import Tortoise
from src.infra.tortoise_client.chat_repo import TortoiseChatRepository as ChatRepo
from src.port.dto.message_dto import MessageDTO
from src.domain.entity.message_entity import Role
from src.usecase.chat_interaction.main import ChatInteraction
from src.usecase.chat_interaction.message_cache import MessageCache
import uuid as uuidGen


class TestTitleGeneration:
    @pytest.fixture(autouse=True)
    async def setup(self):
        """各テストの前にデータベースをセットアップ"""
        # テスト用インメモリデータベースを初期化
        await Tortoise.init(
            db_url="sqlite://:memory:",
            modules={"models": ["src.infra.tortoise_client.models"]}
        )
        await Tortoise.generate_schemas()
        
        # テストユーザーを作成
        self.test_user_id = str(uuidGen.uuid4())
        self.test_user = await User.create(
            name="testuser",
            uuid=self.test_user_id,
            password="dummy_hash"
        )
        
        yield
        
        # テスト後にクリーンアップ
        await Tortoise.close_connections()
    
    @pytest.mark.asyncio
    async def test_title_generation_after_first_assistant_response(self):
        """最初のアシスタント応答後にタイトルが自動生成されることを確認"""
        # Arrange
        chat_repo = ChatRepo(user_id=self.test_user_id)
        
        # LLMクライアントをモック
        mock_llm_client = Mock()
        mock_llm_client.complete_message = AsyncMock()
        
        # 最初の応答（通常の会話）
        mock_llm_client.complete_message.side_effect = [
            # 1回目: 通常の応答
            {
                "content": "Hello! I'd be happy to help you with Python programming. What specific topic would you like to learn about?",
                "model": "gpt-4",
                "usage": {"total_tokens": 30}
            },
            # 2回目: タイトル生成
            {
                "content": "Python Programming Help",
                "model": "gpt-4", 
                "usage": {"total_tokens": 10}
            }
        ]
        
        cache = MessageCache()
        interaction = ChatInteraction(chat_repo, mock_llm_client, cache)
        
        # チャットを開始
        initial_message = "Hello, can you help me with Python?"
        system_prompt = "You are a helpful programming assistant."
        interaction.start_new_chat(initial_message, system_prompt)
        
        # Act - 最初のユーザーメッセージを送信（これでタイトル生成がトリガーされる）
        with patch.object(interaction, '_generate_title') as mock_generate_title:
            mock_generate_title.return_value = "Python Programming Help"
            
            response = await interaction.continue_chat("Can you explain variables?")
        
        # Assert
        # 応答が正しく返されたことを確認
        assert response is not None
        assert "help you with Python" in response.content
        
        # タイトル生成メソッドが呼ばれたことを確認
        mock_generate_title.assert_called_once()
        
        # データベースでタイトルが更新されたことを確認
        chat_uuid = interaction.structure.get_uuid()
        chat = await DiscussionStructure.filter(uuid=chat_uuid).first()
        assert chat.title == "Python Programming Help"
    
    @pytest.mark.asyncio
    async def test_title_generation_with_short_conversation(self):
        """短い会話からもタイトルが生成されることを確認"""
        # Arrange
        chat_repo = ChatRepo(user_id=self.test_user_id)
        
        # チャットを手動で作成
        initial_message_dto = MessageDTO(Role.SYSTEM, "Hi")
        new_tree, initial_message_entity = chat_repo.init_structure(initial_message_dto)
        
        # ユーザーメッセージを追加
        user_message_dto = MessageDTO(Role.USER, "What's 2+2?")
        user_message = chat_repo.save_message(new_tree.uuid, user_message_dto)
        
        # アシスタントメッセージを追加
        assistant_message_dto = MessageDTO(Role.ASSISTANT, "2+2 equals 4.")
        assistant_message = chat_repo.save_message(new_tree.uuid, assistant_message_dto)
        
        # Act - タイトル生成メソッドを直接テスト
        messages = [user_message, assistant_message]
        
        # LLMクライアントをモック
        mock_llm_client = Mock()
        mock_llm_client.complete_message = AsyncMock(return_value={
            "content": "Math Question",
            "model": "gpt-4",
            "usage": {"total_tokens": 5}
        })
        
        # タイトル生成メソッドをテスト（実装後に詳細化）
        title = await chat_repo.generate_chat_title(new_tree.uuid, messages, mock_llm_client)
        
        # Assert
        assert title == "Math Question"
        
        # LLMが適切なプロンプトで呼ばれたことを確認
        call_args = mock_llm_client.complete_message.call_args[0][0]
        assert any("タイトル" in msg.get("content", "") for msg in call_args)
    
    @pytest.mark.asyncio
    async def test_title_generation_fallback_for_llm_error(self):
        """LLMエラー時にフォールバック処理が動作することを確認"""
        # Arrange
        chat_repo = ChatRepo(user_id=self.test_user_id)
        
        # チャットを手動で作成
        initial_message_dto = MessageDTO(Role.SYSTEM, "Hello")
        new_tree, initial_message_entity = chat_repo.init_structure(initial_message_dto)
        
        # ユーザーメッセージを追加
        user_message_dto = MessageDTO(Role.USER, "This is a test message")
        user_message = chat_repo.save_message(new_tree.uuid, user_message_dto)
        
        # Act - LLMエラーをシミュレート
        mock_llm_client = Mock()
        mock_llm_client.complete_message = AsyncMock(side_effect=Exception("LLM service error"))
        
        messages = [user_message]
        title = await chat_repo.generate_chat_title(new_tree.uuid, messages, mock_llm_client)
        
        # Assert - フォールバック処理が動作し、最初のメッセージから生成される
        assert title == "This is a test message"  # 最初の50文字以内
    
    @pytest.mark.asyncio
    async def test_title_generation_max_length_limit(self):
        """生成されるタイトルが適切な長さに制限されることを確認"""
        # Arrange
        chat_repo = ChatRepo(user_id=self.test_user_id)
        
        # チャットを手動で作成
        initial_message_dto = MessageDTO(Role.SYSTEM, "Start")
        new_tree, initial_message_entity = chat_repo.init_structure(initial_message_dto)
        
        # ユーザーメッセージを追加
        user_message_dto = MessageDTO(Role.USER, "Short question")
        user_message = chat_repo.save_message(new_tree.uuid, user_message_dto)
        
        # LLMが非常に長いタイトルを返すケース
        mock_llm_client = Mock()
        very_long_title = "This is an extremely long title that exceeds the reasonable length limit for chat titles and should be truncated appropriately"
        mock_llm_client.complete_message = AsyncMock(return_value={
            "content": very_long_title,
            "model": "gpt-4",
            "usage": {"total_tokens": 15}
        })
        
        # Act
        messages = [user_message]
        title = await chat_repo.generate_chat_title(new_tree.uuid, messages, mock_llm_client)
        
        # Assert - タイトルが50文字以内に制限される
        assert len(title) <= 50
        assert title.startswith("This is an extremely long title")
    
    @pytest.mark.asyncio
    async def test_no_title_generation_for_empty_chat(self):
        """メッセージが空のチャットではタイトル生成されないことを確認"""
        # Arrange
        chat_repo = ChatRepo(user_id=self.test_user_id)
        
        # チャットを手動で作成（初期メッセージのみ）
        initial_message_dto = MessageDTO(Role.SYSTEM, "")
        new_tree, initial_message_entity = chat_repo.init_structure(initial_message_dto)
        
        mock_llm_client = Mock()
        
        # Act
        messages = []  # 空のメッセージリスト
        title = await chat_repo.generate_chat_title(new_tree.uuid, messages, mock_llm_client)
        
        # Assert
        assert title == "New Chat"  # デフォルトタイトル
        
        # LLMが呼ばれないことを確認
        mock_llm_client.complete_message.assert_not_called()