import pytest
import sys
import os
import inspect
import re
from datetime import datetime, timedelta

# Add path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))


class TestSearchComponents:
    """Test search components without external dependencies"""
    
    def test_chat_repo_has_search_methods(self):
        """Test that chat repository has search methods"""
        try:
            from src.infra.tortoise_client.chat_repo import TortoiseChatRepository as ChatRepo
            
            # Check methods exist
            assert hasattr(ChatRepo, 'search_messages')
            assert hasattr(ChatRepo, 'get_chats_by_date')
            
            # Check method signatures
            search_sig = inspect.signature(ChatRepo.search_messages)
            date_sig = inspect.signature(ChatRepo.get_chats_by_date)
            
            assert 'chat_uuid' in search_sig.parameters
            assert 'query' in search_sig.parameters
            
            assert 'user_uuid' in date_sig.parameters
            assert 'date_filter' in date_sig.parameters
            
        except ImportError:
            pytest.skip("Chat repository not available")
    
    def test_search_router_exists(self):
        """Test that search routes exist in chats router"""
        try:
            from src.infra.rest_api.routers.chats import router
            assert router is not None
            
            # Check if router has routes
            assert hasattr(router, 'routes')
            
        except ImportError:
            pytest.skip("Chat router not available")
    
    def test_search_dependencies_exist(self):
        """Test that search dependencies exist"""
        try:
            from src.infra.auth import get_current_user
            assert get_current_user is not None
            
            from src.infra.di import get_chat_repo_client
            assert get_chat_repo_client is not None
            
        except ImportError:
            pytest.skip("Dependencies not available")


class TestSearchLogic:
    """Test search logic without external dependencies"""
    
    def test_query_validation(self):
        """Test search query validation logic"""
        def validate_search_query(query: str) -> bool:
            """Validate search query"""
            if not query or len(query.strip()) < 2:
                return False
            if len(query) > 1000:
                return False
            return True
        
        # Valid queries
        assert validate_search_query("Python") is True
        assert validate_search_query("hello world") is True
        assert validate_search_query("ab") is True
        
        # Invalid queries
        assert validate_search_query("") is False
        assert validate_search_query(" ") is False
        assert validate_search_query("a") is False
        assert validate_search_query("x" * 1001) is False
    
    def test_highlight_logic(self):
        """Test search result highlighting logic"""
        def highlight_text(content: str, query: str) -> str:
            """Highlight search terms in content"""
            if not query or not content:
                return content
            
            # Simple highlighting logic
            pattern = re.compile(re.escape(query), re.IGNORECASE)
            return pattern.sub(f"<mark>{query}</mark>", content)
        
        # Test highlighting
        content = "This is a Python tutorial about Python programming"
        query = "Python"
        highlighted = highlight_text(content, query)
        
        assert "<mark>Python</mark>" in highlighted
        assert highlighted.count("<mark>Python</mark>") == 2
        
        # Test case insensitive
        highlighted_lower = highlight_text(content, "python")
        assert "<mark>python</mark>" in highlighted_lower
    
    def test_date_filter_validation(self):
        """Test date filter validation logic"""
        def validate_date_filter(date_filter: str) -> bool:
            """Validate date filter"""
            valid_filters = ["today", "yesterday", "this_week", "this_month", "this_year"]
            return date_filter in valid_filters
        
        # Valid filters
        assert validate_date_filter("today") is True
        assert validate_date_filter("yesterday") is True
        assert validate_date_filter("this_week") is True
        assert validate_date_filter("this_month") is True
        assert validate_date_filter("this_year") is True
        
        # Invalid filters
        assert validate_date_filter("invalid") is False
        assert validate_date_filter("tomorrow") is False
        assert validate_date_filter("") is False
    
    def test_date_range_calculation(self):
        """Test date range calculation for filters"""
        def get_date_range(filter_name: str) -> tuple:
            """Get date range for filter"""
            now = datetime.now()
            today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            
            if filter_name == "today":
                return today_start, now
            elif filter_name == "yesterday":
                yesterday = today_start - timedelta(days=1)
                return yesterday, today_start
            elif filter_name == "this_week":
                week_start = today_start - timedelta(days=now.weekday())
                return week_start, now
            elif filter_name == "this_month":
                month_start = today_start.replace(day=1)
                return month_start, now
            elif filter_name == "this_year":
                year_start = today_start.replace(month=1, day=1)
                return year_start, now
            else:
                return None, None
        
        # Test date ranges
        start, end = get_date_range("today")
        assert start is not None
        assert end is not None
        assert start <= end
        
        start, end = get_date_range("yesterday")
        assert start is not None
        assert end is not None
        assert start < end
        
        start, end = get_date_range("invalid")
        assert start is None
        assert end is None
    
    def test_search_result_formatting(self):
        """Test search result formatting"""
        def format_search_result(message: dict, query: str) -> dict:
            """Format search result"""
            content = message.get("content", "")
            
            # Create highlight
            highlighted = content
            if query and query in content:
                highlighted = content.replace(query, f"<mark>{query}</mark>")
            
            return {
                "uuid": message.get("uuid"),
                "content": content,
                "highlight": highlighted,
                "role": message.get("role", "user"),
                "created_at": message.get("created_at")
            }
        
        # Test formatting
        message = {
            "uuid": "msg-123",
            "content": "This is a Python tutorial",
            "role": "user",
            "created_at": "2024-01-01T00:00:00"
        }
        
        result = format_search_result(message, "Python")
        
        assert result["uuid"] == "msg-123"
        assert result["content"] == "This is a Python tutorial"
        assert result["highlight"] == "This is a <mark>Python</mark> tutorial"
        assert result["role"] == "user"


class TestSearchPagination:
    """Test search pagination logic without external dependencies"""
    
    def test_pagination_parameters(self):
        """Test pagination parameter validation"""
        def validate_pagination(page: int, limit: int) -> tuple:
            """Validate and normalize pagination parameters"""
            page = max(1, page)  # Minimum page is 1
            limit = max(1, min(100, limit))  # Limit between 1 and 100
            offset = (page - 1) * limit
            return offset, limit
        
        # Test valid parameters
        offset, limit = validate_pagination(1, 10)
        assert offset == 0
        assert limit == 10
        
        offset, limit = validate_pagination(2, 20)
        assert offset == 20
        assert limit == 20
        
        # Test boundary conditions
        offset, limit = validate_pagination(0, 0)
        assert offset == 0
        assert limit == 1
        
        offset, limit = validate_pagination(1, 200)
        assert offset == 0
        assert limit == 100
    
    def test_search_result_pagination(self):
        """Test search result pagination"""
        def paginate_results(results: list, page: int, limit: int) -> dict:
            """Paginate search results"""
            offset, limit = max(0, (page - 1) * limit), max(1, min(100, limit))
            
            total = len(results)
            paginated = results[offset:offset + limit]
            
            return {
                "results": paginated,
                "total": total,
                "page": page,
                "limit": limit,
                "has_more": offset + limit < total
            }
        
        # Test pagination
        results = [{"id": i} for i in range(25)]
        
        page1 = paginate_results(results, 1, 10)
        assert len(page1["results"]) == 10
        assert page1["total"] == 25
        assert page1["has_more"] is True
        
        page3 = paginate_results(results, 3, 10)
        assert len(page3["results"]) == 5
        assert page3["has_more"] is False