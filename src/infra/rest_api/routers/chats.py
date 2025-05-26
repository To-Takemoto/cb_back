from fastapi import APIRouter, Depends, HTTPException

from ..dependencies import get_chat_interaction, ChatInteraction
from ..schemas import (
    ChatCreateRequest, ChatCreateResponse,
    MessageRequest, MessageResponse,
    SelectRequest, PathResponse,
    HistoryMessage, HistoryResponse
)

router = APIRouter(
    prefix="/api/v1/chats",
    tags=["chats"]
)

@router.post("/", response_model=ChatCreateResponse)
async def create_chat(
    req: ChatCreateRequest,
    interaction: ChatInteraction = Depends(get_chat_interaction)
):
    """
    新しいチャットを開始し、チャットUUIDを返す
    """
    interaction.start_new_chat(req.initial_message)
    return ChatCreateResponse(chat_uuid=str(interaction.structure.get_uuid()))

@router.post("/{chat_uuid}/messages", response_model=MessageResponse)
async def send_message(
    chat_uuid: str,
    req: MessageRequest,
    interaction: ChatInteraction = Depends(get_chat_interaction)
):
    """
    既存チャットにメッセージを送信し、アシスタントの応答を返す
    """
    try:
        interaction.restart_chat(chat_uuid)
    except Exception:
        raise HTTPException(status_code=404, detail="Chat not found")

    msg = await interaction.continue_chat(req.content)
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
    指定チャットの全メッセージ履歴を返却（キャッシュ利用）
    """
    try:
        interaction.restart_chat(chat_uuid)
    except Exception:
        raise HTTPException(status_code=404, detail="Chat not found")

    # ツリーパスに沿ったメッセージUUIDリスト
    path = interaction.structure.get_current_path()

    # キャッシュから取得し、存在しないものはDBフェッチ
    messages = []
    missing = []
    for u in path:
        if interaction.cache.exists(u):
            messages.append(interaction.cache.get(u))
        else:
            missing.append(u)

    if missing:
        fetched = interaction.chat_repo.get_history(missing)
        for m in fetched:
            interaction.cache.set(m)
        messages = [interaction.cache.get(u) for u in path]

    return HistoryResponse(
        messages=[
            HistoryMessage(
                message_uuid=str(m.uuid),
                role=m.role.value,
                content=m.content
            ) for m in messages
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