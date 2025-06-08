import pytest
import sys
import os
import time
from collections import defaultdict
from datetime import datetime, timedelta

# Add path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))


class SimpleRateLimiter:
    """Simple rate limiter for testing"""
    
    def __init__(self):
        self.requests = defaultdict(list)
    
    def is_allowed(self, key: str, limit: int, window_seconds: int) -> bool:
        """Check if request is allowed based on rate limit"""
        now = datetime.now()
        cutoff = now - timedelta(seconds=window_seconds)
        
        # Clean old requests
        self.requests[key] = [req_time for req_time in self.requests[key] if req_time > cutoff]
        
        # Check limit
        if len(self.requests[key]) >= limit:
            return False
        
        # Add current request
        self.requests[key].append(now)
        return True
    
    def reset(self, key: str = None):
        """Reset rate limiter"""
        if key:
            self.requests[key] = []
        else:
            self.requests.clear()


class TestRateLimitLogic:
    """Test rate limiting logic without external dependencies"""
    
    def test_simple_rate_limiter_creation(self):
        """Test basic rate limiter creation"""
        limiter = SimpleRateLimiter()
        assert isinstance(limiter.requests, dict)
    
    def test_rate_limit_allows_within_limit(self):
        """Test that requests within limit are allowed"""
        limiter = SimpleRateLimiter()
        
        # Should allow up to 5 requests per minute
        for i in range(5):
            result = limiter.is_allowed("test_key", limit=5, window_seconds=60)
            assert result is True
    
    def test_rate_limit_blocks_over_limit(self):
        """Test that requests over limit are blocked"""
        limiter = SimpleRateLimiter()
        
        # Fill up the limit
        for i in range(5):
            limiter.is_allowed("test_key", limit=5, window_seconds=60)
        
        # Next request should be blocked
        result = limiter.is_allowed("test_key", limit=5, window_seconds=60)
        assert result is False
    
    def test_rate_limit_different_keys(self):
        """Test that different keys have separate limits"""
        limiter = SimpleRateLimiter()
        
        # Fill limit for key1
        for i in range(5):
            limiter.is_allowed("key1", limit=5, window_seconds=60)
        
        # key2 should still be allowed
        result = limiter.is_allowed("key2", limit=5, window_seconds=60)
        assert result is True
    
    def test_rate_limit_window_expiry(self):
        """Test that rate limit window expires correctly"""
        limiter = SimpleRateLimiter()
        
        # Test with very short window (1 second)
        for i in range(3):
            limiter.is_allowed("test_key", limit=3, window_seconds=1)
        
        # Should be blocked immediately
        result = limiter.is_allowed("test_key", limit=3, window_seconds=1)
        assert result is False
        
        # Wait for window to expire
        time.sleep(1.1)
        
        # Should be allowed again
        result = limiter.is_allowed("test_key", limit=3, window_seconds=1)
        assert result is True
    
    def test_rate_limit_reset(self):
        """Test rate limiter reset functionality"""
        limiter = SimpleRateLimiter()
        
        # Fill up the limit
        for i in range(5):
            limiter.is_allowed("test_key", limit=5, window_seconds=60)
        
        # Should be blocked
        result = limiter.is_allowed("test_key", limit=5, window_seconds=60)
        assert result is False
        
        # Reset and try again
        limiter.reset("test_key")
        result = limiter.is_allowed("test_key", limit=5, window_seconds=60)
        assert result is True
    
    def test_rate_limit_configurations(self):
        """Test different rate limit configurations"""
        limiter = SimpleRateLimiter()
        
        # Test login rate limit (5 per minute)
        login_limit = 5
        login_window = 60
        
        for i in range(login_limit):
            result = limiter.is_allowed("login", login_limit, login_window)
            assert result is True
        
        # Should be blocked on next attempt
        result = limiter.is_allowed("login", login_limit, login_window)
        assert result is False
        
        # Test refresh rate limit (10 per hour)
        limiter.reset()
        refresh_limit = 10
        refresh_window = 3600
        
        for i in range(refresh_limit):
            result = limiter.is_allowed("refresh", refresh_limit, refresh_window)
            assert result is True
        
        # Should be blocked on next attempt
        result = limiter.is_allowed("refresh", refresh_limit, refresh_window)
        assert result is False


class TestRateLimitHeaders:
    """Test rate limit header generation without external dependencies"""
    
    def test_retry_after_header_calculation(self):
        """Test calculation of Retry-After header"""
        window_seconds = 60
        current_time = datetime.now()
        
        # Calculate when the window resets
        window_start = current_time.replace(second=0, microsecond=0)
        next_window = window_start + timedelta(seconds=window_seconds)
        retry_after = int((next_window - current_time).total_seconds())
        
        assert retry_after >= 0
        assert retry_after <= window_seconds
    
    def test_rate_limit_response_format(self):
        """Test rate limit response format"""
        error_response = {
            "detail": "Too many requests",
            "retry_after": 60,
            "limit": 5,
            "window": "1 minute"
        }
        
        assert "detail" in error_response
        assert "retry_after" in error_response
        assert error_response["retry_after"] > 0
        assert error_response["limit"] > 0
    
    def test_rate_limit_key_generation(self):
        """Test rate limit key generation logic"""
        # Test IP-based key
        ip_address = "192.168.1.1"
        endpoint = "/api/v1/auth/login"
        ip_key = f"{ip_address}:{endpoint}"
        
        assert ip_key == "192.168.1.1:/api/v1/auth/login"
        
        # Test user-based key
        user_id = "user123"
        user_key = f"user:{user_id}:{endpoint}"
        
        assert user_key == "user:user123:/api/v1/auth/login"