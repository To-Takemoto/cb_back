from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Annotated
import re

class ChatCreateRequest(BaseModel):
    initial_message: Optional[Annotated[str, Field(max_length=4000)]] = None
    
    @field_validator('initial_message')
    @classmethod
    def validate_initial_message(cls, v):
        if v is not None and not v.strip():
            return None
        return v

class ChatCreateResponse(BaseModel):
    chat_uuid: Annotated[str, Field(pattern=r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$')]

class MessageRequest(BaseModel):
    content: Annotated[str, Field(min_length=1, max_length=4000)]
    parent_message_uuid: Optional[Annotated[str, Field(pattern=r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$')]] = None
    
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