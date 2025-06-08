import pytest
import uuid as uuidGen
from datetime import datetime, timedelta
from tortoise import Tortoise

from src.infra.tortoise_client.models import User, DiscussionStructure, Message, LLMDetails
from src.infra.tortoise_client.chat_repo import TortoiseChatRepository
from src.domain.entity.message_entity import MessageEntity, Role


class TestChatUnimplementedFeatures:
    """未実装のチャット機能のテストケース"""
    
    @pytest.fixture
    async def setup_db_with_data(self):
        """テスト用のデータベースとデータを準備"""
        await Tortoise.init(
            db_url="sqlite://:memory:",
            modules={"models": ["src.infra.tortoise_client.models"]}
        )
        await Tortoise.generate_schemas()
        
        # テスト用ユーザーを作成
        user = await User.create(
            uuid=str(uuidGen.uuid4()),
            username="testuser",
            password_hash="hashed_password"
        )
        
        # テスト用ディスカッション構造を作成
        discussion = await DiscussionStructure.create(
            user=user,
            uuid=str(uuidGen.uuid4()),
            title="Test Chat",
            system_prompt="You are a helpful assistant",
            serialized_structure=b"test_tree_data",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        # テスト用メッセージを作成
        message1 = await Message.create(
            discussion=discussion,
            uuid=str(uuidGen.uuid4()),
            role="user",
            content="Hello, how are you?",
            created_at=datetime.utcnow()
        )
        
        message2 = await Message.create(
            discussion=discussion,
            uuid=str(uuidGen.uuid4()),
            role="assistant",
            content="I'm doing well, thank you!",
            created_at=datetime.utcnow()
        )
        
        # リポジトリインスタンスを作成
        repo = TortoiseChatRepository(user.id)
        
        yield {
            "user": user,
            "discussion": discussion,
            "message1": message1,
            "message2": message2,
            "repo": repo
        }
        
        await Tortoise.close_connections()

    async def test_delete_chat_success(self, setup_db_with_data):
        """チャット削除機能のテスト - 成功ケース（現在は失敗する）"""
        data = await setup_db_with_data
        user = data["user"]
        discussion = data["discussion"]
        repo = data["repo"]
        
        # 削除前にディスカッションが存在することを確認
        discussion_exists = await DiscussionStructure.filter(uuid=discussion.uuid).exists()
        assert discussion_exists
        
        # チャットを削除（現在の実装はFalseを返す）
        result = await repo.delete_chat(discussion.uuid, user.uuid)
        
        # 削除が成功することを期待
        assert result is True

    async def test_update_chat_success(self, setup_db_with_data):
        """チャット更新機能のテスト - 成功ケース（現在は失敗する）"""
        data = await setup_db_with_data
        user = data["user"]
        discussion = data["discussion"]
        repo = data["repo"]
        
        new_title = "Updated Chat Title"
        new_system_prompt = "You are a coding assistant"
        
        # 更新（現在の実装はFalseを返す）
        result = await repo.update_chat(
            discussion.uuid, 
            user.uuid, 
            new_title, 
            new_system_prompt
        )
        
        # 更新が成功することを期待
        assert result is True

    async def test_search_messages_success(self, setup_db_with_data):
        """メッセージ検索機能のテスト - 成功ケース（現在は失敗する）"""
        data = await setup_db_with_data
        discussion = data["discussion"]
        message1 = data["message1"]
        repo = data["repo"]
        
        # 検索（現在の実装は空リストを返す）
        results = await repo.search_messages(discussion.uuid, "Hello")
        
        # 検索結果が返されることを期待
        assert len(results) == 1
        assert results[0]["uuid"] == message1.uuid
        assert results[0]["content"] == "Hello, how are you?"

    async def test_edit_message_success(self, setup_db_with_data):
        """メッセージ編集機能のテスト - 成功ケース（現在は失敗する）"""
        data = await setup_db_with_data
        user = data["user"]
        discussion = data["discussion"]
        message1 = data["message1"]
        repo = data["repo"]
        
        new_content = "Updated message content"
        
        # 編集（現在の実装はFalseを返す）
        result = await repo.edit_message(
            discussion.uuid, 
            message1.uuid, 
            user.uuid, 
            new_content
        )
        
        # 編集が成功することを期待
        assert result is True

    async def test_delete_message_success(self, setup_db_with_data):
        """メッセージ削除機能のテスト - 成功ケース（現在は失敗する）"""
        data = await setup_db_with_data
        user = data["user"]
        discussion = data["discussion"]
        message1 = data["message1"]
        repo = data["repo"]
        
        # 削除（現在の実装はFalseを返す）
        result = await repo.delete_message(
            discussion.uuid, 
            message1.uuid, 
            user.uuid
        )
        
        # 削除が成功することを期待
        assert result is True