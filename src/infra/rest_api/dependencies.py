"""
FastAPI依存性注入の定義

このモジュールは、FastAPIエンドポイントで使用される依存性注入関数を提供します。
DIコンテナから適切なサービスインスタンスを取得し、FastAPIの依存性システムに
統合するためのアダプターレイヤーとして機能します。

主要機能:
- DIコンテナからのサービス取得
- 認証済みユーザー用のChatInteraction組み立て
- 各サービスの適切なライフサイクル管理
"""

from fastapi import Depends
from typing import Annotated

from ..di import get_llm_client, get_user_repository, create_chat_repo_for_user, get_container
from ...usecase.chat_interaction.main import ChatInteraction
from ...usecase.chat_interaction.message_cache import MessageCache
from ...usecase.user_management.register_user import RegisterUserUseCase
from ..auth import get_current_user
from ...port.llm_client import LLMClient
from ...port.user_repository import UserRepository
from ...port.chat_repo import ChatRepository

def get_message_cache_dependency() -> MessageCache:
    """
    メッセージキャッシュの依存性を取得
    
    DIコンテナからシングルトンのメッセージキャッシュインスタンスを取得します。
    
    Returns:
        MessageCache: メッセージキャッシュインスタンス
    """
    return get_container().message_cache

def get_llm_client_dependency() -> LLMClient:
    """
    LLMクライアントの依存性を取得
    
    Returns:
        LLMClient: LLMサービスクライアントインスタンス
    """
    return get_llm_client()

def get_user_repository_dependency() -> UserRepository:
    """
    ユーザーリポジトリの依存性を取得
    
    Returns:
        UserRepository: ユーザーデータアクセスインスタンス
    """
    return get_user_repository()

async def get_chat_interaction_for_user(
    current_user_id: Annotated[str, Depends(get_current_user)],
    llm_client: Annotated[LLMClient, Depends(get_llm_client_dependency)],
    cache: Annotated[MessageCache, Depends(get_message_cache_dependency)]
) -> ChatInteraction:
    """
    認証されたユーザー用のChatInteractionを組み立て
    
    ユーザー固有のチャットリポジトリを作成し、共有サービス（LLMクライアント、
    メッセージキャッシュ）と組み合わせてChatInteractionインスタンスを構築します。
    
    Args:
        current_user_id: 認証済みユーザーのID
        llm_client: LLMサービスクライアント
        cache: メッセージキャッシュ
    
    Returns:
        ChatInteraction: ユーザー専用のチャットインタラクションインスタンス
    """
    chat_repo = await create_chat_repo_for_user(current_user_id)
    return ChatInteraction(chat_repo, llm_client, cache)

def get_register_user_usecase(
    user_repo: Annotated[UserRepository, Depends(get_user_repository_dependency)]
) -> RegisterUserUseCase:
    """
    ユーザー登録ユースケースを取得
    
    Args:
        user_repo: ユーザーリポジトリインスタンス
    
    Returns:
        RegisterUserUseCase: ユーザー登録ユースケースインスタンス
    """
    return RegisterUserUseCase(user_repo)

# 下位互換性のための旧関数（非推奨）
def get_message_cache() -> MessageCache:
    """
    非推奨: get_message_cache_dependencyを使用してください
    
    この関数は後方互換性のために残されていますが、新しいコードでは
    get_message_cache_dependency()を使用してください。
    
    Returns:
        MessageCache: メッセージキャッシュインスタンス
    """
    return get_message_cache_dependency()