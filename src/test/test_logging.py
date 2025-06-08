import pytest
import logging
import json
import sys
import os
from pathlib import Path

# Add path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))


class TestLogging:
    """Test logging functions without external dependencies"""
    
    def test_logger_configuration(self):
        """Test basic logger setup and configuration"""
        from src.infra.logging_config import setup_logging
        
        logger = setup_logging("test_logger")
        
        assert logger.name == "test_logger"
        assert logger.level == logging.INFO
        assert len(logger.handlers) > 0
    
    def test_logger_writes_json_format(self, tmp_path):
        """Test JSON log format writing"""
        log_file = tmp_path / "test.log"
        
        from src.infra.logging_config import setup_logging
        logger = setup_logging("test_json", log_file=str(log_file))
        logger.info("Test message", extra={"user_id": 123})
        
        assert log_file.exists()
        with open(log_file) as f:
            log_line = json.loads(f.readline())
            assert log_line["message"] == "Test message"
            assert log_line["user_id"] == 123
            assert "timestamp" in log_line
            assert log_line["level"] == "INFO"
    
    def test_logger_different_levels(self, capsys):
        """Test different logging levels"""
        from src.infra.logging_config import setup_logging
        logger = setup_logging("test_levels", console=True)
        
        logger.debug("Debug message")
        logger.info("Info message")
        logger.warning("Warning message")
        logger.error("Error message")
        
        captured = capsys.readouterr()
        # DEBUG should not appear at INFO level
        assert "Debug message" not in captured.out
        assert "Info message" in captured.out
        assert "Warning message" in captured.out
        assert "Error message" in captured.out
    
    def test_logger_with_exception(self, tmp_path):
        """Test exception logging with traceback"""
        log_file = tmp_path / "error.log"
        
        from src.infra.logging_config import setup_logging
        logger = setup_logging("test_error", log_file=str(log_file))
        
        try:
            raise ValueError("Test exception")
        except ValueError:
            logger.exception("An error occurred")
        
        with open(log_file) as f:
            log_content = f.read()
            assert "An error occurred" in log_content
            assert "ValueError: Test exception" in log_content
            assert "Traceback" in log_content
    
    def test_get_logger_singleton(self):
        """Test logger singleton behavior"""
        from src.infra.logging_config import get_logger
        
        logger1 = get_logger("test_singleton")
        logger2 = get_logger("test_singleton")
        
        # Same instance should be returned
        assert logger1 is logger2
    
    def test_logger_file_and_console_output(self, tmp_path, capsys):
        """Test logger output to both file and console"""
        log_file = tmp_path / "test_combined.log"
        
        from src.infra.logging_config import setup_logging
        logger = setup_logging("test_combined", log_file=str(log_file), console=True)
        
        test_message = "Test combined output"
        logger.info(test_message)
        
        # Check file output
        assert log_file.exists()
        with open(log_file) as f:
            log_content = f.read()
            assert test_message in log_content
        
        # Check console output
        captured = capsys.readouterr()
        assert test_message in captured.out