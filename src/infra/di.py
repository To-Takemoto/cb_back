from ..usecase.chat_interaction.message_cache import MessageCache
from .sqlite_client.chat_repo import ChatRepo
from .openrouter_client import OpenRouterLLMService
from .sqlite_client.user_repository import SqliteUserRepository
from .sqlite_client.peewee_models import User


def get_chat_repo_client():
    # This is a legacy function that shouldn't be used for authenticated endpoints
    return ChatRepo(user_id=1)


def create_chat_repo_for_user(user_uuid: str) -> ChatRepo:
    """Create a ChatRepo instance for a specific user UUID"""
    user = User.get(User.uuid == user_uuid)
    return ChatRepo(user_id=user.id)


def get_llm_client():
    return OpenRouterLLMService(None, "google/gemini-2.0-flash-001")


def generate_message_cache():
    return MessageCache()


def get_user_repository():
    """
    UserRepositoryの取得
    """
    return SqliteUserRepository()