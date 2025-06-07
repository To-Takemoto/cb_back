"""
systemロールメッセージ指定機能に関するテスト

このテストファイルは、チャット作成時にsystem_promptを指定でき、
LLM呼び出し時に適切に使用されることを検証します。
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from fastapi.testclient import TestClient
from src.infra.sqlite_client.peewee_models import (
    User, DiscussionStructure, Message as mm, LLMDetails, db_proxy
)
from peewee import SqliteDatabase
from src.infra.rest_api.main import app
from src.infra.rest_api.dependencies import get_current_user
from src.infra.auth import create_access_token
import uuid as uuidGen
import json


class TestSystemPrompt:
    @pytest.fixture(autouse=True)
    def setup(self):
        """各テストの前にデータベースをセットアップ"""
        # テスト用インメモリデータベースを初期化
        test_db = SqliteDatabase(':memory:')
        db_proxy.initialize(test_db)
        
        test_db.connect()
        test_db.create_tables([User, DiscussionStructure, mm, LLMDetails])
        
        # テストユーザーを作成
        self.test_user_id = str(uuidGen.uuid4())
        self.test_user = User.create(
            name="testuser",
            uuid=self.test_user_id,
            password="dummy_hash"
        )
        
        # テストクライアントを作成
        self.client = TestClient(app)
        
        # 認証をモック
        app.dependency_overrides[get_current_user] = lambda: self.test_user_id
        
        # アクセストークンを作成
        self.token = create_access_token(data={"sub": self.test_user_id})
        self.headers = {"Authorization": f"Bearer {self.token}"}
        
        yield
        
        # テスト後にクリーンアップ
        app.dependency_overrides.clear()
        test_db.drop_tables([LLMDetails, mm, DiscussionStructure, User])
        test_db.close()
    
    @pytest.mark.asyncio
    async def test_create_chat_with_system_prompt(self):
        """system_promptを指定してチャットを作成できることを確認"""
        # Arrange
        system_prompt = "You are a helpful AI assistant specialized in Python programming."
        request_data = {
            "initial_message": "Hello, can you help me with Python?",
            "model_id": "gpt-4",
            "system_prompt": system_prompt
        }
        
        # Act
        with patch('src.infra.openrouter_client.OpenRouterLLMService.complete_message') as mock_complete:
            mock_complete.return_value = AsyncMock(return_value={
                "content": "Hello! I'd be happy to help you with Python.",
                "model": "gpt-4",
                "usage": {
                    "prompt_tokens": 20,
                    "completion_tokens": 10,
                    "total_tokens": 30
                }
            })()
            
            response = self.client.post(
                "/api/v1/chats/",
                json=request_data,
                headers=self.headers
            )
        
        # Assert
        print(f"Response status: {response.status_code}")
        print(f"Response body: {response.text}")
        assert response.status_code == 201
        data = response.json()
        assert "chat_id" in data
        assert "messages" in data
        
        # データベースでsystem_promptが保存されていることを確認
        chat = DiscussionStructure.get(DiscussionStructure.uuid == data["chat_id"])
        assert chat.system_prompt == system_prompt
    
    @pytest.mark.asyncio
    async def test_create_chat_without_system_prompt(self):
        """system_promptなしでもチャットを作成できることを確認"""
        # Arrange
        request_data = {
            "initial_message": "Hello!",
            "model_id": "gpt-3.5-turbo"
        }
        
        # Act
        with patch('src.infra.openrouter_client.OpenRouterLLMService.complete_message') as mock_complete:
            mock_complete.return_value = AsyncMock(return_value={
                "content": "Hello! How can I help you?",
                "model": "gpt-3.5-turbo",
                "usage": {
                    "prompt_tokens": 10,
                    "completion_tokens": 8,
                    "total_tokens": 18
                }
            })()
            
            response = self.client.post(
                "/api/v1/chats/",
                json=request_data,
                headers=self.headers
            )
        
        # Assert
        assert response.status_code == 201
        data = response.json()
        
        # system_promptがNullであることを確認
        chat = DiscussionStructure.get(DiscussionStructure.uuid == data["chat_id"])
        assert chat.system_prompt is None
    
    @pytest.mark.asyncio
    async def test_system_prompt_used_in_llm_call(self):
        """LLM呼び出し時にsystem_promptが使用されることを確認"""
        # Arrange
        system_prompt = "You are a math tutor. Always explain step by step."
        
        # まずsystem_prompt付きでチャットを作成
        with patch('src.infra.openrouter_client.OpenRouterLLMService.complete_message') as mock_complete:
            mock_complete.return_value = AsyncMock(return_value={
                "content": "I'll help you with math!",
                "model": "gpt-4",
                "usage": {"total_tokens": 20}
            })()
            
            create_response = self.client.post(
                "/api/v1/chats/",
                json={
                    "initial_message": "Help me with calculus",
                    "model_id": "gpt-4",
                    "system_prompt": system_prompt
                },
                headers=self.headers
            )
        
        chat_id = create_response.json()["chat_id"]
        
        # Act - 続きのメッセージを送信
        with patch('src.infra.openrouter_client.OpenRouterLLMService.complete_message') as mock_complete:
            mock_complete.return_value = AsyncMock(return_value={
                "content": "Let me explain derivatives step by step...",
                "model": "gpt-4",
                "usage": {"total_tokens": 50}
            })()
            
            continue_response = self.client.post(
                f"/api/v1/chats/{chat_id}/messages",
                json={"content": "What is a derivative?"},
                headers=self.headers
            )
            
            # complete_messageが呼ばれた際の引数を確認
            call_args = mock_complete.call_args[0][0]  # 最初の位置引数（messages）を取得
        
        # Assert
        assert continue_response.status_code == 201
        
        # system_promptが最初のメッセージとして含まれていることを確認
        assert len(call_args) >= 1
        assert call_args[0]["role"] == "system"
        assert call_args[0]["content"] == system_prompt
    
    @pytest.mark.asyncio
    async def test_update_chat_system_prompt(self):
        """既存のチャットのsystem_promptを更新できることを確認"""
        # Arrange - チャットを作成
        with patch('src.infra.openrouter_client.OpenRouterLLMService.complete_message') as mock_complete:
            mock_complete.return_value = AsyncMock(return_value={
                "content": "Hello!",
                "model": "gpt-4",
                "usage": {"total_tokens": 10}
            })()
            
            create_response = self.client.post(
                "/api/v1/chats/",
                json={
                    "initial_message": "Hi",
                    "system_prompt": "You are a general assistant."
                },
                headers=self.headers
            )
        
        chat_id = create_response.json()["chat_id"]
        new_system_prompt = "You are now a coding expert specializing in Python."
        
        # Act - system_promptを更新
        update_response = self.client.patch(
            f"/api/v1/chats/{chat_id}",
            json={"system_prompt": new_system_prompt},
            headers=self.headers
        )
        
        # Assert
        assert update_response.status_code == 200
        
        # データベースで更新されていることを確認
        chat = DiscussionStructure.get(DiscussionStructure.uuid == chat_id)
        assert chat.system_prompt == new_system_prompt
    
    @pytest.mark.asyncio
    async def test_get_chat_includes_system_prompt(self):
        """チャット取得時にsystem_promptが含まれることを確認"""
        # Arrange - system_prompt付きチャットを作成
        system_prompt = "You are a friendly assistant."
        
        with patch('src.infra.openrouter_client.OpenRouterLLMService.complete_message') as mock_complete:
            mock_complete.return_value = AsyncMock(return_value={
                "content": "Hi there!",
                "model": "gpt-4",
                "usage": {"total_tokens": 10}
            })()
            
            create_response = self.client.post(
                "/api/v1/chats/",
                json={
                    "initial_message": "Hello",
                    "system_prompt": system_prompt
                },
                headers=self.headers
            )
        
        chat_id = create_response.json()["chat_id"]
        
        # Act - チャット情報を取得
        get_response = self.client.get(
            f"/api/v1/chats/{chat_id}",
            headers=self.headers
        )
        
        # Assert
        assert get_response.status_code == 200
        data = get_response.json()
        assert "system_prompt" in data
        assert data["system_prompt"] == system_prompt