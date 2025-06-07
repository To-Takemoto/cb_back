"""
Integration test for Tortoise ORM with FastAPI
"""
import pytest
from fastapi.testclient import TestClient
from tortoise import Tortoise

from src.infra.rest_api.main import app


class TestTortoiseIntegration:
    """Test Tortoise ORM integration with FastAPI"""

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

    def test_user_registration_endpoint(self, client):
        """Test user registration with Tortoise ORM"""
        import time
        username = f"testuser_{int(time.time())}"
        
        response = client.post(
            "/api/v1/users",
            json={
                "username": username,
                "password": "password123"
            }
        )
        
        if response.status_code != 200:
            print(f"Error response: {response.json()}")
            
        assert response.status_code == 200
        data = response.json()
        assert "uuid" in data
        assert data["username"] == username
        assert "created_at" in data