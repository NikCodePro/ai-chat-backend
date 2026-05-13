from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field

class MessageResponse(BaseModel):
    role: str
    content: str
    timestamp: datetime

class ChatResponse(BaseModel):
    id: str
    user_id: str
    title: str
    model: str
    messages: List[MessageResponse] = []
    created_at: datetime
    updated_at: datetime

def serialize_message(message: dict) -> MessageResponse:
    return MessageResponse(
        role=message["role"],
        content=message["content"],
        timestamp=message["timestamp"]
    )

def serialize_chat(chat: dict) -> ChatResponse:
    return ChatResponse(
        id=str(chat["_id"]),
        user_id=str(chat["user_id"]),
        title=chat["title"],
        model=chat["model"],
        messages=[serialize_message(m) for m in chat.get("messages", [])],
        created_at=chat["created_at"],
        updated_at=chat["updated_at"]
    )
