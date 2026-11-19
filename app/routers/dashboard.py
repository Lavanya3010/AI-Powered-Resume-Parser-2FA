
from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.resume import UserResume
from app.core.dependencies import get_db, get_current_user

router = APIRouter(
    prefix="/api/v1/dashboard",
    tags=["Dashboard"]
)


@router.get("/summary")
async def get_dashboard_summary(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Count current user's resumes
    count_result = await db.execute(
        select(func.count(UserResume.id)).where(
            UserResume.user_id == current_user.id
        )
    )

    total_resumes = count_result.scalar_one()

    # Get recent 5 resumes
    recent_result = await db.execute(
        select(UserResume)
        .where(UserResume.user_id == current_user.id)
        .order_by(UserResume.created_at.desc())
        .limit(5)
    )

    recent_resumes = recent_result.scalars().all()

    return {
        "message": "Dashboard loaded successfully",
        "user": {
            "user_id": current_user.id,
            "full_name": current_user.full_name,
            "email": current_user.email,
            "is_active": current_user.is_active,
            "is_totp_enabled": current_user.is_totp_enabled
        },
        "statistics": {
            "total_resumes": total_resumes
        },
        "recent_resumes": [
            {
                "resume_id": resume.id,
                "file_name": resume.file_name,
                "created_at": resume.created_at,
                "skills": resume.skills,
                "experience": resume.experience
            }
            for resume in recent_resumes
        ]
    }
