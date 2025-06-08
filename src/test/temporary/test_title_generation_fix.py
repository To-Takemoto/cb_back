"""
Title Generation Service Fix Tests

タイトル生成サービスの404エラー修正をテスト
"""

import pytest
import sys
import os
from unittest.mock import AsyncMock, Mock

# Add path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from src.domain.entity.message_entity import MessageEntity, Role
from src.usecase.chat_interaction.title_generation import TitleGenerationService
from src.port.llm_client import LLMClient


class TestTitleGenerationFix:
    """タイトル生成の修正テスト"""
    
    @pytest.fixture
    def mock_llm_client(self):
        """モックLLMClientフィクスチャ"""
        mock = AsyncMock(spec=LLMClient)
        mock.model = "default-model"
        mock.set_model = Mock()
        return mock
    
    @pytest.fixture
    def service(self, mock_llm_client):
        """TitleGenerationServiceインスタンス"""
        return TitleGenerationService(mock_llm_client)
    
    @pytest.fixture
    def sample_messages(self):
        """サンプルメッセージ"""
        return [
            MessageEntity(id=1, uuid="msg-1", role=Role.USER, content="How do I use Python?"),
            MessageEntity(id=2, uuid="msg-2", role=Role.ASSISTANT, content="Python is a programming language...")
        ]
    
    @pytest.fixture
    def japanese_messages(self):
        """日本語メッセージ"""
        return [
            MessageEntity(id=1, uuid="msg-1", role=Role.USER, content="Pythonの使い方を教えてください"),
            MessageEntity(id=2, uuid="msg-2", role=Role.ASSISTANT, content="Pythonはプログラミング言語です...")
        ]

    # === モデル選択テスト ===
    
    def test_get_title_generation_model(self, service):
        """タイトル生成用モデルの取得"""
        model = service._get_title_generation_model()
        assert model == "google/gemini-2.0-flash-001"
    
    @pytest.mark.asyncio
    async def test_model_switching_success(self, service, mock_llm_client, sample_messages):
        """モデル切り替えの正常動作"""
        # Given
        mock_llm_client.complete_message.return_value = {"content": "Python Programming Guide"}
        
        # When
        await service.generate_title(sample_messages)
        
        # Then
        # 最初の呼び出しがタイトル生成モデルへの切り替え
        first_call = mock_llm_client.set_model.call_args_list[0]
        assert first_call[0][0] == "google/gemini-2.0-flash-001"

    # === Role enum修正テスト ===
    
    def test_format_conversation_preview_role_handling(self, service, sample_messages):
        """Role enumの正しい処理"""
        preview = service._format_conversation_preview(sample_messages)
        
        assert "User: How do I use Python?" in preview
        assert "Assistant: Python is a programming language..." in preview
    
    def test_fallback_title_role_handling(self, service, sample_messages):
        """フォールバック処理でのRole enumの正しい処理"""
        title = service._fallback_title(sample_messages)
        assert title == "How do I use Python?"

    # === エラーハンドリングテスト ===
    
    @pytest.mark.asyncio
    async def test_llm_404_error_fallback(self, service, mock_llm_client, sample_messages):
        """LLM 404エラー時のフォールバック"""
        # Given
        from src.domain.exception.chat_exceptions import LLMServiceError
        mock_llm_client.complete_message.side_effect = LLMServiceError("LLM API error: 404")
        
        # When
        title = await service.generate_title(sample_messages)
        
        # Then
        assert title == "How do I use Python?"  # フォールバックタイトル
    
    @pytest.mark.asyncio
    async def test_network_error_fallback(self, service, mock_llm_client, sample_messages):
        """ネットワークエラー時のフォールバック"""
        # Given
        mock_llm_client.complete_message.side_effect = Exception("Network connection failed")
        
        # When
        title = await service.generate_title(sample_messages)
        
        # Then
        assert title == "How do I use Python?"  # フォールバックタイトル
    
    @pytest.mark.asyncio
    async def test_model_restoration_after_error(self, service, mock_llm_client, sample_messages):
        """エラー後のモデル復元"""
        # Given
        original_model = "original-model"
        mock_llm_client.model = original_model
        mock_llm_client.complete_message.side_effect = Exception("API Error")
        
        # When
        await service.generate_title(sample_messages)
        
        # Then
        # モデルが元に戻されることを確認
        restore_calls = [call for call in mock_llm_client.set_model.call_args_list 
                        if call[0][0] == original_model]
        assert len(restore_calls) > 0

    # === 言語検出テスト ===
    
    def test_japanese_detection(self, service):
        """日本語検出の正確性"""
        japanese_text = "これは日本語のテストです"
        assert service._is_japanese_dominant(japanese_text) == True
        
        english_text = "This is an English test"
        assert service._is_japanese_dominant(english_text) == False
        
        mixed_text = "This is mixed 日本語 text"
        # 30%以下なのでFalse
        assert service._is_japanese_dominant(mixed_text) == False
    
    def test_create_japanese_prompt(self, service, japanese_messages):
        """日本語プロンプト生成"""
        prompt = service._create_title_prompt(japanese_messages)
        
        assert "簡潔で分かりやすいタイトルを生成" in prompt.content
        assert "User: Pythonの使い方を教えてください" in prompt.content
    
    def test_create_english_prompt(self, service, sample_messages):
        """英語プロンプト生成"""
        prompt = service._create_title_prompt(sample_messages)
        
        assert "Generate a concise and descriptive title" in prompt.content
        assert "User: How do I use Python?" in prompt.content

    # === タイトル処理テスト ===
    
    def test_extract_and_validate_title_success(self, service):
        """正常なタイトル抽出"""
        # 基本的なタイトル
        assert service._extract_and_validate_title("Python Programming") == "Python Programming"
        
        # プレフィックス除去
        assert service._extract_and_validate_title("タイトル: Python プログラミング") == "Python プログラミング"
        assert service._extract_and_validate_title("Title: Python Guide") == "Python Guide"
        
        # 引用符除去
        assert service._extract_and_validate_title('"Python Tutorial"') == "Python Tutorial"
        assert service._extract_and_validate_title("'Learning Python'") == "Learning Python"
    
    def test_extract_and_validate_title_edge_cases(self, service):
        """タイトル抽出のエッジケース"""
        # 空のタイトル
        assert service._extract_and_validate_title("") is None
        assert service._extract_and_validate_title("   ") is None
        
        # 短すぎるタイトル
        assert service._extract_and_validate_title("Hi") is None
        
        # 長すぎるタイトル
        long_title = "A" * 150
        result = service._extract_and_validate_title(long_title)
        assert len(result) <= 100
        assert result.endswith("...")
    
    @pytest.mark.asyncio
    async def test_successful_title_generation(self, service, mock_llm_client, sample_messages):
        """正常なタイトル生成"""
        # Given
        mock_llm_client.complete_message.return_value = {"content": "Python Programming Tutorial"}
        
        # When
        title = await service.generate_title(sample_messages)
        
        # Then
        assert title == "Python Programming Tutorial"
    
    @pytest.mark.asyncio
    async def test_empty_response_fallback(self, service, mock_llm_client, sample_messages):
        """空のレスポンス時のフォールバック"""
        # Given
        mock_llm_client.complete_message.return_value = {"content": ""}
        
        # When
        title = await service.generate_title(sample_messages)
        
        # Then
        assert title == "How do I use Python?"  # フォールバックタイトル
    
    @pytest.mark.asyncio
    async def test_no_user_messages_fallback(self, service):
        """ユーザーメッセージがない場合のフォールバック"""
        # Given
        assistant_only_messages = [
            MessageEntity(id=1, uuid="msg-1", role=Role.ASSISTANT, content="Hello there!")
        ]
        
        # When
        title = await service.generate_title(assistant_only_messages)
        
        # Then
        assert title is None  # ユーザーメッセージがないのでNone