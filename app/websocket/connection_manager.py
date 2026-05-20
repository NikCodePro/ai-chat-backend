import json
import logging
from typing import Dict, Any
from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)

class ConnectionManager:
    def __init__(self):
        # Maps user_id to their active websocket connection
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        self.active_connections[user_id] = websocket
        logger.info(f"User {user_id} connected. Active connections: {len(self.active_connections)}")

    def disconnect(self, user_id: str):
        if user_id in self.active_connections:
            del self.active_connections[user_id]
            logger.info(f"User {user_id} disconnected.")

    async def send_json(self, user_id: str, message: dict):
        if user_id in self.active_connections:
            try:
                await self.active_connections[user_id].send_json(message)
            except Exception as e:
                logger.error(f"Error sending message to {user_id}: {e}")

    async def send_bytes(self, user_id: str, data: bytes):
        if user_id in self.active_connections:
            try:
                await self.active_connections[user_id].send_bytes(data)
            except Exception as e:
                logger.error(f"Error sending bytes to {user_id}: {e}")

connection_manager = ConnectionManager()
