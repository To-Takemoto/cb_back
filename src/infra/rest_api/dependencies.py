from fastapi import Depends

from ..di import get_chat_repo_client, get_llm_client
from ...usecase.chat_interaction.main import ChatInteraction
from ...usecase.chat_interaction.message_cache import MessageCache

# グローバルキャッシュインスタンス
_global_cache = MessageCache()

def get_message_cache() -> MessageCache:
    """
    全チャット共通のメッセージキャッシュを返す
    """
    return _global_cache


def get_chat_interaction(
    llm_client = Depends(get_llm_client),
    chat_repo  = Depends(get_chat_repo_client),
    cache      = Depends(get_message_cache)
) -> ChatInteraction:
    """
    注入された依存関係から ChatInteraction を組み立て（永続キャッシュ利用）
    """
    return ChatInteraction(chat_repo, llm_client, cache)