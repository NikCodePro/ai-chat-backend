import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query
from app.services.jwt_service import verify_access_token
from app.services.ai_service import AIService
from app.services.chat_service import get_chat_history, add_message_to_chat, update_chat_title
from app.websocket.manager import manager
import asyncio

router = APIRouter(tags=["Chat WebSocket"])

@router.websocket("/ws/chat")
async def chat_websocket(
    websocket: WebSocket,
    token: str = Query(...)
):
    # 1. Authenticate
    try:
        payload = verify_access_token(token)
        user_id = payload["user_id"]
    except Exception:
        await websocket.close(code=4003) # Unauthorized
        return

    await manager.connect(websocket)
    
    try:
        while True:
            # Receive message from user
            data = await websocket.receive_text()
            message_data = json.loads(data)
            
            user_message = message_data.get("message")
            chat_id = message_data.get("chat_id")
            provider = message_data.get("provider", "mistral") # mistral, openai, gemini

            if not user_message or not chat_id:
                await websocket.send_text(json.dumps({"error": "Missing message or chat_id"}))
                continue

            # 2. Get history
            chat = await get_chat_history(chat_id, user_id)
            if not chat:
                await websocket.send_text(json.dumps({"error": "Chat not found"}))
                continue

            history = chat.get("messages", [])

            # 3. Save user message
            await add_message_to_chat(chat_id, "user", user_message)

            # Check if this is the first message to trigger auto-titling
            if len(history) == 0:
                async def generate_and_update_title():
                    try:
                        new_title = await AIService.generate_chat_title(user_message, provider)
                        await update_chat_title(chat_id, new_title)
                        await websocket.send_text(json.dumps({
                            "type": "title_update",
                            "chat_id": chat_id,
                            "title": new_title
                        }))
                    except Exception as e:
                        print(f"Failed to generate title: {e}")
                
                asyncio.create_task(generate_and_update_title())

            # 4. Stream AI Response
            full_ai_response = ""
            socket_active = True
            
            # Send a start signal
            try:
                await websocket.send_text(json.dumps({"type": "start", "chat_id": chat_id}))
            except Exception:
                socket_active = False

            async for chunk in AIService.stream_chat(user_message, history, provider):
                full_ai_response += chunk
                if socket_active:
                    try:
                        await websocket.send_text(json.dumps({
                            "type": "chunk",
                            "content": chunk,
                            "chat_id": chat_id
                        }))
                    except Exception:
                        socket_active = False

            # 5. Save AI response
            if full_ai_response:
                await add_message_to_chat(chat_id, "assistant", full_ai_response)
            
            # Send an end signal
            if socket_active:
                try:
                    await websocket.send_text(json.dumps({"type": "end", "chat_id": chat_id}))
                except Exception:
                    socket_active = False

    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        print(f"WS Error: {e}")
        manager.disconnect(websocket)
