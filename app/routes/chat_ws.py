import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query
from app.services.jwt_service import verify_access_token
from app.services.ai_service import AIService
from app.services.chat_service import get_chat_history, add_message_to_chat
from app.websocket.manager import manager

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

            # 4. Stream AI Response
            full_ai_response = ""
            
            # Send a start signal
            await websocket.send_text(json.dumps({"type": "start", "chat_id": chat_id}))

            async for chunk in AIService.stream_chat(user_message, history, provider):
                full_ai_response += chunk
                await websocket.send_text(json.dumps({
                    "type": "chunk",
                    "content": chunk,
                    "chat_id": chat_id
                }))

            # 5. Save AI response
            await add_message_to_chat(chat_id, "assistant", full_ai_response)
            
            # Send an end signal
            await websocket.send_text(json.dumps({"type": "end", "chat_id": chat_id}))

    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        print(f"WS Error: {e}")
        manager.disconnect(websocket)
