from typing import Generic, TypeVar, Type, List, Optional
from uuid import UUID
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.infrastructure.db.models import (
    Candidate,
    Job,
    Interview,
    QuestionBank,
    InterviewResponse,
    VisionMetric,
    Evaluation
)

T = TypeVar("T")

class BaseRepository(Generic[T]):
    """Generic Base Repository containing common async SQLAlchemy operations."""
    def __init__(self, model: Type[T], session: AsyncSession):
        self.model = model
        self.session = session

    async def get_by_id(self, id: UUID) -> Optional[T]:
        result = await self.session.execute(
            select(self.model).filter(self.model.id == id)
        )
        return result.scalars().first()

    async def list(self, skip: int = 0, limit: int = 100) -> List[T]:
        result = await self.session.execute(
            select(self.model).offset(skip).limit(limit)
        )
        return list(result.scalars().all())

    async def add(self, entity: T) -> T:
        self.session.add(entity)
        await self.session.flush()
        return entity

    async def delete(self, entity: T) -> None:
        await self.session.delete(entity)
        await self.session.flush()

    async def commit(self) -> None:
        await self.session.commit()

    async def rollback(self) -> None:
        await self.session.rollback()


class CandidateRepository(BaseRepository[Candidate]):
    def __init__(self, session: AsyncSession):
        super().__init__(Candidate, session)

    async def get_by_email(self, email: str) -> Optional[Candidate]:
        result = await self.session.execute(
            select(Candidate).filter(Candidate.email == email)
        )
        return result.scalars().first()


class JobRepository(BaseRepository[Job]):
    def __init__(self, session: AsyncSession):
        super().__init__(Job, session)


class InterviewRepository(BaseRepository[Interview]):
    def __init__(self, session: AsyncSession):
        super().__init__(Interview, session)

    async def get_with_details(self, id: UUID) -> Optional[Interview]:
        """Loads an interview with eager-loaded relations (Candidate & Job)."""
        result = await self.session.execute(
            select(Interview)
            .filter(Interview.id == id)
            .options(
                selectinload(Interview.candidate),
                selectinload(Interview.job)
            )
        )
        return result.scalars().first()

    async def get_by_candidate_and_job(self, candidate_id: UUID, job_id: UUID) -> Optional[Interview]:
        result = await self.session.execute(
            select(Interview).filter(
                Interview.candidate_id == candidate_id,
                Interview.job_id == job_id
            )
        )
        return result.scalars().first()
    async def get_all(self) -> List[Interview]:
        result = await self.session.execute(
            select(Interview)
            .options(
                selectinload(Interview.candidate),
                selectinload(Interview.job)
            )
            .order_by(Interview.created_at.desc())
        )
        return list(result.scalars().all())


class QuestionBankRepository(BaseRepository[QuestionBank]):
    def __init__(self, session: AsyncSession):
        super().__init__(QuestionBank, session)

    async def get_by_interview_ordered(self, interview_id: UUID) -> List[QuestionBank]:
        """Gets all questions generated for an interview, sorted by sort_order."""
        result = await self.session.execute(
            select(QuestionBank)
            .filter(QuestionBank.interview_id == interview_id)
            .order_by(QuestionBank.sort_order.asc())
        )
        return list(result.scalars().all())


class InterviewResponseRepository(BaseRepository[InterviewResponse]):
    def __init__(self, session: AsyncSession):
        super().__init__(InterviewResponse, session)

    async def get_by_interview(self, interview_id: UUID) -> List[InterviewResponse]:
        result = await self.session.execute(
            select(InterviewResponse)
            .filter(InterviewResponse.interview_id == interview_id)
            .options(selectinload(InterviewResponse.question))
        )
        return list(result.scalars().all())

    async def get_by_question(self, interview_id: UUID, question_id: UUID) -> Optional[InterviewResponse]:
        result = await self.session.execute(
            select(InterviewResponse).filter(
                InterviewResponse.interview_id == interview_id,
                InterviewResponse.question_id == question_id
            )
        )
        return result.scalars().first()


class VisionMetricRepository(BaseRepository[VisionMetric]):
    def __init__(self, session: AsyncSession):
        super().__init__(VisionMetric, session)

    async def get_by_interview(self, interview_id: UUID) -> List[VisionMetric]:
        result = await self.session.execute(
            select(VisionMetric)
            .filter(VisionMetric.interview_id == interview_id)
            .order_by(VisionMetric.recorded_at.asc())
        )
        return list(result.scalars().all())


class EvaluationRepository(BaseRepository[Evaluation]):
    def __init__(self, session: AsyncSession):
        super().__init__(Evaluation, session)

    async def get_by_interview(self, interview_id: UUID) -> Optional[Evaluation]:
        result = await self.session.execute(
            select(Evaluation).filter(Evaluation.interview_id == interview_id)
        )
        return result.scalars().first()
