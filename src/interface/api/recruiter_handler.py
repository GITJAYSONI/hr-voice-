from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from typing import List, Dict, Any
from uuid import UUID

from src.infrastructure.db.database import get_db
from src.infrastructure.db.repository import InterviewRepository, EvaluationRepository
from src.infrastructure.db.models import Interview, InterviewResponse

router = APIRouter(prefix="/recruiter", tags=["Recruiter Dashboard"])

@router.get("/candidates")
async def get_all_candidates(db: AsyncSession = Depends(get_db)) -> List[Dict[str, Any]]:
    """
    Returns a list of all candidates, their current interview status, and overall evaluation scores.
    """
    result = await db.execute(
        select(Interview)
        .options(
            selectinload(Interview.candidate),
            selectinload(Interview.job),
            selectinload(Interview.evaluation)
        )
        .order_by(Interview.created_at.desc())
    )
    interviews = result.scalars().all()
    
    res = []
    for interview in interviews:
        eval_data = None
        if interview.evaluation:
            eval_data = {
                "overall_score": float(interview.evaluation.overall_score),
                "recommendation": interview.evaluation.recommendation
            }
        res.append({
            "interview_id": str(interview.id),
            "candidate_name": interview.candidate.name,
            "candidate_email": interview.candidate.email,
            "candidate_phone": interview.candidate.phone,
            "job_title": interview.job.title,
            "status": interview.status,
            "created_at": interview.created_at.isoformat(),
            "evaluation": eval_data
        })
    return res

@router.get("/interviews/{interview_id}")
async def get_interview_detail(
    interview_id: UUID,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Returns the complete details of a specific interview, including candidate, job,
    evaluation scores, and full question-by-question responses (playback).
    """
    result = await db.execute(
        select(Interview)
        .filter(Interview.id == interview_id)
        .options(
            selectinload(Interview.candidate),
            selectinload(Interview.job),
            selectinload(Interview.evaluation),
            selectinload(Interview.responses).selectinload(InterviewResponse.question),
            selectinload(Interview.questions)
        )
    )
    interview = result.scalars().first()
    if not interview:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Interview with ID {interview_id} not found."
        )

    # Serialize evaluation details if available
    evaluation_data = None
    if interview.evaluation:
        evaluation_data = {
            "id": str(interview.evaluation.id),
            "technical_score": float(interview.evaluation.technical_score),
            "communication_score": float(interview.evaluation.communication_score),
            "behavioral_score": float(interview.evaluation.behavioral_score),
            "vision_score": float(interview.evaluation.vision_score),
            "overall_score": float(interview.evaluation.overall_score),
            "recommendation": interview.evaluation.recommendation,
            "summary": interview.evaluation.summary,
            "created_at": interview.evaluation.created_at.isoformat()
        }

    # Serialize playback / responses details
    responses_data = []
    # Sort responses by the associated question's sort_order
    sorted_responses = sorted(
        interview.responses,
        key=lambda r: r.question.sort_order if r.question else 0
    )
    for resp in sorted_responses:
        responses_data.append({
            "response_id": str(resp.id),
            "question_text": resp.question.question_text if resp.question else None,
            "question_category": resp.question.category if resp.question else None,
            "candidate_transcript": resp.candidate_transcript,
            "bot_transcript": resp.bot_transcript,
            "technical_score": float(resp.technical_score) if resp.technical_score is not None else None,
            "relevance_score": float(resp.relevance_score) if resp.relevance_score is not None else None,
            "communication_score": float(resp.communication_score) if resp.communication_score is not None else None,
            "confidence_score": float(resp.confidence_score) if resp.confidence_score is not None else None,
            "created_at": resp.created_at.isoformat()
        })

    # Fallback to questions list if no responses are recorded yet
    questions_data = []
    if not responses_data:
        sorted_questions = sorted(interview.questions, key=lambda q: q.sort_order)
        for q in sorted_questions:
            questions_data.append({
                "question_text": q.question_text,
                "category": q.category,
                "sort_order": q.sort_order
            })

    return {
        "interview_id": str(interview.id),
        "status": interview.status,
        "created_at": interview.created_at.isoformat(),
        "completed_at": interview.completed_at.isoformat() if interview.completed_at else None,
        "candidate": {
            "name": interview.candidate.name,
            "email": interview.candidate.email,
            "phone": interview.candidate.phone,
        },
        "job": {
            "title": interview.job.title,
            "description": interview.job.description_text
        },
        "evaluation": evaluation_data,
        "responses": responses_data,
        "questions": questions_data
    }

@router.get("/interviews/{interview_id}/report")
async def download_evaluation_report(
    interview_id: UUID, 
    db: AsyncSession = Depends(get_db)
) -> Response:
    """
    Retrieves the final PDF evaluation report from the database and returns it as a downloadable file.
    """
    eval_repo = EvaluationRepository(db)
    evaluation = await eval_repo.get_by_interview(interview_id)
    
    if not evaluation or not evaluation.pdf_report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="PDF evaluation report not found or has not been generated yet."
        )

    # Return the raw PDF bytes as a streaming response
    return Response(
        content=evaluation.pdf_report, 
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=Evaluation_Report_{interview_id}.pdf"
        }
    )

