from anytree import RenderTree
from anytree.render import AsciiStyle

import time
import asyncio
import functools

from src.infra.openrouter_client import OpenRouterLLMService
from src.usecase.chat_interaction.main import ChatInteraction
from src.infra.tortoise_client.chat_repo import TortoiseChatRepository

def measure_time(func):
    if asyncio.iscoroutinefunction(func):
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            start = time.time()
            result = await func(*args, **kwargs)
            end = time.time()
            print(f"{func.__name__} の処理時間: {end - start:.6f} 秒")
            return result
        return async_wrapper
    else:
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            start = time.time()
            result = func(*args, **kwargs)
            end = time.time()
            print(f"{func.__name__} の処理時間: {end - start:.6f} 秒")
            return result
        return sync_wrapper
    

@measure_time
async def start_chat():
    opnerouter_client = OpenRouterLLMService(None, "google/gemini-2.0-flash-001")
    chat_repo = TortoiseChatRepository(user_id=1)
    interaction_manageer = ChatInteraction(chat_repo, opnerouter_client)
    interaction_manageer.start_new_chat("あなたは優秀なアシスタントです。userは日本語で回答を期待しています。")
    message = await interaction_manageer.continue_chat("こんにちは")
    print(message.content)
    return interaction_manageer.structure.chat_tree.uuid

@measure_time   
async def restart(user_message, target_chat_uuid):
    opnerouter_client = OpenRouterLLMService(None, "google/gemini-2.0-flash-001")
    chat_repo = TortoiseChatRepository(user_id=1)
    interaction_manageer = ChatInteraction(chat_repo, opnerouter_client)
    interaction_manageer.restart_chat(chat_uuid=target_chat_uuid)
    message = await interaction_manageer.continue_chat(user_message)
    print(message.content)
    for pre, fill, node in RenderTree(interaction_manageer.structure.chat_tree.tree, style=AsciiStyle()):
        print(f"{pre}{node.uuid}")

@measure_time 
async def select_message(target_chat_uuid, ):
    opnerouter_client = OpenRouterLLMService(None, "google/gemini-2.0-flash-001")
    chat_repo = TortoiseChatRepository(user_id=1)
    interaction_manageer = ChatInteraction(chat_repo, opnerouter_client)
    interaction_manageer.restart_chat(chat_uuid=target_chat_uuid)
    interaction_manageer.select_message(message_uuid="4198b4df-0a26-4d8c-9510-81e5876f7b7d")
    message = await interaction_manageer.continue_chat("２つ目について詳しく教えてくれませんか")
    print(message.content)
    for pre, fill, node in RenderTree(interaction_manageer.structure.chat_tree.tree, style=AsciiStyle()):
        print(f"{pre}{node.uuid}")

if __name__ == "__main__":
    a = asyncio.run(start_chat())
    asyncio.run(restart("何か雑学を教えてくれませんか", a))
    


#uv run -m src.test.test_api_endpoint