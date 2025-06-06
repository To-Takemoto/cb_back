from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request, Response
from typing import Optional

def get_identifier(request: Request) -> str:
    """
    リクエストの識別子を取得する。
    認証済みユーザーの場合はユーザーIDを使用し、
    未認証の場合はIPアドレスを使用する。
    """
    if hasattr(request.state, "user_id") and request.state.user_id:
        return f"user:{request.state.user_id}"
    return get_remote_address(request)

# レート制限の設定
limiter = Limiter(key_func=get_identifier)

# レート制限エラーハンドラー
def rate_limit_error_handler(request: Request, exc: RateLimitExceeded) -> Response:
    response = Response(
        content=f'{{"detail": "リクエストが多すぎます。しばらく待ってから再試行してください。"}}',
        status_code=429,
        headers={
            "Retry-After": str(exc.retry_after) if hasattr(exc, "retry_after") else "60",
            "Content-Type": "application/json"
        }
    )
    return response