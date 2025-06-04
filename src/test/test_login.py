import pytest
from fastapi.testclient import TestClient
from src.infra.auth import get_password_hash


class TestLogin:
    @pytest.fixture
    def client(self):
        from src.infra.rest_api.main import app
        return TestClient(app)
    
    @pytest.fixture
    def test_user(self):
        return {
            "username": "testuser",
            "password": "testpassword123",
            "hashed_password": get_password_hash("testpassword123")
        }
    
    def test_login_successful(self, client, test_user, monkeypatch):
        # Mock user repository to return test user
        def mock_get_user_by_name(username):
            if username == test_user["username"]:
                from src.port.dto.user_dto import UserDTO
                return UserDTO(
                    id=1,
                    uuid="test-uuid",
                    name=test_user["username"],
                    password=test_user["hashed_password"]
                )
            return None
        
        # Apply mock to DI container
        def mock_get_user_repository():
            class MockUserRepository:
                def get_user_by_name(self, username):
                    return mock_get_user_by_name(username)
                def get_all_users(self):
                    return []
            return MockUserRepository()
        
        monkeypatch.setattr("src.infra.di.get_user_repository", mock_get_user_repository)
        
        # Act
        response = client.post(
            "/api/v1/auth/login",
            data={
                "username": test_user["username"],
                "password": test_user["password"]
            }
        )
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
    
    def test_login_invalid_username(self, client, monkeypatch):
        # Mock user repository to return None
        monkeypatch.setattr("src.infra.rest_api.routers.auth.user_repository.get_user_by_name", lambda x: None)
        
        # Act
        response = client.post(
            "/api/v1/auth/login",
            data={
                "username": "nonexistent",
                "password": "password"
            }
        )
        
        # Assert
        assert response.status_code == 401
        assert response.json()["detail"] == "Incorrect username or password"
    
    def test_login_invalid_password(self, client, test_user, monkeypatch):
        # Mock user repository to return test user
        def mock_get_user_by_name(username):
            if username == test_user["username"]:
                from src.port.dto.user_dto import UserDTO
                return UserDTO(
                    id=1,
                    uuid="test-uuid",
                    name=test_user["username"],
                    password=test_user["hashed_password"]
                )
            return None
        
        def mock_get_user_repository():
            class MockUserRepository:
                def get_user_by_name(self, username):
                    return mock_get_user_by_name(username)
                def get_all_users(self):
                    return []
            return MockUserRepository()
        
        monkeypatch.setattr("src.infra.di.get_user_repository", mock_get_user_repository)
        
        # Act
        response = client.post(
            "/api/v1/auth/login",
            data={
                "username": test_user["username"],
                "password": "wrongpassword"
            }
        )
        
        # Assert
        assert response.status_code == 401
        assert response.json()["detail"] == "Incorrect username or password"
    
    def test_login_missing_fields(self, client):
        # Act - Missing password
        response = client.post(
            "/api/v1/auth/login",
            data={"username": "testuser"}
        )
        
        # Assert
        assert response.status_code == 422  # Validation error
    
    def test_protected_endpoint_with_token(self, client, test_user, monkeypatch):
        # Mock user repository
        def mock_get_user_by_name(username):
            if username == test_user["username"]:
                from src.port.dto.user_dto import UserDTO
                return UserDTO(
                    id=1,
                    uuid="test-uuid",
                    name=test_user["username"],
                    password=test_user["hashed_password"]
                )
            return None
        
        def mock_get_user_repository():
            class MockUserRepository:
                def get_user_by_name(self, username):
                    return mock_get_user_by_name(username)
                def get_all_users(self):
                    if mock_get_user_by_name(test_user["username"]):
                        from src.port.dto.user_dto import UserDTO
                        return [UserDTO(
                            id=1,
                            uuid="test-uuid",
                            name=test_user["username"],
                            password=test_user["hashed_password"]
                        )]
                    return []
            return MockUserRepository()
        
        monkeypatch.setattr("src.infra.di.get_user_repository", mock_get_user_repository)
        
        # Login first
        login_response = client.post(
            "/api/v1/auth/login",
            data={
                "username": test_user["username"],
                "password": test_user["password"]
            }
        )
        token = login_response.json()["access_token"]
        
        # Access protected endpoint
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        # Assert
        assert response.status_code == 200
        assert response.json()["username"] == test_user["username"]
    
    def test_protected_endpoint_without_token(self, client):
        # Act
        response = client.get("/api/v1/auth/me")
        
        # Assert
        assert response.status_code == 401
        assert response.json()["detail"] == "Not authenticated"