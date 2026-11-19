
from fastapi import FastAPI

from app.routers.resume import router as resume_router
from app.routers.auth import router as auth_router
from app.routers.totp import router as totp_router
from app.routers.profile import router as profile_router
from app.routers.dashboard import router as dashboard_router


app = FastAPI(
    title="AI Powered Resume Parser",
    description="AI-powered Resume Parsing and Multi-Channel 2FA Onboarding Pipeline",
    version="1.0.0"
)

# Register all routers
app.include_router(auth_router)
app.include_router(resume_router)
app.include_router(totp_router)
app.include_router(profile_router)
app.include_router(dashboard_router)


@app.get("/")
async def root():
    return {
        "message": "Resume Parser API is running"
    }


@app.get("/health")
async def health():
    return {
        "status": "healthy"
    }
