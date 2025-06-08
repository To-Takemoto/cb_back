"""例外処理のテスト"""
import pytest
from unittest.mock import AsyncMock, patch
from src.infra.tortoise_client.chat_repo import TortoiseChatRepository
from src.port.dto.message_dto import MessageDTO
from src.domain.entity.message_entity import Role


class TestExceptionHandling:
    """具体的な例外処理のテスト"""
    
    @pytest.mark.asyncio
    async def test_add_message_should_raise_specific_exception_when_discussion_not_found(self):
        """ディスカッション構造が見つからない場合、具体的な例外が発生するべき"""
        repo = TortoiseChatRepository(user_id=1)
        
        message_dto = MessageDTO(
            role=Role.USER,
            content="test message"
        )
        
        # DiscussionStructure.getが例外を発生させる場合をテスト
        with patch('src.infra.tortoise_client.chat_repo.DiscussionStructure.get') as mock_get:
            mock_get.side_effect = Exception("Database error")
            
            with pytest.raises(ValueError, match="Discussion structure not found"):
                await repo.add_message("non-existent-uuid", message_dto)
    
    @pytest.mark.asyncio
    async def test_get_discussion_should_handle_database_errors_properly(self):
        """データベースエラーを適切に処理するべき"""
        repo = TortoiseChatRepository(user_id=1)
        
        # DiscussionStructure.getが例外を発生させる場合をテスト
        with patch('src.infra.tortoise_client.chat_repo.DiscussionStructure.get') as mock_get:
            mock_get.side_effect = Exception("Connection error")
            
            with pytest.raises(ValueError, match="Discussion structure not found"):
                await repo.get_discussion("test-uuid")
    
    def test_chat_repo_should_not_use_bare_except(self):
        """chat_repo.pyでbare except文が使用されていないことを確認"""
        with open('/Users/take/pp/cb_back/src/infra/tortoise_client/chat_repo.py', 'r') as f:
            lines = f.readlines()
        
        bare_except_lines = []
        for i, line in enumerate(lines, 1):
            if 'except:' in line and 'except Exception' not in line:
                bare_except_lines.append(f"Line {i}: {line.strip()}")
        
        assert len(bare_except_lines) == 0, f"Bare except statements found: {bare_except_lines}"