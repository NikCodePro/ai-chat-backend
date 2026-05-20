import json
import logging
from typing import Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, HTTPException

from app.websocket.connection_manager import connection_manager
from app.services.gemini_live_service import gemini_live_service
from app.services.jwt_service import verify_access_token

logger = logging.getLogger(__name__)

router = APIRouter(tags=["voice_socket"])

@router.websocket("/ws/voice")
async def voice_websocket_endpoint(websocket: WebSocket, token: Optional[str] = Query(None)):
    if not token:
        await websocket.close(code=1008, reason="Missing token")
        return
        
    try:
        payload = verify_access_token(token)
        user_id = payload.get("user_id")
        if not user_id:
            raise ValueError("Invalid token payload")
    except HTTPException as e:
        logger.error(f"WebSocket auth failed: {e.detail}")
        await websocket.close(code=1008, reason=str(e.detail))
        return
    except Exception as e:
        logger.error(f"WebSocket auth failed: {e}")
        await websocket.close(code=1008, reason="Invalid token")
        return

    await connection_manager.connect(websocket, user_id)

    async def receive_from_client():
        try:
            data = await websocket.receive()
            if "bytes" in data:
                return data["bytes"]
            elif "text" in data:
                return json.loads(data["text"])
        except WebSocketDisconnect:
            return None
        except Exception as e:
            logger.error(f"Error receiving from client: {e}")
            return None

    async def send_to_client_json(msg: dict):
        await connection_manager.send_json(user_id, msg)
        
    async def send_to_client_bytes(data: bytes):
        await connection_manager.send_bytes(user_id, data)

    try:
        await send_to_client_json({"type": "connection_established", "message": "Connected to voice backend"})
        
        # Start the Gemini live session
        await gemini_live_service.run_session(
            receive_from_client=receive_from_client,
            send_to_client_json=send_to_client_json,
            send_to_client_bytes=send_to_client_bytes
        )
    except WebSocketDisconnect:
        logger.info(f"User {user_id} disconnected from voice websocket.")
    except Exception as e:
        logger.error(f"Voice websocket error for user {user_id}: {e}")
    finally:
        connection_manager.disconnect(user_id)
