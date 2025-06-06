#!/usr/bin/env python3
"""
REST API エンドポイントのテスト
実際のHTTPリクエストを使用して分岐機能をテスト
"""

import asyncio
import json
import httpx
from typing import Dict, Any

class APIBranchingTest:
    def __init__(self):
        self.base_url = "http://localhost:8000"
        self.auth_token = None
        self.chat_uuid = None
        
    async def login(self):
        """テストユーザーでログイン"""
        async with httpx.AsyncClient() as client:
            # まずユーザー登録
            register_data = {
                "username": "testuser",
                "email": "test@example.com", 
                "password": "testpass123"
            }
            try:
                response = await client.post(f"{self.base_url}/api/v1/auth/register", json=register_data)
                print(f"Register response: {response.status_code}")
            except:
                pass  # すでに登録済みの場合
                
            # ログイン
            login_data = {
                "username": "testuser",
                "password": "testpass123"
            }
            response = await client.post(f"{self.base_url}/api/v1/auth/login", data=login_data)
            if response.status_code == 200:
                result = response.json()
                self.auth_token = result.get("access_token")
                print(f"✓ ログイン成功: {self.auth_token[:20]}...")
                return True
            else:
                print(f"✗ ログイン失敗: {response.status_code} - {response.text}")
                return False
    
    def get_headers(self):
        """認証ヘッダーを取得"""
        return {"Authorization": f"Bearer {self.auth_token}"}
    
    async def test_api_branching(self):
        print("=== REST API 分岐テスト開始 ===\n")
        
        if not await self.login():
            print("認証に失敗しました")
            return
            
        async with httpx.AsyncClient() as client:
            # 1. 新しいチャット作成
            print("1. 新しいチャット作成...")
            create_response = await client.post(
                f"{self.base_url}/api/v1/chats/",
                json={"initial_message": "Hello, this is a test chat."},
                headers=self.get_headers()
            )
            if create_response.status_code == 200:
                result = create_response.json()
                self.chat_uuid = result["chat_uuid"]
                print(f"   ✓ チャット作成成功: {self.chat_uuid}")
            else:
                print(f"   ✗ チャット作成失敗: {create_response.status_code}")
                return
            
            # 2. 最初のメッセージ送信
            print("\n2. 最初のメッセージ送信...")
            msg1_response = await client.post(
                f"{self.base_url}/api/v1/chats/{self.chat_uuid}/messages",
                json={"content": "What is the capital of Japan?"},
                headers=self.get_headers()
            )
            if msg1_response.status_code == 200:
                msg1_result = msg1_response.json()
                msg1_uuid = msg1_result["message_uuid"]
                print(f"   ✓ メッセージ1送信成功: {msg1_uuid}")
                print(f"   アシスタント応答: {msg1_result['content']}")
            else:
                print(f"   ✗ メッセージ1送信失敗: {msg1_response.status_code}")
                return
            
            # 3. 2番目のメッセージ送信
            print("\n3. 2番目のメッセージ送信...")
            msg2_response = await client.post(
                f"{self.base_url}/api/v1/chats/{self.chat_uuid}/messages",
                json={"content": "Tell me about Tokyo."},
                headers=self.get_headers()
            )
            if msg2_response.status_code == 200:
                msg2_result = msg2_response.json()
                msg2_uuid = msg2_result["message_uuid"]
                print(f"   ✓ メッセージ2送信成功: {msg2_uuid}")
                print(f"   アシスタント応答: {msg2_result['content']}")
            else:
                print(f"   ✗ メッセージ2送信失敗: {msg2_response.status_code}")
                return
            
            # 4. 現在のパス確認
            print("\n4. 現在のパス確認...")
            path_response = await client.get(
                f"{self.base_url}/api/v1/chats/{self.chat_uuid}/path",
                headers=self.get_headers()
            )
            if path_response.status_code == 200:
                path_result = path_response.json()
                print(f"   ✓ パス取得成功:")
                for i, uuid in enumerate(path_result["path"]):
                    print(f"     {i}: {uuid}")
            else:
                print(f"   ✗ パス取得失敗: {path_response.status_code}")
                return
            
            # 5. ノード選択（分岐点に戻る）
            print(f"\n5. ノード選択（{msg1_uuid} に戻る）...")
            select_response = await client.post(
                f"{self.base_url}/api/v1/chats/{self.chat_uuid}/select",
                json={"message_uuid": msg1_uuid},
                headers=self.get_headers()
            )
            if select_response.status_code == 200:
                print(f"   ✓ ノード選択成功")
            else:
                print(f"   ✗ ノード選択失敗: {select_response.status_code} - {select_response.text}")
                return
            
            # 6. 選択後のパス確認
            print("\n6. 選択後のパス確認...")
            new_path_response = await client.get(
                f"{self.base_url}/api/v1/chats/{self.chat_uuid}/path",
                headers=self.get_headers()
            )
            if new_path_response.status_code == 200:
                new_path_result = new_path_response.json()
                print(f"   ✓ 新しいパス:")
                for i, uuid in enumerate(new_path_result["path"]):
                    print(f"     {i}: {uuid}")
            else:
                print(f"   ✗ パス取得失敗: {new_path_response.status_code}")
                return
            
            # 7. 分岐したメッセージ送信
            print("\n7. 分岐したメッセージ送信...")
            branch_response = await client.post(
                f"{self.base_url}/api/v1/chats/{self.chat_uuid}/messages",
                json={"content": "What about Osaka?"},
                headers=self.get_headers()
            )
            if branch_response.status_code == 200:
                branch_result = branch_response.json()
                branch_uuid = branch_result["message_uuid"]
                print(f"   ✓ 分岐メッセージ送信成功: {branch_uuid}")
                print(f"   アシスタント応答: {branch_result['content']}")
            else:
                print(f"   ✗ 分岐メッセージ送信失敗: {branch_response.status_code}")
                return
            
            # 8. ツリー構造取得
            print("\n8. ツリー構造取得...")
            tree_response = await client.get(
                f"{self.base_url}/api/v1/chats/{self.chat_uuid}/tree",
                headers=self.get_headers()
            )
            if tree_response.status_code == 200:
                tree_result = tree_response.json()
                print(f"   ✓ ツリー構造取得成功:")
                print(f"   現在のノード: {tree_result['current_node_uuid']}")
                print("   ツリー構造:")
                print(json.dumps(tree_result["tree"], indent=2, ensure_ascii=False))
            else:
                print(f"   ✗ ツリー構造取得失敗: {tree_response.status_code} - {tree_response.text}")
                return
            
            # 9. 元のブランチに戻る
            print(f"\n9. 元のブランチに戻る（{msg2_uuid}）...")
            back_select_response = await client.post(
                f"{self.base_url}/api/v1/chats/{self.chat_uuid}/select",
                json={"message_uuid": msg2_uuid},
                headers=self.get_headers()
            )
            if back_select_response.status_code == 200:
                print(f"   ✓ 元のブランチに戻る成功")
                
                # 戻った後のパス確認
                final_path_response = await client.get(
                    f"{self.base_url}/api/v1/chats/{self.chat_uuid}/path",
                    headers=self.get_headers()
                )
                if final_path_response.status_code == 200:
                    final_path_result = final_path_response.json()
                    print(f"   最終パス:")
                    for i, uuid in enumerate(final_path_result["path"]):
                        print(f"     {i}: {uuid}")
            else:
                print(f"   ✗ 元のブランチに戻る失敗: {back_select_response.status_code}")
        
        print("\n=== REST API 分岐テスト完了 ===")

async def main():
    test = APIBranchingTest()
    await test.test_api_branching()

if __name__ == "__main__":
    asyncio.run(main())