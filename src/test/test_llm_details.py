"""
LLMDetailsテーブルの活用に関するテスト

このテストファイルは、LLMDetailsテーブルが適切に
メッセージと関連付けられ、トークン情報が保存されることを検証します。
"""

import pytest
from unittest.mock import Mock, patch
from src.infra.tortoise_client.chat_repo import TortoiseChatRepository as ChatRepo
from src.infra.tortoise_client.models import (
    User, DiscussionStructure, Message as mm, LLMDetails
)
from tortoise import Tortoise
from src.port.dto.message_dto import MessageDTO
from src.domain.entity.message_entity import Role
import uuid as uuidGen


class TestLLMDetails:
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
        self.test_user = await User.create(
            name="testuser",
            uuid=str(uuidGen.uuid4()),
            password="dummy_hash"
        )
        
        # テストチャットを作成
        self.test_chat = await DiscussionStructure.create(
            user=self.test_user,
            uuid=str(uuidGen.uuid4()),
            serialized_structure=b"",
            title="Test Chat"
        )
        
        yield
        
        # テスト後にクリーンアップ
        await Tortoise.close_connections()
    
    @pytest.mark.asyncio
    async def test_save_message_with_llm_details_for_assistant(self):
        """アシスタントメッセージ保存時にLLM詳細情報が保存されることを確認"""
        # Arrange
        chat_repo = ChatRepo(user_id=self.test_user.id)
        message_dto = MessageDTO(
            role=Role.ASSISTANT,
            content="This is an AI response"
        )
        
        llm_details = {
            "model": "gpt-4",
            "provider": "openrouter",
            "prompt_tokens": 50,
            "completion_tokens": 30,
            "total_tokens": 80
        }
        
        # Act
        saved_message = await chat_repo.save_message(
            discussion_structure_uuid=self.test_chat.uuid,
            message_dto=message_dto,
            llm_details=llm_details
        )
        
        # Assert
        # メッセージが保存されたことを確認
        assert saved_message is not None
        assert saved_message.content == "This is an AI response"
        assert saved_message.role == Role.ASSISTANT
        
        # LLMDetailsが保存されたことを確認
        message_record = await mm.filter(uuid=saved_message.uuid).first()
        llm_record = await LLMDetails.filter(message=message_record).first()
        assert llm_record is not None
        assert llm_record.model == "gpt-4"
        assert llm_record.provider == "openrouter"
        assert llm_record.prompt_tokens == 50
        assert llm_record.completion_tokens == 30
        assert llm_record.total_tokens == 80
    
    @pytest.mark.asyncio
    async def test_save_message_without_llm_details_for_user(self):
        """ユーザーメッセージ保存時にLLM詳細情報が保存されないことを確認"""
        # Arrange
        chat_repo = ChatRepo(user_id=self.test_user.id)
        message_dto = MessageDTO(
            role=Role.USER,
            content="This is a user message"
        )
        
        # Act
        saved_message = await chat_repo.save_message(
            discussion_structure_uuid=self.test_chat.uuid,
            message_dto=message_dto,
            llm_details=None  # ユーザーメッセージにはLLM詳細なし
        )
        
        # Assert
        # メッセージが保存されたことを確認
        assert saved_message is not None
        assert saved_message.content == "This is a user message"
        assert saved_message.role == Role.USER
        
        # LLMDetailsが保存されていないことを確認
        message_record = await mm.filter(uuid=saved_message.uuid).first()
        llm_record = await LLMDetails.filter(message=message_record).first()
        assert llm_record is None
    
    @pytest.mark.asyncio
    async def test_save_message_with_partial_llm_details(self):
        """部分的なLLM詳細情報でも適切にデフォルト値で保存されることを確認"""
        # Arrange
        chat_repo = ChatRepo(user_id=self.test_user.id)
        message_dto = MessageDTO(
            role=Role.ASSISTANT,
            content="AI response with partial details"
        )
        
        llm_details = {
            "model": "gpt-3.5-turbo",
            # providerとトークン情報が欠けている
        }
        
        # Act
        saved_message = await chat_repo.save_message(
            discussion_structure_uuid=self.test_chat.uuid,
            message_dto=message_dto,
            llm_details=llm_details
        )
        
        # Assert
        message_record = await mm.filter(uuid=saved_message.uuid).first()
        llm_record = await LLMDetails.filter(message=message_record).first()
        assert llm_record is not None
        assert llm_record.model == "gpt-3.5-turbo"
        assert llm_record.provider == "openrouter"  # デフォルト値
        assert llm_record.prompt_tokens == 0  # デフォルト値
        assert llm_record.completion_tokens == 0  # デフォルト値
        assert llm_record.total_tokens == 0  # デフォルト値
    
    @pytest.mark.asyncio
    async def test_delete_message_also_deletes_llm_details(self):
        """メッセージ削除時に関連するLLM詳細情報も削除されることを確認"""
        # Arrange
        chat_repo = ChatRepo(user_id=self.test_user.id)
        message_dto = MessageDTO(
            role=Role.ASSISTANT,
            content="Message to be deleted"
        )
        
        llm_details = {
            "model": "gpt-4",
            "provider": "openrouter",
            "total_tokens": 100
        }
        
        # メッセージとLLM詳細を保存
        saved_message = await chat_repo.save_message(
            discussion_structure_uuid=self.test_chat.uuid,
            message_dto=message_dto,
            llm_details=llm_details
        )
        
        # LLM詳細が存在することを確認
        message_record = await mm.filter(uuid=saved_message.uuid).first()
        llm_record = await LLMDetails.filter(message=message_record).first()
        assert llm_record is not None
        
        # Act - メッセージを削除
        result = await chat_repo.delete_message(
            chat_uuid=self.test_chat.uuid,
            message_id=saved_message.uuid,
            user_uuid=self.test_user.uuid
        )
        
        # Assert
        assert result is True
        
        # メッセージが削除されたことを確認
        deleted_message = await mm.filter(uuid=saved_message.uuid).first()
        assert deleted_message is None
        
        # LLM詳細も削除されたことを確認
        deleted_llm_record = await LLMDetails.filter(id=llm_record.id).first()
        assert deleted_llm_record is None