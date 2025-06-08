import asyncio
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded

from src.infra.config import Settings
from src.infra.logging_config import LoggingMiddleware, get_logger

from .routers.chats import router as chats_router
from .routers.users import router as users_router
from .routers.auth import router as auth_router
from .routers.models import router as models_router
from .routers.templates import router as templates_router
from .routers.analytics import router as analytics_router
from .error_handlers import (
    handle_timeout_error,
    handle_connection_error,
    handle_validation_error,
    handle_permission_error,
    handle_generic_error,
    handle_chat_exception,
    handle_validation_exception,
    handle_user_not_found_error
)
from .rate_limiter import limiter, rate_limit_error_handler

# Initialize settings and logger
settings = Settings()
# 本番環境では適切なログレベルを設定する
log_level = logging.INFO if settings.environment == "production" else logging.DEBUG
logger = get_logger("app", level=log_level)

app = FastAPI(
    title="Chat LLM Service API",
    version="0.1.0"
)

# レート制限の設定
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_error_handler)

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
app.include_router(models_router)
app.include_router(templates_router)
app.include_router(analytics_router, prefix="/api/v1")

@app.on_event("startup")
async def startup_event():
    """アプリケーション起動時の初期化処理"""
    logger.info("Application starting up", extra={"environment": settings.environment})
    
    # Tortoise ORM初期化
    from tortoise import Tortoise
    from src.infra.tortoise_client.config import TORTOISE_ORM
    
    await Tortoise.init(config=TORTOISE_ORM)
    logger.info("Tortoise ORM initialized")

@app.on_event("shutdown")
async def shutdown_event():
    """アプリケーション終了時のクリーンアップ"""
    from tortoise import Tortoise
    await Tortoise.close_connections()
    logger.info("Application shutdown complete")

@app.get("/api/v1/health")
async def health_check():
    """ヘルスチェックエンドポイント"""
    return {"status": "healthy", "version": "0.1.0"}

# エラーハンドラーの登録
from src.domain.exception.chat_exceptions import ChatException
from src.domain.exception.user_exceptions import UserNotFoundError
from fastapi.exceptions import RequestValidationError

app.add_exception_handler(UserNotFoundError, handle_user_not_found_error)
app.add_exception_handler(ChatException, handle_chat_exception)
app.add_exception_handler(RequestValidationError, handle_validation_exception)
app.add_exception_handler(asyncio.TimeoutError, handle_timeout_error)
app.add_exception_handler(ConnectionError, handle_connection_error)
app.add_exception_handler(ValueError, handle_validation_error)
app.add_exception_handler(PermissionError, handle_permission_error)
app.add_exception_handler(Exception, handle_generic_error)


#uvicorn src.infra.rest_api.main:app --reload