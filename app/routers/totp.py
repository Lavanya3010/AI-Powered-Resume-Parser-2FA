
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.core.dependencies import get_db, get_current_user
from app.services.totp_service import (
    generate_totp_secret,
    generate_totp_qr,
    verify_totp_code
)

router = APIRouter(
    prefix="/api/v1/totp",
    tags=["TOTP Authentication"]
)


class TOTPVerifyRequest(BaseModel):
    code: str = Field(min_length=6, max_length=6)


# Generate TOTP secret and QR code
@router.post("/setup")
async def setup_totp(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    if current_user.is_totp_enabled:
        raise HTTPException(
            status_code=400,
            detail="TOTP already enabled"
        )

    secret = generate_totp_secret()
    qr_code = generate_totp_qr(current_user.email, secret)

    current_user.totp_secret = secret
    await db.commit()

    return {
        "message": "TOTP setup initiated",
        "secret": secret,
        "qr_code_base64": qr_code,
        "next_step": "Scan QR code and verify OTP"
    }


# Verify TOTP and enable authentication
@router.post("/verify")
async def verify_totp(
    data: TOTPVerifyRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    if not current_user.totp_secret:
        raise HTTPException(
            status_code=400,
            detail="Please setup TOTP first"
        )

    if current_user.is_totp_enabled:
        raise HTTPException(
            status_code=400,
            detail="TOTP already enabled"
        )

    if not verify_totp_code(current_user.totp_secret, data.code):
        raise HTTPException(
            status_code=400,
            detail="Invalid TOTP code"
        )

    current_user.is_totp_enabled = True
    await db.commit()

    return {
        "message": "TOTP enabled successfully"
    }


# Disable TOTP
@router.post("/disable")
async def disable_totp(
    data: TOTPVerifyRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    if not current_user.is_totp_enabled or not current_user.totp_secret:
        raise HTTPException(
            status_code=400,
            detail="TOTP is not enabled"
        )

    if not verify_totp_code(current_user.totp_secret, data.code):
        raise HTTPException(
            status_code=400,
            detail="Invalid TOTP code"
        )

    current_user.is_totp_enabled = False
    current_user.totp_secret = None
    await db.commit()

    return {
        "message": "TOTP disabled successfully"
    }
