
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.core.dependencies import get_db, get_current_user

router = APIRouter(
    prefix="/api/v1/profile",
    tags=["User Profile"]
)


class ProfileUpdate(BaseModel):
    full_name: str | None = Field(
        default=None,
        min_length=2,
        max_length=150
    )
    phone: str | None = Field(
        default=None,
        min_length=10,
        max_length=20
    )


# GET USER PROFILE
@router.get("/me")
async def get_my_profile(
    current_user: User = Depends(get_current_user)
):
    return {
        "user_id": current_user.id,
        "full_name": current_user.full_name,
        "email": current_user.email,
        "phone": current_user.phone,
        "is_active": current_user.is_active,
        "is_totp_enabled": current_user.is_totp_enabled,
        "created_at": current_user.created_at
    }


# UPDATE USER PROFILE
@router.patch("/me")
async def update_my_profile(
    data: ProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    if data.full_name is not None:
        full_name = data.full_name.strip()

        if len(full_name) < 2:
            raise HTTPException(
                status_code=400,
                detail="Full name must contain at least 2 characters"
            )

        current_user.full_name = full_name

    if data.phone is not None:
        phone = data.phone.strip()

        if not phone:
            raise HTTPException(
                status_code=400,
                detail="Phone cannot be empty"
            )

        existing = await db.execute(
            select(User).where(
                User.phone == phone,
                User.id != current_user.id
            )
        )

        if existing.scalars().first():
            raise HTTPException(
                status_code=409,
                detail="Phone number already registered"
            )

        current_user.phone = phone

    await db.commit()
    await db.refresh(current_user)

    return {
        "message": "Profile updated successfully",
        "user_id": current_user.id,
        "full_name": current_user.full_name,
        "email": current_user.email,
        "phone": current_user.phone
    }
