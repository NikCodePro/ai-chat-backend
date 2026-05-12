from fastapi import APIRouter

from app.schemas.response_schema import success_response


router = APIRouter(prefix="/health", tags=["Health"])


@router.get("")
async def health_check():
    return success_response("Service is healthy", {"status": "ok"})
