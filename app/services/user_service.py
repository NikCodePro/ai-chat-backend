from bson import ObjectId
from bson.errors import InvalidId

from app.database.collections import USERS_COLLECTION
from app.database.mongodb import get_database


async def get_user_by_email(email: str) -> dict | None:
    db = get_database()
    return await db[USERS_COLLECTION].find_one({"email": email.lower()})


async def get_user_by_phone(phone: str) -> dict | None:
    db = get_database()
    return await db[USERS_COLLECTION].find_one({"phone": phone})


async def get_user_by_username(username: str) -> dict | None:
    db = get_database()
    return await db[USERS_COLLECTION].find_one({"username": username})


async def get_user_by_identifier(identifier: str) -> dict | None:
    if "@" in identifier:
        return await get_user_by_email(identifier)
    return await get_user_by_phone(identifier)


async def get_user_by_id(user_id: str) -> dict | None:
    try:
        object_id = ObjectId(user_id)
    except InvalidId:
        return None

    db = get_database()
    return await db[USERS_COLLECTION].find_one({"_id": object_id})


async def create_user(user_document: dict) -> dict:
    db = get_database()
    await db[USERS_COLLECTION].insert_one(user_document)
    return user_document


async def mark_identifier_verified(identifier: str) -> dict | None:
    db = get_database()
    if "@" in identifier:
        await db[USERS_COLLECTION].update_one(
            {"email": identifier.lower()},
            {"$set": {"email_verified": True}},
        )
        return await get_user_by_email(identifier)

    await db[USERS_COLLECTION].update_one(
        {"phone": identifier},
        {"$set": {"phone_verified": True}},
    )
    return await get_user_by_phone(identifier)


async def update_user(user_id: str, update_data: dict) -> dict | None:
    try:
        object_id = ObjectId(user_id)
    except InvalidId:
        return None

    db = get_database()
    await db[USERS_COLLECTION].update_one({"_id": object_id}, {"$set": update_data})
    return await get_user_by_id(user_id)
