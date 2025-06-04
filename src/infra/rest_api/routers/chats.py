from fastapi import APIRouter, Depends, HTTPException
from typing import Optional
import asyncio

from ..dependencies import get_chat_interaction, ChatInteraction, get_chat_repo_client
from src.infra.logging_config import get_logger
from ..schemas import (
    ChatCreateRequest, ChatCreateResponse,
    MessageRequest, MessageResponse,
    SelectRequest, PathResponse,
    HistoryMessage, HistoryResponse
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
    interaction: ChatInteraction = Depends(get_chat_interaction)
):
    """
    新しいチャットを開始し、チャットUUIDを返す
    """
    # 初期メッセージがNoneの場合は空文字列を渡す
    interaction.start_new_chat(req.initial_message or "")
    return ChatCreateResponse(chat_uuid=str(interaction.structure.get_uuid()))

@router.post("/{chat_uuid}/messages", response_model=MessageResponse)
async def send_message(
    chat_uuid: str,
    req: MessageRequest,
    interaction: ChatInteraction = Depends(get_chat_interaction),
    current_user_id: str = Depends(get_current_user),
    chat_repo: ChatRepository = Depends(get_chat_repo_client)
):
    """
    既存チャットにメッセージを送信し、アシスタントの応答を返す
    """
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
    interaction: ChatInteraction = Depends(get_chat_interaction)
):
    """
    指定チャットの全メッセージ履歴を返却
    """
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
    interaction: ChatInteraction = Depends(get_chat_interaction)
):
    """
    特定のメッセージを選択し、以降の会話の親に設定する
    """
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
    interaction: ChatInteraction = Depends(get_chat_interaction)
):
    """
    現在のノードまでのメッセージUUIDパスを取得する
    """
    try:
        interaction.restart_chat(chat_uuid)
    except Exception:
        raise HTTPException(status_code=404, detail="Chat not found")
    return PathResponse(path=[str(u) for u in interaction.structure.get_current_path()])

@router.get("/{chat_uuid}/last-position")
async def get_last_position(
    chat_uuid: str,
    current_user_id: str = Depends(get_current_user),
    chat_repo: ChatRepository = Depends(get_chat_repo_client)
):
    """
    ユーザーの最後の位置（ノードID）を取得する
    """
    last_position = chat_repo.get_last_position(chat_uuid, current_user_id)
    return {
        "chat_uuid": chat_uuid,
        "node_id": last_position
    }

@router.post("/{chat_uuid}/messages/{message_id}/retry", response_model=MessageResponse)
async def retry_message(
    chat_uuid: str,
    message_id: str,
    interaction: ChatInteraction = Depends(get_chat_interaction),
    current_user_id: str = Depends(get_current_user),
    chat_repo: ChatRepository = Depends(get_chat_repo_client)
):
    """
    失敗したメッセージを再試行する
    """
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

@router.get("/recent")
async def get_recent_chats(
    limit: int = 10,
    current_user_id: str = Depends(get_current_user),
    chat_repo: ChatRepository = Depends(get_chat_repo_client)
):
    """
    最近のチャット一覧を取得する
    """
    if limit > 100:
        limit = 100  # 最大100件まで
    
    chats = chat_repo.get_recent_chats(current_user_id, limit)
    return {"chats": chats}

@router.delete("/{chat_uuid}")
async def delete_chat(
    chat_uuid: str,
    current_user_id: str = Depends(get_current_user),
    chat_repo: ChatRepository = Depends(get_chat_repo_client)
):
    """
    チャットを削除する
    """
    success = chat_repo.delete_chat(chat_uuid, current_user_id)
    if not success:
        raise HTTPException(status_code=404, detail="Chat not found or access denied")
    
    logger.info(f"Chat {chat_uuid} deleted by user {current_user_id}")
    return {"detail": f"Chat {chat_uuid} deleted successfully"}

@router.get("/{chat_uuid}/current-node")
async def get_current_node(
    chat_uuid: str,
    interaction: ChatInteraction = Depends(get_chat_interaction)
):
    """
    現在のノードIDを取得する
    """
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
    chat_repo: ChatRepository = Depends(get_chat_repo_client)
):
    """
    チャット内のメッセージを検索する
    """
    if not q or len(q.strip()) < 2:
        raise HTTPException(status_code=400, detail="Query must be at least 2 characters")
    
    results = chat_repo.search_messages(chat_uuid, q.strip())
    return {"results": results, "query": q}

@router.get("/")
async def get_chats_with_filter(
    date: Optional[str] = None,
    current_user_id: str = Depends(get_current_user),
    chat_repo: ChatRepository = Depends(get_chat_repo_client)
):
    """
    日付フィルタでチャット一覧を取得する
    """
    if date:
        valid_filters = ["today", "yesterday", "week", "month"]
        if date not in valid_filters:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid date filter. Must be one of: {', '.join(valid_filters)}"
            )
        
        chats = chat_repo.get_chats_by_date(current_user_id, date)
        return {"chats": chats, "filter": date}
    else:
        # デフォルトは最近のチャット
        chats = chat_repo.get_recent_chats(current_user_id, 10)
        return {"chats": chats}