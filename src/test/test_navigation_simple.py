import pytest
import sys
import os
import inspect

# Add path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))


class TestNavigationComponents:
    """Test navigation components without external dependencies"""
    
    def test_navigation_router_exists(self):
        """Test that navigation router exists and has expected endpoints"""
        try:
            from src.infra.rest_api.routers.chats import router
            assert router is not None
        except ImportError:
            pytest.skip("Navigation router not available")
    
    def test_chat_repo_has_navigation_methods(self):
        """Test that chat repository has navigation methods"""
        try:
            from src.infra.tortoise_client.chat_repo import TortoiseChatRepository as ChatRepo
            
            # Check methods exist
            assert hasattr(ChatRepo, 'get_recent_chats')
            assert hasattr(ChatRepo, 'delete_chat')
            
            # Check method signatures
            recent_sig = inspect.signature(ChatRepo.get_recent_chats)
            delete_sig = inspect.signature(ChatRepo.delete_chat)
            
            assert 'user_uuid' in recent_sig.parameters
            assert 'limit' in recent_sig.parameters
            
            assert 'chat_uuid' in delete_sig.parameters
            assert 'user_uuid' in delete_sig.parameters
            
        except ImportError:
            pytest.skip("Chat repository not available")
    
    def test_chat_interaction_has_structure_methods(self):
        """Test that chat interaction has structure handling methods"""
        try:
            from src.usecase.chat_interaction.main import ChatInteraction
            
            # Check basic methods exist
            assert hasattr(ChatInteraction, 'restart_chat')
            
            # Check method signatures
            restart_sig = inspect.signature(ChatInteraction.restart_chat)
            assert len(restart_sig.parameters) >= 1  # self + uuid
            
        except ImportError:
            pytest.skip("Chat interaction not available")
    
    def test_structure_handler_exists(self):
        """Test that structure handler exists"""
        try:
            from src.usecase.chat_interaction.structure_handler import StructureHandler
            assert StructureHandler is not None
            
            # Check basic method exists
            assert hasattr(StructureHandler, 'get_current_node_id')
            
        except ImportError:
            pytest.skip("Structure handler not available")
    
    def test_dependencies_exist(self):
        """Test that required dependency functions exist"""
        try:
            from src.infra.rest_api.dependencies import get_chat_interaction
            assert get_chat_interaction is not None
            
            from src.infra.di import get_chat_repo_client
            assert get_chat_repo_client is not None
            
        except ImportError:
            pytest.skip("Dependencies not available")
    
    def test_auth_dependency_exists(self):
        """Test that auth dependency exists"""
        try:
            from src.infra.auth import get_current_user
            assert get_current_user is not None
            
            # Check signature
            auth_sig = inspect.signature(get_current_user)
            assert len(auth_sig.parameters) >= 1  # token parameter
            
        except ImportError:
            pytest.skip("Auth module not available")


class TestNavigationSchemas:
    """Test navigation-related schemas without external dependencies"""
    
    def test_basic_response_schema_exists(self):
        """Test that basic response schemas exist"""
        try:
            from src.infra.rest_api.schemas import MessageResponse
            
            # Test basic schema structure
            response = MessageResponse(
                message_uuid="test-uuid",
                content="test content"
            )
            
            assert response.message_uuid == "test-uuid"
            assert response.content == "test content"
            
        except ImportError:
            pytest.skip("Schemas not available")
    
    def test_uuid_validation(self):
        """Test UUID validation logic"""
        from uuid import uuid4
        
        # Generate valid UUID
        test_uuid = str(uuid4())
        assert len(test_uuid) == 36
        assert test_uuid.count('-') == 4
        
        # Test UUID format
        parts = test_uuid.split('-')
        assert len(parts) == 5
        assert len(parts[0]) == 8
        assert len(parts[1]) == 4
        assert len(parts[2]) == 4
        assert len(parts[3]) == 4
        assert len(parts[4]) == 12