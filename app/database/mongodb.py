from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.config import settings


client: AsyncIOMotorClient | None = None
database: AsyncIOMotorDatabase | None = None


async def connect_to_mongo() -> None:
    global client, database
    client = AsyncIOMotorClient(settings.MONGO_URI)
    database = client[settings.DATABASE_NAME]
    await database.command("ping")
    await _ensure_sparse_unique_index("users", "email", "email_1")
    await database.users.create_index("email", unique=True, sparse=True)
    await database.users.create_index("phone", unique=True, sparse=True)
    await database.refresh_tokens.create_index("refresh_token", unique=True)
    await database.refresh_tokens.create_index("expires_at")
    await database.otp_challenges.create_index("identifier")
    await database.otp_challenges.create_index("expires_at", expireAfterSeconds=0)


async def close_mongo_connection() -> None:
    if client:
        client.close()


def get_database() -> AsyncIOMotorDatabase:
    if database is None:
        raise RuntimeError("Database is not initialized")
    return database


async def _ensure_sparse_unique_index(collection_name: str, field: str, index_name: str) -> None:
    if database is None:
        return

    indexes = await database[collection_name].index_information()
    existing = indexes.get(index_name)
    if existing and existing.get("unique") and not existing.get("sparse"):
        await database[collection_name].drop_index(index_name)
