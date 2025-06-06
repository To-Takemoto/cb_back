from typing import List, Optional
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
import json


class Settings(BaseSettings):
    # API Keys
    openrouter_api_key: str = Field(...)
    
    # Security
    secret_key: str = Field(...)
    algorithm: str = Field(default="HS256")
    access_token_expire_minutes: int = Field(default=30)
    
    # Database
    database_url: str = Field(default="sqlite:///./data/chat_app.db")
    
    # Environment
    environment: str = Field(default="development")
    
    # CORS
    cors_origins: List[str] = Field(default=["http://localhost:5173"])
    
    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            return json.loads(v)
        return v
    
    @field_validator("openrouter_api_key")
    @classmethod
    def validate_openrouter_api_key(cls, v):
        if not v:
            raise ValueError("OPENROUTER_API_KEY must be provided")
        return v
    
    @field_validator("secret_key")
    @classmethod
    def validate_secret_key(cls, v):
        if not v:
            raise ValueError("SECRET_KEY must be provided")
        if len(v) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters long")
        return v
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"  # Ignore extra environment variables
    )