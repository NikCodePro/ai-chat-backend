from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Dict, Any

from app.services.heygen_service import heygen_service

router = APIRouter(prefix="/avatar", tags=["Avatar"])

class CreateSessionRequest(BaseModel):
    avatar_name: str = "Anna_public_3_20240108"

class StartSessionRequest(BaseModel):
    session_id: str
    sdp: Dict[str, Any]

class IceCandidateRequest(BaseModel):
    session_id: str
    candidate: Dict[str, Any]

class TaskRequest(BaseModel):
    session_id: str
    text: str

class StopSessionRequest(BaseModel):
    session_id: str

@router.post("/new")
async def create_new_session(req: CreateSessionRequest):
    try:
        data = await heygen_service.create_session(avatar_name=req.avatar_name)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/start")
async def start_session(req: StartSessionRequest):
    try:
        data = await heygen_service.start_session(session_id=req.session_id, sdp=req.sdp)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/ice")
async def send_ice_candidate(req: IceCandidateRequest):
    try:
        data = await heygen_service.send_ice_candidate(session_id=req.session_id, candidate=req.candidate)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/task")
async def send_task(req: TaskRequest):
    try:
        data = await heygen_service.send_task(session_id=req.session_id, text=req.text)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/stop")
async def stop_session(req: StopSessionRequest):
    try:
        data = await heygen_service.stop_session(session_id=req.session_id)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
