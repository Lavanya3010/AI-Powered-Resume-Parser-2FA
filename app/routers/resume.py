
import os
import re
import uuid
from pathlib import Path

import pdfplumber
from docx import Document
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db, get_current_user
from app.models.resume import UserResume
from app.models.user import User

router = APIRouter(
    prefix="/api/v1/resume",
    tags=["Resume"]
)

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

MAX_FILE_SIZE = 5 * 1024 * 1024

SKILL_LIST = [
    "Python", "FastAPI", "Java", "SQL", "PostgreSQL",
    "MySQL", "SQLAlchemy", "Docker", "Git", "AWS",
    "Machine Learning", "Deep Learning", "React",
    "JavaScript", "HTML", "CSS", "REST APIs"
]


# UPLOAD AND PARSE RESUME
@router.post("/parse")
async def parse_resume(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    filename = Path(file.filename or "").name
    extension = Path(filename).suffix.lower()

    if extension not in [".pdf", ".docx"]:
        raise HTTPException(
            status_code=400,
            detail="Only PDF and DOCX files allowed"
        )

    content = await file.read(MAX_FILE_SIZE + 1)

    if not content:
        raise HTTPException(400, "Empty file")

    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail="File size exceeds 5 MB limit"
        )

    unique_filename = f"{uuid.uuid4().hex}{extension}"
    file_path = UPLOAD_DIR / unique_filename

    try:
        file_path.write_bytes(content)

        if extension == ".pdf":
            with pdfplumber.open(file_path) as pdf:
                extracted_text = "\n".join(
                    page.extract_text() or ""
                    for page in pdf.pages
                )
        else:
            document = Document(file_path)
            extracted_text = "\n".join(
                paragraph.text
                for paragraph in document.paragraphs
            )

        if not extracted_text.strip():
            raise HTTPException(
                status_code=400,
                detail="No readable text found in resume"
            )

    except HTTPException:
        file_path.unlink(missing_ok=True)
        raise

    except Exception:
        file_path.unlink(missing_ok=True)
        raise HTTPException(
            status_code=400,
            detail="Unable to read resume. Check the file format."
        )

    lines = [
        line.strip()
        for line in extracted_text.splitlines()
        if line.strip()
    ]

    email_match = re.search(
        r"[\w.+-]+@[\w-]+\.[\w.-]+",
        extracted_text
    )

    phone_match = re.search(
        r"\b(?:\+91[- ]?)?[6-9]\d{9}\b",
        extracted_text
    )

    name = None

    for line in lines[:8]:
        if (
            not re.search(r"@|https?://|\d", line)
            and len(line.split()) <= 5
            and line.upper() not in [
                "RESUME",
                "CURRICULUM VITAE"
            ]
        ):
            name = line
            break

    skills = [
        skill for skill in SKILL_LIST
        if re.search(
            r"\b" + re.escape(skill) + r"\b",
            extracted_text,
            re.IGNORECASE
        )
    ]

    experience_lines = [
        line for line in lines
        if re.search(
            r"\b\d+\+?\s*(?:years?|yrs?)\b|experience|professional summary",
            line,
            re.IGNORECASE
        )
    ]

    experience = "\n".join(experience_lines) or None

    resume = UserResume(
        user_id=current_user.id,
        file_name=filename,
        file_path=str(file_path),
        extracted_text=extracted_text,
        skills=", ".join(skills),
        experience=experience
    )

    try:
        db.add(resume)
        await db.commit()
        await db.refresh(resume)

    except Exception:
        await db.rollback()
        file_path.unlink(missing_ok=True)
        raise HTTPException(
            status_code=500,
            detail="Unable to save resume"
        )

    return {
        "message": "Resume parsed and saved successfully",
        "resume_id": resume.id,
        "user_id": current_user.id,
        "filename": filename,
        "name": name,
        "email": email_match.group(0) if email_match else None,
        "phone": phone_match.group(0) if phone_match else None,
        "skills": skills,
        "experience": experience,
        "extracted_text": extracted_text
    }


# GET ALL RESUMES OF CURRENT USER
@router.get("/my-resumes")
async def get_my_resumes(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(UserResume)
        .where(UserResume.user_id == current_user.id)
        .order_by(UserResume.created_at.desc())
    )

    resumes = result.scalars().all()

    return {
        "total_resumes": len(resumes),
        "resumes": [
            {
                "resume_id": resume.id,
                "file_name": resume.file_name,
                "skills": resume.skills,
                "experience": resume.experience,
                "created_at": resume.created_at
            }
            for resume in resumes
        ]
    }


# GET SINGLE RESUME
@router.get("/{resume_id}")
async def get_resume_details(
    resume_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(UserResume).where(
            UserResume.id == resume_id,
            UserResume.user_id == current_user.id
        )
    )

    resume = result.scalars().first()

    if not resume:
        raise HTTPException(
            status_code=404,
            detail="Resume not found"
        )

    return {
        "resume_id": resume.id,
        "user_id": resume.user_id,
        "file_name": resume.file_name,
        "extracted_text": resume.extracted_text,
        "skills": resume.skills,
        "experience": resume.experience,
        "created_at": resume.created_at
    }


# DELETE RESUME
@router.delete("/{resume_id}")
async def delete_resume(
    resume_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(UserResume).where(
            UserResume.id == resume_id,
            UserResume.user_id == current_user.id
        )
    )

    resume = result.scalars().first()

    if not resume:
        raise HTTPException(
            status_code=404,
            detail="Resume not found"
        )

    file_path = resume.file_path

    await db.delete(resume)
    await db.commit()

    if file_path and os.path.isfile(file_path):
        try:
            os.remove(file_path)
        except OSError:
            pass

    return {
        "message": "Resume deleted successfully",
        "resume_id": resume_id
    }
