import pytest
from uuid import uuid4
from datetime import datetime, timedelta, date
from fastapi.testclient import TestClient


class TestSearchAndFilter:
    @pytest.fixture
    def client(self):
        from src.infra.rest_api.main import app
        return TestClient(app)
    
    @pytest.fixture
    def auth_headers(self, monkeypatch):
        """Mock authentication headers"""
        def mock_get_current_user(token):
            return "test-user-uuid"
        
        monkeypatch.setattr("src.infra.auth.get_current_user", mock_get_current_user)
        return {"Authorization": "Bearer test-token"}
    
    @pytest.fixture
    def mock_chat_repo(self, monkeypatch):
        """Mock chat repository with search capabilities"""
        class MockChatRepo:
            def __init__(self):
                self.messages = [
                    {
                        "uuid": str(uuid4()),
                        "chat_uuid": str(uuid4()),
                        "content": "How to use Python decorators?",
                        "role": "user",
                        "created_at": datetime.now() - timedelta(hours=1)
                    },
                    {
                        "uuid": str(uuid4()),
                        "chat_uuid": str(uuid4()),
                        "content": "Explain machine learning concepts",
                        "role": "user",
                        "created_at": datetime.now() - timedelta(days=1)
                    },
                    {
                        "uuid": str(uuid4()),
                        "chat_uuid": str(uuid4()),
                        "content": "Python async/await tutorial",
                        "role": "user",
                        "created_at": datetime.now() - timedelta(days=2)
                    }
                ]
            
            def search_messages(self, chat_uuid: str, query: str):
                results = []
                for msg in self.messages:
                    if msg["chat_uuid"] == chat_uuid and query.lower() in msg["content"].lower():
                        results.append({
                            "uuid": msg["uuid"],
                            "content": msg["content"],
                            "role": msg["role"],
                            "created_at": msg["created_at"].isoformat(),
                            "highlight": self._highlight_text(msg["content"], query)
                        })
                return results
            
            def _highlight_text(self, text: str, query: str):
                # Simple highlight by wrapping matched text
                import re
                pattern = re.compile(re.escape(query), re.IGNORECASE)
                return pattern.sub(f"<mark>{query}</mark>", text)
            
            def get_chats_by_date(self, user_uuid: str, date_filter: str):
                today = datetime.now().date()
                
                if date_filter == "today":
                    start_date = today
                elif date_filter == "yesterday":
                    start_date = today - timedelta(days=1)
                elif date_filter == "week":
                    start_date = today - timedelta(days=7)
                elif date_filter == "month":
                    start_date = today - timedelta(days=30)
                else:
                    return []
                
                filtered = []
                for msg in self.messages:
                    if msg["created_at"].date() >= start_date:
                        filtered.append({
                            "chat_uuid": msg["chat_uuid"],
                            "last_message": msg["content"],
                            "created_at": msg["created_at"].isoformat()
                        })
                
                return filtered
        
        mock_repo = MockChatRepo()
        monkeypatch.setattr("src.infra.di.get_chat_repo_client", lambda: mock_repo)
        return mock_repo
    
    def test_search_messages_in_chat(self, client, auth_headers, mock_chat_repo):
        # Arrange
        chat_uuid = mock_chat_repo.messages[0]["chat_uuid"]
        
        # Act
        response = client.get(
            f"/api/v1/chats/{chat_uuid}/search?q=Python",
            headers=auth_headers
        )
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data["results"]) >= 1
        assert "Python" in data["results"][0]["content"]
        assert "<mark>Python</mark>" in data["results"][0]["highlight"]
    
    def test_search_no_results(self, client, auth_headers, mock_chat_repo):
        # Arrange
        chat_uuid = mock_chat_repo.messages[0]["chat_uuid"]
        
        # Act
        response = client.get(
            f"/api/v1/chats/{chat_uuid}/search?q=NonexistentKeyword",
            headers=auth_headers
        )
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data["results"]) == 0
    
    def test_filter_chats_by_date_today(self, client, auth_headers, mock_chat_repo):
        # Act
        response = client.get(
            "/api/v1/chats?date=today",
            headers=auth_headers
        )
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data["chats"]) >= 1
        
        # Verify all results are from today
        for chat in data["chats"]:
            created_date = datetime.fromisoformat(chat["created_at"]).date()
            assert created_date == date.today()
    
    def test_filter_chats_by_date_week(self, client, auth_headers, mock_chat_repo):
        # Act
        response = client.get(
            "/api/v1/chats?date=week",
            headers=auth_headers
        )
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data["chats"]) >= 2
        
        # Verify all results are from the last week
        week_ago = date.today() - timedelta(days=7)
        for chat in data["chats"]:
            created_date = datetime.fromisoformat(chat["created_at"]).date()
            assert created_date >= week_ago
    
    def test_invalid_date_filter(self, client, auth_headers):
        # Act
        response = client.get(
            "/api/v1/chats?date=invalid",
            headers=auth_headers
        )
        
        # Assert
        assert response.status_code == 400
        data = response.json()
        assert "Invalid date filter" in data["detail"]