# src/test/test_sqlite_client.py
import os
import unittest
import asyncio
import uuid

from tortoise import Tortoise

from src.entity.message import Message, Role
from src.infra.sqlite_client import TortoiseMessageRepository, MessageModel


class TestTortoiseMessageRepository(unittest.TestCase):
    """TortoiseMessageRepositoryの単体テスト"""
    
    async def asyncSetUp(self):
        """非同期のセットアップ"""
        # テスト用のインメモリデータベースを使用
        self.db_url = "sqlite://:memory:"
        
        # TortoiseORMの初期化 - ここを修正
        await Tortoise.init(
            db_url=self.db_url,
            modules={'models': ['src.infra.sqlite_client']}  # 正しいパスに修正
        )
        
        # スキーマの生成
        await Tortoise.generate_schemas()
        
        # テスト用のリポジトリを作成
        self.repo = TortoiseMessageRepository(db_url=self.db_url)
    
    async def asyncTearDown(self):
        """非同期のクリーンアップ"""
        if hasattr(self, 'repo'):
            await self.repo.close()
        await Tortoise.close_connections()
    
    def setUp(self):
        """テストのセットアップ"""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.loop.run_until_complete(self.asyncSetUp())
    
    def tearDown(self):
        """テストのクリーンアップ"""
        self.loop.run_until_complete(self.asyncTearDown())
        self.loop.close()
    
    def test_save_message(self):
        """メッセージ保存のテスト"""
        async def run_test():
            # テスト用のメッセージを作成
            test_message = Message(
                id=None,  # IDは自動生成される
                uuid="",  # 空のUUIDは自動生成される
                role=Role.USER,
                content="テストメッセージ"
            )
            
            # 会話IDを生成
            conversation_id = str(uuid.uuid4())
            
            # メッセージを保存
            saved_message = await self.repo.save(test_message, conversation_id)
            
            # 検証
            self.assertIsNotNone(saved_message.id)
            self.assertNotEqual(saved_message.uuid, "")
            self.assertEqual(saved_message.role, Role.USER)
            self.assertEqual(saved_message.content, "テストメッセージ")
            
            # UUIDを指定した場合のテスト
            specific_uuid = str(uuid.uuid4())
            test_message2 = Message(
                id=None,
                uuid=specific_uuid,
                role=Role.ASSISTANT,
                content="応答メッセージ"
            )
            
            saved_message2 = await self.repo.save(test_message2, conversation_id)
            
            # 検証
            self.assertEqual(saved_message2.uuid, specific_uuid)
        
        self.loop.run_until_complete(run_test())
    
    def test_get_conversation_history(self):
        """会話履歴取得のテスト"""
        async def run_test():
            # テスト用の会話IDを生成
            conversation_id = str(uuid.uuid4())
            another_conversation_id = str(uuid.uuid4())
            
            # テスト用のメッセージを複数作成
            messages = [
                Message(id=None, uuid="", role=Role.USER, content="こんにちは"),
                Message(id=None, uuid="", role=Role.ASSISTANT, content="どうしましたか？"),
                Message(id=None, uuid="", role=Role.USER, content="質問があります")
            ]
            
            # 別の会話用のメッセージも作成
            another_message = Message(id=None, uuid="", role=Role.USER, content="別の会話")
            
            # メッセージを保存
            for msg in messages:
                await self.repo.save(msg, conversation_id)
            
            # 別の会話IDでメッセージを保存
            await self.repo.save(another_message, another_conversation_id)
            
            # 会話履歴を取得
            history = await self.repo.get_conversation_history(conversation_id)
            
            # 検証
            self.assertEqual(len(history), 3)
            self.assertEqual(history[0].content, "こんにちは")
            self.assertEqual(history[1].content, "どうしましたか？")
            self.assertEqual(history[2].content, "質問があります")
            
            # 別の会話の履歴を取得
            another_history = await self.repo.get_conversation_history(another_conversation_id)
            
            # 検証
            self.assertEqual(len(another_history), 1)
            self.assertEqual(another_history[0].content, "別の会話")
            
            # 存在しない会話IDの場合
            non_existent_history = await self.repo.get_conversation_history("non_existent_id")
            self.assertEqual(len(non_existent_history), 0)
        
        self.loop.run_until_complete(run_test())
    
    def test_message_order(self):
        """メッセージの順序のテスト"""
        async def run_test():
            # テスト用の会話IDを生成
            conversation_id = str(uuid.uuid4())
            
            # テスト用のメッセージを作成
            messages = [
                Message(id=None, uuid="", role=Role.USER, content="1番目のメッセージ"),
                Message(id=None, uuid="", role=Role.ASSISTANT, content="2番目のメッセージ"),
                Message(id=None, uuid="", role=Role.USER, content="3番目のメッセージ")
            ]
            
            # 順番に保存
            for msg in messages:
                await self.repo.save(msg, conversation_id)
                await asyncio.sleep(0.1)  # 少し待つ
            
            # 会話履歴を取得
            history = await self.repo.get_conversation_history(conversation_id)
            
            # 検証 - 保存順に取得されるはず
            self.assertEqual(len(history), 3)
            self.assertEqual(history[0].content, "1番目のメッセージ")
            self.assertEqual(history[1].content, "2番目のメッセージ")
            self.assertEqual(history[2].content, "3番目のメッセージ")
        
        self.loop.run_until_complete(run_test())


if __name__ == "__main__":
    unittest.main()