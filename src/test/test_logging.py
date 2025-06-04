import pytest
import logging
import json
from pathlib import Path
import sys


class TestLogging:
    def test_logger_configuration(self):
        # Act
        from src.infra.logging_config import setup_logging
        logger = setup_logging("test_logger")
        
        # Assert
        assert logger.name == "test_logger"
        assert logger.level == logging.INFO
        assert len(logger.handlers) > 0
    
    def test_logger_writes_json_format(self, tmp_path):
        # Arrange
        log_file = tmp_path / "test.log"
        
        # Act
        from src.infra.logging_config import setup_logging
        logger = setup_logging("test_json", log_file=str(log_file))
        logger.info("Test message", extra={"user_id": 123})
        
        # Assert
        assert log_file.exists()
        with open(log_file) as f:
            log_line = json.loads(f.readline())
            assert log_line["message"] == "Test message"
            assert log_line["user_id"] == 123
            assert "timestamp" in log_line
            assert log_line["level"] == "INFO"
    
    def test_logger_different_levels(self, capsys):
        # Act
        from src.infra.logging_config import setup_logging
        logger = setup_logging("test_levels", console=True)
        
        logger.debug("Debug message")
        logger.info("Info message")
        logger.warning("Warning message")
        logger.error("Error message")
        
        # Assert
        captured = capsys.readouterr()
        assert "Debug message" not in captured.out  # DEBUG should not appear at INFO level
        assert "Info message" in captured.out
        assert "Warning message" in captured.out
        assert "Error message" in captured.out
    
    def test_logger_with_exception(self, tmp_path):
        # Arrange
        log_file = tmp_path / "error.log"
        
        # Act
        from src.infra.logging_config import setup_logging
        logger = setup_logging("test_error", log_file=str(log_file))
        
        try:
            raise ValueError("Test exception")
        except ValueError:
            logger.exception("An error occurred")
        
        # Assert
        with open(log_file) as f:
            log_content = f.read()
            assert "An error occurred" in log_content
            assert "ValueError: Test exception" in log_content
            assert "Traceback" in log_content
    
    def test_request_logger_middleware(self):
        # Act
        from src.infra.logging_config import LoggingMiddleware
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        
        app = FastAPI()
        app.add_middleware(LoggingMiddleware)
        
        @app.get("/test")
        def test_endpoint():
            return {"message": "test"}
        
        client = TestClient(app)
        
        # Assert
        response = client.get("/test")
        assert response.status_code == 200
    
    def test_get_logger_singleton(self):
        # Act
        from src.infra.logging_config import get_logger
        logger1 = get_logger("test_singleton")
        logger2 = get_logger("test_singleton")
        
        # Assert
        assert logger1 is logger2  # Same instance