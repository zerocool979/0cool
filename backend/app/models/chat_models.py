from pydantic import BaseModel, Field
from typing import List, Optional
from enum import Enum
from datetime import datetime


class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class ChatMessage(BaseModel):
    role: MessageRole
    content: str
    timestamp: datetime = Field(default_factory=datetime.now)


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    context: Optional[str] = None
    scan_id: Optional[str] = None


class ChatResponse(BaseModel):
    session_id: str
    message: str
    role: MessageRole = MessageRole.ASSISTANT
    timestamp: datetime = Field(default_factory=datetime.now)


class ChatSession(BaseModel):
    session_id: str
    messages: List[ChatMessage] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
