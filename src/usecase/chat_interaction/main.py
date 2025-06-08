"""
チャットインタラクション管理ユースケース

このモジュールは、ユーザーとLLMとの会話を管理する中核的なユースケースを提供します。
会話の開始、継続、履歴管理、ツリー構造の操作等を統合的に管理し、
ドメインロジックとインフラストラクチャを適切に分離します。

主要機能:
- 新規チャットの開始
- メッセージの送信とLLM応答の取得
- 会話履歴の管理
- 分岐会話（ツリー構造）の操作
- メッセージキャッシュによる性能最適化

アーキテクチャ:
- ドメイン層のエンティティを操作
- ポート層のインターフェースを介してインフラにアクセス
- 例外処理とエラーハンドリングを統合管理
"""

from typing import Optional, List, AsyncGenerator
import uuid
from ...domain.entity.message_entity import MessageEntity, Role
from ...domain.exception.chat_exceptions import ChatNotFoundError, LLMServiceError
from ...port.chat_repo import ChatRepository
from ...port.llm_client import LLMClient
from ...port.dto.message_dto import MessageDTO
from .structure_handler import StructureHandle
from .message_cache import MessageCache

class ChatInteraction:
    """
    チャットインタラクションを管理するユースケースクラス
    
    ユーザーとLLMとの会話を統合的に管理し、メッセージの送受信、
    履歴の保存、ツリー構造の操作、キャッシュ管理等を行います。
    
    このクラスは依存性逆転原則に従い、抽象インターフェースを
    介してインフラストラクチャにアクセスします。
    
    Attributes:
        chat_repo (ChatRepository): チャットデータの永続化インターフェース
        llm_client (LLMClient): LLMサービスとの通信インターフェース
        structure (StructureHandle): ツリー構造の管理ハンドラ
        cache (MessageCache): メッセージキャッシュ管理
    """
    
    def __init__(
        self,
        chat_repo: ChatRepository,
        llm_client: LLMClient,
        cache_handle: MessageCache
    ) -> None:
        """
        チャットインタラクションマネージャーを初期化
        
        Args:
            chat_repo (ChatRepository): チャットデータの永続化インターフェース
            llm_client (LLMClient): LLMサービスとの通信インターフェース
            cache_handle (MessageCache): メッセージキャッシュインスタンス
        """
        self.chat_repo = chat_repo
        self.llm_client = llm_client
        self.structure = StructureHandle(self.chat_repo)
        self.cache = cache_handle

    async def start_new_chat(self, initial_strings: Optional[str] = None, system_prompt: Optional[str] = None) -> None:
        """
        新しいチャットセッションを開始
        
        初期メッセージ（システムプロンプト）を設定し、
        新しいチャット構造を初期化します。
        
        Args:
            initial_strings (Optional[str]): 初期システムメッセージ
                                            Noneの場合は空のシステムメッセージ
            system_prompt (Optional[str]): システムプロンプト
                                         LLM呼び出し時に使用される
        
        Side Effects:
            - データベースに新しいチャットと初期メッセージを作成
            - 内部状態を新しいチャットに設定
            - メッセージキャッシュに初期メッセージを登録
        """
        # MessageEntityを作成してinit_structureに渡す
        initial_message = MessageEntity(
            id=0,
            uuid=str(uuid.uuid4()),
            role=Role.SYSTEM,
            content=initial_strings or ""
        )
        new_tree, initial_message_entity = await self.chat_repo.init_structure(initial_message)
        await self.structure.store_tree(new_tree)
        self.cache.set(initial_message_entity)

    async def continue_chat(self, user_message_strings: str) -> MessageEntity:
        """チャットを継続し、LLMからの応答を取得する"""
        if not user_message_strings.strip():
            raise ValueError("Message content cannot be empty")
            
        try:
            user_message_dto = MessageDTO(Role.USER, user_message_strings)
            await self._process_message(user_message_dto)
            chat_history = await self._get_chat_history()
            
            llm_response = await self.llm_client.complete_message(chat_history)
            if not llm_response.get("content"):
                raise LLMServiceError("Empty response from LLM service")
                
            llm_message_dto = MessageDTO(Role.ASSISTANT, llm_response["content"])
            llm_message = await self._process_message(llm_message_dto, llm_response)
            
            # Generate title automatically after first assistant response
            await self._try_generate_title(chat_history, llm_message)
            
            return llm_message
        except Exception as e:
            if isinstance(e, (LLMServiceError, ValueError)):
                raise
            raise LLMServiceError(f"Failed to continue chat: {str(e)}")

    async def continue_chat_stream(self, user_message_strings: str) -> AsyncGenerator[MessageEntity, None]:
        """
        チャットを継続し、LLMからのストリーミング応答を取得する
        
        ユーザーメッセージを即座に保存し、LLMからの応答を
        リアルタイムで部分的に配信します。最終的に完全なメッセージとして確定します。
        
        Args:
            user_message_strings (str): ユーザーからのメッセージ内容
            
        Yields:
            MessageEntity: ストリーミング中の部分メッセージと最終確定メッセージ
            
        Raises:
            ValueError: メッセージ内容が空の場合
            LLMServiceError: LLMサービスとの通信でエラーが発生した場合
            
        Usage:
            async for message_chunk in interaction.continue_chat_stream("質問内容"):
                if message_chunk.is_streaming:
                    # ストリーミング中の部分メッセージ
                    display_partial_message(message_chunk.content)
                else:
                    # 最終確定メッセージ
                    save_final_message(message_chunk)
        """
        if not user_message_strings.strip():
            raise ValueError("Message content cannot be empty")
            
        try:
            # ユーザーメッセージを即座に保存
            user_message_dto = MessageDTO(Role.USER, user_message_strings)
            await self._process_message(user_message_dto)
            
            # チャット履歴取得
            chat_history = await self._get_chat_history()
            
            # ストリーミングレスポンスの蓄積
            accumulated_content = ""
            temp_id = str(uuid.uuid4())
            
            # LLMからのストリーミングレスポンスを処理
            async for chunk in self.llm_client.complete_message_stream(chat_history):
                delta_content = chunk.get("choices", [{}])[0].get("delta", {}).get("content", "")
                if delta_content:
                    accumulated_content += delta_content
                    
                    # 部分的なメッセージエンティティを配信
                    streaming_message = MessageEntity(
                        id=0,  # 一時的な値
                        uuid="",  # 一時的な値
                        role=Role.ASSISTANT,
                        content=accumulated_content,
                        is_streaming=True,
                        temp_id=temp_id
                    )
                    yield streaming_message
            
            # 空のレスポンスチェック
            if not accumulated_content.strip():
                raise LLMServiceError("Empty response from LLM service")
            
            # 最終メッセージをデータベースに保存
            llm_message_dto = MessageDTO(Role.ASSISTANT, accumulated_content)
            # LLM詳細情報は現在のチャンクから構築（簡略化）
            llm_details = {"content": accumulated_content}
            final_message = await self._process_message(llm_message_dto, llm_details)
            
            # Generate title automatically after first assistant response
            await self._try_generate_title(chat_history, final_message)
            
            # 最終確定メッセージを配信
            yield final_message
            
        except Exception as e:
            if isinstance(e, (LLMServiceError, ValueError)):
                raise
            raise LLMServiceError(f"Failed to stream chat: {str(e)}")
    
    async def restart_chat(self, chat_uuid: str) -> None:
        """
        既存のチャットセッションを再開
        
        指定されたチャットUUIDのデータをロードし、
        現在のセッションをそのチャットに切り替えます。
        
        Args:
            chat_uuid (str): 再開するチャットのUUID
        
        Raises:
            ChatNotFoundError: 指定されたチャットが存在しない場合
            
        Side Effects:
            - 内部状態を指定されたチャットに切り替え
            - ツリー構造をロードし、最新メッセージに移動
        """
        chat_tree = await self.chat_repo.load_tree(chat_uuid)
        await self.structure.store_tree(chat_tree)

    def select_message(self, message_uuid: str) -> None:
        """
        特定のメッセージに現在位置を移動
        
        指定されたメッセージを現在の会話位置として設定します。
        これにより、過去の会話ポイントから分岐することが可能です。
        
        Args:
            message_uuid (str): 移動先メッセージのUUID
        
        Raises:
            MessageNotFoundError: 指定されたメッセージが存在しない場合
            InvalidTreeStructureError: ツリー構造が無効な場合
            
        Usage:
            # 過去のメッセージから分岐した会話を開始
            interaction.select_message("some-message-uuid")
            response = await interaction.continue_chat("新しい質問")
        """
        self.structure.select_node(message_uuid)

    async def retry_last_message(self) -> MessageEntity:
        """
        最後のアシスタントメッセージを再生成する
        
        現在の位置から最後のユーザーメッセージを取得し、
        新しいLLM応答を生成して返します。
        
        Returns:
            MessageEntity: 新しく生成されたアシスタントメッセージ
            
        Raises:
            ValueError: 最後のメッセージがユーザーメッセージでない場合
            LLMServiceError: LLMサービスとの通信でエラーが発生した場合
        """
        try:
            # 現在のチャット履歴を取得
            chat_history = await self._get_chat_history()
            
            # 最後のメッセージがアシスタントメッセージの場合、その前のユーザーメッセージまで戻る
            if chat_history and chat_history[-1].role == Role.ASSISTANT:
                # アシスタントメッセージを除いたヒストリーを取得
                chat_history = chat_history[:-1]
            
            if not chat_history or chat_history[-1].role != Role.USER:
                raise ValueError("No user message found to retry from")
            
            # LLMから新しい応答を取得
            llm_response = await self.llm_client.complete_message(chat_history)
            if not llm_response.get("content"):
                raise LLMServiceError("Empty response from LLM service")
                
            # 新しいアシスタントメッセージを生成・保存
            llm_message_dto = MessageDTO(Role.ASSISTANT, llm_response["content"])
            llm_message = await self._process_message(llm_message_dto, llm_response)
            
            return llm_message
            
        except Exception as e:
            if isinstance(e, (LLMServiceError, ValueError)):
                raise
            raise LLMServiceError(f"Failed to retry message: {str(e)}")
        
    async def _get_chat_history(self) -> List[MessageEntity]:
        """
        現在の会話パスのメッセージ履歴を取得
        
        現在のノードからルートまでのパスを取得し、
        対応するメッセージエンティティをロードします。
        
        Returns:
            List[MessageEntity]: ルートから現在ノードまでのメッセージ一覧
                               時間的順序でソートされている
        """
        chat_history_uuid_list = self.structure.get_current_path()
        chat_history = await self.chat_repo.get_history(chat_history_uuid_list)
        return chat_history
        
    async def _process_message(self, message_dto: MessageDTO, llm_details: Optional[dict] = None) -> MessageEntity:
        """
        メッセージを処理してデータベースに保存
        
        メッセージの保存、キャッシュ更新、ツリー構造の更新を
        一連の操作として実行します。
        
        Args:
            message_dto (MessageDTO): 保存するメッセージのデータ
            llm_details (Optional[dict]): LLMレスポンスの詳細情報
                                        （トークン数、モデル情報等）
        
        Returns:
            MessageEntity: 保存されたメッセージエンティティ
            
        Side Effects:
            - データベースにメッセージを保存
            - メッセージキャッシュを更新
            - ツリー構造にメッセージを追加
            - データベースのツリー構造を更新
        """
        message_entity = await self.chat_repo.save_message(
            discussion_structure_uuid = self.structure.get_uuid(),
            message_dto = message_dto,
            llm_details = llm_details
            )
        self.cache.set(message_entity)
        self.structure.append_message(message_entity)
        new_tree = self.structure.get_chat_tree()
        await self.chat_repo.update_tree(new_tree)
        return message_entity
    
    async def _try_generate_title(self, chat_history: List[MessageEntity], assistant_message: MessageEntity) -> None:
        """
        Try to generate a title for the chat if this is the first assistant response.
        
        Args:
            chat_history: Current chat history before the new assistant message
            assistant_message: The newly generated assistant message
        """
        try:
            # Check if this is the first assistant response (title generation trigger)
            # chat_history doesn't include the new assistant message yet
            assistant_messages = [msg for msg in chat_history if msg.role == Role.ASSISTANT]
            
            # Generate title only for the first assistant response (so assistant_messages should be empty)
            if len(assistant_messages) == 0:
                # Get all messages including the new one for title generation
                all_messages = chat_history + [assistant_message]
                
                # Generate title using the chat repository method
                chat_uuid = self.structure.get_uuid()
                await self.chat_repo.generate_chat_title(chat_uuid, all_messages, self.llm_client)
                
        except Exception as e:
            # Title generation is not critical - log but don't raise
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Title generation failed: {e}")