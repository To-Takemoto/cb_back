from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from typing import Dict, Any
import asyncio
from src.infra.logging_config import get_logger
from ...domain.exception.chat_exceptions import (
    ChatException,
    ChatNotFoundError,
    MessageNotFoundError,
    InvalidTreeStructureError,
    LLMServiceError,
    AccessDeniedError
)
from ...domain.exception.user_exceptions import UserNotFoundError

logger = get_logger("api.errors")


class UserFriendlyError(Exception):
    """ユーザーフレンドリーなエラーメッセージを持つ例外"""
    def __init__(self, 
                 message: str, 
                 user_message: str,
                 status_code: int = 500,
                 error_type: str = "internal_error",
                 retry_available: bool = False):
        super().__init__(message)
        self.user_message = user_message
        self.status_code = status_code
        self.error_type = error_type
        self.retry_available = retry_available


def create_error_response(
    error_type: str,
    user_message: str,
    detail: str = None,
    status_code: int = 500,
    retry_available: bool = False,
    additional_data: Dict[str, Any] = None
) -> JSONResponse:
    """統一されたエラーレスポンスを作成"""
    content = {
        "error_type": error_type,
        "user_message": user_message,
        "retry_available": retry_available
    }
    
    if detail:
        content["detail"] = detail
    
    if additional_data:
        content.update(additional_data)
    
    return JSONResponse(
        status_code=status_code,
        content=content
    )


async def handle_timeout_error(request: Request, exc: asyncio.TimeoutError):
    """タイムアウトエラーのハンドリング"""
    logger.warning(
        "Request timeout",
        extra={
            "path": request.url.path,
            "method": request.method,
            "error": str(exc)
        }
    )
    
    return create_error_response(
        error_type="timeout",
        user_message="処理がタイムアウトしました。もう一度お試しください。",
        detail="LLM API timeout",
        status_code=status.HTTP_504_GATEWAY_TIMEOUT,
        retry_available=True
    )


async def handle_connection_error(request: Request, exc: ConnectionError):
    """接続エラーのハンドリング"""
    logger.error(
        "Connection error",
        extra={
            "path": request.url.path,
            "method": request.method,
            "error": str(exc)
        }
    )
    
    return create_error_response(
        error_type="connection_error",
        user_message="接続エラーが発生しました。しばらく待ってから再試行してください。",
        detail=str(exc),
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        retry_available=True
    )


async def handle_validation_error(request: Request, exc: ValueError):
    """バリデーションエラーのハンドリング"""
    logger.warning(
        "Validation error",
        extra={
            "path": request.url.path,
            "method": request.method,
            "error": str(exc)
        }
    )
    
    return create_error_response(
        error_type="validation_error",
        user_message="入力内容に問題があります。内容を確認してください。",
        detail=str(exc),
        status_code=status.HTTP_400_BAD_REQUEST,
        retry_available=False
    )


async def handle_permission_error(request: Request, exc: PermissionError):
    """権限エラーのハンドリング"""
    logger.warning(
        "Permission denied",
        extra={
            "path": request.url.path,
            "method": request.method,
            "error": str(exc)
        }
    )
    
    return create_error_response(
        error_type="permission_error",
        user_message="このリソースへのアクセス権限がありません。",
        detail=str(exc),
        status_code=status.HTTP_403_FORBIDDEN,
        retry_available=False
    )


async def handle_chat_exception(request: Request, exc: ChatException):
    """チャット例外のハンドリング"""
    status_code_map = {
        ChatNotFoundError: status.HTTP_404_NOT_FOUND,
        MessageNotFoundError: status.HTTP_404_NOT_FOUND,
        AccessDeniedError: status.HTTP_403_FORBIDDEN,
        InvalidTreeStructureError: status.HTTP_400_BAD_REQUEST,
        LLMServiceError: status.HTTP_502_BAD_GATEWAY,
    }
    
    status_code = status_code_map.get(type(exc), status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    logger.warning(
        f"Chat exception: {exc.__class__.__name__}",
        extra={
            "path": request.url.path,
            "method": request.method,
            "error_code": exc.error_code,
            "error": str(exc)
        }
    )
    
    return create_error_response(
        error_type=exc.error_code or "chat_error",
        user_message=str(exc),
        status_code=status_code,
        retry_available=isinstance(exc, LLMServiceError)
    )

async def handle_validation_exception(request: Request, exc: RequestValidationError):
    """FastAPIバリデーションエラーのハンドリング"""
    logger.warning(
        "FastAPI validation error",
        extra={
            "path": request.url.path,
            "method": request.method,
            "errors": exc.errors()
        }
    )
    
    return create_error_response(
        error_type="validation_error",
        user_message="入力データが無効です",
        detail=exc.errors(),
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        retry_available=False
    )

async def handle_user_not_found_error(request: Request, exc: UserNotFoundError):
    """ユーザーが見つからない場合のエラーハンドリング"""
    logger.warning(
        "User not found",
        extra={
            "path": request.url.path,
            "method": request.method,
            "error": str(exc)
        }
    )
    
    return create_error_response(
        error_type="user_not_found",
        user_message="ユーザーが見つかりません。再度ログインしてください。",
        detail=str(exc),
        status_code=status.HTTP_404_NOT_FOUND,
        retry_available=False
    )

async def handle_generic_error(request: Request, exc: Exception):
    """その他のエラーのハンドリング"""
    logger.error(
        "Unhandled exception",
        extra={
            "path": request.url.path,
            "method": request.method,
            "error": str(exc),
            "error_type": type(exc).__name__
        },
        exc_info=True
    )
    
    return create_error_response(
        error_type="internal_error",
        user_message="予期しないエラーが発生しました。問題が続く場合はサポートにお問い合わせください。",
        detail=str(exc) if request.app.debug else None,
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        retry_available=True
    )