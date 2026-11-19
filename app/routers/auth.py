
import hashlib
import secrets
import hmac
import os

import aiosmtplib

from email.message import EmailMessage
from datetime import datetime, timedelta, timezone

from jose import jwt, JWTError

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from dotenv import load_dotenv

from app.database import AsyncSessionLocal
from app.models.user import User
from app.models.otp import OTPChallenge
from app.services.totp_service import verify_totp_code

load_dotenv()

router = APIRouter(
    prefix="/api/v1/auth",
    tags=["Authentication"]
)


# -----------------------------
# SETTINGS
# -----------------------------

class AuthSettings(BaseSettings):
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    class Config:
        env_file = ".env"
        extra = "ignore"


auth_settings = AuthSettings()


# -----------------------------
# DATABASE
# -----------------------------

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session


# -----------------------------
# PASSWORD HASHING
# -----------------------------

def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)

    hashed = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=2**14,
        r=8,
        p=1
    )

    return f"{salt.hex()}:{hashed.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        salt_hex, hash_hex = stored_hash.split(":")
        salt = bytes.fromhex(salt_hex)
        expected_hash = bytes.fromhex(hash_hex)

        actual_hash = hashlib.scrypt(
            password.encode("utf-8"),
            salt=salt,
            n=2**14,
            r=8,
            p=1
        )

        return hmac.compare_digest(
            actual_hash,
            expected_hash
        )

    except (ValueError, TypeError):
        return False


# -----------------------------
# JWT TOKEN
# -----------------------------

def create_access_token(user_id: int):
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=auth_settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )

    payload = {
        "sub": str(user_id),
        "type": "access",
        "exp": expire
    }

    return jwt.encode(
        payload,
        auth_settings.JWT_SECRET_KEY,
        algorithm=auth_settings.JWT_ALGORITHM
    )


def create_mfa_token(user_id: int):
    expire = datetime.now(timezone.utc) + timedelta(minutes=5)

    payload = {
        "sub": str(user_id),
        "type": "totp_login",
        "exp": expire
    }

    return jwt.encode(
        payload,
        auth_settings.JWT_SECRET_KEY,
        algorithm=auth_settings.JWT_ALGORITHM
    )


def verify_access_token(token: str):
    try:
        payload = jwt.decode(
            token.strip(),
            auth_settings.JWT_SECRET_KEY,
            algorithms=[auth_settings.JWT_ALGORITHM]
        )

        if payload.get("type") != "access":
            raise HTTPException(
                status_code=401,
                detail="Access token required"
            )

        user_id = payload.get("sub")

        if not user_id:
            raise HTTPException(
                status_code=401,
                detail="Token missing user ID"
            )

        return int(user_id)

    except JWTError:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token"
        )

    except ValueError:
        raise HTTPException(
            status_code=401,
            detail="Invalid user ID in token"
        )


def verify_mfa_token(token: str):
    try:
        payload = jwt.decode(
            token.strip(),
            auth_settings.JWT_SECRET_KEY,
            algorithms=[auth_settings.JWT_ALGORITHM]
        )

        if payload.get("type") != "totp_login":
            raise HTTPException(
                status_code=401,
                detail="Invalid MFA token"
            )

        user_id = payload.get("sub")

        if not user_id:
            raise HTTPException(
                status_code=401,
                detail="MFA token missing user ID"
            )

        return int(user_id)

    except JWTError:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired MFA token"
        )

    except ValueError:
        raise HTTPException(
            status_code=401,
            detail="Invalid user ID in MFA token"
        )


# -----------------------------
# REQUEST SCHEMAS
# -----------------------------

class RegisterRequest(BaseModel):
    full_name: str = Field(min_length=2, max_length=150)
    email: str
    phone: str = Field(min_length=10, max_length=20)
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    email: str
    password: str


class LoginTOTPRequest(BaseModel):
    mfa_token: str
    code: str = Field(min_length=6, max_length=6)


# -----------------------------
# REGISTER
# -----------------------------

@router.post("/register", status_code=201)
async def register_user(
    data: RegisterRequest,
    db: AsyncSession = Depends(get_db)
):
    email = data.email.strip().lower()
    phone = data.phone.strip()

    if "@" not in email or "." not in email.split("@")[-1]:
        raise HTTPException(400, "Invalid email address")

    result = await db.execute(
        select(User).where(
            (User.email == email) | (User.phone == phone)
        )
    )

    if result.scalars().first():
        raise HTTPException(
            409,
            "Email or phone number already registered"
        )

    user = User(
        full_name=data.full_name.strip(),
        email=email,
        phone=phone,
        hashed_password=hash_password(data.password)
    )

    db.add(user)
    await db.commit()
    await db.refresh(user)

    return {
        "message": "User registered successfully",
        "user_id": user.id,
        "full_name": user.full_name,
        "email": user.email
    }


# -----------------------------
# LOGIN - FIRST FACTOR
# -----------------------------

@router.post("/login")
async def login_user(
    data: LoginRequest,
    db: AsyncSession = Depends(get_db)
):
    email = data.email.strip().lower()

    result = await db.execute(
        select(User).where(User.email == email)
    )

    user = result.scalars().first()

    if not user or not verify_password(
        data.password,
        user.hashed_password
    ):
        raise HTTPException(
            401,
            "Invalid email or password"
        )

    if not user.is_active:
        raise HTTPException(
            403,
            "Account is inactive"
        )
    if not user.is_email_verified:
        raise HTTPException(
        status_code=403,
        detail="Please verify your email before login"
    )

    # If TOTP is enabled, require second factor
    if user.is_totp_enabled:
        if not user.totp_secret:
            raise HTTPException(
                403,
                "TOTP configuration is incomplete"
            )

        return {
            "message": "Password verified. TOTP verification required.",
            "requires_totp": True,
            "mfa_token": create_mfa_token(user.id),
            "token_type": "mfa",
            "expires_in": "5 minutes"
        }

    # Normal login when TOTP is disabled
    access_token = create_access_token(user.id)

    return {
        "message": "Login successful",
        "requires_totp": False,
        "user_id": user.id,
        "full_name": user.full_name,
        "email": user.email,
        "access_token": access_token,
        "token_type": "bearer"
    }


# -----------------------------
# LOGIN - SECOND FACTOR
# -----------------------------

@router.post("/login/verify-totp")
async def login_verify_totp(
    data: LoginTOTPRequest,
    db: AsyncSession = Depends(get_db)
):
    user_id = verify_mfa_token(data.mfa_token)

    result = await db.execute(
        select(User).where(User.id == user_id)
    )

    user = result.scalars().first()

    if not user or not user.is_active:
        raise HTTPException(
            401,
            "Invalid or inactive user"
        )

    if not user.is_totp_enabled or not user.totp_secret:
        raise HTTPException(
            400,
            "TOTP is not enabled for this account"
        )

    if not verify_totp_code(user.totp_secret, data.code):
        raise HTTPException(
            401,
            "Invalid TOTP code"
        )

    access_token = create_access_token(user.id)

    return {
        "message": "Login successful. TOTP verified.",
        "user_id": user.id,
        "full_name": user.full_name,
        "email": user.email,
        "access_token": access_token,
        "token_type": "bearer"
    }


# -----------------------------
# PROTECTED API
# -----------------------------

@router.get("/protected")
async def protected_route(token: str):
    user_id = verify_access_token(token)

    return {
        "message": "Access granted",
        "user_id": user_id
    }


# -----------------------------
# SEND EMAIL OTP
# -----------------------------

@router.post("/send-email-otp")
async def send_email_otp(
    email: str,
    db: AsyncSession = Depends(get_db)
):
    normalized_email = email.strip().lower()

    result = await db.execute(
        select(User).where(User.email == normalized_email)
    )

    user = result.scalars().first()

    if not user:
        raise HTTPException(
            404,
            "User not found"
        )

    # Check resend cooldown for latest unverified OTP
    latest_result = await db.execute(
        select(OTPChallenge)
        .where(
            OTPChallenge.user_id == user.id,
            OTPChallenge.channel == "email",
            OTPChallenge.is_verified.is_(False)
        )
        .order_by(OTPChallenge.created_at.desc())
        .limit(1)
    )

    latest_challenge = latest_result.scalars().first()

    now = datetime.now(timezone.utc)

    if latest_challenge:
        created_at = latest_challenge.created_at

        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)

        elapsed = (now - created_at).total_seconds()

        if elapsed < 60:
            raise HTTPException(
                status_code=429,
                detail="Please wait 60 seconds before requesting another OTP"
            )

    smtp_email = os.getenv("SMTP_EMAIL")
    smtp_password = os.getenv("SMTP_PASSWORD")
    smtp_host = os.getenv("SMTP_HOST")
    smtp_port = os.getenv("SMTP_PORT")

    if not all([
        smtp_email,
        smtp_password,
        smtp_host,
        smtp_port
    ]):
        raise HTTPException(
            500,
            "SMTP configuration missing in .env"
        )

    otp = f"{secrets.randbelow(1000000):06d}"

    challenge = OTPChallenge(
        user_id=user.id,
        otp_code=hashlib.sha256(
            otp.encode()
        ).hexdigest(),
        channel="email",
        expires_at=now + timedelta(minutes=5)
    )

    message = EmailMessage()
    message["From"] = smtp_email
    message["To"] = user.email
    message["Subject"] = "Your Email Verification OTP"

    message.set_content(
        f"Your OTP is {otp}. "
        "It expires in 5 minutes."
    )

    try:
        await aiosmtplib.send(
            message,
            hostname=smtp_host,
            port=int(smtp_port),
            start_tls=True,
            username=smtp_email,
            password=smtp_password
        )

    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Unable to send OTP email"
        )

    db.add(challenge)
    await db.commit()

    return {
        "message": "OTP sent successfully",
        "email": user.email,
        "expires_in": "5 minutes",
        "resend_wait": "60 seconds"
    }


# -----------------------------
# VERIFY EMAIL OTP
# -----------------------------

@router.post("/verify-email-otp")
async def verify_email_otp(
    email: str,
    otp: str,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(User).where(
            User.email == email.strip().lower()
        )
    )

    user = result.scalars().first()

    if not user:
        raise HTTPException(
            404,
            "User not found"
        )

    result = await db.execute(
        select(OTPChallenge)
        .where(
            OTPChallenge.user_id == user.id,
            OTPChallenge.channel == "email",
            OTPChallenge.is_verified.is_(False)
        )
        .order_by(OTPChallenge.created_at.desc())
        .limit(1)
    )

    challenge = result.scalars().first()

    if not challenge:
        raise HTTPException(
            400,
            "OTP not found"
        )

    now = datetime.now(timezone.utc)
    expires_at = challenge.expires_at

    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    if expires_at < now:
        raise HTTPException(
            400,
            "OTP expired"
        )

    if challenge.attempts >= 5:
        raise HTTPException(
            429,
            "Maximum OTP attempts reached. Request a new OTP."
        )

    entered_hash = hashlib.sha256(
        otp.encode()
    ).hexdigest()

    if not hmac.compare_digest(
        entered_hash,
        challenge.otp_code
    ):
        challenge.attempts += 1

        if challenge.attempts >= 5:
            challenge.expires_at = now

        await db.commit()

        raise HTTPException(
            400,
            "Invalid OTP"
        )

    challenge.is_verified = True
    user.is_email_verified = True
    await db.commit()
    await db.refresh(user)

    return {
        "message": "Email verified successfully"
    }
