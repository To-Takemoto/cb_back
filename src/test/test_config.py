import os
import pytest
import sys
from pathlib import Path

# Add path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))


class TestConfig:
    def test_config_loads_from_env(self, monkeypatch, tmp_path):
        # Arrange
        monkeypatch.setenv("OPENROUTER_API_KEY", "test-api-key")
        monkeypatch.setenv("SECRET_KEY", "test-secret-key-that-is-at-least-32-characters-long")
        monkeypatch.setenv("ALGORITHM", "HS256")
        monkeypatch.setenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30")
        monkeypatch.setenv("ENVIRONMENT", "test")
        monkeypatch.setenv("CORS_ORIGINS", '["http://localhost:3000"]')
        monkeypatch.chdir(tmp_path)  # Use temp dir to avoid reading .env
        
        # Act
        from src.infra.config import Settings
        settings = Settings()
        
        # Assert
        assert settings.openrouter_api_key == "test-api-key"
        assert settings.secret_key == "test-secret-key-that-is-at-least-32-characters-long"
        assert settings.algorithm == "HS256"
        assert settings.access_token_expire_minutes == 30
        assert settings.environment == "test"
        assert settings.cors_origins == ["http://localhost:3000"]
    
    def test_config_validates_required_fields(self, monkeypatch, tmp_path):
        # Arrange - Missing required fields
        monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
        monkeypatch.delenv("SECRET_KEY", raising=False)
        monkeypatch.chdir(tmp_path)  # Use temp dir to avoid reading .env
        
        # Act & Assert
        from src.infra.config import Settings
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            Settings()
    
    def test_config_uses_default_values(self, monkeypatch, tmp_path):
        # Arrange
        monkeypatch.setenv("OPENROUTER_API_KEY", "test-api-key")
        monkeypatch.setenv("SECRET_KEY", "test-secret-key-that-is-at-least-32-characters-long")
        monkeypatch.chdir(tmp_path)  # Use temp dir to avoid reading .env
        
        # Act
        from src.infra.config import Settings
        settings = Settings()
        
        # Assert
        assert settings.algorithm == "HS256"
        assert settings.access_token_expire_minutes == 30
        assert settings.environment == "development"
        assert settings.cors_origins == ["http://localhost:5173"]
    
    def test_config_loads_from_env_file(self, tmp_path, monkeypatch):
        # Arrange
        env_file = tmp_path / ".env"
        env_file.write_text("""
OPENROUTER_API_KEY=file-api-key
SECRET_KEY=file-secret-key-that-is-at-least-32-characters-long
ENVIRONMENT=test
""")
        monkeypatch.chdir(tmp_path)
        
        # Clear existing env vars to ensure we're reading from file
        monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
        monkeypatch.delenv("SECRET_KEY", raising=False)
        
        # Act
        from src.infra.config import Settings
        settings = Settings()
        
        # Assert
        assert settings.openrouter_api_key == "file-api-key"
        assert settings.secret_key == "file-secret-key-that-is-at-least-32-characters-long"
        assert settings.environment == "test"