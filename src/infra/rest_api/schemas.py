from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Annotated
import re

class ChatCreateRequest(BaseModel):
    initial_message: Optional[Annotated[str, Field(max_length=4000)]] = None
    model_id: Optional[str] = None
    system_prompt: Optional[Annotated[str, Field(max_length=2000)]] = None
    
    @field_validator('initial_message')
    @classmethod
    def validate_initial_message(cls, v):
        if v is not None and not v.strip():
            return None
        return v
    
    @field_validator('system_prompt')
    @classmethod
    def validate_system_prompt(cls, v):
        if v is not None and not v.strip():
            return None
        return v

class ChatCreateResponse(BaseModel):
    chat_uuid: Annotated[str, Field(pattern=r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$')]

class MessageRequest(BaseModel):
    content: Annotated[str, Field(min_length=1, max_length=4000)]
    parent_message_uuid: Optional[Annotated[str, Field(pattern=r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$')]] = None
    model_id: Optional[str] = None
    
    @field_validator('content')
    @classmethod
    def validate_content(cls, v):
        if not v.strip():
            raise ValueError('Message content cannot be empty or whitespace only')
        return v.strip()

class MessageResponse(BaseModel):
    message_uuid: str
    content: str
    parent_message_uuid: Optional[str] = None
    current_path: Optional[List[str]] = None

class HistoryMessage(BaseModel):
    message_uuid: str
    role: str
    content: str

class HistoryResponse(BaseModel):
    messages: List[HistoryMessage]

class TreeNode(BaseModel):
    uuid: str
    role: str
    content: str
    children: List['TreeNode']

class CompleteChatDataResponse(BaseModel):
    chat_uuid: str
    title: str
    system_prompt: Optional[str]
    messages: List[HistoryMessage]
    tree_structure: TreeNode
    metadata: dict

class PaginationParams(BaseModel):
    page: int = Field(default=1, ge=1)
    limit: int = Field(default=20, ge=1, le=100)
    
class PaginatedResponse(BaseModel):
    items: List[dict]
    total: int
    page: int
    limit: int
    pages: int

class ChatMetadataResponse(BaseModel):
    chat_uuid: str
    title: str
    created_at: str
    updated_at: str
    message_count: int
    owner_id: str

class UpdateChatRequest(BaseModel):
    title: Optional[Annotated[str, Field(min_length=1, max_length=200)]] = None
    system_prompt: Optional[Annotated[str, Field(max_length=2000)]] = None
    
    @field_validator('title')
    @classmethod
    def validate_title(cls, v):
        if v is not None and not v.strip():
            raise ValueError('Title cannot be empty or whitespace only')
        return v.strip() if v else None
    
    @field_validator('system_prompt')
    @classmethod
    def validate_system_prompt(cls, v):
        if v is not None and not v.strip():
            return None
        return v

class EditMessageRequest(BaseModel):
    content: Annotated[str, Field(min_length=1, max_length=4000)]
    
    @field_validator('content')
    @classmethod
    def validate_content(cls, v):
        if not v.strip():
            raise ValueError('Message content cannot be empty or whitespace only')
        return v.strip()

class SearchPaginationParams(BaseModel):
    page: int = Field(default=1, ge=1)
    limit: int = Field(default=20, ge=1, le=100)
    sort: Optional[str] = Field(default="updated_at.desc")
    q: Optional[str] = None

class TreeStructureResponse(BaseModel):
    chat_uuid: str
    tree: TreeNode

# Template関連のスキーマ
class TemplateCreateRequest(BaseModel):
    name: Annotated[str, Field(min_length=1, max_length=100)]
    description: Optional[Annotated[str, Field(max_length=500)]] = None
    template_content: Annotated[str, Field(min_length=1, max_length=5000)]
    category: Optional[Annotated[str, Field(max_length=50)]] = None
    variables: Optional[List[str]] = None
    is_public: bool = False
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v):
        if not v.strip():
            raise ValueError('Template name cannot be empty')
        return v.strip()

class TemplateUpdateRequest(BaseModel):
    name: Optional[Annotated[str, Field(min_length=1, max_length=100)]] = None
    description: Optional[Annotated[str, Field(max_length=500)]] = None
    template_content: Optional[Annotated[str, Field(min_length=1, max_length=5000)]] = None
    category: Optional[Annotated[str, Field(max_length=50)]] = None
    variables: Optional[List[str]] = None
    is_public: Optional[bool] = None
    is_favorite: Optional[bool] = None

class TemplateResponse(BaseModel):
    uuid: str
    name: str
    description: Optional[str]
    template_content: str
    category: Optional[str]
    variables: Optional[List[str]]
    is_public: bool
    is_favorite: bool
    usage_count: int
    created_at: str
    updated_at: str

class TemplateListParams(BaseModel):
    page: int = Field(default=1, ge=1)
    limit: int = Field(default=20, ge=1, le=100)
    category: Optional[str] = None
    is_favorite: Optional[bool] = None
    q: Optional[str] = None

# Preset関連のスキーマ
class PresetCreateRequest(BaseModel):
    name: Annotated[str, Field(min_length=1, max_length=100)]
    description: Optional[Annotated[str, Field(max_length=500)]] = None
    model_id: str
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=1000, ge=1, le=4000)
    system_prompt: Optional[Annotated[str, Field(max_length=2000)]] = None
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v):
        if not v.strip():
            raise ValueError('Preset name cannot be empty')
        return v.strip()

class PresetUpdateRequest(BaseModel):
    name: Optional[Annotated[str, Field(min_length=1, max_length=100)]] = None
    description: Optional[Annotated[str, Field(max_length=500)]] = None
    model_id: Optional[str] = None
    temperature: Optional[float] = Field(default=None, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(default=None, ge=1, le=4000)
    system_prompt: Optional[Annotated[str, Field(max_length=2000)]] = None
    is_favorite: Optional[bool] = None

class PresetResponse(BaseModel):
    uuid: str
    name: str
    description: Optional[str]
    model_id: str
    temperature: float
    max_tokens: int
    system_prompt: Optional[str]
    is_favorite: bool
    usage_count: int
    created_at: str
    updated_at: str

class PresetListParams(BaseModel):
    page: int = Field(default=1, ge=1)
    limit: int = Field(default=20, ge=1, le=100)
    is_favorite: Optional[bool] = None
    q: Optional[str] = None

# Analytics関連のスキーマ
class UsageStatsResponse(BaseModel):
    total_messages: int
    total_tokens: int
    total_cost: float
    period_start: str
    period_end: str

class ModelUsageStats(BaseModel):
    model_id: str
    model_name: str
    message_count: int
    token_count: int
    cost: float
    percentage: float

class DailyUsageStats(BaseModel):
    date: str
    message_count: int
    token_count: int
    cost: float

class HourlyUsageStats(BaseModel):
    hour: int
    message_count: int
    token_count: int

class AnalyticsResponse(BaseModel):
    overview: UsageStatsResponse
    model_breakdown: List[ModelUsageStats]
    daily_usage: List[DailyUsageStats]
    hourly_pattern: List[HourlyUsageStats]
    top_categories: List[dict]
    cost_trends: List[dict]

class AnalyticsParams(BaseModel):
    period: str = Field(default="7d", pattern="^(1d|7d|30d|90d|1y)$")
    timezone: Optional[str] = Field(default="UTC")
    model_filter: Optional[str] = None