from anytree import RenderTree
from anytree.render import AsciiStyle
import time

import asyncio

from ..infra.openrouter_client import OpenRouterLLMService
from ..usecase.chat_interaction.main import ChatInteraction
from ..infra.sqlite_client.main import SqliteClient


async def starter():
    opnerouter_client = OpenRouterLLMService(None, "google/gemini-2.0-flash-001")
    sqlite_client = SqliteClient(user_id=1)
    interaction_manageer = ChatInteraction(sqlite_client, opnerouter_client)
    interaction_manageer.start_new_chat("あなたは優秀なアシスタントです。userは日本語で回答を期待しています。")
    await interaction_manageer.continue_chat("こんにちは")
    for pre, fill, node in RenderTree(interaction_manageer.structure_handler.chat_tree.tree, style=AsciiStyle()):
        print(f"{pre}{node.uuid}")

async def restart():
    opnerouter_client = OpenRouterLLMService(None, "google/gemini-2.0-flash-001")
    sqlite_client = SqliteClient(user_id=1)
    interaction_manageer = ChatInteraction(sqlite_client, opnerouter_client)
    interaction_manageer.restart_chat(chat_uuid="d1bdf3ee-33c2-49c5-ac18-ea0268f27db4")
    a = await interaction_manageer.continue_chat("ほかには？")
    print(a.content)
    for pre, fill, node in RenderTree(interaction_manageer.structure_handler.chat_tree.tree, style=AsciiStyle()):
        print(f"{pre}{node.uuid}")

async def select_node():
    opnerouter_client = OpenRouterLLMService(None, "google/gemini-2.0-flash-001")
    sqlite_client = SqliteClient(user_id=1)
    interaction_manageer = ChatInteraction(sqlite_client, opnerouter_client)
    interaction_manageer.restart_chat(chat_uuid="d1bdf3ee-33c2-49c5-ac18-ea0268f27db4")
    interaction_manageer.select_message("78c8c0cd-d666-4f43-9213-bba28286f02e")
    a = await interaction_manageer.continue_chat("それについて詳しく教えてくれませんか")
    print(a.content)
    for pre, fill, node in RenderTree(interaction_manageer.structure_handler.chat_tree.tree, style=AsciiStyle()):
        print(f"{pre}{node.uuid}")

start = time.time()

asyncio.run(select_node())

end = time.time()

print(f"処理時間: {end - start:.6f} 秒")

#uv run -m src.test.test_llm_interaction