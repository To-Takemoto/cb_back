"""
Security middleware for FastAPI application.
"""
from typing import Callable, Dict
from fastapi import FastAPI, Request, Response
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
import logging

logger = logging.getLogger(__name__)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses."""
    
    def __init__(self, app, headers: Dict[str, str]):
        super().__init__(app)
        self.headers = headers
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        
        # Add security headers
        for header, value in self.headers.items():
            response.headers[header] = value
        
        return response


class HTTPSRedirectMiddleware(BaseHTTPMiddleware):
    """Redirect HTTP to HTTPS in production."""
    
    def __init__(self, app, force_https: bool = True):
        super().__init__(app)
        self.force_https = force_https
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if self.force_https and request.url.scheme == "http":
            # Skip redirect for health checks
            if request.url.path in ["/health", "/ready"]:
                return await call_next(request)
            
            url = request.url.replace(scheme="https")
            return Response(
                content=f"Redirecting to {url}",
                status_code=301,
                headers={"Location": str(url)}
            )
        
        return await call_next(request)


class AuditLogMiddleware(BaseHTTPMiddleware):
    """Log security-relevant events."""
    
    def __init__(self, app, log_security_events: bool = True):
        super().__init__(app)
        self.log_security_events = log_security_events
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if not self.log_security_events:
            return await call_next(request)
        
        # Log request details
        user_id = request.headers.get("X-User-ID", "anonymous")
        logger.info(
            "Security audit",
            extra={
                "event": "api_request",
                "method": request.method,
                "path": request.url.path,
                "user_id": user_id,
                "client_ip": request.client.host if request.client else "unknown",
                "user_agent": request.headers.get("User-Agent", "unknown")
            }
        )
        
        response = await call_next(request)
        
        # Log response status
        if response.status_code >= 400:
            logger.warning(
                "Security audit - error response",
                extra={
                    "event": "api_error",
                    "status_code": response.status_code,
                    "method": request.method,
                    "path": request.url.path,
                    "user_id": user_id
                }
            )
        
        return response


def setup_security_middleware(
    app: FastAPI,
    security_headers: Dict[str, str],
    force_https: bool = False,
    trusted_hosts: list = None,
    log_security_events: bool = True
) -> None:
    """Setup all security middleware for the application."""
    
    # Add security headers middleware
    app.add_middleware(SecurityHeadersMiddleware, headers=security_headers)
    
    # Add HTTPS redirect middleware (should be early in the chain)
    if force_https:
        app.add_middleware(HTTPSRedirectMiddleware, force_https=force_https)
    
    # Add trusted host middleware
    if trusted_hosts:
        app.add_middleware(TrustedHostMiddleware, allowed_hosts=trusted_hosts)
    
    # Add audit logging middleware
    app.add_middleware(AuditLogMiddleware, log_security_events=log_security_events)
    
    logger.info("Security middleware configured successfully")