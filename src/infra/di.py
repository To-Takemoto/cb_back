from ..usecase.chat_interaction.message_cache import MessageCache
from .sqlite_client.chat_repo import ChatRepo
from .openrouter_client import OpenRouterLLMService


def get_chat_repo_client():
    return ChatRepo(user_id=1)

def get_llm_client():
    return OpenRouterLLMService(None, "google/gemini-2.0-flash-001")

def generate_message_cache():
    return MessageCache()