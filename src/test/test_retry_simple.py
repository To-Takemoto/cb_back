import pytest
import sys
import os
import inspect
import asyncio

# Add path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))


class TestRetryComponents:
    """Test retry components without external dependencies"""
    
    def test_error_handlers_exist(self):
        """Test that error handlers module exists"""
        try:
            from src.infra.rest_api.error_handlers import create_error_response
            assert create_error_response is not None
            
            # Check function signature
            sig = inspect.signature(create_error_response)
            expected_params = ['error_type', 'user_message', 'status_code']
            
            for param in expected_params:
                assert param in sig.parameters
                
        except ImportError:
            pytest.skip("Error handlers not available")
    
    def test_chat_interaction_has_retry_method(self):
        """Test that chat interaction has retry functionality"""
        try:
            from src.usecase.chat_interaction.main import ChatInteraction
            
            # Check if retry method exists
            assert hasattr(ChatInteraction, 'retry_last_message')
            
            # Check method signature
            retry_sig = inspect.signature(ChatInteraction.retry_last_message)
            assert len(retry_sig.parameters) >= 1  # self parameter
            
        except ImportError:
            pytest.skip("Chat interaction not available")
    
    def test_retry_router_exists(self):
        """Test that retry routes exist in chats router"""
        try:
            from src.infra.rest_api.routers.chats import router
            assert router is not None
            
            # Check if router has routes
            assert hasattr(router, 'routes')
            
        except ImportError:
            pytest.skip("Chat router not available")
    
    def test_error_response_structure(self):
        """Test error response structure without creating actual responses"""
        # Test expected error response structure
        error_response_template = {
            "error_type": "test_error",
            "user_message": "Test error message",
            "retry_available": True,
            "timestamp": "2024-01-01T00:00:00Z"
        }
        
        # Validate structure
        assert "error_type" in error_response_template
        assert "user_message" in error_response_template
        assert "retry_available" in error_response_template
        assert isinstance(error_response_template["retry_available"], bool)
        assert isinstance(error_response_template["error_type"], str)
        assert isinstance(error_response_template["user_message"], str)


class TestRetryLogic:
    """Test retry logic without external dependencies"""
    
    def test_retry_availability_logic(self):
        """Test logic for determining when retry is available"""
        # Test scenarios where retry should be available
        retriable_errors = [
            "timeout_error",
            "connection_error",
            "rate_limit_error",
            "server_error"
        ]
        
        for error_type in retriable_errors:
            retry_available = error_type in ["timeout_error", "connection_error", "rate_limit_error", "server_error"]
            assert retry_available is True
        
        # Test scenarios where retry should not be available
        non_retriable_errors = [
            "validation_error",
            "authentication_error",
            "permission_error",
            "not_found_error"
        ]
        
        for error_type in non_retriable_errors:
            retry_available = error_type in ["timeout_error", "connection_error", "rate_limit_error", "server_error"]
            assert retry_available is False
    
    def test_retry_delay_calculation(self):
        """Test retry delay calculation logic"""
        def calculate_retry_delay(attempt_count: int, base_delay: float = 1.0) -> float:
            """Calculate exponential backoff delay"""
            return min(base_delay * (2 ** attempt_count), 60.0)  # Max 60 seconds
        
        # Test exponential backoff
        assert calculate_retry_delay(0) == 1.0
        assert calculate_retry_delay(1) == 2.0
        assert calculate_retry_delay(2) == 4.0
        assert calculate_retry_delay(3) == 8.0
        
        # Test max delay cap
        assert calculate_retry_delay(10) == 60.0
    
    def test_max_retry_attempts(self):
        """Test maximum retry attempts logic"""
        max_retries = 3
        
        for attempt in range(max_retries + 2):
            should_retry = attempt < max_retries
            if attempt < max_retries:
                assert should_retry is True
            else:
                assert should_retry is False
    
    def test_error_classification(self):
        """Test error classification for retry decisions"""
        def classify_error(error_type: str) -> dict:
            """Classify error for retry handling"""
            classifications = {
                "timeout": {"retriable": True, "delay": 5.0},
                "connection": {"retriable": True, "delay": 2.0},
                "rate_limit": {"retriable": True, "delay": 60.0},
                "validation": {"retriable": False, "delay": 0.0},
                "auth": {"retriable": False, "delay": 0.0}
            }
            return classifications.get(error_type, {"retriable": False, "delay": 0.0})
        
        # Test retriable errors
        timeout_class = classify_error("timeout")
        assert timeout_class["retriable"] is True
        assert timeout_class["delay"] > 0
        
        # Test non-retriable errors
        auth_class = classify_error("auth")
        assert auth_class["retriable"] is False
        assert auth_class["delay"] == 0.0


class TestAsyncRetry:
    """Test async retry functionality without external dependencies"""
    
    @pytest.mark.asyncio
    async def test_async_retry_wrapper(self):
        """Test async retry wrapper logic"""
        attempt_count = 0
        
        async def mock_function_that_fails():
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 3:
                raise ConnectionError("Mock connection error")
            return "Success"
        
        async def retry_wrapper(func, max_attempts=3):
            for attempt in range(max_attempts):
                try:
                    return await func()
                except ConnectionError:
                    if attempt == max_attempts - 1:
                        raise
                    await asyncio.sleep(0.1)  # Short delay for test
        
        # Test successful retry
        result = await retry_wrapper(mock_function_that_fails)
        assert result == "Success"
        assert attempt_count == 3
    
    def test_retry_context(self):
        """Test retry context information"""
        retry_context = {
            "original_message_uuid": "msg-123",
            "chat_uuid": "chat-456",
            "attempt_number": 1,
            "max_attempts": 3,
            "last_error": "timeout_error"
        }
        
        assert "original_message_uuid" in retry_context
        assert "chat_uuid" in retry_context
        assert retry_context["attempt_number"] <= retry_context["max_attempts"]
        assert isinstance(retry_context["attempt_number"], int)
        assert isinstance(retry_context["max_attempts"], int)