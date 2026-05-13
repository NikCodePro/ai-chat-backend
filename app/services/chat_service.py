from datetime import datetime, timezone
from typing import List, Optional
from bson import ObjectId

from app.database.collections import CHATS_COLLECTION
from app.database.mongodb import get_database
from app.models.chat_model import create_chat_document, create_message_document

async def get_user_chats(user_id: str) -> List[dict]:
    db = get_database()
    chats = await db[CHATS_COLLECTION].find(
        {"user_id": ObjectId(user_id)},
        {"messages": {"$slice": -1}} # Only get the last message for preview
    ).sort("updated_at", -1).to_list(length=100)
    return chats

async def get_chat_history(chat_id: str, user_id: str) -> Optional[dict]:
    db = get_database()
    chat = await db[CHATS_COLLECTION].find_one({
        "_id": ObjectId(chat_id),
        "user_id": ObjectId(user_id)
    })
    return chat

async def create_new_chat(user_id: str, title: str, model: str) -> dict:
    db = get_database()
    chat_doc = create_chat_document(user_id, title, model)
    await db[CHATS_COLLECTION].insert_one(chat_doc)
    return chat_doc

async def add_message_to_chat(chat_id: str, role: str, content: str):
    db = get_database()
    message = create_message_document(role, content)
    await db[CHATS_COLLECTION].update_one(
        {"_id": ObjectId(chat_id)},
        {
            "$push": {"messages": message},
            "$set": {"updated_at": datetime.now(timezone.utc)}
        }
    )
    return message
