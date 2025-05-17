from fastapi import FastAPI, Depends

from ..di import get_chat_repo_client, get_llm_client, generate_message_cache
from ...usecase.chat_interaction.main import ChatInteraction


app = FastAPI()

# ユーザー作成エンドポイント - リクエストとレスポンスにスキーマを使用
@app.post("/TEST_start_new_chat")
async def start_new_chat(
        llm_client = Depends(get_llm_client),
        chat_repo = Depends(get_chat_repo_client),
        chat_cache = Depends(generate_message_cache)
    ):
    interaction_manageer = ChatInteraction(chat_repo, llm_client, chat_cache)
    interaction_manageer.start_new_chat("あなたは優秀なアシスタントです。userは日本語で回答を期待しています。")
    message = await interaction_manageer.continue_chat("こんにちは")
    print(message.content)
    return interaction_manageer.structure.chat_tree.uuid

#uvicorn src.infra.rest_api.main:app --reload