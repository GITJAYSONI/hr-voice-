from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field
from uuid import UUID

from src.infrastructure.db.database import get_db
from src.infrastructure.db.models import VisionMetric
from src.infrastructure.db.repository import VisionMetricRepository, InterviewRepository

router = APIRouter(prefix="/interviews", tags=["Vision Metrics"])

class VisionMetricRequest(BaseModel):
    eye_contact_score: float = Field(..., ge=0.0, le=1.0, description="Eye contact compliance score between 0 and 1")
    posture_score: float = Field(..., ge=0.0, le=1.0, description="Posture score between 0 and 1")
    presence_detected: bool = Field(..., description="Whether the candidate was present in the frame")
    distraction_event: bool = Field(..., description="Whether a distraction event was detected")
    potential_cheating: bool = Field(..., description="Whether potential cheating behavior was detected")

@router.post("/{interview_id}/vision-metrics", status_code=status.HTTP_201_CREATED)
async def add_vision_metrics(
    interview_id: UUID,
    request: VisionMetricRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Submits continuous candidate behavior/vision metrics (eye contact, posture, etc.)
    recorded during the live interview session.
    """
    interview_repo = InterviewRepository(db)
    interview = await interview_repo.get_by_id(interview_id)
    if not interview:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Interview with ID {interview_id} not found."
        )

    vision_repo = VisionMetricRepository(db)
    metric = VisionMetric(
        interview_id=interview_id,
        eye_contact_score=request.eye_contact_score,
        posture_score=request.posture_score,
        presence_detected=request.presence_detected,
        distraction_event=request.distraction_event,
        potential_cheating=request.potential_cheating
    )

    await vision_repo.add(metric)
    await vision_repo.commit()

    return {"status": "recorded", "message": "Vision metrics saved successfully."}
