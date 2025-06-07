"""
LLMDetailsテーブルの活用に関するテスト

このテストファイルは、LLMDetailsテーブルが適切に
メッセージと関連付けられ、トークン情報が保存されることを検証します。
"""

import pytest
from unittest.mock import Mock, patch
from src.infra.sqlite_client.chat_repo import ChatRepo
from src.infra.sqlite_client.peewee_models import (
    User, DiscussionStructure, Message as mm, LLMDetails, db_proxy
)
from peewee import SqliteDatabase
from src.port.dto.message_dto import MessageDTO
from src.domain.entity.message_entity import Role
import uuid as uuidGen


class TestLLMDetails:
    @pytest.fixture(autouse=True)
    def setup(self):
        """各テストの前にデータベースをセットアップ"""
        # テスト用インメモリデータベースを初期化
        test_db = SqliteDatabase(':memory:')
        db_proxy.initialize(test_db)
        
        test_db.connect()
        test_db.create_tables([User, DiscussionStructure, mm, LLMDetails])
        
        # テストユーザーを作成
        self.test_user = User.create(
            name="testuser",
            uuid=str(uuidGen.uuid4()),
            password="dummy_hash"
        )
        
        # テストチャットを作成
        self.test_chat = DiscussionStructure.create(
            user=self.test_user,
            uuid=str(uuidGen.uuid4()),
            serialized_structure=b"",
            title="Test Chat"
        )
        
        yield
        
        # テスト後にクリーンアップ
        test_db.drop_tables([LLMDetails, mm, DiscussionStructure, User])
        test_db.close()
    
    def test_save_message_with_llm_details_for_assistant(self):
        """アシスタントメッセージ保存時にLLM詳細情報が保存されることを確認"""
        # Arrange
        chat_repo = ChatRepo(user_id=self.test_user.uuid)
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
        saved_message = chat_repo.save_message(
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
        llm_record = LLMDetails.get_or_none(
            LLMDetails.message == mm.get(mm.uuid == saved_message.uuid)
        )
        assert llm_record is not None
        assert llm_record.model == "gpt-4"
        assert llm_record.provider == "openrouter"
        assert llm_record.prompt_tokens == 50
        assert llm_record.completion_tokens == 30
        assert llm_record.total_tokens == 80
    
    def test_save_message_without_llm_details_for_user(self):
        """ユーザーメッセージ保存時にLLM詳細情報が保存されないことを確認"""
        # Arrange
        chat_repo = ChatRepo(user_id=self.test_user.uuid)
        message_dto = MessageDTO(
            role=Role.USER,
            content="This is a user message"
        )
        
        # Act
        saved_message = chat_repo.save_message(
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
        llm_record = LLMDetails.get_or_none(
            LLMDetails.message == mm.get(mm.uuid == saved_message.uuid)
        )
        assert llm_record is None
    
    def test_save_message_with_partial_llm_details(self):
        """部分的なLLM詳細情報でも適切にデフォルト値で保存されることを確認"""
        # Arrange
        chat_repo = ChatRepo(user_id=self.test_user.uuid)
        message_dto = MessageDTO(
            role=Role.ASSISTANT,
            content="AI response with partial details"
        )
        
        llm_details = {
            "model": "gpt-3.5-turbo",
            # providerとトークン情報が欠けている
        }
        
        # Act
        saved_message = chat_repo.save_message(
            discussion_structure_uuid=self.test_chat.uuid,
            message_dto=message_dto,
            llm_details=llm_details
        )
        
        # Assert
        llm_record = LLMDetails.get_or_none(
            LLMDetails.message == mm.get(mm.uuid == saved_message.uuid)
        )
        assert llm_record is not None
        assert llm_record.model == "gpt-3.5-turbo"
        assert llm_record.provider == "openrouter"  # デフォルト値
        assert llm_record.prompt_tokens == 0  # デフォルト値
        assert llm_record.completion_tokens == 0  # デフォルト値
        assert llm_record.total_tokens == 0  # デフォルト値
    
    def test_delete_message_also_deletes_llm_details(self):
        """メッセージ削除時に関連するLLM詳細情報も削除されることを確認"""
        # Arrange
        chat_repo = ChatRepo(user_id=self.test_user.uuid)
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
        saved_message = chat_repo.save_message(
            discussion_structure_uuid=self.test_chat.uuid,
            message_dto=message_dto,
            llm_details=llm_details
        )
        
        # LLM詳細が存在することを確認
        llm_record = LLMDetails.get_or_none(
            LLMDetails.message == mm.get(mm.uuid == saved_message.uuid)
        )
        assert llm_record is not None
        
        # Act - メッセージを削除
        result = chat_repo.delete_message(
            chat_uuid=self.test_chat.uuid,
            message_id=saved_message.uuid,
            user_uuid=self.test_user.uuid
        )
        
        # Assert
        assert result is True
        
        # メッセージが削除されたことを確認
        deleted_message = mm.get_or_none(mm.uuid == saved_message.uuid)
        assert deleted_message is None
        
        # LLM詳細も削除されたことを確認
        deleted_llm_record = LLMDetails.get_or_none(
            LLMDetails.id == llm_record.id
        )
        assert deleted_llm_record is None