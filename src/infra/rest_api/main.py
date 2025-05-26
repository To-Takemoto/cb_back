from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers.chats import router as chats_router

app = FastAPI(
    title="Chat LLM Service API",
    version="0.1.0"
)

# CORS 設定（Reflex / SolidJS 対応）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 各機能モジュールのルーター登録
app.include_router(chats_router)


#uvicorn src.infra.rest_api.main:app --reload