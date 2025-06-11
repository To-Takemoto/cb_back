"""
Security integration helper for main.py
"""
from fastapi import FastAPI
from src.infra.config import Settings
from src.infra.security_config import SecuritySettings, get_security_middleware_config
from src.infra.rest_api.security_middleware import setup_security_middleware
import logging

logger = logging.getLogger(__name__)


def integrate_security(app: FastAPI, settings: Settings) -> None:
    """
    Integrate security configurations into the FastAPI application.
    
    This should be called in main.py after app initialization but before
    adding routers.
    
    Example usage in main.py:
        from src.infra.rest_api.security_integration import integrate_security
        
        app = FastAPI(...)
        
        # Add security before routers
        integrate_security(app, settings)
        
        # Then add routers
        app.include_router(...)
    """
    
    # Load security settings
    security_settings = SecuritySettings()
    
    # Get middleware configuration
    security_config = get_security_middleware_config(security_settings)
    
    # Apply different configurations based on environment
    if settings.environment == "production":
        logger.info("Applying production security configuration")
        
        # Update CORS for production
        app.middleware("cors").kwargs.update({
            "allow_origins": security_config["cors"]["allow_origins"],
            "allow_methods": security_config["cors"]["allow_methods"],
            "allow_headers": security_config["cors"]["allow_headers"],
            "allow_credentials": security_config["cors"]["allow_credentials"],
        })
        
        # Setup security middleware
        setup_security_middleware(
            app,
            security_headers=security_config["headers"],
            force_https=security_settings.force_https,
            trusted_hosts=security_settings.cors_allowed_origins,  # Use same domains
            log_security_events=security_settings.log_security_events
        )
        
        # Update rate limits for production
        logger.info(f"Rate limits set - Login: {security_config['rate_limit']['login']}/min, "
                   f"API: {security_config['rate_limit']['api']}/min")
        
    else:
        logger.info(f"Running in {settings.environment} mode - relaxed security settings")
        
        # Development/staging might have more relaxed settings
        # but still apply basic security headers
        basic_headers = {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "SAMEORIGIN",
            "X-XSS-Protection": "1; mode=block"
        }
        setup_security_middleware(
            app,
            security_headers=basic_headers,
            force_https=False,
            trusted_hosts=None,
            log_security_events=True
        )
    
    logger.info("Security configuration completed")


def validate_deployment_readiness() -> tuple[bool, list[str]]:
    """
    Validate that the application is ready for deployment from a security perspective.
    
    Returns:
        tuple: (is_ready, list_of_issues)
    """
    issues = []
    
    try:
        settings = Settings()
        security_settings = SecuritySettings()
        
        # Check critical settings
        if len(settings.secret_key) < 32:
            issues.append("SECRET_KEY must be at least 32 characters long")
        
        if settings.secret_key == "your-secret-key-here":
            issues.append("Default SECRET_KEY detected - must be changed for production")
        
        if not settings.openrouter_api_key:
            issues.append("OPENROUTER_API_KEY is not set")
        
        if settings.environment == "production":
            # Production-specific checks
            if not security_settings.force_https:
                issues.append("HTTPS should be forced in production")
            
            if "localhost" in security_settings.cors_allowed_origins:
                issues.append("localhost should not be in CORS allowed origins for production")
            
            if settings.log_level.upper() == "DEBUG":
                issues.append("DEBUG logging should be disabled in production")
        
    except Exception as e:
        issues.append(f"Failed to load configuration: {str(e)}")
    
    is_ready = len(issues) == 0
    return is_ready, issues


if __name__ == "__main__":
    # Run deployment readiness check
    ready, issues = validate_deployment_readiness()
    
    if ready:
        print("✅ Application is ready for deployment from a security perspective")
    else:
        print("❌ Security issues found:")
        for issue in issues:
            print(f"  - {issue}")