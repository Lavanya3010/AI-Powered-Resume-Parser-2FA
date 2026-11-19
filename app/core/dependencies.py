from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.models.user import User
from app.routers.auth import verify_access_token


# Bearer token security for Swagger
bearer_scheme = HTTPBearer()


# Database dependency
async def get_db():
    async with AsyncSessionLocal() as session:
        yield session


# Get logged-in user from access token
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db)
):
    token = credentials.credentials

    # Validate access token
    user_id = verify_access_token(token)

    # Find user in database
    result = await db.execute(
        select(User).where(User.id == user_id)
    )

    user = result.scalars().first()

    # Check user status
    if not user or not user.is_active:
        raise HTTPException(
            status_code=401,
            detail="Invalid or inactive user"
        )

    return user