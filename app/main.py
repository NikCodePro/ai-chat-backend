from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database.mongodb import close_mongo_connection, connect_to_mongo
from app.routes import auth_routes, health_routes, user_routes, chat_routes, chat_ws


@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_to_mongo()
    yield
    await close_mongo_connection()


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.API_VERSION,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_routes.router, prefix=settings.API_PREFIX)
app.include_router(user_routes.router, prefix=settings.API_PREFIX)
app.include_router(health_routes.router, prefix=settings.API_PREFIX)
app.include_router(chat_routes.router, prefix=settings.API_PREFIX)
app.include_router(chat_ws.router, prefix=settings.API_PREFIX)
