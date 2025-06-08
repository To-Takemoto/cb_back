"""認証処理効率化のテスト"""
import pytest
from unittest.mock import AsyncMock, patch
from fastapi import HTTPException
from src.infra.rest_api.routers.auth import get_current_user_info
from src.infra.tortoise_client.user_repository import TortoiseUserRepository


class TestAuthEfficiency:
    """認証処理の効率化をテスト"""
    
    @pytest.mark.asyncio
    async def test_get_current_user_info_should_use_efficient_query(self):
        """get_current_user_info関数が効率的なクエリを使用するべき"""
        mock_user_repository = AsyncMock()
        
        # 効率的なget_user_by_uuidメソッドが呼ばれることを期待
        mock_user = {
            'id': 1,
            'uuid': 'test-uuid-123',
            'username': 'testuser'
        }
        mock_user_repository.get_user_by_uuid.return_value = mock_user
        
        # get_all_usersは呼ばれないべき
        mock_user_repository.get_all_users.return_value = []
        
        with patch('src.infra.rest_api.routers.auth.get_user_repository', return_value=mock_user_repository):
            result = await get_current_user_info('test-uuid-123', mock_user_repository)
            
            # 効率的なメソッドが呼ばれることを確認
            mock_user_repository.get_user_by_uuid.assert_called_once_with('test-uuid-123')
            
            # 非効率なメソッドは呼ばれないことを確認
            mock_user_repository.get_all_users.assert_not_called()
    
    def test_user_repository_should_have_get_user_by_uuid_method(self):
        """UserRepositoryがget_user_by_uuidメソッドを持つべき"""
        repo = TortoiseUserRepository()
        
        # get_user_by_uuidメソッドが存在することを確認
        assert hasattr(repo, 'get_user_by_uuid'), "UserRepository should have get_user_by_uuid method"
        
        # メソッドが非同期関数であることを確認
        import asyncio
        assert asyncio.iscoroutinefunction(repo.get_user_by_uuid), "get_user_by_uuid should be an async method"
    
    @pytest.mark.asyncio
    async def test_get_user_by_uuid_should_not_fetch_all_users(self):
        """get_user_by_uuidが全ユーザーを取得しないべき"""
        repo = TortoiseUserRepository()
        
        # モックを使用してデータベースクエリの効率性をテスト
        with patch('src.infra.tortoise_client.models.User.get') as mock_get:
            mock_user = AsyncMock()
            mock_user.id = 1
            mock_user.uuid = 'test-uuid'
            mock_user.username = 'testuser'
            mock_get.return_value = mock_user
            
            result = await repo.get_user_by_uuid('test-uuid')
            
            # User.getが呼ばれることを確認（効率的）
            mock_get.assert_called_once_with(uuid='test-uuid')
            
            # 結果が正しいことを確認
            assert result is not None