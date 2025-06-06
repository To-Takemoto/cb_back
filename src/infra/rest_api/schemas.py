from pydantic import BaseModel, Field
from typing import List, Optional

class ChatCreateRequest(BaseModel):
    initial_message: Optional[str] = None

class ChatCreateResponse(BaseModel):
    chat_uuid: str

class MessageRequest(BaseModel):
    content: str

class MessageResponse(BaseModel):
    message_uuid: str
    content: str

class SelectRequest(BaseModel):
    message_uuid: str

class PathResponse(BaseModel):
    path: List[str]

class HistoryMessage(BaseModel):
    message_uuid: str
    role: str
    content: str

class HistoryResponse(BaseModel):
    messages: List[HistoryMessage]

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
    title: Optional[str] = None
    system_prompt: Optional[str] = None

class EditMessageRequest(BaseModel):
    content: str

class SearchPaginationParams(BaseModel):
    page: int = Field(default=1, ge=1)
    limit: int = Field(default=20, ge=1, le=100)
    sort: Optional[str] = Field(default="updated_at.desc")
    q: Optional[str] = None

class TreeNode(BaseModel):
    uuid: str
    role: str
    content: str
    children: List['TreeNode']

class TreeStructureResponse(BaseModel):
    chat_uuid: str
    tree: TreeNode
    current_node_uuid: str