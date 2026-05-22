from fastapi import APIRouter, Depends

from app.dependencies import get_current_user
from app.schemas.response_schema import success_response
from app.schemas.user_schema import serialize_user, UpdateProfileRequest
from app.services.user_service import update_user, get_user_by_username, get_user_by_email, get_user_by_phone
from fastapi import HTTPException, status
from datetime import datetime, timezone


router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me")
async def get_current_user_profile(current_user=Depends(get_current_user)):
    return success_response("Current user fetched", serialize_user(current_user))

@router.patch("/me")
async def update_current_user_profile(payload: UpdateProfileRequest, current_user=Depends(get_current_user)):
    update_data = {}
    if payload.name is not None:
        update_data["name"] = payload.name
        
    if payload.username is not None and payload.username != current_user.get("username"):
        existing_username = await get_user_by_username(payload.username)
        if existing_username:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username is already taken",
            )
        update_data["username"] = payload.username
        
    if payload.email is not None and payload.email != current_user.get("email"):
        existing_email = await get_user_by_email(payload.email)
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email is already taken",
            )
        update_data["email"] = payload.email
        update_data["email_verified"] = False
        
    if payload.phone is not None and payload.phone != current_user.get("phone"):
        existing_phone = await get_user_by_phone(payload.phone)
        if existing_phone:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Phone number is already taken",
            )
        update_data["phone"] = payload.phone
        update_data["phone_verified"] = False
        
    if not update_data:
        return success_response("No changes made", serialize_user(current_user))
        
    update_data["updated_at"] = datetime.now(timezone.utc)
    updated_user = await update_user(str(current_user["_id"]), update_data)
    
    if not updated_user:
        raise HTTPException(status_code=404, detail="User not found")
        
    return success_response("Profile updated successfully", serialize_user(updated_user))
