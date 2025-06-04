from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.infra.config import Settings
from src.infra.logging_config import LoggingMiddleware, get_logger
import asyncio

from .routers.chats import router as chats_router
from .routers.users import router as users_router
from .routers.auth import router as auth_router
from .error_handlers import (
    handle_timeout_error,
    handle_connection_error,
    handle_validation_error,
    handle_permission_error,
    handle_generic_error
)

# Initialize settings and logger
settings = Settings()
logger = get_logger("app")

app = FastAPI(
    title="Chat LLM Service API",
    version="0.1.0"
)

# Add logging middleware
app.add_middleware(LoggingMiddleware)

# CORS 設定（環境設定に基づく）
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 各機能モジュールのルーター登録
app.include_router(auth_router)
app.include_router(chats_router)
app.include_router(users_router)

@app.on_event("startup")
async def startup_event():
    logger.info("Application starting up", extra={"environment": settings.environment})

# エラーハンドラーの登録
app.add_exception_handler(asyncio.TimeoutError, handle_timeout_error)
app.add_exception_handler(ConnectionError, handle_connection_error)
app.add_exception_handler(ValueError, handle_validation_error)
app.add_exception_handler(PermissionError, handle_permission_error)
app.add_exception_handler(Exception, handle_generic_error)


#uvicorn src.infra.rest_api.main:app --reload