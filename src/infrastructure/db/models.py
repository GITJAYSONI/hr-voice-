import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, LargeBinary, ForeignKey, DateTime, Boolean, Numeric, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from src.infrastructure.db.database import Base

class Candidate(Base):
    __tablename__ = "candidates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    phone = Column(String(50), nullable=False)
    resume_data = Column(LargeBinary, nullable=False)  # Stores PDF file binary directly
    resume_filename = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    # Relationships
    interviews = relationship("Interview", back_populates="candidate", cascade="all, delete-orphan")


class Job(Base):
    __tablename__ = "jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(255), nullable=False)
    description_text = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    # Relationships
    interviews = relationship("Interview", back_populates="job", cascade="all, delete-orphan")


class Interview(Base):
    __tablename__ = "interviews"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    candidate_id = Column(UUID(as_uuid=True), ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False, index=True)
    job_id = Column(UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    status = Column(String(50), default="scheduled", nullable=False)  # scheduled, active, completed, evaluated
    
    # State Management (Replacing Redis)
    current_question_idx = Column(Integer, default=0, nullable=False)
    total_questions = Column(Integer, default=0, nullable=False)
    
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    candidate = relationship("Candidate", back_populates="interviews")
    job = relationship("Job", back_populates="interviews")
    questions = relationship("QuestionBank", back_populates="interview", cascade="all, delete-orphan")
    responses = relationship("InterviewResponse", back_populates="interview", cascade="all, delete-orphan")
    vision_metrics = relationship("VisionMetric", back_populates="interview", cascade="all, delete-orphan")
    evaluation = relationship("Evaluation", uselist=False, back_populates="interview", cascade="all, delete-orphan")


class QuestionBank(Base):
    __tablename__ = "question_banks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    interview_id = Column(UUID(as_uuid=True), ForeignKey("interviews.id", ondelete="CASCADE"), nullable=False, index=True)
    category = Column(String(50), nullable=False)  # technical, behavioral, situational, communication
    question_text = Column(Text, nullable=False)
    sort_order = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    # Relationships
    interview = relationship("Interview", back_populates="questions")
    responses = relationship("InterviewResponse", back_populates="question", cascade="all, delete-orphan")


class InterviewResponse(Base):
    __tablename__ = "interview_responses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    interview_id = Column(UUID(as_uuid=True), ForeignKey("interviews.id", ondelete="CASCADE"), nullable=False, index=True)
    question_id = Column(UUID(as_uuid=True), ForeignKey("question_banks.id", ondelete="CASCADE"), nullable=False, index=True)
    candidate_transcript = Column(Text, nullable=True)
    bot_transcript = Column(Text, nullable=True)
    technical_score = Column(Numeric(3, 2), nullable=True)
    relevance_score = Column(Numeric(3, 2), nullable=True)
    communication_score = Column(Numeric(3, 2), nullable=True)
    confidence_score = Column(Numeric(3, 2), nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    # Relationships
    interview = relationship("Interview", back_populates="responses")
    question = relationship("QuestionBank", back_populates="responses")


class VisionMetric(Base):
    __tablename__ = "vision_metrics"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    interview_id = Column(UUID(as_uuid=True), ForeignKey("interviews.id", ondelete="CASCADE"), nullable=False, index=True)
    recorded_at = Column(DateTime(timezone=True), default=datetime.utcnow, index=True)
    eye_contact_score = Column(Numeric(3, 2), nullable=True)
    posture_score = Column(Numeric(3, 2), nullable=True)
    presence_detected = Column(Boolean, default=True, nullable=False)
    distraction_event = Column(Boolean, default=False, nullable=False)
    potential_cheating = Column(Boolean, default=False, nullable=False)

    # Relationships
    interview = relationship("Interview", back_populates="vision_metrics")


class Evaluation(Base):
    __tablename__ = "evaluations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    interview_id = Column(UUID(as_uuid=True), ForeignKey("interviews.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    technical_score = Column(Numeric(3, 2), nullable=False)
    communication_score = Column(Numeric(3, 2), nullable=False)
    behavioral_score = Column(Numeric(3, 2), nullable=False)
    vision_score = Column(Numeric(3, 2), nullable=False)
    overall_score = Column(Numeric(3, 2), nullable=False)
    recommendation = Column(String(50), nullable=False)  # strong_hire, hire, consider, reject
    summary = Column(Text, nullable=False)
    pdf_report = Column(LargeBinary, nullable=True)  # PDF report saved directly in database
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    # Relationships
    interview = relationship("Interview", back_populates="evaluation")
