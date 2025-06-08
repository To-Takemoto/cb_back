"""HTTPクライアント競合状態のテスト"""
import asyncio
import pytest
from unittest.mock import patch, AsyncMock
from src.infra.openrouter_client import OpenRouterLLMService
from src.domain.entity.message_entity import MessageEntity, Role


class TestHTTPClientConcurrency:
    """HTTPクライアントの競合状態をテスト"""
    
    @pytest.mark.asyncio
    async def test_concurrent_client_creation_should_not_cause_race_condition(self):
        """同時実行時にクライアント作成で競合状態が発生しないべき"""
        service = OpenRouterLLMService(api_key="test-key", default_model="test-model")
        
        # 初期状態ではクライアントはNone
        assert service._client is None
        
        # httpx.AsyncClientをモック
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            mock_client.post.return_value.json.return_value = {
                "choices": [{"message": {"content": "test response"}}],
                "usage": {"total_tokens": 10}
            }
            mock_client.post.return_value.raise_for_status = AsyncMock()
            
            # 同時に複数のメソッドを実行
            messages = [MessageEntity(role=Role.USER, content="test")]
            
            tasks = [
                service.send_message(messages),
                service.send_message(messages),
                service.send_message(messages)
            ]
            
            # 同時実行
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # AsyncClientが一度だけ作成されることを確認
            assert mock_client_class.call_count == 1
            
            # すべてのタスクが成功することを確認
            for result in results:
                assert not isinstance(result, Exception)
    
    @pytest.mark.asyncio
    async def test_client_should_be_singleton_per_instance(self):
        """インスタンス内でクライアントがシングルトンであるべき"""
        service = OpenRouterLLMService(api_key="test-key", default_model="test-model")
        
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            mock_client.post.return_value.json.return_value = {
                "choices": [{"message": {"content": "test response"}}],
                "usage": {"total_tokens": 10}
            }
            mock_client.post.return_value.raise_for_status = AsyncMock()
            
            messages = [MessageEntity(role=Role.USER, content="test")]
            
            # 最初の呼び出し
            await service.send_message(messages)
            first_client = service._client
            
            # 2回目の呼び出し
            await service.send_message(messages)
            second_client = service._client
            
            # 同じクライアントインスタンスが使用されることを確認
            assert first_client is second_client
            assert mock_client_class.call_count == 1
    
    def test_client_initialization_should_be_thread_safe(self):
        """クライアント初期化がスレッドセーフであるべき"""
        # この関数は競合状態を避けるためのロック機構が必要であることを示すテスト
        service = OpenRouterLLMService(api_key="test-key", default_model="test-model")
        
        # _ensure_client メソッドが存在するかチェック
        # 修正後はこのメソッドが実装されているべき
        assert hasattr(service, '_ensure_client'), "Thread-safe client initialization method should exist"