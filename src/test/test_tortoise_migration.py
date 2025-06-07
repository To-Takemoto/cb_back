"""
TDD tests for Tortoise ORM migration
These tests should initially fail and pass after implementation
"""
import pytest
from tortoise import Tortoise
from uuid import uuid4
from datetime import datetime

from src.port.dto.user_dto import CreateUserDTO
from src.domain.entity.user_entity import UserEntity


class TestTortoiseUserRepository:
    """Test async user repository with Tortoise ORM"""

    @pytest.fixture
    async def setup_db(self):
        """Setup test database"""
        await Tortoise.init(
            db_url="sqlite://:memory:",
            modules={"models": ["src.infra.tortoise_client.models"]}
        )
        await Tortoise.generate_schemas()
        yield
        await Tortoise.close_connections()

    async def test_user_repository_exists_by_username(self, setup_db):
        """Test async exists_by_username method - should fail initially"""
        from src.infra.tortoise_client.user_repository import TortoiseUserRepository
        
        repo = TortoiseUserRepository()
        
        # This should return False for non-existent user
        exists = await repo.exists_by_username("nonexistent")
        assert exists is False
        
        # Create a user and test again
        user_dto = CreateUserDTO(username="testuser", raw_password="password123")
        await repo.save(user_dto)
        
        exists = await repo.exists_by_username("testuser")
        assert exists is True

    async def test_user_repository_save(self, setup_db):
        """Test async save method - should fail initially"""
        from src.infra.tortoise_client.user_repository import TortoiseUserRepository
        
        repo = TortoiseUserRepository()
        user_dto = CreateUserDTO(username="newuser", raw_password="password123")
        
        user_entity = await repo.save(user_dto)
        
        assert isinstance(user_entity, UserEntity)
        assert user_entity.username == "newuser"
        assert user_entity.uuid is not None
        assert user_entity.id is not None

    async def test_user_repository_get_by_name(self, setup_db):
        """Test async get_user_by_name method - should fail initially"""
        from src.infra.tortoise_client.user_repository import TortoiseUserRepository
        
        repo = TortoiseUserRepository()
        
        # Should return None for non-existent user
        user = await repo.get_user_by_name("nonexistent")
        assert user is None
        
        # Create user and test retrieval
        user_dto = CreateUserDTO(username="testuser", raw_password="password123")
        await repo.save(user_dto)
        
        user = await repo.get_user_by_name("testuser")
        assert user is not None
        assert user.name == "testuser"


class TestTortoiseChatRepository:
    """Test async chat repository with Tortoise ORM"""

    @pytest.fixture
    async def setup_db_with_user(self):
        """Setup test database with a test user"""
        await Tortoise.init(
            db_url="sqlite://:memory:",
            modules={"models": ["src.infra.tortoise_client.models"]}
        )
        await Tortoise.generate_schemas()
        
        # Create test user
        from src.infra.tortoise_client.models import User
        user = await User.create(
            uuid=str(uuid4()),
            name="testuser",
            password="hashed_password",
            created_at=datetime.utcnow()
        )
        
        yield user.id
        await Tortoise.close_connections()

    async def test_chat_repository_init_structure(self, setup_db_with_user):
        """Test async init_structure method - should create new discussion"""
        from src.infra.tortoise_client.chat_repo import TortoiseChatRepository
        from src.domain.entity.message_entity import MessageEntity, Role
        
        user_id = setup_db_with_user
        repo = TortoiseChatRepository(user_id)
        
        # Create initial message
        initial_message = MessageEntity(
            id=0,  # Will be set by repository
            uuid=str(uuid4()),
            role=Role.USER,
            content="Hello, this is a test message"
        )
        
        # Should create new chat structure
        chat_tree, saved_message = await repo.init_structure(initial_message)
        
        assert chat_tree is not None
        assert saved_message.uuid == initial_message.uuid
        assert saved_message.content == initial_message.content
        assert saved_message.role == Role.USER

    async def test_chat_repository_load_tree(self, setup_db_with_user):
        """Test async load_tree method"""
        from src.infra.tortoise_client.chat_repo import TortoiseChatRepository
        from src.domain.entity.message_entity import MessageEntity, Role
        
        user_id = setup_db_with_user
        repo = TortoiseChatRepository(user_id)
        
        # First create a structure
        initial_message = MessageEntity(
            id=0,
            uuid=str(uuid4()),
            role=Role.USER,
            content="Test message for loading"
        )
        
        chat_tree, _ = await repo.init_structure(initial_message)
        chat_uuid = chat_tree.uuid
        
        # Now load it back
        loaded_tree = await repo.load_tree(chat_uuid)
        assert loaded_tree.uuid == chat_uuid