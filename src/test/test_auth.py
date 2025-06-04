import pytest
from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError


class TestAuth:
    def test_create_access_token(self):
        # Arrange
        from src.infra.auth import create_access_token
        data = {"sub": "user123"}
        
        # Act
        token = create_access_token(data)
        
        # Assert
        assert isinstance(token, str)
        assert len(token) > 0
    
    def test_create_access_token_with_expiration(self, monkeypatch):
        # Arrange
        monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
        monkeypatch.setenv("SECRET_KEY", "test-secret-key-that-is-at-least-32-characters-long")
        
        from src.infra.auth import create_access_token, get_settings
        settings = get_settings()
        data = {"sub": "user123"}
        expires_delta = timedelta(minutes=15)
        
        # Act
        token = create_access_token(data, expires_delta)
        
        # Assert
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        assert payload["sub"] == "user123"
        assert "exp" in payload
    
    def test_verify_token_valid(self):
        # Arrange
        from src.infra.auth import create_access_token, verify_token
        data = {"sub": "user123"}
        token = create_access_token(data)
        
        # Act
        payload = verify_token(token)
        
        # Assert
        assert payload["sub"] == "user123"
    
    def test_verify_token_expired(self):
        # Arrange
        from src.infra.auth import create_access_token, verify_token
        from src.infra.config import Settings
        settings = Settings(
            openrouter_api_key="test-key",
            secret_key="test-secret-key-that-is-at-least-32-characters-long"
        )
        
        # Create expired token
        data = {"sub": "user123", "exp": datetime.now(timezone.utc) - timedelta(hours=1)}
        token = jwt.encode(data, settings.secret_key, algorithm=settings.algorithm)
        
        # Act & Assert
        with pytest.raises(JWTError):
            verify_token(token)
    
    def test_verify_token_invalid(self):
        # Arrange
        from src.infra.auth import verify_token
        
        # Act & Assert
        with pytest.raises(JWTError):
            verify_token("invalid.token.here")
    
    def test_verify_password(self):
        # Arrange
        from src.infra.auth import get_password_hash, verify_password
        plain_password = "mysecretpassword"
        
        # Act
        hashed = get_password_hash(plain_password)
        
        # Assert
        assert verify_password(plain_password, hashed) is True
        assert verify_password("wrongpassword", hashed) is False
    
    def test_get_current_user(self):
        # Arrange
        from src.infra.auth import create_access_token, get_current_user
        from fastapi import HTTPException
        
        # Valid token
        valid_token = create_access_token({"sub": "user123"})
        
        # Act
        user_id = get_current_user(valid_token)
        
        # Assert
        assert user_id == "user123"
    
    def test_get_current_user_invalid_token(self):
        # Arrange
        from src.infra.auth import get_current_user
        from fastapi import HTTPException
        
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            get_current_user("invalid.token")
        
        assert exc_info.value.status_code == 401
    
    def test_get_current_user_no_sub(self):
        # Arrange
        from src.infra.auth import create_access_token, get_current_user
        from fastapi import HTTPException
        
        # Token without 'sub' claim
        token = create_access_token({"user": "test"})  # Missing 'sub'
        
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            get_current_user(token)
        
        assert exc_info.value.status_code == 401