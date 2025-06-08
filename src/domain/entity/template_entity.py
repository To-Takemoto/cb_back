"""
Domain entities for template management
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any
from uuid import uuid4


@dataclass
class PromptTemplate:
    """
    Prompt template entity containing template definition and metadata
    """
    name: str
    template_content: str
    user_id: int
    uuid: str = field(default_factory=lambda: str(uuid4()))
    id: Optional[int] = None
    description: Optional[str] = None
    category: Optional[str] = None
    variables: Optional[Dict[str, Any]] = None
    is_public: bool = False
    is_favorite: bool = False
    usage_count: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def increment_usage(self) -> None:
        """Increment usage count"""
        self.usage_count += 1
        self.updated_at = datetime.utcnow()

    def mark_as_favorite(self) -> None:
        """Mark template as favorite"""
        self.is_favorite = True
        self.updated_at = datetime.utcnow()

    def unmark_as_favorite(self) -> None:
        """Unmark template as favorite"""
        self.is_favorite = False
        self.updated_at = datetime.utcnow()

    def make_public(self) -> None:
        """Make template public"""
        self.is_public = True
        self.updated_at = datetime.utcnow()

    def make_private(self) -> None:
        """Make template private"""
        self.is_public = False
        self.updated_at = datetime.utcnow()

    def update_content(self, content: str) -> None:
        """Update template content"""
        self.template_content = content
        self.updated_at = datetime.utcnow()

    def update_metadata(self, name: Optional[str] = None, description: Optional[str] = None, 
                       category: Optional[str] = None, variables: Optional[Dict[str, Any]] = None) -> None:
        """Update template metadata"""
        if name is not None:
            self.name = name
        if description is not None:
            self.description = description
        if category is not None:
            self.category = category
        if variables is not None:
            self.variables = variables
        self.updated_at = datetime.utcnow()


@dataclass
class ConversationPreset:
    """
    Conversation preset entity containing model configuration and system prompt
    """
    name: str
    model_id: str
    user_id: int
    uuid: str = field(default_factory=lambda: str(uuid4()))
    id: Optional[int] = None
    description: Optional[str] = None
    temperature: str = "0.7"
    max_tokens: int = 1000
    system_prompt: Optional[str] = None
    is_favorite: bool = False
    usage_count: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def increment_usage(self) -> None:
        """Increment usage count"""
        self.usage_count += 1
        self.updated_at = datetime.utcnow()

    def mark_as_favorite(self) -> None:
        """Mark preset as favorite"""
        self.is_favorite = True
        self.updated_at = datetime.utcnow()

    def unmark_as_favorite(self) -> None:
        """Unmark preset as favorite"""
        self.is_favorite = False
        self.updated_at = datetime.utcnow()

    def update_model_settings(self, model_id: Optional[str] = None, temperature: Optional[str] = None,
                             max_tokens: Optional[int] = None) -> None:
        """Update model configuration"""
        if model_id is not None:
            self.model_id = model_id
        if temperature is not None:
            self.temperature = temperature
        if max_tokens is not None:
            self.max_tokens = max_tokens
        self.updated_at = datetime.utcnow()

    def update_system_prompt(self, system_prompt: str) -> None:
        """Update system prompt"""
        self.system_prompt = system_prompt
        self.updated_at = datetime.utcnow()

    def update_metadata(self, name: Optional[str] = None, description: Optional[str] = None) -> None:
        """Update preset metadata"""
        if name is not None:
            self.name = name
        if description is not None:
            self.description = description
        self.updated_at = datetime.utcnow()