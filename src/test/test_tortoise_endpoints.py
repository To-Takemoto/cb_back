"""
Basic integration tests for Tortoise ORM endpoints
"""
import pytest
from fastapi.testclient import TestClient

from src.infra.rest_api.main import app


class TestTortoiseEndpoints:
    """Test Tortoise ORM endpoints integration"""

    @pytest.fixture
    def client(self):
        """Setup test client"""
        with TestClient(app) as client:
            yield client

    def test_health_check(self, client):
        """Test health check endpoint"""
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"

    def test_user_registration_flow(self, client):
        """Test complete user registration flow"""
        import time
        username = f"testuser_endpoints_{int(time.time())}"
        
        response = client.post(
            "/api/v1/users",
            json={
                "username": username,
                "password": "password123"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "uuid" in data
        assert data["username"] == username
        
        # Test duplicate registration fails
        response = client.post(
            "/api/v1/users",
            json={
                "username": username,
                "password": "different123"
            }
        )
        assert response.status_code == 400

    def test_chat_creation_without_auth(self, client):
        """Test chat creation without authentication fails properly"""
        response = client.post(
            "/api/v1/chats/",
            json={
                "initial_message": "Hello",
                "system_prompt": None,
                "model_id": None
            }
        )
        # Should require authentication
        assert response.status_code == 401