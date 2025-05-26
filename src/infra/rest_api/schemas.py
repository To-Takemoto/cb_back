from pydantic import BaseModel
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