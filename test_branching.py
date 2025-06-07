#!/usr/bin/env python3
"""
会話分岐機能のテストスクリプト
select nodeとメッセージ送信の動作を確認
"""

import asyncio
import json
from typing import Dict, Any
from src.infra.tortoise_client.chat_repo import TortoiseChatRepository
from src.usecase.chat_interaction.main import ChatInteraction
from src.usecase.chat_interaction.message_cache import MessageCache
from src.port.dto.message_dto import MessageDTO
from src.domain.entity.message_entity import Role
from tortoise import Tortoise
from src.infra.tortoise_client.models import User

class BranchingTest:
    def __init__(self):
        # データベース初期化
        db = SqliteDatabase("data/sqlite.db")
        db_proxy.initialize(db)
        db.connect()
        
        # テストユーザーを作成または取得
        self.user_id = 1
        try:
            user = User.get_by_id(self.user_id)
        except:
            # テストユーザーが存在しない場合は作成
            user = User.create(
                id=1,
                uuid="test_user_123",
                username="testuser",
                email="test@example.com",
                password_hash="dummy_hash"
            )
        
        self.chat_repo = ChatRepo(self.user_id)
        
        # MockLLMを使用してテスト用のレスポンスを返す
        class MockLLM:
            def __init__(self):
                self.response_count = 0
            
            async def complete_message(self, messages):
                self.response_count += 1
                last_msg = messages[-1].content if messages else "no message"
                return {"content": f"Assistant response #{self.response_count} to: {last_msg}"}
        
        self.llm_client = MockLLM()
        self.cache = MessageCache()
        self.interaction = ChatInteraction(self.chat_repo, self.llm_client, self.cache)
        
    def print_tree_structure(self, node, level=0):
        """ツリー構造を視覚的に表示"""
        indent = "  " * level
        print(f"{indent}├─ {node.uuid}")
        for child in node.children:
            self.print_tree_structure(child, level + 1)
    
    async def test_conversation_branching(self):
        print("=== 会話分岐テスト開始 ===\n")
        
        # 1. 新しいチャットを開始
        print("1. 新しいチャットを開始...")
        self.interaction.start_new_chat("Hello, this is the initial message.")
        chat_uuid = self.interaction.structure.get_uuid()
        print(f"   チャットUUID: {chat_uuid}")
        
        # 2. 最初のメッセージを送信（分岐点となる）
        print("\n2. 最初のユーザーメッセージを送信...")
        msg1 = await self.interaction.continue_chat("What is the capital of Japan?")
        msg1_uuid = str(msg1.uuid)
        print(f"   アシスタント応答1: {msg1.content}")
        print(f"   メッセージUUID: {msg1_uuid}")
        
        # 3. 2番目のメッセージを送信
        print("\n3. 2番目のユーザーメッセージを送信...")
        msg2 = await self.interaction.continue_chat("Tell me about Tokyo.")
        msg2_uuid = str(msg2.uuid)
        print(f"   アシスタント応答2: {msg2.content}")
        print(f"   メッセージUUID: {msg2_uuid}")
        
        # 4. 現在のパスを確認
        print("\n4. 現在のパス:")
        current_path = self.interaction.structure.get_current_path()
        for i, uuid in enumerate(current_path):
            print(f"   {i}: {uuid}")
        
        # 5. 最初のアシスタント応答にselect（分岐点に戻る）
        print(f"\n5. メッセージ {msg1_uuid} を選択（分岐点に戻る）...")
        try:
            self.interaction.select_message(msg1_uuid)
            print("   ✓ 選択成功")
        except Exception as e:
            print(f"   ✗ 選択失敗: {e}")
            return False
        
        # 6. 選択後のパスを確認
        print("\n6. 選択後のパス:")
        new_path = self.interaction.structure.get_current_path()
        for i, uuid in enumerate(new_path):
            print(f"   {i}: {uuid}")
        
        # 7. 分岐した新しいメッセージを送信
        print("\n7. 分岐したメッセージを送信...")
        msg3 = await self.interaction.continue_chat("What about Osaka?")
        msg3_uuid = str(msg3.uuid)
        print(f"   アシスタント応答3（分岐）: {msg3.content}")
        print(f"   メッセージUUID: {msg3_uuid}")
        
        # 8. ツリー構造を表示
        print("\n8. 最終的なツリー構造:")
        self.print_tree_structure(self.interaction.structure.chat_tree.tree)
        
        # 9. select機能のさらなるテスト
        print(f"\n9. 再度メッセージ {msg2_uuid} を選択...")
        try:
            self.interaction.select_message(msg2_uuid)
            print("   ✓ 選択成功")
            final_path = self.interaction.structure.get_current_path()
            print("   選択後のパス:")
            for i, uuid in enumerate(final_path):
                print(f"     {i}: {uuid}")
        except Exception as e:
            print(f"   ✗ 選択失敗: {e}")
        
        # 10. ツリー構造APIテスト
        print("\n10. ツリー構造API経由でのデータ取得...")
        try:
            tree_data = self.chat_repo.get_tree_structure(chat_uuid)
            print("   ツリー構造JSON:")
            print(json.dumps(tree_data, indent=2, ensure_ascii=False))
        except Exception as e:
            print(f"   ツリー構造取得エラー: {e}")
        
        print("\n=== テスト完了 ===")
        return True

async def main():
    test = BranchingTest()
    await test.test_conversation_branching()

if __name__ == "__main__":
    asyncio.run(main())