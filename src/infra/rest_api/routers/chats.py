from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from typing import Optional
import asyncio
import json

from ..dependencies import get_message_cache_dependency, get_llm_client_dependency
from ....usecase.model_management.model_service import ModelManagementService
from src.infra.di import create_chat_repo_for_user
from src.usecase.chat_interaction.main import ChatInteraction
from src.infra.logging_config import get_logger
from ..schemas import (
    ChatCreateRequest, ChatCreateResponse,
    MessageRequest, MessageResponse,
    HistoryMessage, HistoryResponse,
    PaginationParams, PaginatedResponse,
    ChatMetadataResponse, UpdateChatRequest, EditMessageRequest,
    SearchPaginationParams, TreeStructureResponse, TreeNode, CompleteChatDataResponse
)
from src.infra.auth import get_current_user
from src.port.chat_repo import ChatRepository

router = APIRouter(
    prefix="/api/v1/chats",
    tags=["chats"]
)

logger = get_logger("api.chats")

def get_model_service(llm_client = Depends(get_llm_client_dependency)) -> ModelManagementService:
    """モデル管理サービスの依存性注入"""
    return ModelManagementService(llm_client)

@router.post("/", response_model=ChatCreateResponse)
async def create_chat(
    req: ChatCreateRequest,
    current_user_id: str = Depends(get_current_user),
    llm_client = Depends(get_llm_client_dependency),
    cache = Depends(get_message_cache_dependency),
    model_service: ModelManagementService = Depends(get_model_service)
):
    """
    新しいチャットを開始し、チャットUUIDを返す
    """
    # モデルが指定されている場合はバリデーションして設定
    if req.model_id:
        try:
            available_models = await model_service.get_available_models()
            if not model_service.validate_model_id(req.model_id, available_models):
                raise HTTPException(
                    status_code=400, 
                    detail=f"Model '{req.model_id}' is not available"
                )
            model_service.set_model(req.model_id)
            logger.info(f"Model set to {req.model_id} for new chat by user {current_user_id}")
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to set model {req.model_id} for user {current_user_id}", exc_info=True)
            raise HTTPException(status_code=500, detail="Failed to set model")
    
    # Create user-specific chat repo and interaction
    chat_repo = create_chat_repo_for_user(current_user_id)
    interaction = ChatInteraction(chat_repo, llm_client, cache)
    
    # 初期メッセージがNoneの場合は空文字列を渡す
    interaction.start_new_chat(req.initial_message or "", req.system_prompt)
    return ChatCreateResponse(chat_uuid=str(interaction.structure.get_uuid()))

@router.post("/{chat_uuid}/messages", response_model=MessageResponse)
async def send_message(
    chat_uuid: str,
    req: MessageRequest,
    current_user_id: str = Depends(get_current_user),
    llm_client = Depends(get_llm_client_dependency),
    cache = Depends(get_message_cache_dependency),
    model_service: ModelManagementService = Depends(get_model_service)
):
    """
    既存チャットにメッセージを送信し、アシスタントの応答を返す
    parent_message_uuidが指定されている場合、その親から分岐させる
    """
    # モデルが指定されている場合はバリデーションして設定
    if req.model_id:
        try:
            available_models = await model_service.get_available_models()
            if not model_service.validate_model_id(req.model_id, available_models):
                raise HTTPException(
                    status_code=400, 
                    detail=f"Model '{req.model_id}' is not available"
                )
            model_service.set_model(req.model_id)
            logger.info(f"Model set to {req.model_id} for message in chat {chat_uuid} by user {current_user_id}")
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to set model {req.model_id} for user {current_user_id}", exc_info=True)
            raise HTTPException(status_code=500, detail="Failed to set model")
    
    # Create user-specific chat repo and interaction
    chat_repo = create_chat_repo_for_user(current_user_id)
    interaction = ChatInteraction(chat_repo, llm_client, cache)
    
    try:
        interaction.restart_chat(chat_uuid)
    except Exception:
        raise HTTPException(status_code=404, detail="Chat not found")

    # 新機能: 親メッセージが指定されていれば選択
    if req.parent_message_uuid:
        try:
            interaction.select_message(req.parent_message_uuid)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid parent message UUID")

    msg = await interaction.continue_chat(req.content)
    
    # レスポンスに親ノード情報を含める
    response_data = {
        "message_uuid": str(msg.uuid),
        "content": msg.content
    }
    
    # 親ノードとパス情報を追加
    try:
        if hasattr(interaction.structure.current_node, 'parent') and interaction.structure.current_node.parent:
            response_data["parent_message_uuid"] = str(interaction.structure.current_node.parent.uuid)
        response_data["current_path"] = [str(u) for u in interaction.structure.get_current_path()]
    except Exception:
        # エラー時は基本情報のみ返す
        pass
    
    return MessageResponse(**response_data)

@router.get("/{chat_uuid}/messages", response_model=HistoryResponse)
async def get_history(
    chat_uuid: str,
    current_user_id: str = Depends(get_current_user),
    llm_client = Depends(get_llm_client_dependency),
    cache = Depends(get_message_cache_dependency)
):
    """
    指定チャットの全メッセージ履歴を返却
    """
    # Create user-specific chat repo and interaction
    chat_repo = create_chat_repo_for_user(current_user_id)
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




@router.post("/{chat_uuid}/messages/{message_id}/retry", response_model=MessageResponse)
async def retry_message(
    chat_uuid: str,
    message_id: str,
    current_user_id: str = Depends(get_current_user),
    llm_client = Depends(get_llm_client_dependency),
    cache = Depends(get_message_cache_dependency)
):
    """
    失敗したメッセージを再試行する
    """
    # Create user-specific chat repo and interaction
    chat_repo = create_chat_repo_for_user(current_user_id)
    interaction = ChatInteraction(chat_repo, llm_client, cache)
    
    try:
        interaction.restart_chat(chat_uuid)
        
        # メッセージIDからノードを選択してリトライ
        interaction.select_message(message_id)
        msg = await interaction.retry_last_message()
        
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

@router.get("/{chat_uuid}/complete", response_model=CompleteChatDataResponse)
async def get_complete_chat_data(
    chat_uuid: str,
    current_user_id: str = Depends(get_current_user)
):
    """
    チャットの全データを一括取得する（フロントエンド状態管理用）
    メッセージ履歴、ツリー構造、メタデータを一度に返す
    """
    try:
        # Create user-specific chat repo
        chat_repo = create_chat_repo_for_user(current_user_id)
        
        # メタデータを取得してチャットの存在確認
        metadata = chat_repo.get_chat_metadata(chat_uuid, current_user_id)
        if not metadata:
            raise HTTPException(status_code=404, detail="Chat not found")
        
        # ツリー構造全体を取得
        tree_data = chat_repo.get_tree_structure(chat_uuid)
        
        # ツリーから全メッセージUUIDを抽出
        all_uuids = []
        def extract_uuids(node_data):
            all_uuids.append(node_data['uuid'])
            for child in node_data.get('children', []):
                extract_uuids(child)
        extract_uuids(tree_data)
        
        # 全メッセージを取得
        messages_entities = chat_repo.get_history(all_uuids)
        
        # レスポンス構築
        messages = [
            HistoryMessage(
                message_uuid=str(m.uuid),
                role=m.role.value,
                content=m.content
            ) for m in messages_entities
        ]
        
        return CompleteChatDataResponse(
            chat_uuid=chat_uuid,
            title=metadata.get('title', ''),
            system_prompt=metadata.get('system_prompt'),
            messages=messages,
            tree_structure=TreeNode(**tree_data),
            metadata=metadata
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get complete chat data for {chat_uuid}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to get chat data")

@router.get("/{chat_uuid}/tree", response_model=TreeStructureResponse)
async def get_tree_structure(
    chat_uuid: str,
    current_user_id: str = Depends(get_current_user),
    llm_client = Depends(get_llm_client_dependency),
    cache = Depends(get_message_cache_dependency)
):
    """
    チャットのツリー構造のみを取得する（レガシーサポート）
    """
    try:
        # Create user-specific chat repo and interaction
        chat_repo = create_chat_repo_for_user(current_user_id)
        interaction = ChatInteraction(chat_repo, llm_client, cache)
        
        # チャットの存在確認とロード
        interaction.restart_chat(chat_uuid)
        
        # ツリー構造を取得
        tree_data = chat_repo.get_tree_structure(chat_uuid)
        
        return TreeStructureResponse(
            chat_uuid=chat_uuid,
            tree=TreeNode(**tree_data)
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

@router.post("/{chat_uuid}/messages/stream")
async def send_message_stream(
    chat_uuid: str,
    req: MessageRequest,
    current_user_id: str = Depends(get_current_user),
    llm_client = Depends(get_llm_client_dependency),
    cache = Depends(get_message_cache_dependency)
):
    """
    ストリーミング形式でメッセージを送信し、リアルタイムでLLMの応答を取得する
    
    Server-Sent Events (SSE)を使用して、LLMの応答生成過程を
    クライアントにリアルタイムで配信します。
    
    Args:
        chat_uuid: チャットのUUID
        req: メッセージリクエスト（内容と親メッセージUUID）
        current_user_id: 現在のユーザーID
        llm_client: LLMクライアント
        cache: メッセージキャッシュ
        
    Returns:
        StreamingResponse: SSE形式のストリーミングレスポンス
        
    Events:
        - chunk: 部分的なメッセージ内容
        - final: 最終的な確定メッセージ
        - error: エラー情報
        - [DONE]: ストリーム終了
    """
    async def generate_sse():
        try:
            # Create user-specific chat repo and interaction
            chat_repo = create_chat_repo_for_user(current_user_id)
            interaction = ChatInteraction(chat_repo, llm_client, cache)
            
            # チャットの存在確認とロード
            try:
                interaction.restart_chat(chat_uuid)
            except Exception:
                error_data = {
                    "type": "error",
                    "message": "Chat not found"
                }
                yield f"data: {json.dumps(error_data)}\n\n"
                yield "data: [DONE]\n\n"
                return
            
            # 親メッセージが指定されている場合は分岐
            if req.parent_message_uuid:
                try:
                    interaction.select_message(req.parent_message_uuid)
                except Exception:
                    error_data = {
                        "type": "error", 
                        "message": "Parent message not found"
                    }
                    yield f"data: {json.dumps(error_data)}\n\n"
                    yield "data: [DONE]\n\n"
                    return
            
            # ストリーミングチャットを実行
            final_message = None
            async for message_chunk in interaction.continue_chat_stream(req.content):
                if message_chunk.is_streaming:
                    # ストリーミング中の部分データ
                    chunk_data = {
                        "type": "chunk",
                        "content": message_chunk.content,
                        "temp_id": message_chunk.temp_id
                    }
                    yield f"data: {json.dumps(chunk_data)}\n\n"
                else:
                    # 最終確定データ
                    chunk_data = {
                        "type": "final",
                        "content": message_chunk.content,
                        "message_uuid": str(message_chunk.uuid),
                        "role": message_chunk.role.value
                    }
                    final_message = message_chunk
                    yield f"data: {json.dumps(chunk_data)}\n\n"
            
            logger.info(f"Streaming chat completed for chat {chat_uuid}, user {current_user_id}")
            
        except ValueError as e:
            # 入力検証エラー
            error_data = {
                "type": "error", 
                "message": str(e)
            }
            yield f"data: {json.dumps(error_data)}\n\n"
        except Exception as e:
            # その他のエラー
            logger.error(f"Streaming chat failed for chat {chat_uuid}", exc_info=True)
            error_data = {
                "type": "error", 
                "message": "Internal server error occurred during streaming"
            }
            yield f"data: {json.dumps(error_data)}\n\n"
        
        # ストリーム終了マーカー
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        generate_sse(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # nginx bufferingを無効化
        }
    )