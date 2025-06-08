import pytest
import sys
import os

# Add path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from src.domain.entity.model_entity import ModelEntity, ModelArchitecture, ModelPricing


class TestModelEntity:
    """Test model entities and validation without external dependencies"""
    
    def test_model_entity_creation_full(self):
        """Test complete model entity creation"""
        architecture = ModelArchitecture(
            input_modalities=["text"],
            output_modalities=["text"],
            tokenizer="GPT"
        )
        pricing = ModelPricing(prompt="0.001", completion="0.002")
        
        model = ModelEntity(
            id="test/model",
            name="Test Model",
            created=1234567890,
            description="A test model",
            architecture=architecture,
            pricing=pricing,
            context_length=4096
        )
        
        assert model.id == "test/model"
        assert model.name == "Test Model"
        assert model.created == 1234567890
        assert model.description == "A test model"
        assert model.architecture == architecture
        assert model.pricing == pricing
        assert model.context_length == 4096
    
    def test_model_entity_minimal(self):
        """Test minimal model entity creation"""
        model = ModelEntity(
            id="test/model",
            name="Test Model",
            created=1234567890
        )
        
        assert model.id == "test/model"
        assert model.name == "Test Model"
        assert model.created == 1234567890
        assert model.description is None
        assert model.architecture is None
        assert model.pricing is None
        assert model.context_length is None
    
    def test_model_architecture_creation(self):
        """Test model architecture creation"""
        architecture = ModelArchitecture(
            input_modalities=["text", "image"],
            output_modalities=["text"],
            tokenizer="GPT"
        )
        
        assert architecture.input_modalities == ["text", "image"]
        assert architecture.output_modalities == ["text"]
        assert architecture.tokenizer == "GPT"
    
    def test_model_pricing_creation(self):
        """Test model pricing creation"""
        pricing = ModelPricing(
            prompt="0.001",
            completion="0.002"
        )
        
        assert pricing.prompt == "0.001"
        assert pricing.completion == "0.002"
    
    def test_model_entity_with_different_types(self):
        """Test model entity with various data types"""
        model = ModelEntity(
            id="anthropic/claude-3",
            name="Claude 3",
            created=1709251200,
            description="Advanced AI model",
            context_length=200000
        )
        
        assert isinstance(model.id, str)
        assert isinstance(model.name, str)
        assert isinstance(model.created, int)
        assert isinstance(model.description, str)
        assert isinstance(model.context_length, int)


class TestModelValidation:
    """Test model validation logic without external dependencies"""
    
    def test_validate_model_id_in_list(self):
        """Test model ID validation against a list"""
        models = [
            ModelEntity(id="gpt-3.5", name="GPT-3.5", created=123),
            ModelEntity(id="gpt-4", name="GPT-4", created=456)
        ]
        
        # Valid model ID
        assert any(model.id == "gpt-3.5" for model in models)
        # Invalid model ID
        assert not any(model.id == "invalid-model" for model in models)
    
    def test_model_entity_equality(self):
        """Test model entity equality comparison"""
        model1 = ModelEntity(
            id="test/model",
            name="Test Model",
            created=1234567890
        )
        model2 = ModelEntity(
            id="test/model",
            name="Test Model",
            created=1234567890
        )
        model3 = ModelEntity(
            id="different/model",
            name="Different Model",
            created=1234567890
        )
        
        # Same models should be equal
        assert model1.id == model2.id
        # Different models should not be equal
        assert model1.id != model3.id
    
    def test_model_pricing_validation(self):
        """Test model pricing validation"""
        # Valid pricing
        pricing = ModelPricing(prompt="0.001", completion="0.002")
        assert pricing.prompt == "0.001"
        assert pricing.completion == "0.002"
        
        # Test numeric conversion if needed
        prompt_float = float(pricing.prompt)
        completion_float = float(pricing.completion)
        assert prompt_float == 0.001
        assert completion_float == 0.002
    
    def test_model_architecture_validation(self):
        """Test model architecture validation"""
        # Valid architecture
        arch = ModelArchitecture(
            input_modalities=["text"],
            output_modalities=["text"],
            tokenizer="GPT"
        )
        
        assert "text" in arch.input_modalities
        assert "text" in arch.output_modalities
        assert arch.tokenizer == "GPT"
        
        # Multimodal architecture
        multimodal = ModelArchitecture(
            input_modalities=["text", "image", "audio"],
            output_modalities=["text", "image"],
            tokenizer="Custom"
        )
        
        assert len(multimodal.input_modalities) == 3
        assert len(multimodal.output_modalities) == 2