from fastapi import APIRouter, HTTPException

from app.services.heygen_service import heygen_service

router = APIRouter(prefix="/avatar", tags=["Avatar"])

@router.post("/token")
async def get_livekit_token():
    """Generates a LiveKit connection URL and Token from HeyGen LiveAvatar API."""
    try:
        data = await heygen_service.get_session_token()
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/stop")
async def stop_avatar_session():
    """Stops the current LiveAvatar session on the server."""
    try:
        await heygen_service.stop_session()
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
