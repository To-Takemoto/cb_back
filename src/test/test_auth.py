import pytest
import sys
import os
from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError

# Add path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))


class TestAuthFunctions:
    """Test auth functions without external dependencies"""
    
    def test_password_hashing(self):
        """Test password hashing and verification"""
        from src.infra.auth import get_password_hash, verify_password
        
        plain_password = "mysecretpassword"
        hashed = get_password_hash(plain_password)
        
        assert verify_password(plain_password, hashed) is True
        assert verify_password("wrongpassword", hashed) is False
    
    def test_jwt_token_creation_and_verification(self, monkeypatch):
        """Test JWT token creation and verification"""
        # Set environment variables for config
        monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
        monkeypatch.setenv("SECRET_KEY", "test-secret-key-that-is-at-least-32-characters-long")
        
        from src.infra.auth import create_access_token, verify_token
        
        # Test token creation
        data = {"sub": "user123"}
        token = create_access_token(data)
        
        assert isinstance(token, str)
        assert len(token) > 0
        
        # Test token verification
        payload = verify_token(token)
        assert payload["sub"] == "user123"
    
    def test_jwt_token_with_expiration(self, monkeypatch):
        """Test JWT token with custom expiration"""
        monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
        monkeypatch.setenv("SECRET_KEY", "test-secret-key-that-is-at-least-32-characters-long")
        
        from src.infra.auth import create_access_token
        
        data = {"sub": "user123"}
        expires_delta = timedelta(minutes=15)
        token = create_access_token(data, expires_delta)
        
        # Decode to verify expiration was set
        from src.infra.config import Settings
        settings = Settings()
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        
        assert payload["sub"] == "user123"
        assert "exp" in payload
    
    def test_invalid_jwt_token(self):
        """Test handling of invalid JWT tokens"""
        from src.infra.auth import verify_token
        
        with pytest.raises(JWTError):
            verify_token("invalid.token.here")
    
    def test_expired_jwt_token(self, monkeypatch):
        """Test handling of expired JWT tokens"""
        monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
        monkeypatch.setenv("SECRET_KEY", "test-secret-key-that-is-at-least-32-characters-long")
        
        from src.infra.auth import verify_token
        from src.infra.config import Settings
        
        settings = Settings()
        
        # Create expired token
        data = {"sub": "user123", "exp": datetime.now(timezone.utc) - timedelta(hours=1)}
        token = jwt.encode(data, settings.secret_key, algorithm=settings.algorithm)
        
        with pytest.raises(JWTError):
            verify_token(token)
    
    def test_get_current_user_valid_token(self, monkeypatch):
        """Test extracting user from valid token"""
        monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
        monkeypatch.setenv("SECRET_KEY", "test-secret-key-that-is-at-least-32-characters-long")
        
        from src.infra.auth import create_access_token, get_current_user
        
        valid_token = create_access_token({"sub": "user123"})
        user_id = get_current_user(valid_token)
        
        assert user_id == "user123"
    
    def test_get_current_user_invalid_token(self):
        """Test error handling for invalid token"""
        from src.infra.auth import get_current_user
        from fastapi import HTTPException
        
        with pytest.raises(HTTPException) as exc_info:
            get_current_user("invalid.token")
        
        assert exc_info.value.status_code == 401
    
    def test_get_current_user_missing_sub(self, monkeypatch):
        """Test error handling for token without sub claim"""
        monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
        monkeypatch.setenv("SECRET_KEY", "test-secret-key-that-is-at-least-32-characters-long")
        
        from src.infra.auth import create_access_token, get_current_user
        from fastapi import HTTPException
        
        # Token without 'sub' claim
        token = create_access_token({"user": "test"})
        
        with pytest.raises(HTTPException) as exc_info:
            get_current_user(token)
        
        assert exc_info.value.status_code == 401