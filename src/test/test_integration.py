import pytest
from fastapi.testclient import TestClient


def test_application_startup():
    """アプリケーションが正常に起動することを確認"""
    from src.infra.rest_api.main import app
    
    # Test that app can be created without errors
    assert app is not None
    assert app.title == "Chat LLM Service API"
    assert app.version == "0.1.0"


def test_all_required_endpoints_exist():
    """すべての必要なエンドポイントが存在することを確認"""
    from src.infra.rest_api.main import app
    
    # Extract all route paths
    routes = []
    for route in app.routes:
        if hasattr(route, 'path') and hasattr(route, 'methods'):
            for method in route.methods:
                if method != "HEAD":  # Skip HEAD methods
                    routes.append(f"{method} {route.path}")
    
    # Check required endpoints exist
    required_endpoints = [
        # Authentication
        "POST /api/v1/auth/login",
        "GET /api/v1/auth/me",
        
        # Basic chat functionality
        "POST /api/v1/chats/",
        "POST /api/v1/chats/{chat_uuid}/messages",
        "GET /api/v1/chats/{chat_uuid}/messages",
        
        # New UX features
        "GET /api/v1/chats/{chat_uuid}/last-position",
        "POST /api/v1/chats/{chat_uuid}/messages/{message_id}/retry",
        "GET /api/v1/chats/recent",
        "DELETE /api/v1/chats/{chat_uuid}",
        "GET /api/v1/chats/{chat_uuid}/search",
        "GET /api/v1/chats/",
        
        # User management
        "POST /api/v1/users"
    ]
    
    for endpoint in required_endpoints:
        assert endpoint in routes, f"Missing endpoint: {endpoint}"


def test_middleware_configuration():
    """ミドルウェアが正しく設定されていることを確認"""
    from src.infra.rest_api.main import app
    
    # Check middleware is configured
    middleware_names = [middleware.cls.__name__ for middleware in app.user_middleware]
    
    assert "LoggingMiddleware" in middleware_names
    assert "CORSMiddleware" in middleware_names


def test_exception_handlers_configured():
    """例外ハンドラーが設定されていることを確認"""
    from src.infra.rest_api.main import app
    import asyncio
    
    # Check that exception handlers are configured
    assert len(app.exception_handlers) > 0
    
    # Check specific handlers
    assert asyncio.TimeoutError in app.exception_handlers
    assert ConnectionError in app.exception_handlers
    assert ValueError in app.exception_handlers
    assert PermissionError in app.exception_handlers
    assert Exception in app.exception_handlers


def test_openapi_documentation():
    """OpenAPIドキュメントが生成されることを確認"""
    from src.infra.rest_api.main import app
    
    client = TestClient(app)
    
    # Test OpenAPI schema
    response = client.get("/openapi.json")
    assert response.status_code == 200
    
    openapi_schema = response.json()
    assert "openapi" in openapi_schema
    assert "info" in openapi_schema
    assert openapi_schema["info"]["title"] == "Chat LLM Service API"
    
    # Test Swagger UI
    response = client.get("/docs")
    assert response.status_code == 200
    
    # Test ReDoc
    response = client.get("/redoc")
    assert response.status_code == 200


def test_configuration_loading():
    """設定が正しく読み込まれることを確認"""
    from src.infra.config import Settings
    
    # Test settings can be loaded
    settings = Settings()
    assert settings is not None
    assert hasattr(settings, 'cors_origins')
    assert hasattr(settings, 'environment')
    assert hasattr(settings, 'access_token_expire_minutes')


def test_database_models():
    """データベースモデルが正しく定義されていることを確認"""
    from src.infra.sqlite_client.peewee_models import (
        User, DiscussionStructure, Message, LLMDetails, UserChatPosition
    )
    
    # Test models exist
    assert User is not None
    assert DiscussionStructure is not None
    assert Message is not None
    assert LLMDetails is not None
    assert UserChatPosition is not None
    
    # Test UserChatPosition has required fields
    assert hasattr(UserChatPosition, 'user')
    assert hasattr(UserChatPosition, 'discussion')
    assert hasattr(UserChatPosition, 'last_node_id')
    assert hasattr(UserChatPosition, 'updated_at')


if __name__ == "__main__":
    test_application_startup()
    test_all_required_endpoints_exist()
    test_middleware_configuration()
    test_exception_handlers_configured()
    test_openapi_documentation()
    test_configuration_loading()
    test_database_models()
    print("✅ All integration tests passed!")