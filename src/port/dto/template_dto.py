"""
Data Transfer Objects for template operations
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any


@dataclass
class PromptTemplateDto:
    """DTO for prompt template data"""
    name: str
    template_content: str
    user_id: int
    uuid: str
    id: Optional[int] = None
    description: Optional[str] = None
    category: Optional[str] = None
    variables: Optional[Dict[str, Any]] = None
    is_public: bool = False
    is_favorite: bool = False
    usage_count: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@dataclass
class ConversationPresetDto:
    """DTO for conversation preset data"""
    name: str
    model_id: str
    user_id: int
    uuid: str
    id: Optional[int] = None
    description: Optional[str] = None
    temperature: str = "0.7"
    max_tokens: int = 1000
    system_prompt: Optional[str] = None
    is_favorite: bool = False
    usage_count: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@dataclass
class TemplateSearchCriteria:
    """Search criteria for templates"""
    user_id: Optional[int] = None
    category: Optional[str] = None
    is_public: Optional[bool] = None
    is_favorite: Optional[bool] = None
    search_text: Optional[str] = None
    limit: Optional[int] = None
    offset: Optional[int] = None


@dataclass
class PresetSearchCriteria:
    """Search criteria for presets"""
    user_id: Optional[int] = None
    model_id: Optional[str] = None
    is_favorite: Optional[bool] = None
    search_text: Optional[str] = None
    limit: Optional[int] = None
    offset: Optional[int] = None