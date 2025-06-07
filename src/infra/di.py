from functools import lru_cache
from typing import Optional
from ..usecase.chat_interaction.message_cache import MessageCache
from .tortoise_client.chat_repo import TortoiseChatRepository
from .openrouter_client import OpenRouterLLMService
from .tortoise_client.user_repository import TortoiseUserRepository
from .tortoise_client.models import User
from ..port.llm_client import LLMClient
from ..port.chat_repo import ChatRepository
from ..port.user_repository import UserRepository as UserRepositoryPort

class DIContainer:
    """依存性注入コンテナ"""
    
    def __init__(self):
        self._llm_client: Optional[LLMClient] = None
        self._message_cache: Optional[MessageCache] = None
        self._user_repository: Optional[UserRepositoryPort] = None
    
    @property
    def llm_client(self) -> LLMClient:
        """LLMクライアントのシングルトンインスタンスを取得"""
        if self._llm_client is None:
            self._llm_client = OpenRouterLLMService(None, "google/gemini-2.0-flash-001")
        return self._llm_client
    
    @property
    def message_cache(self) -> MessageCache:
        """メッセージキャッシュのシングルトンインスタンスを取得"""
        if self._message_cache is None:
            self._message_cache = MessageCache()
        return self._message_cache
    
    @property
    def user_repository(self) -> UserRepositoryPort:
        """ユーザーリポジトリのシングルトンインスタンスを取得"""
        if self._user_repository is None:
            self._user_repository = TortoiseUserRepository()
        return self._user_repository
    
    async def create_chat_repo_for_user(self, user_uuid: str) -> ChatRepository:
        """指定されたユーザー用のChatRepoインスタンスを作成"""
        from ..domain.exception.user_exceptions import UserNotFoundError
        
        try:
            user = await User.get(uuid=user_uuid)
            return TortoiseChatRepository(user_id=user.id)
        except Exception as e:
            raise UserNotFoundError(f"User not found: {user_uuid}") from e

# グローバルDIコンテナインスタンス
_container = DIContainer()

def get_chat_repo_client():
    """レガシー関数：認証が必要なエンドポイントでは使用しない"""
    return TortoiseChatRepository(user_id=1)

async def create_chat_repo_for_user(user_uuid: str) -> ChatRepository:
    """指定されたユーザー用のChatRepoインスタンスを作成"""
    return await _container.create_chat_repo_for_user(user_uuid)

def get_llm_client() -> LLMClient:
    """LLMクライアントを取得"""
    return _container.llm_client

def generate_message_cache() -> MessageCache:
    """レガシー関数：新しいコードではget_message_cacheを使用"""
    return MessageCache()

def get_message_cache() -> MessageCache:
    """メッセージキャッシュを取得"""
    return _container.message_cache

def get_user_repository() -> UserRepositoryPort:
    """ユーザーリポジトリを取得"""
    return _container.user_repository

def get_container() -> DIContainer:
    """DIコンテナを取得（テスト用）"""
    return _container