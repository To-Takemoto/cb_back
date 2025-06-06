from anytree import RenderTree
from anytree.render import AsciiStyle
import asyncio

from src.infra.openrouter_client import OpenRouterLLMService
from src.usecase.chat_interaction.main import ChatInteraction
from src.infra.sqlite_client.chat_repo import ChatRepo


class TuiChat:
    def __init__(
            self,
            user_id: int,
            model_name: str = "google/gemini-2.0-flash-001"
            ) -> None:
        """
        TUIベースのチャットインターフェースを提供するクラス
        
        Args:
            user_id: ユーザーID
            model_name: 使用するLLMモデル名
        """
        self.user_id = user_id
        self.model_name = model_name
        self.openrouter_client = OpenRouterLLMService(None, self.model_name)
        self.sqlite_client = SqliteClient(user_id=self.user_id)
        self.interaction_manager = ChatInteraction(self.sqlite_client, self.openrouter_client)
        self.status = True

    async def start_chat(self, initial_message: str = None) -> None:
        """新しいチャットを開始する"""
        self.interaction_manager.start_new_chat(initial_message or "あなたは優秀なアシスタントです。userは日本語で回答を期待しています。")
        print(f"チャット開始 - UUID: {self.interaction_manager.structure.chat_tree.uuid}")
    
    async def restart_chat(self, chat_uuid: str) -> None:
        """既存のチャットを再開する"""
        self.interaction_manager.restart_chat(chat_uuid=chat_uuid)
        print(f"チャット再開 - UUID: {self.interaction_manager.structure.chat_tree.uuid}")

    async def send_message(self, message_content: str) -> str:
        """メッセージを送信し、応答を取得する"""
        response = await self.interaction_manager.continue_chat(message_content)
        return response.content

    async def tui_chat(self) -> None:
        """TUIベースのチャットループ"""
        while self.status:
            print("=====")
            input_ = input("メッセージを入力: ")
            print("-----")
            if input_.startswith("/"):
                if await self.handle_command(input_) == False:
                    break
                else:
                    continue
            else:
                try:
                    llm_message = await self.send_message(input_)
                    print(f"LLM: {llm_message}")
                except Exception as e:
                    print(f"エラーが発生しました: {e}")

    async def handle_command(self, command: str) -> bool:
        """コマンドを処理する"""
        commands = command.split()
        if commands[0] == "/exit":
            print("チャットを終了します。")
            return False
        
        elif commands[0] == "/start":
            initial_message = " ".join(commands[1:]) if len(commands) > 1 else None
            await self.start_chat(initial_message)
            return True
        
        elif commands[0] == "/restart":
            if len(commands) > 1:
                await self.restart_chat(commands[1])
            else:
                print("使用法: /restart <chat_uuid>")
            return True
        
        elif commands[0] == "/tree":
            try:
                tree = self.interaction_manager.structure.chat_tree.tree
                for pre, _, node in RenderTree(tree, style=AsciiStyle()):
                    print(f"{pre}[{node.uuid}]")
            except Exception as e:
                print(f"ツリー表示エラー: {e}")
            return True

        elif commands[0] == "/select":
            if len(commands) > 1:
                try:
                    self.interaction_manager.select_message(message_uuid=commands[1])
                    print(f"メッセージ {commands[1]} を選択しました")
                except Exception as e:
                    print(f"メッセージ選択エラー: {e}")
            else:
                print("使用法: /select <message_uuid>")
            return True
        
        elif commands[0] == "/pwd":
            try:
                current_node = self.interaction_manager.structure.current_node
                print(f"現在のノード: {current_node.uuid}")
            except Exception as e:
                print(f"現在のノード表示エラー: {e}")
            return True

        elif commands[0] == "/uuid":
            try:
                print(f"現在のチャットUUID: {self.interaction_manager.structure.chat_tree.uuid}")
            except Exception as e:
                print(f"UUID表示エラー: {e}")
            return True

        elif commands[0] == "/help":
            print("利用可能なコマンド:")
            print("/exit - チャットを終了")
            print("/start [初期メッセージ] - 新しいチャットを開始")
            print("/restart <chat_uuid> - 既存のチャットを再開")
            print("/tree - チャットツリーを表示")
            print("/select <message_uuid> - 特定のメッセージを選択")
            print("/pwd - 現在のノードを表示")
            print("/uuid - 現在のチャットUUIDを表示")
            print("/help - このヘルプを表示")
            return True

        else:
            print(f"不明なコマンド: {command}")
            print("'/help' でコマンド一覧を表示できます")
            return True


async def run_tui_chat(user_id: int = 1, start_new: bool = True, chat_uuid: str = None, 
                       model_name: str = "google/gemini-2.0-flash-001"):
    """
    TUIチャットを実行する関数
    
    Args:
        user_id: ユーザーID
        start_new: 新しいチャットを開始するかどうか
        chat_uuid: 既存のチャットUUID（start_newがFalseの場合）
        model_name: 使用するLLMモデル名
    """
    tui = TuiChat(user_id=user_id, model_name=model_name)
    
    if start_new:
        await tui.start_chat()
    else:
        if chat_uuid:
            await tui.restart_chat(chat_uuid)
        else:
            print("既存のチャットを再開するにはUUIDが必要です。新しいチャットを開始します。")
            await tui.start_chat()
    
    await tui.tui_chat()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='TUIベースのチャットシステム')
    parser.add_argument('--user_id', type=int, default=1, help='ユーザーID')
    parser.add_argument('--restart', action='store_true', help='既存のチャットを再開する')
    parser.add_argument('--uuid', type=str, help='再開するチャットのUUID')
    parser.add_argument('--model', type=str, default="google/gemini-2.0-flash-001", help='使用するLLMモデル')
    
    args = parser.parse_args()
    
    asyncio.run(run_tui_chat(
        user_id=args.user_id,
        start_new=not args.restart,
        chat_uuid=args.uuid,
        model_name=args.model
    ))