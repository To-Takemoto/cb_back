from fastapi import Depends

from ..di import get_chat_repo_client, get_llm_client, generate_message_cache
from ...usecase.chat_interaction.main import ChatInteraction


def get_chat_interaction(
    llm_client  = Depends(get_llm_client),
    chat_repo   = Depends(get_chat_repo_client),
    cache       = Depends(generate_message_cache)
) -> ChatInteraction:
    """
    注入された依存関係から ChatInteraction を組み立て
    """
    return ChatInteraction(chat_repo, llm_client, cache)