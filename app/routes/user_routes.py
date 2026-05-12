from fastapi import APIRouter, Depends

from app.dependencies import get_current_user
from app.schemas.response_schema import success_response
from app.schemas.user_schema import serialize_user


router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me")
async def get_current_user_profile(current_user=Depends(get_current_user)):
    return success_response("Current user fetched", serialize_user(current_user))
