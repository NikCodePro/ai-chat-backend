from datetime import datetime, timezone
from typing import List, Optional
from bson import ObjectId

def create_chat_document(
    user_id: str,
    title: str = "New Chat",
    model: str = "mistral",
) -> dict:
    return {
        "_id": ObjectId(),
        "user_id": ObjectId(user_id),
        "title": title,
        "model": model,
        "messages": [],
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }

def create_message_document(
    role: str,
    content: str,
) -> dict:
    return {
        "role": role, # 'user' or 'assistant'
        "content": content,
        "timestamp": datetime.now(timezone.utc),
    }
