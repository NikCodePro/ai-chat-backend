from fastapi import APIRouter, Depends, HTTPException
from typing import List

from app.dependencies import get_current_user
from app.schemas.response_schema import success_response
from app.schemas.chat_schema import serialize_chat, serialize_message
from app.services.chat_service import get_user_chats, get_chat_history, create_new_chat, delete_chat
from app.services.ai_service import AIService
from pydantic import BaseModel

router = APIRouter(prefix="/chats", tags=["Chats"])

class CreateChatRequest(BaseModel):
    title: str
    model: str = "mistral"

class TranscribeRequest(BaseModel):
    audio: str
    
@router.post("/transcribe")
async def transcribe(payload: TranscribeRequest, current_user=Depends(get_current_user)):
    try:
        text = await AIService.transcribe_audio(payload.audio)
        return success_response("Audio transcribed successfully", {"text": text})
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")

@router.get("/")
async def list_chats(current_user=Depends(get_current_user)):
    chats = await get_user_chats(str(current_user["_id"]))
    return success_response("Chats fetched successfully", [serialize_chat(c) for c in chats])

@router.post("/")
async def start_chat(payload: CreateChatRequest, current_user=Depends(get_current_user)):
    chat = await create_new_chat(str(current_user["_id"]), payload.title, payload.model)
    return success_response("Chat created successfully", serialize_chat(chat))

@router.get("/{chat_id}/history")
async def fetch_history(chat_id: str, current_user=Depends(get_current_user)):
    chat = await get_chat_history(chat_id, str(current_user["_id"]))
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    return success_response("Chat history fetched", [serialize_message(m) for m in chat["messages"]])

@router.delete("/{chat_id}")
async def delete_user_chat(chat_id: str, current_user=Depends(get_current_user)):
    success = await delete_chat(chat_id, str(current_user["_id"]))
    if not success:
        raise HTTPException(status_code=404, detail="Chat not found or already deleted")
    return success_response("Chat deleted successfully", None)
