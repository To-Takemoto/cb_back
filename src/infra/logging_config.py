import logging
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Any
import traceback
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
import time
import uuid


class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_obj = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Add extra fields
        for key, value in record.__dict__.items():
            if key not in ['name', 'msg', 'args', 'created', 'filename', 'funcName', 
                          'levelname', 'levelno', 'lineno', 'module', 'msecs', 
                          'pathname', 'process', 'processName', 'relativeCreated', 
                          'thread', 'threadName', 'getMessage', 'exc_info', 'exc_text', 
                          'stack_info']:
                log_obj[key] = value
        
        # Add exception info if present
        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)
            
        return json.dumps(log_obj)


def setup_logging(
    name: str,
    level: int = logging.INFO,
    log_file: Optional[str] = None,
    console: bool = False
) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.handlers.clear()
    
    # JSON formatter
    json_formatter = JSONFormatter()
    
    # Console handler
    if console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(json_formatter)
        logger.addHandler(console_handler)
    
    # File handler
    if log_file:
        Path(log_file).parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(json_formatter)
        logger.addHandler(file_handler)
    
    # Default to console if no handlers specified
    if not logger.handlers:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(json_formatter)
        logger.addHandler(console_handler)
    
    return logger


# Global logger instances
_loggers: Dict[str, logging.Logger] = {}


def get_logger(name: str, **kwargs) -> logging.Logger:
    if name not in _loggers:
        _loggers[name] = setup_logging(name, **kwargs)
    return _loggers[name]


class LoggingMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self.logger = get_logger("api.access")
    
    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())
        start_time = time.time()
        
        # Log request
        self.logger.info(
            "Request started",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "client": request.client.host if request.client else None,
            }
        )
        
        try:
            response = await call_next(request)
            duration = time.time() - start_time
            
            # Log response
            self.logger.info(
                "Request completed",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "duration_ms": round(duration * 1000, 2),
                }
            )
            
            return response
            
        except Exception as e:
            duration = time.time() - start_time
            self.logger.error(
                "Request failed",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "duration_ms": round(duration * 1000, 2),
                    "error": str(e),
                    "traceback": traceback.format_exc(),
                }
            )
            raise


# Initialize default loggers
app_logger = get_logger("app")
error_logger = get_logger("app.error")