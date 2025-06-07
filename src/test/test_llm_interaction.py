from anytree import RenderTree
from anytree.render import AsciiStyle

import time
import asyncio

from src.infra.openrouter_client import OpenRouterLLMService
from src.usecase.chat_interaction.main import ChatInteraction
from src.infra.tortoise_client.chat_repo import TortoiseChatRepository


async def starter():
    opnerouter_client = OpenRouterLLMService(None, "google/gemini-2.0-flash-001")
    chat_repo = TortoiseChatRepository(user_id=1)
    interaction_manageer = ChatInteraction(chat_repo, opnerouter_client)
    interaction_manageer.start_new_chat("あなたは優秀なアシスタントです。userは日本語で回答を期待しています。")
    message = await interaction_manageer.continue_chat("こんにちは")
    print(message.content)
    for pre, fill, node in RenderTree(interaction_manageer.structure.chat_tree.tree, style=AsciiStyle()):
        print(f"{pre}{node.uuid}")
    
async def restart():
    opnerouter_client = OpenRouterLLMService(None, "google/gemini-2.0-flash-001")
    chat_repo = TortoiseChatRepository(user_id=1)
    interaction_manageer = ChatInteraction(chat_repo, opnerouter_client)
    interaction_manageer.restart_chat(chat_uuid="ca40f9cf-aca4-4a83-ac06-90b7258c700a")
    message = await interaction_manageer.continue_chat("1個目について詳しく教えてくれませんか")
    print(message.content)
    for pre, fill, node in RenderTree(interaction_manageer.structure.chat_tree.tree, style=AsciiStyle()):
        print(f"{pre}{node.uuid}")

async def select_message():
    opnerouter_client = OpenRouterLLMService(None, "google/gemini-2.0-flash-001")
    chat_repo = TortoiseChatRepository(user_id=1)
    interaction_manageer = ChatInteraction(chat_repo, opnerouter_client)
    interaction_manageer.restart_chat(chat_uuid="ca40f9cf-aca4-4a83-ac06-90b7258c700a")
    interaction_manageer.select_message(message_uuid="4198b4df-0a26-4d8c-9510-81e5876f7b7d")
    message = await interaction_manageer.continue_chat("２つ目について詳しく教えてくれませんか")
    print(message.content)
    for pre, fill, node in RenderTree(interaction_manageer.structure.chat_tree.tree, style=AsciiStyle()):
        print(f"{pre}{node.uuid}")

start = time.time()

asyncio.run(select_message())

end = time.time()

print(f"処理時間: {end - start:.6f} 秒")

#uv run -m src.test.test_llm_interaction