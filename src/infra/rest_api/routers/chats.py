from fastapi import APIRouter, Depends, HTTPException
from typing import Optional
import asyncio

from ..dependencies import get_chat_repo_client
from src.infra.di import create_chat_repo_for_user
from src.usecase.chat_interaction.main import ChatInteraction
from src.infra.logging_config import get_logger
from ..schemas import (
    ChatCreateRequest, ChatCreateResponse,
    MessageRequest, MessageResponse,
    SelectRequest, PathResponse,
    HistoryMessage, HistoryResponse,
    PaginationParams, PaginatedResponse,
    ChatMetadataResponse, UpdateChatRequest, EditMessageRequest,
    SearchPaginationParams, TreeStructureResponse, TreeNode
)
from src.infra.auth import get_current_user
from src.port.chat_repo import ChatRepository

router = APIRouter(
    prefix="/api/v1/chats",
    tags=["chats"]
)

logger = get_logger("api.chats")

@router.post("/", response_model=ChatCreateResponse)
async def create_chat(
    req: ChatCreateRequest,
    current_user_id: str = Depends(get_current_user)
):
    """
    新しいチャットを開始し、チャットUUIDを返す
    """
    from src.infra.di import get_llm_client
    from ..dependencies import get_message_cache
    
    # Create user-specific chat repo and interaction
    chat_repo = create_chat_repo_for_user(current_user_id)
    llm_client = get_llm_client()
    cache = get_message_cache()
    interaction = ChatInteraction(chat_repo, llm_client, cache)
    
    # 初期メッセージがNoneの場合は空文字列を渡す
    interaction.start_new_chat(req.initial_message or "")
    return ChatCreateResponse(chat_uuid=str(interaction.structure.get_uuid()))

@router.post("/{chat_uuid}/messages", response_model=MessageResponse)
async def send_message(
    chat_uuid: str,
    req: MessageRequest,
    current_user_id: str = Depends(get_current_user)
):
    """
    既存チャットにメッセージを送信し、アシスタントの応答を返す
    """
    from src.infra.di import get_llm_client
    from ..dependencies import get_message_cache
    
    # Create user-specific chat repo and interaction
    chat_repo = create_chat_repo_for_user(current_user_id)
    llm_client = get_llm_client()
    cache = get_message_cache()
    interaction = ChatInteraction(chat_repo, llm_client, cache)
    
    try:
        interaction.restart_chat(chat_uuid)
    except Exception:
        raise HTTPException(status_code=404, detail="Chat not found")

    msg = await interaction.continue_chat(req.content)
    
    # 最後の位置を更新（アシスタントの応答ノードID）
    chat_repo.update_last_position(chat_uuid, current_user_id, str(msg.uuid))
    
    return MessageResponse(
        message_uuid=str(msg.uuid),
        content=msg.content
    )

@router.get("/{chat_uuid}/messages", response_model=HistoryResponse)
async def get_history(
    chat_uuid: str,
    current_user_id: str = Depends(get_current_user)
):
    """
    指定チャットの全メッセージ履歴を返却
    """
    from src.infra.di import get_llm_client
    from ..dependencies import get_message_cache
    
    # Create user-specific chat repo and interaction
    chat_repo = create_chat_repo_for_user(current_user_id)
    llm_client = get_llm_client()
    cache = get_message_cache()
    interaction = ChatInteraction(chat_repo, llm_client, cache)
    
    try:
        interaction.restart_chat(chat_uuid)
    except Exception:
        raise HTTPException(status_code=404, detail="Chat not found")

    path = interaction.structure.get_current_path()
    messages_entities = []
    # キャッシュから取得し、存在しないものはDBフェッチ
    for uuid in path:
        msg = interaction.cache.get(uuid)
        if msg is None:
            try:
                fetched = interaction.chat_repo.get_history([uuid])[0]
            except Exception:
                raise HTTPException(status_code=404, detail=f"Message {uuid} not found")
            interaction.cache.set(fetched)
            msg = fetched
        messages_entities.append(msg)

    return HistoryResponse(
        messages=[
            HistoryMessage(
                message_uuid=str(m.uuid),
                role=m.role.value,
                content=m.content
            ) for m in messages_entities
        ]
    )

@router.post("/{chat_uuid}/select")
async def select_node(
    chat_uuid: str,
    req: SelectRequest,
    current_user_id: str = Depends(get_current_user)
):
    """
    特定のメッセージを選択し、以降の会話の親に設定する
    """
    from src.infra.di import get_llm_client
    from ..dependencies import get_message_cache
    
    # Create user-specific chat repo and interaction
    chat_repo = create_chat_repo_for_user(current_user_id)
    llm_client = get_llm_client()
    cache = get_message_cache()
    interaction = ChatInteraction(chat_repo, llm_client, cache)
    
    try:
        interaction.restart_chat(chat_uuid)
        interaction.select_message(req.message_uuid)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        raise HTTPException(status_code=404, detail="Chat not found")
    return {"detail": f"Selected {req.message_uuid}"}

@router.get("/{chat_uuid}/path", response_model=PathResponse)
async def get_path(
    chat_uuid: str,
    current_user_id: str = Depends(get_current_user)
):
    """
    現在のノードまでのメッセージUUIDパスを取得する
    """
    from src.infra.di import get_llm_client
    from ..dependencies import get_message_cache
    
    # Create user-specific chat repo and interaction
    chat_repo = create_chat_repo_for_user(current_user_id)
    llm_client = get_llm_client()
    cache = get_message_cache()
    interaction = ChatInteraction(chat_repo, llm_client, cache)
    
    try:
        interaction.restart_chat(chat_uuid)
    except Exception:
        raise HTTPException(status_code=404, detail="Chat not found")
    return PathResponse(path=[str(u) for u in interaction.structure.get_current_path()])

@router.get("/{chat_uuid}/last-position")
async def get_last_position(
    chat_uuid: str,
    current_user_id: str = Depends(get_current_user)
):
    """
    ユーザーの最後の位置（ノードID）を取得する
    """
    chat_repo = create_chat_repo_for_user(current_user_id)
    last_position = chat_repo.get_last_position(chat_uuid, current_user_id)
    return {
        "chat_uuid": chat_uuid,
        "node_id": last_position
    }

@router.post("/{chat_uuid}/messages/{message_id}/retry", response_model=MessageResponse)
async def retry_message(
    chat_uuid: str,
    message_id: str,
    current_user_id: str = Depends(get_current_user)
):
    """
    失敗したメッセージを再試行する
    """
    from src.infra.di import get_llm_client
    from ..dependencies import get_message_cache
    
    # Create user-specific chat repo and interaction
    chat_repo = create_chat_repo_for_user(current_user_id)
    llm_client = get_llm_client()
    cache = get_message_cache()
    interaction = ChatInteraction(chat_repo, llm_client, cache)
    
    try:
        interaction.restart_chat(chat_uuid)
        
        # メッセージIDからノードを選択してリトライ
        interaction.select_message(message_id)
        msg = await interaction.retry_last_message()
        
        # 最後の位置を更新
        chat_repo.update_last_position(chat_uuid, current_user_id, str(msg.uuid))
        
        return MessageResponse(
            message_uuid=str(msg.uuid),
            content=msg.content
        )
    except asyncio.TimeoutError:
        raise  # エラーハンドラーで処理
    except Exception as e:
        logger.error(f"Retry failed for message {message_id}", exc_info=True)
        raise HTTPException(status_code=500, detail="Retry failed")

@router.get("/recent", response_model=PaginatedResponse)
async def get_recent_chats(
    pagination: PaginationParams = Depends(),
    current_user_id: str = Depends(get_current_user)
):
    """
    最近のチャット一覧を取得する（ページネーション対応）
    """
    chat_repo = create_chat_repo_for_user(current_user_id)
    offset = (pagination.page - 1) * pagination.limit
    
    # 全チャット数を取得
    total_chats = chat_repo.get_user_chat_count(current_user_id)
    
    # ページネーションされたチャットを取得
    chats = chat_repo.get_recent_chats_paginated(current_user_id, pagination.limit, offset)
    
    # 総ページ数を計算
    total_pages = (total_chats + pagination.limit - 1) // pagination.limit
    
    return PaginatedResponse(
        items=chats,
        total=total_chats,
        page=pagination.page,
        limit=pagination.limit,
        pages=total_pages
    )

@router.delete("/{chat_uuid}")
async def delete_chat(
    chat_uuid: str,
    current_user_id: str = Depends(get_current_user)
):
    """
    チャットを削除する
    """
    chat_repo = create_chat_repo_for_user(current_user_id)
    success = chat_repo.delete_chat(chat_uuid, current_user_id)
    if not success:
        raise HTTPException(status_code=404, detail="Chat not found or access denied")
    
    logger.info(f"Chat {chat_uuid} deleted by user {current_user_id}")
    return {"detail": f"Chat {chat_uuid} deleted successfully"}

@router.get("/{chat_uuid}/current-node")
async def get_current_node(
    chat_uuid: str,
    current_user_id: str = Depends(get_current_user)
):
    """
    現在のノードIDを取得する
    """
    from src.infra.di import get_llm_client
    from ..dependencies import get_message_cache
    
    # Create user-specific chat repo and interaction
    chat_repo = create_chat_repo_for_user(current_user_id)
    llm_client = get_llm_client()
    cache = get_message_cache()
    interaction = ChatInteraction(chat_repo, llm_client, cache)
    
    try:
        interaction.restart_chat(chat_uuid)
        current_node_id = interaction.structure.get_current_node_id()
        return {
            "chat_uuid": chat_uuid,
            "node_id": current_node_id
        }
    except Exception:
        raise HTTPException(status_code=404, detail="Chat not found")

@router.get("/{chat_uuid}/search")
async def search_messages(
    chat_uuid: str,
    q: str,
    current_user_id: str = Depends(get_current_user)
):
    """
    チャット内のメッセージを検索する
    """
    if not q or len(q.strip()) < 2:
        raise HTTPException(status_code=400, detail="Query must be at least 2 characters")
    
    chat_repo = create_chat_repo_for_user(current_user_id)
    results = chat_repo.search_messages(chat_uuid, q.strip())
    return {"results": results, "query": q}

@router.get("/{chat_uuid}", response_model=ChatMetadataResponse)
async def get_chat_metadata(
    chat_uuid: str,
    current_user_id: str = Depends(get_current_user)
):
    """
    チャットのメタデータを取得する
    """
    try:
        chat_repo = create_chat_repo_for_user(current_user_id)
        metadata = chat_repo.get_chat_metadata(chat_uuid, current_user_id)
        if not metadata:
            raise HTTPException(status_code=404, detail="Chat not found")
        return ChatMetadataResponse(**metadata)
    except Exception as e:
        logger.error(f"Failed to get chat metadata for {chat_uuid}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to get chat metadata")

@router.patch("/{chat_uuid}")
async def update_chat(
    chat_uuid: str,
    req: UpdateChatRequest,
    current_user_id: str = Depends(get_current_user)
):
    """
    チャットのタイトルやシステムプロンプトを更新する
    """
    try:
        chat_repo = create_chat_repo_for_user(current_user_id)
        success = chat_repo.update_chat(chat_uuid, current_user_id, req.title, req.system_prompt)
        if not success:
            raise HTTPException(status_code=404, detail="Chat not found or access denied")
        
        logger.info(f"Chat {chat_uuid} updated by user {current_user_id}")
        return {"detail": f"Chat {chat_uuid} updated successfully"}
    except Exception as e:
        logger.error(f"Failed to update chat {chat_uuid}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to update chat")

@router.patch("/{chat_uuid}/messages/{message_id}")
async def edit_message(
    chat_uuid: str,
    message_id: str,
    req: EditMessageRequest,
    current_user_id: str = Depends(get_current_user)
):
    """
    既存メッセージの内容を修正する
    """
    try:
        chat_repo = create_chat_repo_for_user(current_user_id)
        success = chat_repo.edit_message(chat_uuid, message_id, current_user_id, req.content)
        if not success:
            raise HTTPException(status_code=404, detail="Message not found or access denied")
        
        logger.info(f"Message {message_id} in chat {chat_uuid} edited by user {current_user_id}")
        return {"detail": f"Message {message_id} updated successfully"}
    except Exception as e:
        logger.error(f"Failed to edit message {message_id} in chat {chat_uuid}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to edit message")

@router.delete("/{chat_uuid}/messages/{message_id}")
async def delete_message(
    chat_uuid: str,
    message_id: str,
    current_user_id: str = Depends(get_current_user)
):
    """
    指定されたメッセージをチャット履歴から削除する
    """
    try:
        chat_repo = create_chat_repo_for_user(current_user_id)
        success = chat_repo.delete_message(chat_uuid, message_id, current_user_id)
        if not success:
            raise HTTPException(status_code=404, detail="Message not found or access denied")
        
        logger.info(f"Message {message_id} in chat {chat_uuid} deleted by user {current_user_id}")
        return {"detail": f"Message {message_id} deleted successfully"}
    except Exception as e:
        logger.error(f"Failed to delete message {message_id} in chat {chat_uuid}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to delete message")

@router.get("/{chat_uuid}/tree", response_model=TreeStructureResponse)
async def get_tree_structure(
    chat_uuid: str,
    current_user_id: str = Depends(get_current_user)
):
    """
    チャットのツリー構造を取得する（フロントエンドレンダリング用）
    """
    from src.infra.di import get_llm_client
    from ..dependencies import get_message_cache
    
    try:
        # Create user-specific chat repo and interaction
        chat_repo = create_chat_repo_for_user(current_user_id)
        llm_client = get_llm_client()
        cache = get_message_cache()
        interaction = ChatInteraction(chat_repo, llm_client, cache)
        
        # チャットの存在確認とロード
        interaction.restart_chat(chat_uuid)
        
        # ツリー構造を取得
        tree_data = chat_repo.get_tree_structure(chat_uuid)
        
        # 現在のノードIDを取得
        current_node_uuid = str(interaction.structure.current_node.uuid)
        
        return TreeStructureResponse(
            chat_uuid=chat_uuid,
            tree=TreeNode(**tree_data),
            current_node_uuid=current_node_uuid
        )
    except Exception as e:
        logger.error(f"Failed to get tree structure for chat {chat_uuid}", exc_info=True)
        raise HTTPException(status_code=404, detail="Chat not found or failed to get tree structure")

@router.get("/")
async def get_chats_with_search_and_pagination(
    pagination: SearchPaginationParams = Depends(),
    current_user_id: str = Depends(get_current_user)
):
    """
    チャットの一覧をページネーション・ソート・キーワード検索付きで取得する
    """
    try:
        chat_repo = create_chat_repo_for_user(current_user_id)
        offset = (pagination.page - 1) * pagination.limit
        
        # 検索・ソート・ページネーション実行
        result = chat_repo.search_and_paginate_chats(
            current_user_id, 
            pagination.q, 
            pagination.sort, 
            pagination.limit, 
            offset
        )
        
        total_chats = result["total"]
        total_pages = (total_chats + pagination.limit - 1) // pagination.limit
        
        return PaginatedResponse(
            items=result["items"],
            total=total_chats,
            page=pagination.page,
            limit=pagination.limit,
            pages=total_pages
        )
    except Exception as e:
        logger.error(f"Failed to search and paginate chats", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to search chats")