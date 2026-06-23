from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.schemas import CandidateRegistrationRequest
from src.application.use_cases.generate_questions import generate_and_save_questions
from src.infrastructure.db.models import Candidate, Job, Interview
from src.infrastructure.db.repository import (
    CandidateRepository,
    JobRepository,
    InterviewRepository,
    QuestionBankRepository
)

async def register_candidate_use_case(
    session: AsyncSession,
    request: CandidateRegistrationRequest,
    resume_bytes: bytes,
    resume_filename: str
) -> UUID:
    """
    Registers a new candidate, creates the job entry, maps them to an interview,
    and automatically generates the question bank from the resume.
    """
    # 1. Initialize Repositories
    candidate_repo = CandidateRepository(session)
    job_repo = JobRepository(session)
    interview_repo = InterviewRepository(session)
    question_repo = QuestionBankRepository(session)

    # 2. Check if candidate exists, otherwise create
    candidate = await candidate_repo.get_by_email(request.email)
    if not candidate:
        candidate = Candidate(
            name=request.name,
            email=request.email,
            phone=request.phone,
            resume_data=resume_bytes,
            resume_filename=resume_filename
        )
        await candidate_repo.add(candidate)

    # 3. Create Job
    job = Job(
        title=request.job_title,
        description_text=request.job_description
    )
    await job_repo.add(job)

    # Flush to get IDs
    await session.flush()

    # 4. Create Interview
    interview = Interview(
        candidate_id=candidate.id,
        job_id=job.id,
        status="scheduled"
    )
    await interview_repo.add(interview)
    await session.flush()

    # 5. Generate Questions via LLM
    # Note: We are running this inline/awaited here for simplicity. 
    # In a massively high-scale environment, this could be dispatched to a Celery worker.
    await generate_and_save_questions(
        interview_id=interview.id,
        resume_bytes=resume_bytes,
        job_description=request.job_description,
        question_repo=question_repo,
        num_questions=8
    )

    # Update interview state with total questions
    questions_count = len(await question_repo.get_by_interview_ordered(interview.id))
    interview.total_questions = questions_count
    await interview_repo.add(interview)

    # 6. Commit Database Transaction
    await session.commit()

    return interview.id
