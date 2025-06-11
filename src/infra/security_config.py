"""
Production security configuration for the application.
"""
from typing import List, Dict
from pydantic import Field
from pydantic_settings import BaseSettings


class SecuritySettings(BaseSettings):
    """Security-specific settings for production deployment."""
    
    # CORS settings
    cors_allowed_origins: List[str] = Field(
        default_factory=lambda: ["https://yourdomain.com"],
        description="Allowed origins for CORS"
    )
    cors_allowed_methods: List[str] = Field(
        default_factory=lambda: ["GET", "POST", "PUT", "DELETE"],
        description="Allowed HTTP methods"
    )
    cors_allowed_headers: List[str] = Field(
        default_factory=lambda: ["Authorization", "Content-Type", "X-Requested-With"],
        description="Allowed headers"
    )
    cors_allow_credentials: bool = Field(
        default=True,
        description="Allow credentials in CORS requests"
    )
    
    # Security headers
    security_headers: Dict[str, str] = Field(
        default_factory=lambda: {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains; preload",
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
            "Content-Security-Policy": "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline';"
        }
    )
    
    # Rate limiting (per minute)
    rate_limit_login: int = Field(default=5, description="Login attempts per minute")
    rate_limit_api: int = Field(default=60, description="API calls per minute")
    rate_limit_register: int = Field(default=3, description="Registration attempts per minute")
    
    # Session settings
    session_timeout_minutes: int = Field(default=30, description="Session timeout in minutes")
    refresh_token_expire_days: int = Field(default=7, description="Refresh token expiration in days")
    
    # Password policy
    password_min_length: int = Field(default=12, description="Minimum password length")
    password_require_uppercase: bool = Field(default=True)
    password_require_lowercase: bool = Field(default=True)
    password_require_numbers: bool = Field(default=True)
    password_require_special: bool = Field(default=True)
    
    # Logging
    log_security_events: bool = Field(default=True)
    mask_sensitive_data: bool = Field(default=True)
    
    # Environment
    force_https: bool = Field(default=True, description="Force HTTPS in production")
    
    class Config:
        env_prefix = "SECURITY_"
        case_sensitive = False


def get_security_middleware_config(settings: SecuritySettings) -> Dict:
    """Get middleware configuration based on security settings."""
    return {
        "cors": {
            "allow_origins": settings.cors_allowed_origins,
            "allow_methods": settings.cors_allowed_methods,
            "allow_headers": settings.cors_allowed_headers,
            "allow_credentials": settings.cors_allow_credentials,
        },
        "headers": settings.security_headers,
        "rate_limit": {
            "login": settings.rate_limit_login,
            "api": settings.rate_limit_api,
            "register": settings.rate_limit_register,
        }
    }


def validate_password_policy(password: str, settings: SecuritySettings) -> tuple[bool, str]:
    """Validate password against security policy."""
    if len(password) < settings.password_min_length:
        return False, f"Password must be at least {settings.password_min_length} characters long"
    
    if settings.password_require_uppercase and not any(c.isupper() for c in password):
        return False, "Password must contain at least one uppercase letter"
    
    if settings.password_require_lowercase and not any(c.islower() for c in password):
        return False, "Password must contain at least one lowercase letter"
    
    if settings.password_require_numbers and not any(c.isdigit() for c in password):
        return False, "Password must contain at least one number"
    
    if settings.password_require_special and not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
        return False, "Password must contain at least one special character"
    
    return True, "Password meets security requirements"