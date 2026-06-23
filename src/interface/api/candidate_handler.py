from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any

from src.infrastructure.db.database import get_db
from src.application.schemas import CandidateRegistrationRequest
from src.application.use_cases.register_candidate import register_candidate_use_case
from src.application.use_cases.generate_questions import extract_text_from_pdf

router = APIRouter(prefix="/interviews", tags=["Candidates"])

@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register_candidate(
    name: str = Form(...),
    email: str = Form(...),
    phone: str = Form(...),
    job_title: str = Form(...),
    jd_file: UploadFile = File(...),
    resume: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Registers a candidate, parses their uploaded resume and JD PDFs, and schedules an interview 
    by generating personalized questions via the Groq LLM.
    """
    if resume.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Only PDF resumes are supported.")
    if jd_file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Only PDF JD files are supported.")
        
    try:
        resume_bytes = await resume.read()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to read resume file: {e}")

    try:
        jd_bytes = await jd_file.read()
        job_description_text = extract_text_from_pdf(jd_bytes)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to read or parse JD file: {e}")

    # Reconstruct the schema
    request_data = CandidateRegistrationRequest(
        name=name,
        email=email,
        phone=phone,
        job_title=job_title,
        job_description=job_description_text
    )

    try:
        interview_id = await register_candidate_use_case(
            session=db,
            request=request_data,
            resume_bytes=resume_bytes,
            resume_filename=resume.filename or "resume.pdf"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return {
        "interview_id": str(interview_id),
        "status": "scheduled",
        "message": "Candidate registered and questions generated successfully."
    }
