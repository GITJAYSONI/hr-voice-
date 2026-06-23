from typing import List
from pydantic import BaseModel, EmailStr, Field

class CandidateRegistrationRequest(BaseModel):
    """Schema for handling incoming candidate registration data."""
    name: str = Field(..., description="Candidate's full name")
    email: EmailStr = Field(..., description="Candidate's email address")
    phone: str = Field(..., description="Candidate's phone number")
    job_title: str = Field(..., description="Title of the job applied for")
    job_description: str = Field(..., description="Parsed text of the job description")
    # Note: resume and jd file bytes will be handled separately in the FastAPI route using UploadFile.

class QuestionData(BaseModel):
    """Schema for an individual generated question."""
    category: str = Field(..., description="Category: technical, behavioral, situational, or communication")
    question_text: str = Field(..., description="The interview question text")

class GeneratedQuestions(BaseModel):
    """Schema for parsing the structured JSON output from the LLM."""
    questions: List[QuestionData] = Field(..., description="List of generated questions")

class StructuredEvaluation(BaseModel):
    """Schema for parsing the final LLM interview grading output."""
    technical_score: int = Field(..., description="Technical skill score out of 100")
    communication_score: int = Field(..., description="Communication skill score out of 100")
    behavioral_score: int = Field(..., description="Behavioral / focus score out of 100 based on presence and distractions")
    vision_score: int = Field(..., description="Vision score out of 100 based on posture and eye contact")
    overall_score: int = Field(..., description="Overall average score out of 100")
    feedback: str = Field(..., description="A detailed paragraph analyzing their performance")
    recommendation: str = Field(..., description="Final hiring recommendation: 'Hire', 'Hold', or 'Reject'")


